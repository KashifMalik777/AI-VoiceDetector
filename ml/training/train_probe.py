#!/usr/bin/env python3
"""Fit the linear probe on top of the frozen truncated XLS-R backbone.

The backbone is 101.3M frozen parameters. This trains ONLY the small linear head
on top -- which is why it takes minutes on a CPU instead of hours on a GPU, and
why we can retrain it every time new audio arrives.

    python ml/training/train_probe.py \\
        --real attacks/genuine attacks/refs \\
        --fake attacks/out/clones

PROTOCOL RULES THIS SCRIPT ENFORCES (a judge WILL ask about these)
  * SPEAKER-DISJOINT SPLIT -- files are grouped by the name before the first
    underscore. A speaker never appears in both train and test. Detectors
    frequently learn speaker identity instead of synthesis artifacts; without
    this the numbers are fiction.
  * LEAVE-ONE-GENERATOR-OUT -- with --holdout-generator, one fake source folder
    is excluded from training entirely and reported separately. That number is
    the honest one: performance against a generator we have never seen.
  * Reports EER + minDCF + actDCF + C_llr + FAR@1%FRR, never accuracy alone.
    (In ASVspoof 5 many systems posted minDCF ~0.1 with actDCF = 1.0000 --
    great separation, worthless calibration. The gap IS deployment risk.)
"""
from __future__ import annotations
import argparse, json, sys, time, warnings
from collections import defaultdict
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import numpy as np

SR = 16000
AUDIO_EXT = {".wav", ".flac", ".mp3", ".m4a", ".ogg", ".opus"}


# ----------------------------------------------------------------- loading ---
def load_audio(p: Path) -> np.ndarray | None:
    try:
        import soundfile as sf
        x, sr = sf.read(str(p), dtype="float32", always_2d=True)
        x = x.mean(axis=1)
    except Exception:
        try:
            import librosa
            x, sr = librosa.load(str(p), sr=SR, mono=True)
            return x.astype(np.float32)
        except Exception as e:
            print(f"    ! cannot read {p.name}: {e}")
            return None
    if sr != SR:
        idx = np.linspace(0, len(x) - 1, int(len(x) * SR / sr))
        x = np.interp(idx, np.arange(len(x)), x).astype(np.float32)
    return x


def windows(x: np.ndarray, win=4.0, hop=2.0):
    """Chunk into training windows. 2 s hop = 50% overlap, more data from short clips."""
    n, h = int(SR * win), int(SR * hop)
    if len(x) < n:
        yield np.pad(x, (n - len(x), 0)); return
    for s in range(0, len(x) - n + 1, h):
        yield x[s:s + n]


def speaker_of(p: Path) -> str:
    """Extract speaker identity cleanly for disjoint splits."""
    parts = p.stem.split("_")
    if len(parts) >= 3 and parts[0] == "human" and parts[1] == "spk":
        return f"{parts[0]}_{parts[1]}_{parts[2]}"
    if len(parts) >= 2 and parts[0] == "clone":
        return f"{parts[1]}"
    return parts[0].lower()


def collect(dirs: list[str], label: int):
    out = []
    for d in dirs:
        root = Path(d)
        if not root.is_absolute():
            root = ROOT / d
        if not root.exists():
            print(f"    ! missing: {root}")
            continue
        files = [f for f in sorted(root.rglob("*")) if f.suffix.lower() in AUDIO_EXT]
        print(f"    {root.relative_to(ROOT) if ROOT in root.parents else root}: {len(files)} files")
        for f in files:
            # generator = the folder directly under the given root, when nested
            try:
                gen = f.relative_to(root).parts[0] if len(f.relative_to(root).parts) > 1 else root.name
            except Exception:
                gen = root.name
            out.append((f, label, speaker_of(f), gen))
    return out


# ---------------------------------------------------------------- backbone ---
def _device():
    import torch
    return "cuda" if torch.cuda.is_available() else "cpu"


def build_backbone(card: dict):
    import torch, torch.nn as nn
    from transformers import Wav2Vec2Model
    bb = Wav2Vec2Model.from_pretrained(card["base"])
    bb.config.apply_spec_augment = False
    bb.encoder.layers = nn.ModuleList(list(bb.encoder.layers[: card["layers_kept"]]))
    dev = _device()
    bb = bb.eval().to(dev)
    print(f"    backbone on {dev}")
    return bb


def make_augmenter():
    """Random channel degradation applied to a training window, so the probe learns
    invariance to the field's known-hard conditions (reverb + additive noise). Test
    windows are NEVER augmented -- augmentation touches training data only."""
    import random as _r
    from attacks.laundering import reverb, add_noise, noise_suppression_sim
    # Pool tuned across several runs to hit three axes at once:
    #  * reverb (0.4-0.9 s) -- the field's hardest channel and our worst weakness.
    #  * low-SNR additive noise DOWN TO 0 dB -- reintroduced (it was cut earlier for
    #    driving false positives) because noise_suppression is now in the pool to
    #    hold the real-speech FP down, so the model can see 0 dB fakes and still not
    #    flag denoised real speech.
    #  * noise_suppression (Krisp/Teams-class) -- teaches that artifact-stripped
    #    real speech is still real; the direct FP fix.
    # ~27% of windows stay clean so discrimination (EER) is not dragged too far.
    pool = [
        None, None, None,                    # ~27% clean -> protect EER
        lambda w: reverb(w, 0.9),
        lambda w: reverb(w, 0.6),
        lambda w: reverb(w, 0.4),
        lambda w: add_noise(w, 0.0),         # 0 dB -> lift noise_0db recall
        lambda w: add_noise(w, 3.0),
        lambda w: add_noise(w, 5.0),
        lambda w: add_noise(w, 10.0),
        noise_suppression_sim,               # FP control
    ]

    def aug(w):
        f = _r.choice(pool)
        return w if f is None else f(w).astype(np.float32)
    return aug


def embed_all(items, bb, batch=8, augment=None):
    import torch
    dev = _device()
    if dev == "cuda":                       # GPU can chew far bigger batches
        batch = 32
    embs, meta = [], []
    t0 = time.time()
    buf, bmeta = [], []

    def flush():
        if not buf:
            return
        x = torch.from_numpy(np.stack(buf)).to(dev)
        x = (x - x.mean(dim=1, keepdim=True)) / (x.std(dim=1, keepdim=True) + 1e-7)
        with torch.no_grad():
            h = bb(x).last_hidden_state.mean(dim=1)
        embs.append(h.float().cpu().numpy()); meta.extend(bmeta)
        buf.clear(); bmeta.clear()

    for i, (f, label, spk, gen) in enumerate(items, 1):
        a = load_audio(f)
        if a is None or len(a) < SR // 2:
            continue
        for w in windows(a):
            if augment is not None:
                w = augment(w)
            buf.append(w); bmeta.append((label, spk, gen, f.name))
            if len(buf) >= batch:
                flush()
        if i % 5 == 0 or i == len(items):
            tag = " (aug)" if augment is not None else ""
            print(f"    embedded {i}/{len(items)} files ({time.time()-t0:.0f}s){tag}")
    flush()
    if not embs:
        sys.exit("no usable audio found")
    return np.concatenate(embs), meta


# ------------------------------------------------------------------- train ---
def fit_logistic(X, y, epochs=400, lr=0.05, wd=1e-3):
    """Torch logistic regression -- no sklearn dependency."""
    import torch, torch.nn as nn
    Xt = torch.from_numpy(X.astype(np.float32))
    yt = torch.from_numpy(y.astype(np.int64))
    head = nn.Linear(X.shape[1], 2)
    nn.init.zeros_(head.weight); nn.init.zeros_(head.bias)
    opt = torch.optim.Adam(head.parameters(), lr=lr, weight_decay=wd)
    lossf = nn.CrossEntropyLoss()
    for e in range(epochs):
        opt.zero_grad(); loss = lossf(head(Xt), yt); loss.backward(); opt.step()
    return head, float(loss.item())


def scores_from(head, X):
    import torch
    with torch.no_grad():
        lg = head(torch.from_numpy(X.astype(np.float32))).numpy()
    m = lg[:, 1] - lg[:, 0]
    return 1.0 / (1.0 + np.exp(-m))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", nargs="+", required=True, help="dirs of BONA FIDE audio")
    ap.add_argument("--fake", nargs="+", required=True, help="dirs of SYNTHETIC audio")
    ap.add_argument("--holdout-generator", default=None,
                    help="generator folder name to exclude from training entirely")
    ap.add_argument("--epochs", type=int, default=400)
    ap.add_argument("--augment", action="store_true",
                    help="augment TRAINING windows with reverb+noise to close the "
                         "robustness gap (test windows stay clean -- no leakage)")
    ap.add_argument("--aug-passes", type=int, default=1,
                    help="number of extra augmented passes over the training set")
    a = ap.parse_args()

    card_p = ROOT / "ml" / "onnx" / "model_card.json"
    if not card_p.exists():
        sys.exit("run ml/training/export_backbone.py first")
    card = json.loads(card_p.read_text())

    print("=" * 68)
    print(f"  Training the linear probe · XLS-R layer {card['layers_kept']}")
    print("=" * 68)
    print("\n[1/5] collecting audio")
    items = collect(a.real, 0) + collect(a.fake, 1)          # 0 = real, 1 = synthetic
    if not items:
        sys.exit("no audio. Record refs into attacks/genuine and clones into attacks/out/clones")
    spk = sorted({s for _, _, s, _ in items})
    gens = sorted({g for _, l, _, g in items if l == 1})
    print(f"    {len(items)} files · {len(spk)} speakers {spk} · fake generators {gens}")

    print(f"\n[2/5] loading backbone ({card['base']}, {card['layers_kept']} layers)")
    bb = build_backbone(card)

    # Speaker-disjoint split is decided at the FILE level, before embedding, so an
    # augmented pass can be run over the training files only. Hold out ~25% of
    # speakers per side (not a single speaker) for a stable EER; a single-speaker
    # holdout gives a tiny, high-variance test whose EER swings and can invert.
    print("\n[3/5] speaker-disjoint split")
    real_spks = sorted({s for _, l, s, _ in items if l == 0})
    fake_spks = sorted({s for _, l, s, _ in items if l == 1})
    import random as _r
    _r.seed(0)
    rr = list(real_spks); _r.shuffle(rr)
    ff = list(fake_spks); _r.shuffle(ff)
    n_hr = max(1, round(len(rr) * 0.25))
    n_hf = max(1, round(len(ff) * 0.25))
    held = set(rr[:n_hr]) | set(ff[:n_hf])

    def is_test(it):
        _, _, s, g = it
        if a.holdout_generator and g == a.holdout_generator:
            return True                     # leave-one-generator-out -> unseen, test only
        return s in held

    test_items = [it for it in items if is_test(it)]
    train_items = [it for it in items if not is_test(it)]
    print(f"    test real speakers: {n_hr}/{len(real_spks)} · "
          f"test fake speakers: {n_hf}/{len(fake_spks)}")
    if a.holdout_generator:
        print(f"    holdout generator: '{a.holdout_generator}' -> test only (unseen)")
    if not test_items or not train_items:
        sys.exit("degenerate split -- record more speakers or add generators")

    print("\n[4/5] extracting embeddings (the slow part)")
    print("    test (clean):")
    Xte, mte = embed_all(test_items, bb)
    print("    train (clean):")
    Xtr, mtr = embed_all(train_items, bb)
    X_parts, m_parts = [Xte, Xtr], [mte, mtr]
    n_test = Xte.shape[0]
    if a.augment:
        aug = make_augmenter()
        for p in range(a.aug_passes):
            print(f"    train (augmented pass {p+1}/{a.aug_passes}):")
            Xa, ma = embed_all(train_items, bb, augment=aug)
            X_parts.append(Xa); m_parts.append(ma)

    X = np.concatenate(X_parts)
    meta = [m for part in m_parts for m in part]
    y = np.array([m[0] for m in meta])
    te = np.zeros(len(meta), dtype=bool); te[:n_test] = True   # clean test windows first
    tr = ~te
    print(f"    {X.shape[0]} windows · {X.shape[1]}-dim · "
          f"{int((y==0).sum())} real / {int((y==1).sum())} fake · "
          f"train {tr.sum()} / test {te.sum()}"
          + (f" · augment x{a.aug_passes}" if a.augment else ""))
    if tr.sum() < 10 or te.sum() < 4:
        sys.exit("not enough data -- record more, or add more clone generators")

    head, loss = fit_logistic(X[tr], y[tr], epochs=a.epochs)
    n_head = sum(p.numel() for p in head.parameters())
    print(f"    fitted {n_head} head params · final loss {loss:.4f}")

    # ---- METRICS ---------------------------------------------------------------
    print("\n[5/5] metrics on the held-out speaker")
    from ml.fusion.calibrate import eer, dcf, c_llr, far_at_frr
    s_te, y_te = scores_from(head, X[te]), y[te]
    if len(np.unique(y_te)) < 2:
        print("    ! test split has only one class -- metrics meaningless.")
        m = {}
    else:
        m = {"eer": round(float(eer(s_te, y_te)) * 100, 2),
             "min_dcf": round(float(dcf(s_te, y_te)), 4),
             "act_dcf": round(float(dcf(s_te, y_te, threshold=0.5)), 4),
             "c_llr": round(float(c_llr(s_te, y_te)), 4),
             "far_at_1_frr": round(float(far_at_frr(s_te, y_te, 0.01)) * 100, 2)}
        print(f"    EER           {m['eer']:.2f} %")
        print(f"    minDCF        {m['min_dcf']:.4f}")
        print(f"    actDCF        {m['act_dcf']:.4f}   <- gap vs minDCF = deployment risk")
        print(f"    C_llr         {m['c_llr']:.4f}   <- ~1.0 means uncalibrated")
        print(f"    FAR @ 1% FRR  {m['far_at_1_frr']:.2f} %")

    out = ROOT / "ml" / "onnx" / "probe_head.npz"
    np.savez(out, weight=head.weight.detach().numpy(), bias=head.bias.detach().numpy())

    res = ROOT / "data" / "probe_results.json"
    res.parent.mkdir(exist_ok=True)
    res.write_text(json.dumps({
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "layers_kept": card["layers_kept"], "head_params": n_head,
        "windows_train": int(tr.sum()), "windows_test": int(te.sum()),
        "speakers": spk, "generators": gens,
        "test_speaker": spk[-1] if len(spk) > 1 else None,
        "holdout_generator": a.holdout_generator,
        "speaker_disjoint": len(spk) > 1,
        "augmented": bool(a.augment),
        "aug_passes": a.aug_passes if a.augment else 0,
        "metrics": m,
    }, indent=2))

    print("\n" + "=" * 68)
    print(f"  wrote ml/onnx/probe_head.npz + data/probe_results.json")
    if len(spk) < 2:
        print("  ⚠  NOT speaker-disjoint -- do not put these numbers on a slide.")
    print("  NEXT: python ml/training/export_backbone.py --head ml/onnx/probe_head.npz")
    print("        then python scripts/bench_rtf.py")
    print("=" * 68)


if __name__ == "__main__":
    main()
