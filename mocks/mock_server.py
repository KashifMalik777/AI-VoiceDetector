#!/usr/bin/env python3
"""Mock server -- serves contracts/fixtures on the REAL routes, with realistic timing.

RULE 02: mock server before real server. The frontend points here on day one and is
never blocked waiting for the backend or ML. Swap the base URL when the real server
is up; nothing else changes, because both honour contracts/.

    python mocks/mock_server.py          # http://localhost:8000

Stdlib only -- no install, runs anywhere, on any laptop, in ten seconds.
"""
from __future__ import annotations
import json, threading, time, math, random, http.server, socketserver, urllib.parse
from pathlib import Path

ROOT = Path(__file__).parent.parent
FX = ROOT / "contracts" / "fixtures"
PORT = 8000


def fx(name):
    return json.loads((FX / name).read_text())


class Handler(http.server.BaseHTTPRequestHandler):
    def _send(self, obj, code=200):
        body = json.dumps(obj, indent=2).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send({})

    def do_GET(self):
        p = urllib.parse.urlparse(self.path).path
        time.sleep(0.05 + random.random() * 0.1)          # realistic latency
        if p == "/health":
            return self._send({"ok": True, "model_version": "mock-v0", "mock": True,
                               "detectors": [{"name": n, "impl": "Mock", "stub": True}
                                             for n in ("neural", "codec", "trajectory")]})
        if p == "/api/metrics/model":
            return self._send(fx("metrics.json"))
        if p == "/api/config":
            return self._send(fx("config.json"))
        if p.startswith("/api/sessions/"):
            return self._send({"session": fx("session.json"), "timeline": _timeline()})
        if p == "/api/sessions":
            return self._send({"sessions": [fx("session.json")]})
        if p == "/api/alerts":
            return self._send({"alerts": [fx("alert.json")]})
        if p == "/api/audit/verify":
            return self._send({"ok": True, "length": 3, "broken_at": None,
                               "detail": "chain intact", "head": "mock" + "0" * 60})
        if p == "/api/audit/entries":
            return self._send({"entries": [
                {"idx": 1, "kind": "ALERT", "ts": "2026-08-28T17:04:11Z",
                 "payload": {"alert_id": "a_7f2c", "risk": 78, "band": "HOLD"},
                 "prev_hash": "0000000000000000...", "hash": "9c1f0a2b3d4e5f60..."}]})
        return self._send({"error": "no mock for " + p}, 404)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        self.rfile.read(n)
        p = urllib.parse.urlparse(self.path).path
        time.sleep(0.1)
        if p == "/api/sessions":
            return self._send({"session_id": "s_mock01"})
        if p == "/api/analyze":
            tl = _timeline()
            return self._send({"filename": "mock.wav", "duration_s": 47.0,
                               "windows": len(tl), "abstained": 3, "abstain_rate": 0.064,
                               "peak_risk": 78, "final_band": "HOLD",
                               "model_version": "mock-v0", "timeline": tl})
        if p == "/api/enroll":
            return self._send({"voiceprint_id": "vp_mock01", "name": "mock", "dims": 256})
        if p.endswith("/override"):
            return self._send({"id": "a_7f2c", "overridden": True,
                               "override_reason": "verified by call-back",
                               "override_by": "officer", "ledger_hash": "ab12cd34"})
        return self._send({"ok": True})

    do_PUT = do_POST

    def log_message(self, fmt, *a):
        print(f"  mock  {self.command:5} {self.path}")


def _timeline():
    """A realistic score arc: green, then a clone plays at ~30 s and it climbs to HOLD."""
    out = []
    for i in range(1, 48):
        t = i * 1000
        if i <= 3:
            out.append({"seq": i, "t_ms": t, "state": "ABSTAIN",
                        "reason": "BUFFER_WARMING",
                        "detail": f"{i:.1f} s buffered; 4 s window needed",
                        "quality": {"net_speech_s": i * 0.8, "snr_db": 22.0,
                                    "pkt_loss": 0.0, "enhancement_detected": False}})
            continue
        base = 0.10 if i < 30 else min(0.10 + (i - 30) * 0.09, 0.92)
        risk = int(min(base * 100 + math.sin(i / 3) * 3, 96))
        band = "HOLD" if risk >= 75 else "VERIFY" if risk >= 55 else "WATCH" if risk >= 30 else "SAFE"
        src = fx("score_hold.json") if risk >= 55 else fx("score_safe.json")
        out.append({"seq": i, "t_ms": t, "state": "SCORED", "risk": risk, "band": band,
                    "confidence": 0.86, "context": 0.44 if i >= 30 else 0.05,
                    "detectors": src["detectors"], "reasons": src["reasons"],
                    "quality": src["quality"]})
    return out


class Reuse(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    print("=" * 62)
    print("  MOCK SERVER -- fixtures from contracts/, real routes, fake data")
    print(f"  http://localhost:{PORT}    (Ctrl-C to stop)")
    print("  Frontend can build against this all of day 1.")
    print("=" * 62)
    with Reuse(("", PORT), Handler) as httpd:
        httpd.serve_forever()
