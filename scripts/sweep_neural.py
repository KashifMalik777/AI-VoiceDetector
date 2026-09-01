#!/usr/bin/env python3
"""Sweep the neural detector's runtime knobs and RECOMMEND a config.

WHY THIS EXISTS
The first export measured ONNX int8 at 2717 ms vs plain PyTorch at 382 ms --
quantisation appearing 7x SLOWER, which is backwards. Two candidate causes:

  1. an apples-to-oranges comparison: ORT was pinned to intra_op_num_threads=1
     (to honour the paper's "1 CPU core" claim) while torch used every core
  2. int8 dynamic quantisation is frequently SLOWER than fp32 on transformer
     MatMuls unless the CPU has AVX512-VNNI

Rather than guess which, measure the grid. The output is a decision, not a vibe.

    python scripts/sweep_neural.py
    python scripts/sweep_neural.py --window 4.0 --runs 5
"""
from __future__ import annotations
import argparse, json, platform, time, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ONNX_DIR = ROOT / "ml" / "onnx"
sys.path.insert(0, str(ROOT))
import numpy as np


def bench_ort(path: Path, x: np.ndarray, threads: int, runs: int) -> float | None:
    import onnxruntime as ort
    so = ort.SessionOptions()
    so.intra_op_num_threads = threads          # 0 = let ORT decide (all cores)
    so.inter_op_num_threads = 1
    so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    try:
        s = ort.InferenceSession(str(path), so, providers=["CPUExecutionProvider"])
        s.run(None, {"input": x}); s.run(None, {"input": x})     # warm
        ts = []
        for _ in range(runs):
            t0 = time.perf_counter(); s.run(None, {"input": x})
            ts.append((time.perf_counter() - t0) * 1000)
        return sum(ts) / len(ts)
    except Exception as e:
        print(f"      ! {path.name} @ {threads or 'auto'} threads failed: {e}")
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", type=float, default=4.0)
    ap.add_argument("--runs", type=int, default=5)
    a = ap.parse_args()

    cores = os.cpu_count() or 1
    print("=" * 70)
    print("  Neural detector config sweep")
    print(f"  {platform.processor() or platform.machine()}  ·  {cores} logical cores")
    print(f"  window {a.window}s  ·  {a.runs} runs per config")
    print("=" * 70)

    models = sorted(ONNX_DIR.glob("xlsr_l*.onnx"))
    if not models:
        sys.exit("no ONNX in ml/onnx/ -- run ml/training/export_backbone.py first")

    x = np.random.randn(1, int(16000 * a.window)).astype(np.float32)
    thread_opts = sorted({1, 2, 4, min(8, cores), 0})

    print(f"\n{'model':<26}{'threads':>9}{'mean ms':>11}{'RTF':>8}   fits 1s hop?")
    print("-" * 70)
    rows = []
    for m in models:
        for th in thread_opts:
            ms = bench_ort(m, x, th, a.runs)
            if ms is None:
                continue
            rtf = ms / (a.window * 1000)
            fits = "YES" if ms < 900 else f"no (every {int(ms // 900) + 1} hops)"
            label = "auto" if th == 0 else str(th)
            print(f"{m.name:<26}{label:>9}{ms:>11.0f}{rtf:>8.3f}   {fits}")
            rows.append({"model": m.name, "threads": th, "mean_ms": round(ms, 1),
                         "rtf": round(rtf, 4), "size_mb": round(m.stat().st_size / 1e6)})

    if not rows:
        sys.exit("every config failed")

    # ---- torch reference, all cores, for the apples-to-apples comparison --------
    torch_ms = None
    try:
        import torch
        from transformers import Wav2Vec2Model
        card = json.loads((ONNX_DIR / "model_card.json").read_text())
        print(f"\n  torch reference ({card.get('layers_kept','?')} layers, all cores) ...", end="", flush=True)
        bb = Wav2Vec2Model.from_pretrained(card["base"])
        bb.config.apply_spec_augment = False
        bb.encoder.layers = torch.nn.ModuleList(list(bb.encoder.layers[: card["layers_kept"]]))
        bb.eval()
        xt = torch.from_numpy(x)
        with torch.no_grad():
            bb((xt - xt.mean()) / (xt.std() + 1e-7))
            ts = []
            for _ in range(a.runs):
                t0 = time.perf_counter()
                bb((xt - xt.mean()) / (xt.std() + 1e-7))
                ts.append((time.perf_counter() - t0) * 1000)
        torch_ms = sum(ts) / len(ts)
        print(f" {torch_ms:.0f} ms")
    except Exception as e:
        print(f" skipped ({e})")

    best = min(rows, key=lambda r: r["mean_ms"])
    print("\n" + "=" * 70)
    print(f"  FASTEST: {best['model']} @ {best['threads'] or 'auto'} threads "
          f"-> {best['mean_ms']:.0f} ms (RTF {best['rtf']:.3f})")

    # int8 vs fp32 at matched thread count -- the question that started this
    for th in thread_opts:
        f = next((r for r in rows if "fp32" in r["model"] and r["threads"] == th), None)
        q = next((r for r in rows if "int8" in r["model"] and r["threads"] == th), None)
        if f and q:
            faster = "int8" if q["mean_ms"] < f["mean_ms"] else "fp32"
            ratio = max(f["mean_ms"], q["mean_ms"]) / max(min(f["mean_ms"], q["mean_ms"]), 1e-9)
            print(f"  at {th or 'auto'} threads: {faster} wins by {ratio:.1f}x "
                  f"(fp32 {f['mean_ms']:.0f} vs int8 {q['mean_ms']:.0f} ms)")
            break

    if torch_ms:
        print(f"  vs torch (all cores): {torch_ms:.0f} ms "
              f"-> ONNX is {torch_ms / best['mean_ms']:.2f}x "
              f"{'faster' if best['mean_ms'] < torch_ms else 'SLOWER'}")

    ms = best["mean_ms"]
    print("\n  RECOMMENDATION")
    if ms < 700:
        print(f"    Run the neural detector EVERY hop. {900 - ms:.0f} ms spare.")
        every = 1
    else:
        every = int(ms // 900) + 1
        print(f"    Neural every {every} hops; codec + gate + speaker every hop.")
        print(f"    Effective neural refresh: {every}s. Codec still scores at 1s.")
        print(f"    Honest framing: 'the fast detectors run every second, the heavy")
        print(f"    one every {every} -- the meter never goes stale.'")
        print(f"    If that is still tight: python ml/training/export_backbone.py --layer 5")
        print(f"    (16.2% OOD EER instead of 8.4% -- still far better than AASIST's 43%)")

    out = ROOT / "data" / "neural_sweep.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({
        "device": platform.platform(), "cores": cores, "window_s": a.window,
        "torch_all_cores_ms": round(torch_ms, 1) if torch_ms else None,
        "results": rows, "best": best, "neural_every_n_hops": every,
    }, indent=2))
    print(f"\n  written -> data/neural_sweep.json")
    print("=" * 70)


if __name__ == "__main__":
    main()
