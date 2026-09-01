"""Day-1 stub detectors. Plausible, deterministic-ish, wrong on purpose.

These exist so the ENTIRE system runs end to end on day one -- mic, stream, gate,
meter, reasons, alert, hold, ledger -- while the real detectors are still being built.
From that point the team is only ever IMPROVING a working system, never assembling one.

Replace one at a time. Verify the demo script still runs after each swap.
"""
from __future__ import annotations
import time, math, random
import numpy as np
from ..types import DetectorResult, Reason, WindowContext


class _Stub:
    """Score drifts on a slow sine plus noise so the meter looks alive, not random."""
    name = "stub"
    _reasons: list[tuple[str, str]] = []
    _phase = 0.0

    def __init__(self, name: str, bias: float = 0.0, seed: int = 0):
        self.name = name
        self.bias = bias
        self._rng = random.Random(seed)
        self._t = 0

    def warmup(self) -> None:
        pass

    def score_window(self, pcm: np.ndarray, sr: int, ctx: WindowContext) -> DetectorResult:
        t0 = time.perf_counter()
        self._t += 1
        # Loud, energetic audio drifts the stub upward -- makes a played clip read
        # differently from a quiet room, which is enough to rehearse the demo with.
        energy = float(np.sqrt(np.mean(pcm.astype(np.float64) ** 2))) if pcm.size else 0.0
        drift = 0.5 + 0.35 * math.sin(self._t / 7.0 + self.bias)
        s = 0.55 * drift + 0.35 * min(energy * 6.0, 1.0) + 0.10 * self._rng.random()
        s = float(min(max(s + self.bias * 0.1, 0.02), 0.98))
        reasons = [Reason(c, l, round(0.15 + 0.2 * self._rng.random(), 2))
                   for c, l in self._reasons[:2]]
        return DetectorResult(
            score=s,
            confidence=0.55 + 0.3 * self._rng.random(),
            reasons=reasons,
            latency_ms=(time.perf_counter() - t0) * 1000.0,
        )


class StubNeural(_Stub):
    _reasons = [
        ("STUB_NEURAL", "[STUB] neural detector not yet wired -- ml/detectors/neural.py"),
        ("HF_ROLLOFF", "Energy collapses above 7.2 kHz"),
    ]
    def __init__(self): super().__init__("neural", bias=0.05, seed=11)


class StubCodec(_Stub):
    _reasons = [
        ("STUB_CODEC", "[STUB] codec detector not yet wired -- ml/detectors/codec.py"),
        ("CODEC_FINGERPRINT", "Neural codec signature consistent with vocoder resynthesis"),
    ]
    def __init__(self): super().__init__("codec", bias=-0.03, seed=22)


class StubSpeaker(_Stub):
    _reasons = [
        ("STUB_SPEAKER", "[STUB] speaker detector not yet wired -- ml/detectors/speaker.py"),
        ("SPEAKER_DRIFT", "Voice differs from enrolled reference"),
    ]
    def __init__(self): super().__init__("trajectory", bias=0.0, seed=33)
