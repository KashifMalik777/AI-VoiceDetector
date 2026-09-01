"""The frozen ML seam. Backend imports get_detectors() and NOTHING else from ml/.

Do not change these shapes without changing contracts/schemas.json and telling everyone.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol, Optional
import numpy as np


@dataclass
class Reason:
    code: str
    label: str
    weight: float

    def to_dict(self) -> dict:
        return {"code": self.code, "label": self.label, "weight": round(self.weight, 3)}


@dataclass
class DetectorResult:
    score: float                       # 0..1, where 1 = synthetic
    confidence: float                  # 0..1
    reasons: list[Reason] = field(default_factory=list)
    latency_ms: float = 0.0
    abstain: bool = False              # this detector alone declines to score


@dataclass
class WindowContext:
    """Everything a detector may need besides the audio itself."""
    seq: int
    t_ms: int
    sr: int = 16000
    net_speech_s: float = 0.0
    snr_db: float = 0.0
    pkt_loss: float = 0.0
    enhancement_detected: bool = False
    enrolled_embedding: Optional[np.ndarray] = None


class Detector(Protocol):
    name: str
    def warmup(self) -> None: ...
    def score_window(self, pcm: np.ndarray, sr: int, ctx: WindowContext) -> DetectorResult: ...
