"""Speaker & trajectory detector -- the one that catches live voice conversion.

THIS SLOT USED TO BE PROSODY. Prosody was removed as a decision rule because:
  * ElevenLabs v3 produces breathing on demand via [exhales] audio tags
  * humans breathe 8-14/min = one breath every 4-7 s, unobservable in short windows
  * the best prosody-only paper: 93% accuracy but 24.7% EER, and 18.92% on expressive TTS
  * MOST IMPORTANTLY: in a live voice-conversion attack a REAL HUMAN is speaking.
    Real lungs, real prosody, real timing. Only timbre is synthetic. Every prosody
    signal correctly answers "human" and passes the attacker.

Voice conversion changes TIMBRE -- which is exactly what a speaker embedding measures.
So this detector does two things:

  1. SPEAKER DRIFT   cosine distance of an ECAPA/Resemblyzer embedding vs the enrolled
                     reference. Catches live VC.
  2. TRAJECTORY      genuine speech traces smooth paths through embedding space; spliced
                     or neurally-edited segments cause abrupt disruptions. TRAINING-FREE,
                     which is why it is affordable on day 2. Targets the realistic hybrid
                     attack: a human on live VC who injects a short synthetic span only
                     for the account number.

Prosody survives here ONLY as a low-weight auxiliary feature. Never a headline reason.
"""
from __future__ import annotations
import time, os
from collections import deque
import numpy as np
from ..types import DetectorResult, Reason, WindowContext

EMBEDDER_READY = True         # speechbrain / resemblyzer is installed
TRAJ_WINDOW = 8               # embeddings kept for trajectory analysis
DRIFT_MATCH_THRESHOLD = 0.62  # cosine above this = same speaker (tune on our own voices)


class SpeakerDetector:
    name = "trajectory"

    def __init__(self):
        self._enc = None
        self._traj: deque[np.ndarray] = deque(maxlen=TRAJ_WINDOW)

    def available(self) -> bool:
        return EMBEDDER_READY

    def warmup(self) -> None:
        if not EMBEDDER_READY:
            raise NotImplementedError(
                "Speaker embedder not wired. pip install resemblyzer (or speechbrain), "
                "then set EMBEDDER_READY = True in ml/detectors/speaker.py")
        from resemblyzer import VoiceEncoder
        self._enc = VoiceEncoder("cpu")

    def score_window(self, pcm: np.ndarray, sr: int, ctx: WindowContext) -> DetectorResult:
        t0 = time.perf_counter()
        emb = self._embed(pcm, sr)
        reasons: list[Reason] = []
        score, weights = 0.0, 0.0

        # --- 1. drift vs enrolled reference (catches live voice conversion) --------
        if ctx.enrolled_embedding is not None:
            cos = _cos(emb, ctx.enrolled_embedding)
            drift = float(np.clip((DRIFT_MATCH_THRESHOLD - cos) / DRIFT_MATCH_THRESHOLD, 0, 1))
            score += 0.65 * drift
            weights += 0.65
            if cos < DRIFT_MATCH_THRESHOLD:
                reasons.append(Reason("SPEAKER_DRIFT",
                    f"Voice differs from enrolled reference (cos {cos:.2f})",
                    round(0.65 * drift, 2)))
            else:
                reasons.append(Reason("SPEAKER_MATCH",
                    f"Voice matches enrolled reference (cos {cos:.2f})", 0.40))

        # --- 2. trajectory smoothness (catches partial splices / neural edits) -----
        self._traj.append(emb)
        if len(self._traj) >= 4:
            steps = [1.0 - _cos(self._traj[i], self._traj[i - 1])
                     for i in range(1, len(self._traj))]
            med = float(np.median(steps))
            last = steps[-1]
            if med > 1e-6 and last > med * 3.0:
                jump = float(np.clip(last / (med * 6.0), 0, 1))
                score += 0.35 * jump
                weights += 0.35
                reasons.append(Reason("TRAJECTORY_BREAK",
                    "Abrupt discontinuity in speaker-embedding trajectory "
                    "(consistent with a spliced or edited segment)", round(0.35 * jump, 2)))
            else:
                weights += 0.35

        p = float(score / weights) if weights > 0 else 0.5
        conf = 0.85 if ctx.enrolled_embedding is not None else 0.45
        if not reasons:
            reasons.append(Reason("SPEAKER_STABLE",
                "Speaker identity stable across the window", 0.25))

        return DetectorResult(score=min(max(p, 0.01), 0.99), confidence=conf,
                              reasons=reasons[:3],
                              latency_ms=(time.perf_counter() - t0) * 1000.0)

    def _embed(self, pcm: np.ndarray, sr: int) -> np.ndarray:
        from resemblyzer import preprocess_wav
        return self._enc.embed_utterance(preprocess_wav(pcm.astype(np.float32), source_sr=sr))

    def reset(self) -> None:
        self._traj.clear()


def _cos(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))
