# Training — runs on Colab / Kaggle T4, never on the demo laptop

## The one rule
**Training data beats architecture.** A controlled study of 96 systems found the front-end
spread was 8.1 EER points and the **back-end spread was 0.8**. Do not do architecture search.
Pick an MLP head, move on, and spend every remaining hour on data and augmentation.

## Recipe

1. **Backbone: CodecFake.** The most transferable training set measured (22.3% macro EER
   across 13 test sets, best-in-class on In-the-Wild despite being out of domain).
2. Pool in **ASVspoof 5**, **IndicSynth** (CC BY-NC 4.0 — non-commercial, check before any
   product claim) and **Indic-CodecFake** (CC BY 4.0).
3. Add **our own clones** from current commercial generators — ElevenLabs, XTTS-v2, F5-TTS,
   Fish Speech, and Seed-VC live conversion. This is what closes the 2026-generator gap.
4. **Hold out In-the-Wild entirely.** It is the honesty check, never a training set.
5. **Hold out one generator family entirely** and report leave-one-generator-out.
6. **Speaker-disjoint splits.** Detectors frequently learn speaker identity instead of
   synthesis artifacts. Without this our numbers are fiction and a judge will ask.

## Augmentation — highest ROI single addition
**RawBoost** (linear/non-linear convolutive + impulsive + stationary additive noise) was
designed for telephony, needs no external data, and gives ~27% relative improvement.
Then the explicit codec chain — see `attacks/codec_chain.py`.

Caveat from the literature: augment HARD during pre-training, GENTLY when fine-tuning on
a small real-world set.

## The counter-intuitive finding — internalise this
A detector trained only on Chinese data FAILED on other Chinese test sets (50.6% EER),
while Spanish-only training generalised second-best overall across English sets.
**The failure mode is synthesis-method mismatch, not language mismatch.**
So the goal is not "Indian-language data" — it is Indian-language data covering MANY
diverse and current generators. Getting this backwards is how the Indic story quietly fails.

## Files to write here
- `train_probe.py`  — freeze XLS-R, keep layers 1..7, mean-pool, fit a logistic probe (769 params)
- `export_onnx.py`  — export + int8 quantise into `ml/onnx/xlsr_l7_int8.onnx`
- `train_codec_lgbm.py` — LightGBM over `ml/features/spectral.py` → `ml/onnx/codec_lgbm.txt`
- `eval.py`         — writes `data/results.json` (EER, minDCF, actDCF, C_llr, FAR@1%FRR, per-language)
