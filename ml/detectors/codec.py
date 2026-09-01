"""Codec & channel detector -- LightGBM over engineered features.

Reframed from "spectral heuristics" into something with a real justification:
modern TTS is itself codec-based (Encodec / SNAC / DAC), so codec artifacts are
SIMULTANEOUSLY the attack signature and the channel noise. Separating the two is
the actual discriminative task.

Runs in <10 ms on CPU. Feature importances feed the reasons panel for free.
Also the safety net if the neural pass is too slow on the demo laptop.

TO ACTIVATE: train a LightGBM model into ml/onnx/codec_lgbm.txt, then flip
USE_TRAINED = True. Until then this returns a calibrated rule-based score so the
pipeline is never blocked.
"""
from __future__ import annotations
import time, os
import numpy as np
from ..types import DetectorResult, Reason, WindowContext
from ..features.spectral import extract, as_vector, FEATURE_NAMES

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "onnx", "codec_lgbm.txt")
USE_TRAINED = False


class CodecDetector:
    name = "codec"

    def __init__(self):
        self._booster = None

    def warmup(self) -> None:
        if USE_TRAINED and os.path.exists(MODEL_PATH):
            import lightgbm as lgb
            self._booster = lgb.Booster(model_file=MODEL_PATH)

    def score_window(self, pcm: np.ndarray, sr: int, ctx: WindowContext) -> DetectorResult:
        t0 = time.perf_counter()
        f = extract(pcm, sr)

        if self._booster is not None:
            p = float(self._booster.predict(as_vector(f).reshape(1, -1))[0])
            reasons = self._reasons_from_importance(f)
        else:
            p, reasons = self._rule_score(f, sr)

        return DetectorResult(
            score=float(min(max(p, 0.01), 0.99)),
            confidence=0.55 if self._booster is None else 0.85,
            reasons=reasons,
            latency_ms=(time.perf_counter() - t0) * 1000.0,
        )

    # --- interim rule-based scoring, replaced by the booster on day 2 -------------
    def _rule_score(self, f: dict, sr: int):
        reasons: list[Reason] = []
        score = 0.0

        # Vocoders lose high-band detail. Real speech through a decent mic keeps some.
        hf = f["hf_ratio_7k"]
        if hf < 0.004:
            w = min((0.004 - hf) / 0.004, 1.0)
            score += 0.40 * w
            reasons.append(Reason("HF_ROLLOFF",
                f"Energy collapses above 7 kHz ({hf*100:.2f}% of total)", round(0.40 * w, 2)))

        # Synthesis flattens fine spectral structure.
        fl = f["flatness"]
        if fl > 0.30:
            w = min((fl - 0.30) / 0.40, 1.0)
            score += 0.25 * w
            reasons.append(Reason("SPECTRAL_FLATNESS",
                f"Spectral fine structure unusually flat ({fl:.2f})", round(0.25 * w, 2)))

        # Unnaturally steep or shallow spectral tilt.
        sl = abs(f["band_slope"])
        if sl > 1.2:
            w = min((sl - 1.2) / 2.0, 1.0)
            score += 0.20 * w
            reasons.append(Reason("SPECTRAL_TILT",
                f"Spectral tilt outside the natural range ({f['band_slope']:.2f})", round(0.20 * w, 2)))

        # Low frame-to-frame variability -- resynthesis is smoother than a real room.
        if f["flux_std"] < 0.02:
            score += 0.15
            reasons.append(Reason("LOW_SPECTRAL_FLUX",
                "Frame-to-frame spectral variation below natural speech", 0.15))

        if not reasons:
            reasons.append(Reason("NO_CODEC_ARTIFACT",
                "No neural-codec resynthesis signature in this window", 0.30))

        return min(score, 0.95), reasons[:3]

    def _reasons_from_importance(self, f: dict):
        imp = self._booster.feature_importance(importance_type="gain")
        order = np.argsort(imp)[::-1][:3]
        out = []
        for i in order:
            k = FEATURE_NAMES[i]
            out.append(Reason(f"FEAT_{k.upper()}",
                              f"{k.replace('_',' ')} = {f.get(k,0.0):.3f}",
                              round(float(imp[i] / (imp.sum() + 1e-9)), 2)))
        return out
