"""Engineered spectral / codec features. numpy+scipy only -- runs on any laptop, ~5 ms.

These become the codec & channel detector's inputs AND the explainability panel:
LightGBM feature importances translate directly into officer-readable reasons.
"""
from __future__ import annotations
import numpy as np
from scipy import signal as sps

FEATURE_NAMES = [
    "centroid", "bandwidth", "rolloff85", "rolloff95", "flatness",
    "zcr", "hf_ratio_7k", "hf_ratio_6k", "lf_ratio_300",
    "flux_mean", "flux_std", "hnr_proxy", "crest", "spread_db",
    "band_slope", "band_kurtosis",
]


def _stft(pcm: np.ndarray, sr: int, n: int = 512):
    f, _, Z = sps.stft(pcm, fs=sr, nperseg=n, noverlap=n // 2, window="hann")
    S = np.abs(Z) + 1e-12
    return f, S


def extract(pcm: np.ndarray, sr: int = 16000) -> dict[str, float]:
    """Return a flat dict of features. Keys are stable -- they are the contract
    with whoever trains the LightGBM model."""
    if pcm.size < sr // 4:
        return {k: 0.0 for k in FEATURE_NAMES}

    pcm = pcm.astype(np.float64)
    f, S = _stft(pcm, sr)
    P = S ** 2
    tot = P.sum(axis=0) + 1e-12
    fv = f[:, None]

    centroid = float(np.mean((fv * P).sum(axis=0) / tot))
    bandwidth = float(np.mean(np.sqrt(((fv - centroid) ** 2 * P).sum(axis=0) / tot)))

    csum = np.cumsum(P, axis=0) / tot
    roll85 = float(np.mean(f[np.argmax(csum >= 0.85, axis=0)]))
    roll95 = float(np.mean(f[np.argmax(csum >= 0.95, axis=0)]))

    # Spectral flatness: the classic vocoder tell -- synthesis flattens fine structure.
    flatness = float(np.mean(np.exp(np.mean(np.log(S), axis=0)) / (np.mean(S, axis=0) + 1e-12)))

    zcr = float(np.mean(np.abs(np.diff(np.sign(pcm))) > 0))

    def band_ratio(lo, hi):
        m = (f >= lo) & (f < hi)
        return float(P[m].sum() / (P.sum() + 1e-12))

    # THE headline feature: vocoders systematically lose detail above ~7 kHz.
    hf7 = band_ratio(7000, sr / 2)
    hf6 = band_ratio(6000, sr / 2)
    lf3 = band_ratio(0, 300)

    flux = np.sqrt(np.sum(np.diff(S, axis=1) ** 2, axis=0))
    flux_mean, flux_std = float(flux.mean()), float(flux.std())

    # Harmonic-to-noise proxy via autocorrelation peak (cheap stand-in for praat HNR).
    # FFT-based: np.correlate(mode="full") is O(n^2) and costs ~750 ms on a 4 s window.
    # This was caught by scripts/bench_rtf.py on day 1 -- exactly why that benchmark exists.
    x = pcm - pcm.mean()
    nfft = 1 << int(np.ceil(np.log2(2 * len(x))))
    X = np.fft.rfft(x, nfft)
    ac = np.fft.irfft(X * np.conj(X), nfft)[: len(x)]
    ac /= (ac[0] + 1e-12)
    lo, hi = int(sr / 400), int(sr / 60)          # 60-400 Hz pitch range
    hnr = float(ac[lo:hi].max()) if hi < len(ac) else 0.0

    rms = float(np.sqrt(np.mean(pcm ** 2)) + 1e-12)
    crest = float(np.max(np.abs(pcm)) / rms)

    db = 20 * np.log10(np.sqrt(np.mean(S ** 2, axis=0)) + 1e-12)
    spread_db = float(np.percentile(db, 90) - np.percentile(db, 10))

    logS = np.log(np.mean(S, axis=1) + 1e-12)
    slope = float(np.polyfit(f, logS, 1)[0]) * 1000.0
    kurt = float(((logS - logS.mean()) ** 4).mean() / ((logS.var() + 1e-12) ** 2))

    return {
        "centroid": centroid, "bandwidth": bandwidth,
        "rolloff85": roll85, "rolloff95": roll95, "flatness": flatness,
        "zcr": zcr, "hf_ratio_7k": hf7, "hf_ratio_6k": hf6, "lf_ratio_300": lf3,
        "flux_mean": flux_mean, "flux_std": flux_std, "hnr_proxy": hnr,
        "crest": crest, "spread_db": spread_db,
        "band_slope": slope, "band_kurtosis": kurt,
    }


def as_vector(feats: dict[str, float]) -> np.ndarray:
    return np.array([feats.get(k, 0.0) for k in FEATURE_NAMES], dtype=np.float32)
