#!/usr/bin/env python3
"""Pull a small, balanced, speaker-disjoint slice of ASVspoof 2019 LA train.

English real (bonafide) vs English fake (spoof, 6 attack systems A01-A06) from the
SAME corpus -- zero language/channel confound. Individually downloads only the
selected flac (a few hundred), not the whole dataset.

    KAGGLE_API_TOKEN=... python scripts/prep_asvspoof.py --n-bona 150 --n-spoof 240
"""
from __future__ import annotations
import argparse, os, random, zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTO = ROOT / "data" / "datasets" / "asv2019" / "ASVspoof2019.LA.cm.train.trn.txt"
GENUINE = ROOT / "attacks" / "genuine"
SPOOF = ROOT / "attacks" / "out" / "clones" / "asvspoof"
DATASET = "anishsarkar22/asvpoof-2019-dataset-la"
FLAC_DIR = "LA/ASVspoof2019_LA_train/flac"
random.seed(1)


def fetch(api, fname: str, dest: Path):
    if dest.exists() and dest.stat().st_size > 0:
        return True                        # resume: already have it
    dest.parent.mkdir(parents=True, exist_ok=True)
    import time
    for attempt in range(4):
        try:
            api.dataset_download_file(DATASET, file_name=f"{FLAC_DIR}/{fname}.flac",
                                      path=str(dest.parent), quiet=True)
            raw = dest.parent / f"{fname}.flac"
            zp = dest.parent / f"{fname}.flac.zip"
            if zp.exists():
                with zipfile.ZipFile(zp) as z:
                    z.extractall(dest.parent)
                zp.unlink()
                raw = dest.parent / f"{fname}.flac"
            if raw.exists() and raw != dest:
                raw.rename(dest)
            return True
        except Exception as e:
            time.sleep(2 * (attempt + 1))
    print(f"      ! gave up on {fname}")
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-bona", type=int, default=150)
    ap.add_argument("--n-spoof", type=int, default=240)
    a = ap.parse_args()

    from kaggle import KaggleApi
    api = KaggleApi(); api.authenticate()

    rows = [l.split() for l in PROTO.read_text().splitlines() if l.strip()]
    bona = [(r[0], r[1]) for r in rows if r[4] == "bonafide"]
    spoof_by_sys = defaultdict(list)
    for r in rows:
        if r[4] == "spoof":
            spoof_by_sys[r[3]].append((r[0], r[1]))

    random.shuffle(bona)
    picks_bona = bona[:a.n_bona]
    print(f"[asv] downloading {len(picks_bona)} bonafide ...")
    for i, (spk, fn) in enumerate(picks_bona):
        s = spk.replace("_", "")
        fetch(api, fn, GENUINE / f"{s}_asvreal_{i:04d}.flac")
        if (i + 1) % 25 == 0:
            print(f"      bonafide {i+1}/{len(picks_bona)}")

    per_sys = a.n_spoof // len(spoof_by_sys)
    for sysid, lst in spoof_by_sys.items():
        random.shuffle(lst)
        sel = lst[:per_sys]
        print(f"[asv] {sysid}: downloading {len(sel)} spoof ...")
        for i, (spk, fn) in enumerate(sel):
            s = spk.replace("_", "")
            fetch(api, fn, SPOOF / sysid / f"{s}_{sysid}_{i:04d}.flac")
    print("[asv] done")


if __name__ == "__main__":
    main()
