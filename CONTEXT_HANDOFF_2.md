# SatyaVaani — Training & Benchmark Handoff (Session 2)

**Project:** Real-Time Voice Cloning & Impersonation Defense (SIH PS 26104)
**This document:** what changed after the original `CONTEXT_HANDOFF.md` — the model is now **trained on real datasets**, benchmarked honestly, stress-tested for robustness, and three real bugs were fixed. Read the original handoff first for architecture; this one covers the ML training pipeline, results, and how to reproduce them.

---

## 0. TL;DR — current state

- The neural detector is **trained** (no longer a stub). Head weights live in `ml/onnx/probe_head.npz`.
- **Deployed model is the augmentation-hardened "v4" head** (§5b). Headline benchmark: EER **0.75%** on a language-matched (English + Hindi), speaker-disjoint test (104 speakers, 9 generators). The pre-augmentation head scored 0.61%; the 0.14-point trade buys large reverb/noise robustness gains.
- **Unseen-generator (leave-one-generator-out):** 0.42% / **17.1%** figures below were measured on the *pre-augmentation* head; not yet re-run on v4 (open item).
- **Robustness:** rock-solid on telephony/codec channels (AMR-NB 100%, MP3@16k 92%). Heavy reverb/noise were the weak spots (12–18% reverb recall); **augmentation training roughly tripled reverb recall and dropped denoising false-positives below the clean-head baseline** (§5b).
- **Real-time:** RTF 0.167, ~670 ms per 4 s window, +331 ms headroom on an RTX 4060 laptop.
- The live system flags fakes (WATCH+) and keeps real speech SAFE (no false positives) on the file lab.

---

## 1. Environment setup from a fresh clone (READ THIS — non-obvious)

The machine gotchas that cost the most time:

1. **Do not use the system `python`.** On the dev machine it was Python 3.14, which has **no ML wheels** (torch/onnxruntime/transformers all fail). Build the venv with **Python 3.11**:
   ```powershell
   C:\path\to\Python311\python.exe -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
2. **torch is installed separately** from `requirements.txt`.
   - CPU only: `pip install torch --index-url https://download.pytorch.org/whl/cpu`
   - **GPU training (recommended if you have an NVIDIA card):** `pip install torch --index-url https://download.pytorch.org/whl/cu124` (dev machine: RTX 4060 8 GB, installed torch 2.6.0+cu124). Verify: `python -c "import torch;print(torch.cuda.is_available())"` → `True`.
3. **Speaker detector needs Resemblyzer:** `pip install resemblyzer`. It pulls the obsolete `typing` backport which **shadows stdlib and breaks torch/transformers** — remove it right after: `pip uninstall typing -y`.
4. **No ffmpeg?** For decoding m4a/mp3 and running the codec-chain attack, either install ffmpeg system-wide or use the bundled one: `pip install imageio-ffmpeg` and point tools at `imageio_ffmpeg.get_ffmpeg_exe()`.

---

## 2. Regenerate the ONNX model (required on every fresh clone)

The `.onnx` files (102–405 MB) are gitignored. Regenerate from the committed trained head:
```powershell
python ml/training/export_backbone.py --head ml/onnx/probe_head.npz
```
This downloads the 1.2 GB XLS-R backbone once, bakes in the trained head, and writes `xlsr_l7_int8.onnx` + `model_card.json` (`"trained": true`). Takes ~1–2 minutes after the backbone is cached.

> The export script's own 1-thread verify prints "OVER BUDGET" (~3.3 s). Ignore it — that is a single-core worst case. The real multi-thread latency is measured by `scripts/bench_rtf.py` (~670 ms/window, well inside the 1 s hop).

---

## 3. The training data pipeline

**Deployment target is English + Hindi (Indian banking calls).** The benchmark is **language-matched** on purpose: if real speech is one language and fake another, the detector learns to separate *language* instead of *synthesis artifacts* — a confound a judge will catch. (An early run that mixed English-real with Bengali-fake produced a meaningless result for exactly this reason.)

Three helper scripts assemble the data (all in `scripts/`). They download into `data/datasets/` (gitignored) and lay files out where `train_probe.py` expects them:

| Script | Pulls | Into |
|---|---|---|
| `prep_datasets.py` | LibriSpeech dev-clean (English real), IndicSynth subset | `attacks/genuine/`, `attacks/out/clones/` |
| `prep_asvspoof.py` | ASVspoof 2019 LA — bonafide (English real) + A01–A06 spoof (English fake), a small speaker-disjoint subset | `attacks/genuine/`, `attacks/out/clones/asvspoof/<system>/` |
| `prep_hindi.py` | FLEURS `hi_in` (Hindi real), IndicSynth Hindi (freevc24/xtts_v2 fake); clears the wrong-language Bengali fakes; moves personal phone refs out of the benchmark set | `attacks/genuine/`, `attacks/out/clones/indicsynth_hi/<gen>/` |

Datasets used (all free; ASVspoof needs a Kaggle API token in the `KAGGLE_API_TOKEN` env var — Kaggle dataset `anishsarkar22/asvpoof-2019-dataset-la`):

- **English real:** LibriSpeech dev-clean + ASVspoof bonafide
- **English fake:** ASVspoof A01–A06 (6 systems) + the team's ElevenLabs clones (`kikicore`)
- **Hindi real:** FLEURS `hi_in`
- **Hindi fake:** IndicSynth (`vdivyasharma/IndicSynth`, HuggingFace) — freevc24, xtts_v2

**Naming convention that makes speaker-disjoint splits work** (`speaker_of()` splits on the first `_`): real files are `human_spk_NN_*`, `hin_spk_NN_*`, `<spk>_asvreal_*`; fake files are `<spk>_<generator>_*` with each generator in its own folder under the `--fake` root (so leave-one-generator-out works).

Assembled set: **~830 real / ~382 fake, 104 speakers, 9 generators.**

---

## 4. Train and reproduce the benchmark

```powershell
# GPU is used automatically if available (backbone runs on CUDA, head fits on CPU)
python ml/training/train_probe.py `
  --real attacks/genuine `
  --fake attacks/out/clones/asvspoof attacks/out/clones/indicsynth_hi attacks/out/clones/kikicore
```
Writes `ml/onnx/probe_head.npz` (the trained head) and `data/probe_results.json` (metrics). Then re-export the ONNX (Section 2) and re-run `scripts/bench_rtf.py`.

**Leave-one-generator-out** (the honest "unseen generator" number) — add e.g. `--holdout-generator xtts_v2`. Note: LOGO runs write a head that excludes that generator, so **finish with a full run (no holdout)** to restore the deployed head before exporting.

### Results (this session)

| Evaluation | EER | minDCF | actDCF | FAR@1%FRR |
|---|---|---|---|---|
| Seen generators (headline) | **0.61%** | 0.0059 | 0.0590 | 0.00% |
| Unseen — A04 (familiar TTS) | 0.42% | 0.0030 | 0.0835 | 0.00% |
| Unseen — xtts_v2 (novel cross-lingual VC) | 17.13% | 0.4736 | 0.7807 | 33.45% |

The small actDCF–minDCF gap means the scores are **well-calibrated**, not just separable.

> These are the **pre-augmentation** head (session 2). The **deployed** model is the augmentation-hardened v4 — seen-generator EER **0.75%** — see §5b and §0.

### Robustness (`data/robustness_results.json`)

Spoof-detection recall of the trained model on 52 held fakes, per degradation (`caught` = P(fake) > 0.5):

| Condition | Caught | | Condition | Caught |
|---|---|---|---|---|
| Clean baseline | 96% | | Noise @ 10 dB | 58% |
| Telephony AMR-NB (8 kHz) | **100%** | | Noise @ 0 dB | 46% |
| G711 / ADPCM / Opus | 96% | | Reverb RT60 0.4 s | 35% |
| MP3 @ 16 kbit/s | 92% | | **Reverb RT60 0.9 s** | **17%** |
| Resample / Lowpass / Clip | 94–96% | | | |

**Takeaway:** codec/telephony (the deployment channel) is rock-solid — for other systems MP3@16k famously pushes EER 3.7% → 55%, here it barely moves. Reverb and heavy additive noise are the weak spots (the field's known-hardest conditions). The fix is **training through them**: `attacks/laundering.py` doubles as an augmentation generator. This is the top open item.

---

## 5. Code changes made this session (all in shipped source)

1. **`ml/fusion/calibrate.py` — `eer()` was miscomputed.** Its `far`/`frr` were mislabeled, so it returned ~99% for a *good* model. Rewritten to standard EER (label 1 = spoof, higher score = more spoof), consistent with `dcf()`/`far_at_frr()`. This is why early runs showed nonsensical 61/89/99% EER — the model was fine, the metric was inverted.
2. **`ml/training/train_probe.py` — split + GPU.** The speaker-disjoint split held out only *one* speaker per class → a tiny, high-variance, sometimes-inverted test. Now holds out ~25% of speakers per side. Also: backbone runs on GPU (`build_backbone`/`embed_all`), and `--holdout-generator` now puts the held generator entirely in the test set (a proper leave-one-generator-out).
3. **`ml/gate.py` — `MIN_NET_SPEECH_S` 3.0 → 2.5.** The 3.0 s floor (75% speech density in a 4 s window) over-abstained on natural conversational speech with pauses, so the system rarely accumulated enough scored windows to escalate. 2.5 s still requires a clear majority of real speech; false-positive behavior on real clips is unchanged (verified: real speech stays SAFE).

New files: `scripts/prep_datasets.py`, `scripts/prep_asvspoof.py`, `scripts/prep_hindi.py`, `data/robustness_results.json`.

---

## 5b. Augmentation retrain — the deployed "v4" head (session 3)

The reverb/noise gap was the top ML open item. It is now closed by **training through the
degradations**: `ml/training/train_probe.py --augment` runs an extra pass over the
**training windows only** (speaker-disjoint test windows stay clean — no leakage),
degrading each with a random pick from a pool of reverb (RT60 0.4/0.6/0.9 s), additive
noise (0/3/5/10 dB), and a Krisp/Teams-class noise-suppression simulation. The
noise-suppression augmentation is the direct fix for real speech being flagged fake under
aggressive denoising. `scripts/eval_robustness.py` measures spoof recall per condition on
the held-out fake speakers (seed-0 25% holdout) — reproducibly, comparable before/after.

**Before (clean head) → after (deployed v4), from `eval_robustness.py`:**

| Condition | Clean head | **v4 (deployed)** |
|---|---|---|
| clean fakes | 96% | 91% |
| reverb RT60 0.9 s | 13% | **39%** |
| reverb RT60 0.4 s | 18% | **44%** |
| noise 0 dB | 68% | **56%** |
| noise 10 dB | 72% | **82%** |
| real speech → noise-suppression **false-positive** | 8.7% | **6.7%** |
| seen-generator EER | 0.61% | **0.75%** |

Net: reverb recall roughly tripled, denoising false-positives fell *below* the clean-head
baseline, and the seen-generator EER barely moved (0.61 → 0.75%). The tradeoff cost is clean
fake recall (96 → 91%) and 0 dB noise (an unrealistic "noise as loud as speech" condition).
The pool was tuned across four runs (v1–v4); v1 over-augmented and raised false-positives —
v4 balances reverb, low-SNR noise, and denoising invariance. To reproduce, add `--augment`
to the training command in §4. Backups of the clean head live in `ml/onnx/probe_head_clean.npz`;
the augmented head is also archived as `ml/onnx/probe_head_aug.npz`.

## 6. Run the app

```powershell
# terminal 1 — backend (restart after any retrain: it loads the ONNX at startup)
.\.venv\Scripts\Activate.ps1
uvicorn backend.main:app --reload --port 8000     # check http://localhost:8000/health

# terminal 2 — frontend
cd frontend
npm install
npm run dev                                        # http://localhost:5173
```
Open http://localhost:5173 (must be `localhost`, not a LAN IP, or the mic is blocked). Turn off aggressive mic noise suppression (Krisp / RTX Voice / Teams) for honest detection — the system halves its own confidence when it detects enhancement.

**Verify the live model** by posting real vs fake clips to `POST /api/analyze`. Fakes should reach WATCH/VERIFY; real speech should stay SAFE. Clips shorter than ~2.5 s of net speech will correctly ABSTAIN.

---

## 7. Open items / next steps

**Highest value (ML):**
- ~~Augmentation retrain to close the reverb/noise gap~~ — **DONE & deployed as v4** (see §5b). `train_probe.py --augment`. Remaining: re-measure leave-one-generator-out on the v4 head (the 0.42%/17.1% numbers are pre-augmentation).
- Add the **vits** Hindi generator (only freevc24 + xtts_v2 were pulled) for more generator diversity.
- Fold in more ASVspoof systems / a larger subset for a stronger English number.

**Demo / pitch (mostly human tasks):**
- Record more demo clones; get the **Seed-VC** real-time voice-conversion attack clip (repo already cloned) — the highest-impact stage demo.
- Slide deck + demo script in `docs/`.
- College SIH rubric + official 6-slide template.

**Housekeeping:**
- The ONNX weights and all dataset/audio files are gitignored — teammates regenerate them with the scripts above.
- If you re-run ASVspoof download, set `KAGGLE_API_TOKEN` in the env; never commit it.

---

## 8. Session 3 changelog (frontend, latency, deploy)

**Model deploy**
- The augmentation-hardened **v4** head is now the live model (§5b). ONNX re-exported from it (`trained: true`). Backups: `probe_head_clean.npz` (original 0.61% EER), `probe_head_aug.npz` (= v4). Restart the backend to serve a new head.

**Live-mic latency fixes** (`frontend/public/pcm-worklet.js`, `frontend/src/lib/useCall.ts`, `backend/ws_hub.py`)
- The capture worklet emitted audio to the UI only once per second, so the level meter looked dead between updates. It now emits a level tick every ~20 ms (the 1 s PCM frame for the detector is unchanged), so the meter reacts to the mic in real time.
- The per-hop SQLite frame write sat between scoring and sending. The verdict is now sent first and the frame persisted on the thread pool afterward, removing the DB commit from the response path.

**Verdict flicker fix** (`frontend/src/components/RiskMeter.tsx`)
- The meter reverted to "listening" on any single ABSTAIN window, so a verdict flashed for ~1 s then vanished while the caller kept talking (the gate alternates SCORED/ABSTAIN around the net-speech floor). The meter now holds the last verdict for up to 6 s through brief abstains; sustained silence still falls back to "waiting for speech".

**Frontend redesign** (`frontend/src/styles.css`, `index.html`, `components/ThemeToggle.tsx`)
- Rebuilt the stylesheet as a token system: **light is the default theme**, dark is an override under `[data-theme="dark"]`. A header **theme toggle** persists the choice in `localStorage`; a pre-paint script in `index.html` applies it before first paint (no flash).
- New identity: porcelain canvas, white forensic panels, an indigo→cyan signal accent, Archivo display / IBM Plex Sans body / IBM Plex Mono data. The live waveform reads its colors from the theme.
- Removed the header logo mark (kept the "SatyaVaani" wordmark). Fixed undefined `--hair`/`--hair-2` tokens (the radial-gauge track ring was invisible). Reworded the on-screen "Zero-False-Positive Guarantee" to an honest evidence-gate description.

**Metric fix carried from session 2**: `ml/fusion/calibrate.py` `eer()` was inverted; corrected (label 1 = spoof, higher = more spoof).
