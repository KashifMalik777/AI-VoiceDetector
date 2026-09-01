# MIQDAAD — Frontend Developer

> Paste this whole file as the first message in your own Claude chat, then say what you're working on.

**You own:** `frontend/`  ·  **Never edit:** backend/, ml/, data/, attacks/, contracts/

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

**You build what the judges actually look at.** The architecture is invisible; your screen is
the product. A 90-second demo lives or dies on this.

You are **never blocked on the backend.** If it isn't running:
```
python mocks/mock_server.py
```
Same routes, same message shapes, fixture data, no dependencies. Build against it freely.

## What already exists and works
| Component | State |
|---|---|
| `lib/useCall.ts` | AudioWorklet mic capture → 16 kHz resample → WS. Works. |
| `components/RiskMeter.tsx` | big number, band colour, **ABSTAIN state** |
| `components/Waveform.tsx` | Canvas level trace (not SVG — SVG drops frames) |
| `components/ReasonsPanel.tsx` | ranked reasons + per-detector scores |
| `components/TransactionGate.tsx` | mock banking screen, hold, override flow |
| `components/Timeline.tsx` | per-window score history |
| `components/QualityStrip.tsx` | net speech / SNR / packet loss / enhancement flag |
| `styles.css` | full design system, light + dark, no Tailwind dependency |

Stack: **Vite + React + TypeScript**, plain CSS. Vite over Next deliberately — no SSR
friction with WebSockets. Add Tailwind/shadcn if you prefer; it's your directory.

---

## TASK 1 — Metrics page ⏱ 1 hr · this is a whole slide

New route/tab. `GET /api/metrics/model` returns `data/results.json` (or the empty template).

Render:
- the **conditions table** — EER · minDCF · **actDCF** · FAR@1%FRR · abstain rate, one row per
  condition (in-domain, In-the-Wild, our clones, 8 kHz telephony, reverb, noise-suppressed,
  Seed-VC)
- the **per-language table** — hi / ta / bn / en, EER **and** false-positive rate
- **runtime**: RTF, ms/window, RAM, threads

**Empty cells must render as "not measured", never as 0 or a dash that looks like a value.**
The API tells you which: `_source` is `"measured"` or `"template (not yet measured)"`. Show a
banner when it's the template.

An invented-looking number on this page is worse than an empty one.

---

## TASK 2 — Admin panel ⏱ 45 min · the "this is real" moment

`GET /api/config` → editable form → `PUT /api/config`.

Sliders/inputs for: band thresholds, fusion weights, risk weights, context weights, gate
floors (min speech, min SNR), EMA alpha, K-of-N, per-intent thresholds.

**Why this earns its hour:** at 1:35 in the demo we drag a threshold and the behaviour
changes live. Nothing says "this is a real system" like retuning it in front of someone.

Make it obviously live — show the current value, apply on change, and reflect the new
threshold on the meter's tick marks.

---

## TASK 3 — Replay mode ⏱ 45 min · the safety net

**One keystroke** plays a pre-recorded call through the same pipeline.

- Load a WAV from `attacks/` (file picker or a hardcoded demo list)
- Stream it over the **same WebSocket** as the mic, 1 s frames, in real time
- Show a small "REPLAY" badge — we say it out loud, we don't hide it

Same pipeline means the fallback is **honest**, not a separate fake. If the venue mic dies on
stage, this is what saves the demo. Bind it to a key that can't be hit by accident.

---

## TASK 4 — Demo choreography polish ⏱ 1 hr · rehearse against `docs/demo_script.md`

The two minutes that decide the round. Make each beat land visually:

| Time | Beat | What you need to nail |
|---|---|---|
| 0:15 | **ABSTAIN** on a 1-second utterance | must read as a *deliberate refusal*, not a loading state |
| 0:44 | meter climbs green → amber → red | smooth, ~4 s, no flicker (EMA already handles the data) |
| 0:50 | Approve → **"Verify caller to continue"** | the button *changes*, never disappears |
| 1:00 | override: 2 clicks, ~8 s | reason picker must be fast and obvious |
| 1:05 | audit ledger view | show the chained hash, prev → current |
| 1:50 | "no audio stored" | a panel listing exactly what IS stored |

**Readability from the back of a room.** Big numbers, high contrast, nothing under 14px that
matters. Test at 150% browser zoom.

---

## TASK 5 — Audit ledger + privacy panel ⏱ 30 min

- `GET /api/audit/entries` → chained list, show `prev_hash → hash`
- `GET /api/audit/verify` → a green "chain intact" badge; red with the broken index if not
- **Privacy panel**: list the columns we actually store (features, embeddings, hashes,
  scores, model version, timestamps) and state plainly that no audio is written to disk

Line to put on the screen: **"We log decisions, not voices."**

---

## TASK 6 — Session history ⏱ 30 min, if time

`GET /api/sessions` → list → click into a past session's timeline. Useful for the demo
("here are the last five calls") and for the evidence-packet story.

---

## CONTRACT — the message shapes you must honour
`contracts/ws-protocol.md` and `contracts/schemas.json` are **frozen**. `src/lib/types.ts`
mirrors them. If you need a field that doesn't exist: tell MrDexxo, the contract changes
first, then Mustafa and you adapt in your own directories.

Two things to get right:
- `state` is `SCORED` or `ABSTAIN`. On ABSTAIN there is **no `risk` and no `band`** —
  do not render a number, do not render a zero.
- `quality.enhancement_detected` true means noise suppression was detected. Surface it —
  it explains a low-confidence score and it's a real Q&A moment.

## Handoffs
- **← Mustafa** the real WS; use the mock until it's up
- **← Fouziya** `data/results.json` for the metrics page; template until then
- **→ Annam** screenshots for the deck as things land
