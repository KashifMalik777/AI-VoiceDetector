"""THE SEAM. The backend imports get_detectors() and nothing else from ml/.

This one function is what lets six people work at once. On day 1 it returns stubs;
the system runs end to end anyway -- mic, gate, meter, reasons, alert, hold, ledger.
Swap detectors in one at a time and verify the demo script still runs after each.

A real detector that cannot load falls back to its stub with a loud warning rather
than crashing the demo. Never let a half-wired detector return silent garbage.
"""
from __future__ import annotations
import logging, os
from .types import Detector, DetectorResult, Reason, WindowContext   # noqa: F401 (re-export)

log = logging.getLogger("ml.registry")

# Set SATYAVAANI_FORCE_STUBS=1 to pin stubs (useful on the demo laptop during rehearsal).
FORCE_STUBS = os.getenv("SATYAVAANI_FORCE_STUBS", "") == "1"

_cache: list[Detector] | None = None


def get_detectors(force_reload: bool = False) -> list[Detector]:
    global _cache
    if _cache is not None and not force_reload:
        return _cache

    from .detectors.stub import StubNeural, StubCodec, StubSpeaker
    dets: list[Detector] = []

    # 1. neural ------------------------------------------------------------------
    dets.append(_try("neural", _load_neural, StubNeural))
    # 2. codec (rule-based fallback is built in, so this one always loads) --------
    dets.append(_try("codec", _load_codec, StubCodec))
    # 3. speaker & trajectory -----------------------------------------------------
    dets.append(_try("trajectory", _load_speaker, StubSpeaker))

    _cache = dets
    log.info("detectors: %s", ", ".join(f"{d.name}({type(d).__name__})" for d in dets))
    return dets


def _try(name, loader, stub_cls):
    if FORCE_STUBS:
        log.warning("[%s] STUB (SATYAVAANI_FORCE_STUBS=1)", name)
        return stub_cls()
    try:
        d = loader()
        d.warmup()
        log.info("[%s] real detector loaded", name)
        return d
    except NotImplementedError as e:
        log.warning("[%s] STUB -- %s", name, e)
    except Exception as e:
        log.warning("[%s] STUB -- failed to load real detector: %s", name, e)
    return stub_cls()


def _load_neural():
    from .detectors.neural import NeuralDetector
    return NeuralDetector()


def _load_codec():
    from .detectors.codec import CodecDetector
    return CodecDetector()


def _load_speaker():
    from .detectors.speaker import SpeakerDetector
    return SpeakerDetector()


def model_version() -> str:
    """Stamped on every verdict. A score with no model version is not auditable."""
    dets = get_detectors()
    real = [d.name for d in dets if not type(d).__name__.startswith("Stub")]
    if not real:
        return "stub-v0"
    try:
        from .detectors.neural import MODEL_VERSION
        if "neural" in real:
            return MODEL_VERSION
    except Exception:
        pass
    return "partial-" + "+".join(sorted(real))
