#!/usr/bin/env python3
"""RTF benchmark -- RUN THIS ON THE DEMO LAPTOP, ON DAY 1. It is a blocker.

The published edge measurement for our chosen model is 5 s of audio in 3.4 s on a
Ryzen 7 and 4.2 s on an Intel i3 -- a real-time factor of 0.68-0.84. That is real-time
on one core with ALMOST NO HEADROOM. If this machine is slower, the neural pass blows
the 1 s hop and the whole latency story changes.

Fallback ladder, in order (decide from THIS measurement, not from panic on day 3):
  1. int8 quantise the ONNX export
  2. run the neural detector every 2nd hop; codec + speaker every hop
  3. truncate XLS-R to layer 5 (16.2% OOD EER instead of 8.4% -- still far better
     than AASIST's 43% on In-the-Wild)

    python scripts/bench_rtf.py            # full pipeline as configured
    python scripts/bench_rtf.py --n 40     # more iterations
"""
from __future__ import annotations
import sys, time, json, argparse, platform, statistics as st
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import numpy as np

from ml.registry import get_detectors, model_version
from ml.types import WindowContext
from ml import gate
from ml.features.spectral import extract

SR, WIN = 16000, 4


def synth_speech(seconds=WIN, sr=SR):
    """Speech-like signal: harmonic stack + formant shaping + pauses. Good enough to
    exercise the same code path; real audio only changes it by a few percent."""
    t = np.linspace(0, seconds, int(sr * seconds), endpoint=False)
    f0 = 120 + 25 * np.sin(2 * np.pi * 0.7 * t)
    x = sum((1.0 / h) * np.sin(2 * np.pi * f0 * h * t) for h in range(1, 12))
    env = (np.sin(2 * np.pi * 2.5 * t) > -0.35).astype(float)
    env = np.convolve(env, np.hanning(400) / np.hanning(400).sum(), mode="same")
    x = x * env + 0.004 * np.random.randn(len(t))
    return (0.25 * x / (np.max(np.abs(x)) + 1e-9)).astype(np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=25)
    args = ap.parse_args()

    print("=" * 66)
    print("  SatyaVaani RTF benchmark")
    print(f"  {platform.platform()}")
    print(f"  {platform.processor() or 'cpu'}  ·  python {platform.python_version()}")
    print("=" * 66)

    dets = get_detectors()
    for d in dets:
        print(f"  detector {d.name:12} {type(d).__name__}"
              + ("   << STUB" if type(d).__name__.startswith("Stub") else ""))
    print(f"  model_version: {model_version()}\n")

    pcm = synth_speech()
    ctx = WindowContext(seq=1, t_ms=0, sr=SR, net_speech_s=3.5, snr_db=22.0)

    for d in dets:          # warm caches
        try: d.score_window(pcm, SR, ctx)
        except Exception: pass

    per, totals = {d.name: [] for d in dets}, []
    gate_t, feat_t = [], []

    for _ in range(args.n):
        t0 = time.perf_counter()
        g0 = time.perf_counter(); q = gate.analyse(pcm, SR); gate_t.append(time.perf_counter() - g0)
        for d in dets:
            s = time.perf_counter()
            try: d.score_window(pcm, SR, ctx)
            except Exception: pass
            per[d.name].append(time.perf_counter() - s)
        f0 = time.perf_counter(); extract(pcm, SR); feat_t.append(time.perf_counter() - f0)
        totals.append(time.perf_counter() - t0)

    def ms(v): return f"{st.mean(v)*1000:8.1f} ms   (p95 {sorted(v)[int(len(v)*0.95)-1]*1000:.1f})"

    print("  stage                       mean latency")
    print("  " + "-" * 52)
    print(f"  evidence gate            {ms(gate_t)}")
    for n, v in per.items():
        print(f"  detector: {n:14} {ms(v)}")
    print(f"  feature extract          {ms(feat_t)}")
    print("  " + "-" * 52)
    print(f"  TOTAL per window         {ms(totals)}")

    mean = st.mean(totals)
    rtf = mean / WIN
    hop_headroom = 1.0 - mean          # 1 s hop

    print(f"\n  RTF (per {WIN}s window)   {rtf:.3f}")
    print(f"  Headroom in the 1 s hop  {hop_headroom*1000:+.0f} ms")

    if any(type(d).__name__.startswith("Stub") for d in dets):
        print("\n  ⚠  STUBS ACTIVE — this number is NOT the real one.")
        print("     Re-run the moment the neural detector is wired. That is the")
        print("     measurement the latency slide depends on.")
    verdict = ("OK — comfortable" if hop_headroom > 0.4 else
               "TIGHT — quantise to int8 now" if hop_headroom > 0.05 else
               "OVER BUDGET — apply the fallback ladder in this file's docstring")
    print(f"\n  VERDICT: {verdict}\n")

    out = Path(__file__).parent.parent / "data" / "rtf_bench.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({
        "device": platform.platform(), "python": platform.python_version(),
        "model_version": model_version(),
        "stubs_active": [d.name for d in dets if type(d).__name__.startswith("Stub")],
        "iterations": args.n, "window_s": WIN,
        "mean_ms": round(mean * 1000, 2), "rtf": round(rtf, 4),
        "hop_headroom_ms": round(hop_headroom * 1000, 1),
        "per_stage_ms": {**{f"detector_{k}": round(st.mean(v) * 1000, 2) for k, v in per.items()},
                         "gate": round(st.mean(gate_t) * 1000, 2),
                         "features": round(st.mean(feat_t) * 1000, 2)},
        "verdict": verdict,
    }, indent=2))
    print(f"  written -> data/rtf_bench.json   (paste into results.json)\n")


if __name__ == "__main__":
    main()
