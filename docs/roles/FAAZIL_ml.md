# FAAZIL — AI/ML Developer

> Paste this whole file as the first message in your own Claude chat, then say what you're working on.

**You own:** `ml/`  ·  **Never edit:** backend/, frontend/, data/, attacks/, contracts/

# SHARED CONTEXT — every role file starts with this

**SIH PS 26104** · AICTE Cyber Security Cell · Theme: Blockchain & Cybersecurity · Software

## What we're building — SatyaVaani
A real-time voice integrity layer. It listens to a live call, scores every second whether
the voice is AI-generated, explains why in plain language, and **holds** a transaction until
a human verifies.

Three defining properties:
1. **Works during the call** — first verdict ~4 s, updates every 1 s
2. **Holds, never cancels** — Approve becomes "Verify caller"; officer releases in 2 clicks, logged
3. **Abstains when unsure** — under 3 s of clean speech it says "insufficient evidence"

## The pitch in one line
> FRI scores the **number**. CNAP scores the **registered name**. KBA scores **leaked secrets**.
> **Nothing scores the human speaking.** We are that sensor.

## Pipeline
```
CAPTURE      GATE            DETECT               FUSE     SCORE      ACT
                    +-> Neural artifact ---+                    +-> Dashboard
Browser -> Evidence +-> Codec & channel ---+-> Fusion -> Risk  -+-> Hold&verify
mic        gate     +-> Speaker&trajectory-+  (Platt)  engine   +-> Audit ledger
16kHz PCM  VAD 4s/1s      |
           noise tracker  v
                    [ ABSTAIN ]  <- <3s speech / low SNR
```

## THE RULES — non-negotiable
1. **One owner per top-level directory.** Never edit another person's directory.
   Need something from it? Change `contracts/`, announce it, both sides adapt.
2. **`contracts/` is FROZEN.** Changing it requires everyone to agree.
3. **`main` is always demoable.** Nothing merges that breaks `docs/demo_script.md`.
4. **Never invent a number.** If it isn't in `data/results.json` it doesn't go on a slide
   or in a sentence. "We didn't measure that, here's how we would" is a good answer.
5. **Integrate 3x**: Day1-end, Day2-noon, Day2-end. 30 min, everyone pulls main, runs the demo.

## Hard gates
| When | Gate |
|---|---|
| Day 1 end | end-to-end green; RTF measured on the demo laptop |
| Day 2, 6pm | fine-tune vs baseline on held-out set — winner ships, decided by NUMBER |
| Day 3, 11am | last merge for anything new |
| Day 3, 2pm | **CODE FREEZE.** Everyone off keyboards. Rehearsal only. |

## Where things stand (30 Aug 2026)
- contracts, mock server, backend (WS + gate + risk + audit ledger), frontend: **all running**
- Neural detector: XLS-R L7 ONNX exported, **127 ms/window**, but **head UNTRAINED -> abstains**
- Codec detector: live, rule-based (LightGBM not yet trained)
- Speaker detector: **STUB** (needs resemblyzer)
- Audio recordings: **NOT DONE — this blocks all ML work**
- `data/results.json`: **EMPTY — this blocks the metrics slide**

## Measured on our demo laptop — real numbers, use these
| Metric | Value |
|---|---|
| Full pipeline per window | **142.6 ms** (RTF 0.036) |
| Neural detector alone | **126.8 ms** |
| Headroom in the 1 s hop | **+857 ms** |
| Model | XLS-R-300M truncated @ layer 7, **101.3M params**, fp32, 8 threads |
| Config finding | int8 was **4.6x SLOWER** than fp32 on this CPU; ONNX 1.52x faster than torch |

⚠ Do NOT say "runs on 1 CPU core" — measured, 1 thread = 5271 ms. Say
**"127 ms per 4-second window on a laptop CPU, 8 threads, no GPU."**

## Setup on any machine
```
cd satyavaani
python -m venv .venv ; .\.venv\Scripts\Activate.ps1     # Windows
pip install -r requirements.txt
pip install torch --index-url https://download.pytorch.org/whl/cpu

# terminal 1
uvicorn backend.main:app --reload --port 8000
# terminal 2
cd frontend ; npm install ; npm run dev
```
No backend yet? `python mocks/mock_server.py` — same routes, fixture data.

---

# YOUR JOB

You own the three detectors and the fusion. The backend imports **exactly one thing** from you:

```python
from ml.registry import get_detectors
```

That is the entire seam. Everything else in `ml/` is private to you. If a detector fails to
load, `registry.py` falls back to its stub with a warning — the demo never crashes.

## Current state
| Detector | Status | File |
|---|---|---|
| **neural** | ONNX exported, 127 ms, **head UNTRAINED → abstains** | `ml/detectors/neural.py` |
| **codec** | live, rule-based; LightGBM not trained | `ml/detectors/codec.py` |
| **trajectory** | **STUB** — needs resemblyzer | `ml/detectors/speaker.py` |

---

## TASK 1 — Train the probe (blocked on Fouziya's audio) ⏱ 30 min once audio exists

The backbone is 101.3M **frozen** params. You train only the small linear head on top —
minutes on CPU, not hours on GPU. That means you can retrain every time new audio lands.

```
python ml/training/train_probe.py --real attacks/genuine attacks/refs --fake attacks/out/clones
python ml/training/export_backbone.py --head ml/onnx/probe_head.npz
python scripts/bench_rtf.py
```

`export --head` bakes the trained weights into the graph and flips `model_card.json` to
`trained: true` — that's what makes the detector stop abstaining.

Then the honest run:
```
python ml/training/train_probe.py --real ... --fake ... --holdout-generator elevenlabs
```
That number — performance against a generator never seen in training — is the one worth
quoting.

**The script enforces speaker-disjoint splitting automatically** (groups by the name before
the first underscore). If only one speaker exists it warns you and tells you not to quote the
result. Listen to it.

### Why layer 7, in case you're asked
| config | OOD mean EER | params |
|---|---|---|
| **XLS-R truncated @ L7 + linear probe** | **8.4%** | **101M** |
| XLS-R truncated @ L5 | 16.2% | ~70M |
| full W2V2-300M fine-tuned + AASIST | 11.3% | 318M |
| full W2V2-300M | 16.9% | 300M |
| RawGAT-ST | 27.0% | 0.44M |

Truncation **beats** the full model — deeper layers encode linguistic content that hurts
generalisation. ~3× less compute and a better number.

A controlled study of 96 systems found the **front-end** spread was 8.1 EER points and the
**back-end** spread was 0.8. **Do not do architecture search.** Spend the time on data.

---

## TASK 2 — Wire the speaker detector ⏱ 45 min · HIGHEST VALUE ITEM YOU HAVE

```
pip install resemblyzer
```
Then in `ml/detectors/speaker.py` set `EMBEDDER_READY = True`. The code is written — it does
two things:
1. **Speaker-embedding drift** vs an enrolled reference (cosine distance)
2. **Trajectory analysis** — genuine speech traces smooth paths through embedding space;
   spliced or edited segments cause abrupt discontinuities. Training-free.

### Why this slot is not prosody, and why that matters
This detector **used** to be prosody + breath. Both were removed:
- **"No breath sounds"** — ElevenLabs v3 produces breathing on demand via `[exhales]` tags.
  Four characters of prompt defeats it. And humans breathe every 4–7 s, so a 4 s window can
  barely observe it at all. The paper that *invented* the signal says both in its limitations.
- **"Flat pitch"** — best prosody-only paper: 93% accuracy but **24.7% EER**. Against
  expressive 2026 TTS it goes to 18.9%.
- **The real killer:** in **live voice conversion** (Seed-VC, ~430 ms) a *real human is
  speaking*. Real lungs, real prosody, real timing. Only timbre is synthetic. Every prosody
  signal correctly answers "human" and passes the attacker.

Voice conversion changes **timbre** — which is exactly what a speaker embedding measures.
That's why this detector exists in this form.

Prosody survives as a low-weight auxiliary feature only. **Never a headline reason.**

---

## TASK 3 — Train the codec detector's LightGBM ⏱ 30 min

`ml/detectors/codec.py` currently uses a rule-based fallback. Train the real thing:
- Features already exist: `ml/features/spectral.py`, ~40 per window, `FEATURE_NAMES` is the contract
- Train on the same real/fake split as the probe → `ml/onnx/codec_lgbm.txt`
- Flip `USE_TRAINED = True`

Bonus you get free: LightGBM feature importances become the officer's **reasons panel**.
A single end-to-end model cannot tell an officer *why*.

---

## TASK 4 — Fusion calibration ⏱ 20 min

`ml/fusion/calibrate.py` has `fit_platt()` and every metric already implemented
(EER, minDCF, actDCF, C_llr, FAR@1%FRR). Fit the Platt coefficients on a held-out split and
put them in `contracts/fixtures/config.json` → `fusion_weights`.

**Calibration matters more than discrimination here.** See the actDCF trap in Fouziya's brief.

---

## TASK 5 — Augmentation if you have time

**RawBoost** is the highest-ROI single addition: designed for telephony, needs no external
data, **+27% relative improvement**. Then the codec chain (µ-law, GSM, AMR, G.729, Encodec)
+ RIR. `attacks/codec_chain.py` and `attacks/laundering.py` already generate these — just
pool them into training.

Caveat from the literature: augment **hard** during pre-training, **gently** when fine-tuning
on a small real-world set.

---

## THINGS THAT WILL GET US KILLED IN Q&A — do not do them
- ❌ **Do not swap in a popular HuggingFace deepfake model.** `MelodyMachine/...` and family
  are the most-downloaded in this space and every other team will use them. Their cards say
  "More information needed" for training data and report accuracy with no EER. Comparable
  architectures score ~38% EER out of domain.
- ❌ **Do not train on In-the-Wild.** It's the honesty check.
- ❌ **Do not report accuracy alone.** EER + minDCF + actDCF + C_llr + FAR@1%FRR.
- ❌ **Do not let a half-wired detector return a real-looking score.** The pattern is already
  built: `abstain=True` costs the compute but contributes nothing. Keep it.

## Config that's already decided — don't re-litigate without measuring
- **fp32, not int8.** Measured: int8 was **4.6× SLOWER** on our CPU (dynamic quantisation adds
  quantise/dequantise around every MatMul, and this part lacks the AVX512-VNNI path).
- **8 threads.** 1 thread = 5271 ms, 8 threads = 127 ms. A 41× difference.
- Both recorded with reasoning in `ml/onnx/model_card.json`.

## Handoffs
- **← Fouziya** audio and clones — you're blocked on these
- **→ Annam** every metric you produce, for the slide
- **→ MrDexxo** if you need anything outside `ml/`
