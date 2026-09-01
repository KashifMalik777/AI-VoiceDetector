"""WebSocket hub -- the live path.

Audio in: binary Float32LE @16 kHz mono, 1 s per frame.
Scoring:  rolling 4 s window, re-scored every 1 s hop.

WHY 4 s / 1 s: 4 s is the de facto standard across the literature and sub-second
windows cannot observe the features that matter; a 1 s hop keeps the meter live.
First verdict lands ~4.4 s into a call, then refreshes with ~1.4 s lag.
"""
from __future__ import annotations
import asyncio, json, time, uuid, logging, datetime as dt
import numpy as np
from fastapi import WebSocket, WebSocketDisconnect

from ml.registry import get_detectors, model_version
from ml.types import WindowContext
from ml import gate
from ml.features.spectral import extract
from . import config as cfgmod
from .db import SessionLocal, Session as DbSession, Frame, Alert
from .risk import RiskEngine, escalated, ACTION, RECOMMENDATION
from . import audit

log = logging.getLogger("ws")

SR = 16000
WINDOW_S = 4.0
HOP_S = 1.0
WINDOW_N = int(SR * WINDOW_S)


class LiveSession:
    def __init__(self, session_id: str):
        self.id = session_id
        self.buf = np.zeros(0, dtype=np.float32)
        self.seq = 0
        self.t_ms = 0
        self.meta: dict = {}
        self.cfg = cfgmod.get()
        self.engine = RiskEngine(self.cfg)
        self.frames = 0
        self.abstained = 0
        self.prev_band = "SAFE"
        self.enrolled = None
        self.noise = gate.NoiseTracker()

    def push(self, pcm: np.ndarray):
        self.buf = np.concatenate([self.buf, pcm])[-WINDOW_N * 2:]

    def ready(self) -> bool:
        return len(self.buf) >= int(SR * HOP_S)

    def window(self) -> np.ndarray:
        return self.buf[-WINDOW_N:] if len(self.buf) >= WINDOW_N else self.buf


async def handle(ws: WebSocket, session_id: str):
    await ws.accept()
    live = LiveSession(session_id)
    _ensure_session_row(session_id)
    dets = get_detectors()
    mv = model_version()
    log.info("session %s open (detectors: %s)", session_id,
             ", ".join(type(d).__name__ for d in dets))

    try:
        while True:
            msg = await ws.receive()
            if msg.get("type") == "websocket.disconnect":
                break

            if (b := msg.get("bytes")) is not None:
                pcm = np.frombuffer(b, dtype="<f4").astype(np.float32)
                if pcm.size == 0:
                    continue
                live.push(pcm)
                live.t_ms += int(1000 * pcm.size / SR)
                if live.ready():
                    out = await asyncio.get_event_loop().run_in_executor(
                        None, _score, live, dets, mv)
                    await ws.send_text(json.dumps(out["score"]))
                    if out.get("alert"):
                        await ws.send_text(json.dumps(out["alert"]))

            elif (t := msg.get("text")) is not None:
                try:
                    data = json.loads(t)
                except Exception:
                    continue
                k = data.get("type")
                if k == "start":
                    live.meta.update(data.get("meta") or {})
                    live.cfg = cfgmod.get()
                    live.engine = RiskEngine(live.cfg)
                elif k == "context":
                    live.meta.update({x: y for x, y in data.items() if x != "type"})
                elif k == "stop":
                    break
    except WebSocketDisconnect:
        pass
    except Exception as e:
        log.exception("session %s error: %s", session_id, e)
    finally:
        _close_session(live)
        log.info("session %s closed (%d frames, %d abstained, peak %d)",
                 session_id, live.frames, live.abstained, live.engine.peak)


def _score(live: LiveSession, dets, mv: str) -> dict:
    live.seq += 1
    w = live.window()

    quality = gate.analyse(w, SR, tracker=live.noise)
    ok, reason, detail = gate.check(quality)
    if len(w) < WINDOW_N and ok:
        ok, reason, detail = False, "BUFFER_WARMING", \
            f"{len(w)/SR:.1f} s buffered; {WINDOW_S:.0f} s window needed"

    # ---- ABSTAIN: say so instead of guessing. Never escalates. -------------------
    if not ok:
        live.abstained += 1
        _persist_frame(live, state="ABSTAIN", quality=quality, mv=mv)
        return {"score": {"type": "score", "seq": live.seq, "t_ms": live.t_ms,
                          "state": "ABSTAIN", "reason": reason, "detail": detail,
                          "quality": quality}}

    ctx = WindowContext(seq=live.seq, t_ms=live.t_ms, sr=SR,
                        net_speech_s=quality["net_speech_s"], snr_db=quality["snr_db"],
                        pkt_loss=quality["pkt_loss"],
                        enhancement_detected=quality["enhancement_detected"],
                        enrolled_embedding=live.enrolled)

    results = {}
    for d in dets:
        try:
            results[d.name] = d.score_window(w, SR, ctx)
        except Exception as e:
            log.warning("detector %s failed: %s", d.name, e)

    r = live.engine.step(results, quality, live.meta)
    live.frames += 1

    feats = extract(w, SR)
    _persist_frame(live, state="SCORED", quality=quality, mv=mv, r=r, feats=feats)

    payload = {
        "type": "score", "seq": live.seq, "t_ms": live.t_ms, "state": "SCORED",
        "risk": r["risk"], "band": r["band"],
        "scores": {
            "synthetic": r["acoustic"],
            "replay": round(results.get("codec").score * 0.4, 3) if "codec" in results else 0.0,
            "speaker": {"enrolled": live.enrolled is not None,
                        "similarity": None, "match": None},
        },
        "context": r["context"], "confidence": r["confidence"],
        "quality": quality, "detectors": r["detectors"], "reasons": r["reasons"],
        "model_version": mv,
    }

    out = {"score": payload}
    if escalated(live.prev_band, r["band"]):
        out["alert"] = _raise_alert(live, r)
    live.prev_band = r["band"]
    return out


def _raise_alert(live: LiveSession, r: dict) -> dict:
    aid = "a_" + uuid.uuid4().hex[:6]
    ts = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    payload = {"type": "alert", "alert_id": aid, "seq": live.seq, "risk": r["risk"],
               "band": r["band"], "action": ACTION[r["band"]],
               "recommendation": RECOMMENDATION[r["band"]], "ts": ts}
    db = SessionLocal()
    try:
        db.add(Alert(id=aid, session_id=live.id, seq=live.seq, risk=r["risk"],
                     band=r["band"], action=ACTION[r["band"]],
                     recommendation=RECOMMENDATION[r["band"]]))
        db.commit()
    finally:
        db.close()
    audit.append("ALERT", {"alert_id": aid, "session": live.id, "risk": r["risk"],
                           "band": r["band"], "reasons": r["reasons"]})
    return payload


def _persist_frame(live, state, quality, mv, r=None, feats=None):
    db = SessionLocal()
    try:
        db.add(Frame(session_id=live.id, seq=live.seq, t_ms=live.t_ms, state=state,
                     risk=(r or {}).get("risk"), band=(r or {}).get("band"),
                     acoustic=(r or {}).get("acoustic"), context=(r or {}).get("context"),
                     confidence=(r or {}).get("confidence"),
                     detectors_json=json.dumps((r or {}).get("detectors", {})),
                     quality_json=json.dumps(quality),
                     reasons_json=json.dumps((r or {}).get("reasons", [])),
                     features_json=json.dumps(feats or {}),   # features, never audio
                     model_version=mv))
        db.commit()
    finally:
        db.close()


def _ensure_session_row(sid: str):
    db = SessionLocal()
    try:
        if not db.get(DbSession, sid):
            db.add(DbSession(id=sid))
            db.commit()
    finally:
        db.close()


def _close_session(live: LiveSession):
    db = SessionLocal()
    try:
        s = db.get(DbSession, live.id)
        if s:
            s.ended_at = dt.datetime.now(dt.timezone.utc)
            s.peak_risk = live.engine.peak
            s.final_band = live.engine.band
            s.frames = live.frames
            s.abstained = live.abstained
            s.meta_json = json.dumps(live.meta)
            db.commit()
    finally:
        db.close()
