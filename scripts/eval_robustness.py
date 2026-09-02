#!/usr/bin/env python3
"""Measure the trained probe's spoof-detection recall under channel degradation.

This is the reproducible version of the ad-hoc script that first produced
`data/robustness_results.json`. It evaluates on HELD-OUT fake speakers only (the
same 25% speaker holdout the trainer uses, seed 0), so the numbers are honest
generalization, not memorization -- and directly comparable before vs. after an
augmentation retrain.

    python scripts/eval_robustness.py                       # -> data/robustness_results.json
    python scripts/eval_robustness.py --out data/robustness_baseline.json

Degradations are the pure-numpy ones from attacks/laundering.py (reverb, additive
noise, clip, resample, lowpass, noise-suppression). Codec-chain conditions need
ffmpeg and live in attacks/codec_chain -- not covered here.
"""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ml.training.train_probe import load_audio, windows, build_backbone, collect, SR
from attacks.laundering import reverb, add_noise, clip_distort, resample_roundtrip, \
    lowpass_8k, noise_suppression_sim

# Conditions to report. Clean baseline first, then the field's known-hard channels.
FAKE_CONDS = {
    "clean": lambda x: x,
    "reverb_rt60_0.9": lambda x: reverb(x, 0.9),
    "reverb_rt60_0.4": lambda x: reverb(x, 0.4),
    "noise_0db": lambda x: add_noise(x, 0.0),
    "noise_10db": lambda x: add_noise(x, 10.0),
    "clip": clip_distort,
    "resample_44k": resample_roundtrip,
    "lowpass_8k": lowpass_8k,
}


def load_head():
    d = np.load(ROOT / "ml" / "onnx" / "probe_head.npz")
    return d["weight"].astype(np.float32), d["bias"].astype(np.float32)  # (2,1024),(2,)


def p_fake_for_windows(wins, bb, W, b):
    """Mean P(fake) over a list of 4 s windows for one clip."""
    import torch
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    x = torch.from_numpy(np.stack(wins)).to(dev)
    x = (x - x.mean(dim=1, keepdim=True)) / (x.std(dim=1, keepdim=True) + 1e-7)
    with torch.no_grad():
        h = bb(x).last_hidden_state.mean(dim=1).float().cpu().numpy()   # (n,1024)
    logits = h @ W.T + b                                                # (n,2)
    m = logits[:, 1] - logits[:, 0]
    return float(np.mean(1.0 / (1.0 + np.exp(-m))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", nargs="+", default=["attacks/genuine"])
    ap.add_argument("--fake", nargs="+",
                    default=["attacks/out/clones/asvspoof",
                             "attacks/out/clones/indicsynth_hi",
                             "attacks/out/clones/kikicore"])
    ap.add_argument("--out", default="data/robustness_results.json")
    a = ap.parse_args()

    import random as _r
    real_items = collect(a.real, 0)
    fake_items = collect(a.fake, 1)
    real_spks = sorted({s for _, _, s, _ in real_items})
    fake_spks = sorted({s for _, _, s, _ in fake_items})
    _r.seed(0)
    rr = list(real_spks); _r.shuffle(rr)
    ff = list(fake_spks); _r.shuffle(ff)
    n_hf = max(1, round(len(ff) * 0.25))
    held_fake = set(ff[:n_hf])
    held = [it for it in fake_items if it[2] in held_fake]
    print(f"held-out fake speakers: {n_hf}/{len(fake_spks)} · {len(held)} clips")

    card = json.loads((ROOT / "ml" / "onnx" / "model_card.json").read_text())
    W, b = load_head()
    print(f"loading backbone ({card['base']}, {card['layers_kept']} layers)")
    bb = build_backbone(card)

    # Pre-load clean audio once; degrade in memory per condition.
    clips = []
    for f, _, _, _ in held:
        x = load_audio(f)
        if x is not None and len(x) >= SR // 2:
            clips.append(x)
    print(f"{len(clips)} usable clips")

    conditions = {}
    t0 = time.time()
    for name, fn in FAKE_CONDS.items():
        ps = []
        for x in clips:
            y = fn(x).astype(np.float32)
            y = y / (np.max(np.abs(y)) + 1e-9) * 0.9
            wins = list(windows(y))
            ps.append(p_fake_for_windows(wins, bb, W, b))
        ps = np.array(ps)
        caught = float(np.mean(ps > 0.5) * 100)
        conditions[name] = {"mean_p_fake": round(float(ps.mean()), 3),
                            "spoof_caught_pct": round(caught, 1)}
        print(f"  {name:20} caught {caught:5.1f}%  (mean P_fake {ps.mean():.3f})  "
              f"[{time.time()-t0:.0f}s]")

    # False-positive check: real speech through aggressive noise suppression.
    _r.seed(0)
    n_hr = max(1, round(len(real_spks) * 0.25))
    held_real = set(rr[:n_hr])
    real_held = [it for it in real_items if it[2] in held_real]
    fp = None
    if real_held:
        ps = []
        for f, _, _, _ in real_held:
            x = load_audio(f)
            if x is None or len(x) < SR // 2:
                continue
            y = noise_suppression_sim(x).astype(np.float32)
            y = y / (np.max(np.abs(y)) + 1e-9) * 0.9
            ps.append(p_fake_for_windows(list(windows(y)), bb, W, b))
        ps = np.array(ps)
        fp = {"n": int(len(ps)),
              "mean_p_fake": round(float(ps.mean()), 3),
              "false_positive_pct": round(float(np.mean(ps > 0.5) * 100), 1)}
        print(f"  real@noise_suppression false-positive {fp['false_positive_pct']:.1f}%")

    out = ROOT / a.out
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "note": "Spoof recall of trained XLS-R L7 probe under degradation, on held-out "
                "fake speakers (seed-0 25% holdout). caught = mean P(fake) > 0.5 per clip.",
        "n_held_fake_clips": len(clips),
        "conditions": conditions,
        "real_false_positive": fp,
    }, indent=2))
    print(f"\nwrote {a.out}")


if __name__ == "__main__":
    main()
