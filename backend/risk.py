"""Risk engine -- fusion, smoothing, persistence, context lift, bands.

THE RULE THIS ENCODES: the system never cancels. It only ever adds a verification step,
and a human always clears it. At HOLD the Approve button does not disappear -- it changes
to "Verify caller to continue". The path forward always exists; it costs 30 seconds
instead of zero.

Two guards that answer the false-positive question:
  * low confidence can reach VERIFY but NEVER HOLD
  * thresholds scale with transaction intent (a balance enquiry is not a payout redirect)
"""
from __future__ import annotations
from collections import deque
import numpy as np

from ml.fusion.calibrate import fuse
from ml.types import DetectorResult

BAND_ORDER = ["SAFE", "WATCH", "VERIFY", "HOLD"]
ACTION = {"SAFE": "NONE", "WATCH": "FLAG", "VERIFY": "ADVISE_VERIFY", "HOLD": "HOLD_TRANSACTION"}
RECOMMENDATION = {
    "SAFE": "",
    "WATCH": "Continue. Session flagged for review.",
    "VERIFY": "Ask a shared-knowledge question before proceeding.",
    "HOLD": "Call back on the registered number before releasing this transaction.",
}


class RiskEngine:
    """One instance per live session."""

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.smoothed: float | None = None
        n = cfg["smoothing"]["persist_n"]
        self.history: deque[float] = deque(maxlen=n)
        self.band = "SAFE"
        self.peak = 0

    # ---------------------------------------------------------------- context ---
    def context_score(self, meta: dict) -> float:
        w = self.cfg["context_weights"]
        fri = {"NONE": 0.0, "MEDIUM": 0.5, "HIGH": 0.8, "VERY_HIGH": 1.0}.get(
            str(meta.get("fri_tier", "NONE")).upper(), 0.0)
        cli_bad = 0.0 if str(meta.get("caller_id", "")).startswith("1600") else \
                  (0.0 if meta.get("known_contact") else 1.0)
        drift = float(meta.get("speaker_drift", 0.0))
        kw = min(len(meta.get("keywords", [])) / 3.0, 1.0)
        amt = float(np.clip(float(meta.get("transaction_amount", 0)) / 5_000_000.0, 0, 1))
        return float(np.clip(
            w["fri_tier"] * fri + w["cli_not_1600"] * cli_bad +
            w["speaker_drift"] * drift + w["scam_keywords"] * kw +
            w["amount_tier"] * amt, 0, 1))

    # ------------------------------------------------------------------ score ---
    def step(self, results: dict[str, DetectorResult], quality: dict, meta: dict) -> dict:
        cfg = self.cfg
        det = {k: r.score for k, r in results.items()}
        acoustic = fuse(det, cfg["fusion_weights"])

        # EMA -- stops the meter flickering on stage.
        a = cfg["smoothing"]["ema_alpha"]
        self.smoothed = acoustic if self.smoothed is None else a * acoustic + (1 - a) * self.smoothed
        self.history.append(self.smoothed)

        # K-of-N persistence, NOT a mean. A mean can be gamed by splicing in real
        # speech to dilute the average; K-of-N cannot.
        k = cfg["smoothing"]["persist_k"]
        hold_thr = cfg["bands"]["HOLD"] / 100.0
        persisted = sum(1 for x in self.history if x >= hold_thr) >= k

        ctx = self.context_score(meta)
        rw = cfg["risk_weights"]
        risk01 = float(np.clip(rw["acoustic"] * self.smoothed + rw["context"] * ctx, 0, 1))
        risk = int(round(risk01 * 100))

        # confidence = weighted mean of detector confidences, penalised by audio quality
        conf = float(np.mean([r.confidence for r in results.values()])) if results else 0.5
        if quality.get("enhancement_detected"):
            conf *= 0.5          # enhancement strips the artifacts we rely on
        if quality.get("snr_db", 30) < 12:
            conf *= 0.8
        conf = float(np.clip(conf, 0.05, 1.0))

        band = self._band(risk, meta.get("intent"))

        # GUARD: a low-confidence score may advise, never hold.
        if band == "HOLD":
            if conf < cfg["confidence_floor_for_hold"] or not persisted:
                band = "VERIFY"

        self.band = band
        self.peak = max(self.peak, risk)

        reasons = []
        for r in results.values():
            reasons.extend(r.reasons)
        reasons.sort(key=lambda x: x.weight, reverse=True)

        return {
            "risk": risk, "band": band, "acoustic": round(self.smoothed, 4),
            "context": round(ctx, 4), "confidence": round(conf, 3),
            "detectors": {k: round(v, 4) for k, v in det.items()},
            "reasons": [r.to_dict() for r in reasons[:3]],
        }

    def _band(self, risk: int, intent: str | None) -> str:
        b = dict(self.cfg["bands"])
        it = self.cfg.get("intent_thresholds", {})
        if intent and intent in it:
            # Risk-proportionate: a balance enquiry is almost never interrupted;
            # a payout redirect holds sooner.
            b["HOLD"] = it[intent]
            b["VERIFY"] = min(b["VERIFY"], max(it[intent] - 20, 30))
        if risk >= b["HOLD"]:
            return "HOLD"
        if risk >= b["VERIFY"]:
            return "VERIFY"
        if risk >= b["WATCH"]:
            return "WATCH"
        return "SAFE"


def escalated(prev: str, cur: str) -> bool:
    return BAND_ORDER.index(cur) > BAND_ORDER.index(prev)
