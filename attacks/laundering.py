#!/usr/bin/env python3
"""Audio laundering — the cheapest attack, and the one a judge can run with sox.

Published: AASIST goes 0.83% -> 58.9% EER at RT60 0.9 s. MP3 @16 kbit/s pushed another
detector to 55.4%. Even a resample to 44.1 kHz took RawGAT-ST from 1.06% to 39.6%.

Use this BOTH ways:
  * as an eval set   -> report our degraded numbers honestly
  * as augmentation  -> train through it so the degradation shrinks

    python attacks/laundering.py IN_DIR OUT_DIR [--only reverb,noise,clip]
"""
from __future__ import annotations
import sys, argparse
from pathlib import Path
import numpy as np

SR = 16000


def _rir(rt60=0.9, sr=SR, n=None):
    """Synthetic exponential-decay room impulse response."""
    n = n or int(sr * rt60 * 1.2)
    t = np.arange(n) / sr
    return (np.random.randn(n) * np.exp(-6.9078 * t / rt60)).astype(np.float32)


def reverb(x, rt60=0.9, sr=SR):
    h = _rir(rt60, sr)
    y = np.convolve(x, h)[: len(x)]
    return (0.7 * y / (np.max(np.abs(y)) + 1e-9) + 0.3 * x).astype(np.float32)


def add_noise(x, snr_db=0.0):
    p = np.mean(x ** 2) + 1e-12
    n = np.random.randn(len(x))
    n *= np.sqrt(p / (10 ** (snr_db / 10)) / (np.mean(n ** 2) + 1e-12))
    return (x + n).astype(np.float32)


def clip_distort(x, ceil=0.35):
    return np.clip(x, -ceil, ceil).astype(np.float32)


def resample_roundtrip(x, via=44100, sr=SR):
    up = np.interp(np.linspace(0, len(x) - 1, int(len(x) * via / sr)), np.arange(len(x)), x)
    return np.interp(np.linspace(0, len(up) - 1, len(x)), np.arange(len(up)), up).astype(np.float32)


def lowpass_8k(x, sr=SR):
    from scipy import signal as sps
    b, a = sps.butter(8, 3400 / (sr / 2), btype="low")
    return sps.lfilter(b, a, x).astype(np.float32)


def noise_suppression_sim(x, sr=SR):
    """Simulates aggressive denoising (Krisp / Teams / Zoom RNNoise-class).

    THE SLEEPER FALSE-POSITIVE KILLER: this makes REAL speech look synthetic by
    stripping the artifacts detection relies on. Run it on BONA FIDE audio and report
    the false-positive rate -- that is the row most teams never measure.
    """
    from scipy import signal as sps
    f, t, Z = sps.stft(x, fs=sr, nperseg=512, noverlap=256)
    mag = np.abs(Z)
    floor = np.percentile(mag, 20, axis=1, keepdims=True)
    gain = np.clip((mag - 1.8 * floor) / (mag + 1e-9), 0.02, 1.0)   # spectral subtraction
    _, y = sps.istft(Z * gain, fs=sr, nperseg=512, noverlap=256)
    return y[: len(x)].astype(np.float32)


TRANSFORMS = {
    "reverb_rt60_0.9": lambda x: reverb(x, 0.9),
    "reverb_rt60_0.4": lambda x: reverb(x, 0.4),
    "noise_0db": lambda x: add_noise(x, 0.0),
    "noise_10db": lambda x: add_noise(x, 10.0),
    "clip": clip_distort,
    "resample_44k": resample_roundtrip,
    "lowpass_8k": lowpass_8k,
    "noise_suppression": noise_suppression_sim,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("indir"); ap.add_argument("outdir")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    import soundfile as sf

    picks = [k.strip() for k in a.only.split(",") if k.strip()] or list(TRANSFORMS)
    src, dst = Path(a.indir), Path(a.outdir)
    files = sorted(list(src.rglob("*.wav")) + list(src.rglob("*.flac")))
    if not files:
        print(f"no audio under {src}"); sys.exit(1)

    for name in picks:
        fn = TRANSFORMS[name]
        out = dst / name; out.mkdir(parents=True, exist_ok=True)
        for f in files:
            x, sr = sf.read(f, dtype="float32", always_2d=True)
            x = x.mean(axis=1)
            if sr != SR:
                x = np.interp(np.linspace(0, len(x) - 1, int(len(x) * SR / sr)),
                              np.arange(len(x)), x).astype(np.float32)
            y = fn(x)
            y = y / (np.max(np.abs(y)) + 1e-9) * 0.9
            sf.write(out / f.name, y, SR)
        print(f"  {name:22} {len(files):4} files -> {out}")
    print("\nNow run each directory through POST /api/analyze and record the EER.")


if __name__ == "__main__":
    main()
