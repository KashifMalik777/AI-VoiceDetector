"""Fusion + Platt calibration.

Calibration matters MORE than discrimination here. In ASVspoof 5 many strong systems
posted minDCF ~= 0.1 with actDCF = 1.0000 -- excellent separation, worthless calibration.
The organisers noted such systems "perform no better than a random coin toss" at their
actual operating point. A system that separates classes but cannot pick a threshold is
undeployable, so we fit Platt scaling and report the minDCF/actDCF gap.

fit_platt() is called offline by data/eval; the coefficients land in config.
"""
from __future__ import annotations
import numpy as np


def sigmoid(z: float) -> float:
    return 1.0 / (1.0 + np.exp(-z))


def fuse(det_scores: dict[str, float], weights: dict[str, float],
         platt: tuple[float, float] = (1.0, 0.0)) -> float:
    """Weighted logit pool, then Platt-scaled to a calibrated probability."""
    num, den = 0.0, 0.0
    for k, s in det_scores.items():
        w = weights.get(k, 0.0)
        if w <= 0:
            continue
        s = min(max(s, 1e-4), 1 - 1e-4)
        num += w * float(np.log(s / (1 - s)))
        den += w
    if den == 0:
        return 0.5
    a, b = platt
    return float(sigmoid(a * (num / den) + b))


def fit_platt(logits: np.ndarray, labels: np.ndarray, iters: int = 200) -> tuple[float, float]:
    """Fit a,b in sigmoid(a*z+b) by Newton steps. labels: 1 = synthetic."""
    a, b = 1.0, 0.0
    for _ in range(iters):
        p = 1.0 / (1.0 + np.exp(-(a * logits + b)))
        g = np.array([np.sum((p - labels) * logits), np.sum(p - labels)])
        w = p * (1 - p) + 1e-9
        H = np.array([[np.sum(w * logits ** 2), np.sum(w * logits)],
                      [np.sum(w * logits), np.sum(w)]]) + 1e-6 * np.eye(2)
        step = np.linalg.solve(H, g)
        a, b = a - step[0], b - step[1]
        if np.linalg.norm(step) < 1e-8:
            break
    return float(a), float(b)


# ---- metrics the panel expects. Report ALL of these, not accuracy. ---------------

def eer(scores: np.ndarray, labels: np.ndarray) -> float:
    """Equal error rate. Convention (matches dcf/far_at_frr): label 1 = spoof,
    higher score = more spoof. FAR = genuine accepted as spoof (score >= t);
    FRR = spoof rejected as genuine (score < t). EER is where FAR == FRR."""
    scores = np.asarray(scores, float)
    labels = np.asarray(labels)
    pos = scores[labels == 1]          # spoof
    neg = scores[labels == 0]          # genuine
    if pos.size == 0 or neg.size == 0:
        return float("nan")
    thr = np.unique(scores)
    far = np.array([np.mean(neg >= t) for t in thr])   # false accept
    frr = np.array([np.mean(pos < t) for t in thr])    # false reject
    i = int(np.nanargmin(np.abs(far - frr)))
    return float((far[i] + frr[i]) / 2)


def dcf(scores: np.ndarray, labels: np.ndarray, beta: float = 1.90,
        threshold: float | None = None) -> float:
    """ASVspoof 5 DCF. beta ~ 1.90 penalises rejecting a genuine caller ~1.9x a missed spoof.

    threshold=None -> minDCF (oracle sweep).
    threshold given -> actDCF (a threshold fixed IN ADVANCE). The gap IS deployment risk.
    """
    def at(t):
        miss = float(np.mean(scores[labels == 1] < t)) if (labels == 1).any() else 0.0
        fa = float(np.mean(scores[labels == 0] >= t)) if (labels == 0).any() else 0.0
        return beta * miss + fa
    if threshold is not None:
        return at(threshold)
    return float(min(at(t) for t in np.unique(scores)))


def c_llr(scores: np.ndarray, labels: np.ndarray) -> float:
    """Log-likelihood-ratio cost. ~1.0 means the scores carry no usable calibration."""
    s = np.clip(scores, 1e-6, 1 - 1e-6)
    llr = np.log(s / (1 - s))
    t = llr[labels == 1]
    n = llr[labels == 0]
    if t.size == 0 or n.size == 0:
        return float("nan")
    return float((np.mean(np.log2(1 + np.exp(-t))) + np.mean(np.log2(1 + np.exp(n)))) / 2)


def far_at_frr(scores: np.ndarray, labels: np.ndarray, target_frr: float = 0.01) -> float:
    """The business operating point: false accepts when we reject 1% of genuine callers."""
    gen = np.sort(scores[labels == 0])
    if gen.size == 0:
        return float("nan")
    t = float(np.quantile(gen, 1 - target_frr))
    return float(np.mean(scores[labels == 1] < t)) if (labels == 1).any() else float("nan")
