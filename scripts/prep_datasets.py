#!/usr/bin/env python3
"""Prepare a balanced, speaker-disjoint training set for the probe.

Pulls REAL speech (LibriSpeech dev-clean) and SYNTHETIC speech (IndicSynth, a few
generator-distinct shards) and lays them out with filenames the train_probe.py
speaker/generator parser understands:

  attacks/genuine/human_spk_NN_*.flac          <- real, grouped by LibriSpeech speaker
  attacks/out/clones/indicsynth/<gen>/spkTID_<gen>_*.wav   <- fake, grouped by target speaker
  attacks/out/clones/<existing>/                <- your ElevenLabs clones, converted to wav

Local user recordings (attacks/refs/*.m4a) are converted to wav and added as real.

    python scripts/prep_datasets.py --n-real 500 --n-fake 500
"""
from __future__ import annotations
import argparse, io, os, random, sys, tarfile, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENUINE = ROOT / "attacks" / "genuine"
CLONES = ROOT / "attacks" / "out" / "clones"
REFS = ROOT / "attacks" / "refs"
CACHE = ROOT / "data" / "datasets"
SR = 16000
LIBRI_URL = "https://www.openslr.org/resources/12/dev-clean.tar.gz"
# Bengali shards, one generator each (verified): freevc24, vits, xtts_v2
INDIC_REPO = "vdivyasharma/IndicSynth"
INDIC_SHARDS = [
    "Bengali/train-00000-of-00054.parquet",   # freevc24
    "Bengali/train-00027-of-00054.parquet",   # vits
    "Bengali/train-00053-of-00054.parquet",   # xtts_v2
]

random.seed(0)


def _ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def to_wav16k(src: Path, dst: Path):
    """Decode anything (m4a/mp3/wav) -> 16 kHz mono wav via bundled ffmpeg."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    import subprocess
    subprocess.run([_ffmpeg(), "-y", "-i", str(src), "-ac", "1", "-ar", str(SR),
                    str(dst)], check=True, capture_output=True)


# ------------------------------------------------------------------- REAL ---
def prep_librispeech(n_real: int):
    GENUINE.mkdir(parents=True, exist_ok=True)
    tar = CACHE / "dev-clean.tar.gz"
    CACHE.mkdir(parents=True, exist_ok=True)
    if not tar.exists():
        print(f"[real] downloading LibriSpeech dev-clean (~337 MB) ...")
        urllib.request.urlretrieve(LIBRI_URL, tar)
    extract = CACHE / "LibriSpeech"
    if not extract.exists():
        print("[real] extracting ...")
        with tarfile.open(tar) as t:
            t.extractall(CACHE)
    flacs = sorted((CACHE / "LibriSpeech" / "dev-clean").rglob("*.flac"))
    # group by speaker (first field of <spk>-<chap>-<utt>.flac)
    by_spk: dict[str, list[Path]] = {}
    for f in flacs:
        spk = f.stem.split("-")[0]
        by_spk.setdefault(spk, []).append(f)
    spks = sorted(by_spk)
    per = max(1, n_real // len(spks))
    print(f"[real] {len(flacs)} clips, {len(spks)} speakers -> ~{per}/speaker")
    written = 0
    for i, spk in enumerate(spks):
        picks = random.sample(by_spk[spk], min(per, len(by_spk[spk])))
        for j, src in enumerate(picks):
            dst = GENUINE / f"human_spk_{i:02d}_{j:03d}.flac"
            dst.write_bytes(src.read_bytes())
            written += 1
            if written >= n_real:
                break
        if written >= n_real:
            break
    print(f"[real] wrote {written} genuine clips -> {GENUINE}")


def prep_refs():
    """User's own recordings -> genuine, as a distinct real speaker group."""
    if not REFS.exists():
        return
    for k, src in enumerate(sorted(REFS.glob("*"))):
        if src.suffix.lower() not in {".m4a", ".mp3", ".wav", ".flac", ".ogg"}:
            continue
        dst = GENUINE / f"human_spk_90_ref{k:02d}.wav"
        to_wav16k(src, dst)
        print(f"[real] ref {src.name} -> {dst.name}")


# ------------------------------------------------------------------- FAKE ---
def prep_indicsynth(n_fake: int):
    import pandas as pd
    from huggingface_hub import hf_hub_download
    per_gen = n_fake // len(INDIC_SHARDS)
    out_root = CLONES / "indicsynth"
    for shard in INDIC_SHARDS:
        print(f"[fake] downloading shard {shard} ...")
        local = hf_hub_download(INDIC_REPO, shard, repo_type="dataset",
                                cache_dir=str(CACHE / "hf"))
        df = pd.read_parquet(local, columns=["audio", "Generative Model", "Target Speaker ID"])
        gen = str(df["Generative Model"].iloc[0])
        idx = random.sample(range(len(df)), min(per_gen, len(df)))
        d = out_root / gen
        d.mkdir(parents=True, exist_ok=True)
        for n, r in enumerate(idx):
            row = df.iloc[r]
            b = row["audio"]["bytes"]
            tid = int(row["Target Speaker ID"])
            (d / f"spk{tid}_{gen}_{n:04d}.wav").write_bytes(b)
        print(f"[fake] {gen}: wrote {len(idx)} clips -> {d}")


def prep_user_clones():
    """Convert existing ElevenLabs/other clone mp3s to wav in place."""
    if not CLONES.exists():
        return
    for src in sorted(CLONES.rglob("*")):
        if src.suffix.lower() in {".mp3", ".m4a", ".ogg"} and "indicsynth" not in src.parts:
            dst = src.with_suffix(".wav")
            if not dst.exists():
                to_wav16k(src, dst)
                print(f"[fake] user clone {src.name} -> {dst.name}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-real", type=int, default=500)
    ap.add_argument("--n-fake", type=int, default=500)
    ap.add_argument("--skip-real", action="store_true")
    ap.add_argument("--skip-fake", action="store_true")
    a = ap.parse_args()
    print("=" * 60)
    print("  Preparing SatyaVaani training data")
    print("=" * 60)
    if not a.skip_real:
        prep_librispeech(a.n_real)
        prep_refs()
    if not a.skip_fake:
        prep_indicsynth(a.n_fake)
        prep_user_clones()
    # tally
    real = len(list(GENUINE.rglob("*"))) if GENUINE.exists() else 0
    fake = len([f for f in CLONES.rglob("*") if f.suffix.lower() == ".wav"]) if CLONES.exists() else 0
    print("\n" + "=" * 60)
    print(f"  REAL clips: {real}   FAKE wav clips: {fake}")
    print("  NEXT: python ml/training/train_probe.py \\")
    print("          --real attacks/genuine \\")
    print("          --fake attacks/out/clones/indicsynth attacks/out/clones/kikicore")
    print("=" * 60)


if __name__ == "__main__":
    main()
