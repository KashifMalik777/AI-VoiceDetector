#!/usr/bin/env python3
"""Assemble the Hindi track + final cleanup for the English+Hindi benchmark.

  - REAL Hindi  : FLEURS hi_in train wavs  -> attacks/genuine/ (pseudo-speaker buckets)
  - FAKE Hindi  : IndicSynth Hindi shards (freevc24 / vits / xtts_v2) -> clones/indicsynth_hi/<gen>
  - Clears the earlier BENGALI IndicSynth fakes (wrong language)
  - Moves the phone refs out of the benchmark set (kept for the live demo only)

Run after the FLEURS + IndicSynth Hindi shards are in data/datasets/hf.
"""
from __future__ import annotations
import random, shutil, tarfile, glob, os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENUINE = ROOT / "attacks" / "genuine"
CLONES = ROOT / "attacks" / "out" / "clones"
REFS_HOLD = ROOT / "attacks" / "refs_demo_only"
HF = ROOT / "data" / "datasets" / "hf"
random.seed(2)


def clear_bengali():
    old = CLONES / "indicsynth"
    if old.exists():
        shutil.rmtree(old)
        print(f"[clean] removed Bengali fakes at {old}")


def drop_phone_refs():
    REFS_HOLD.mkdir(parents=True, exist_ok=True)
    for f in GENUINE.glob("human_spk_90_ref*"):
        shutil.move(str(f), str(REFS_HOLD / f.name))
        print(f"[clean] moved {f.name} out of benchmark set")


def prep_fleurs_hindi(n=200):
    tar = next(iter(glob.glob(str(HF / "**" / "hi_in" / "audio" / "train.tar.gz"), recursive=True)), None)
    if not tar:
        print("[hi-real] FLEURS train.tar.gz not found yet"); return 0
    ex = HF / "fleurs_hi"
    if not ex.exists():
        print("[hi-real] extracting FLEURS hi_in ...")
        with tarfile.open(tar) as t:
            t.extractall(ex)
    wavs = sorted(glob.glob(str(ex / "**" / "*.wav"), recursive=True))
    picks = random.sample(wavs, min(n, len(wavs)))
    for i, w in enumerate(picks):
        spk = i % 12                      # pseudo-speaker buckets for disjoint split
        (GENUINE / f"hin_spk_{spk:02d}_{i:04d}.wav").write_bytes(Path(w).read_bytes())
    print(f"[hi-real] wrote {len(picks)} FLEURS Hindi clips ({len(wavs)} available)")
    return len(picks)


def prep_indicsynth_hindi(per_gen=70):
    import pandas as pd
    shards = sorted(glob.glob(str(HF / "**" / "Hindi" / "*.parquet"), recursive=True))
    out_root = CLONES / "indicsynth_hi"
    seen_gen = set(); total = 0
    for sh in shards:
        df = pd.read_parquet(sh, columns=["audio", "Generative Model", "Target Speaker ID"])
        gen = str(df["Generative Model"].iloc[0])
        if gen in seen_gen:
            continue                       # one shard per generator
        seen_gen.add(gen)
        idx = random.sample(range(len(df)), min(per_gen, len(df)))
        d = out_root / gen; d.mkdir(parents=True, exist_ok=True)
        for n, r in enumerate(idx):
            row = df.iloc[r]
            tid = int(row["Target Speaker ID"])
            (d / f"spk{tid}_{gen}_{n:04d}.wav").write_bytes(row["audio"]["bytes"])
        total += len(idx)
        print(f"[hi-fake] {gen}: {len(idx)} clips")
    print(f"[hi-fake] generators: {sorted(seen_gen)} · {total} clips")


def main():
    print("=" * 60)
    clear_bengali()
    drop_phone_refs()
    prep_fleurs_hindi()
    prep_indicsynth_hindi()
    real = len(list(GENUINE.rglob("*")))
    fake = len([f for f in CLONES.rglob("*") if f.suffix.lower() in {".wav", ".flac"}])
    print("=" * 60)
    print(f"  REAL: {real}   FAKE: {fake}")
    print("=" * 60)


if __name__ == "__main__":
    main()
