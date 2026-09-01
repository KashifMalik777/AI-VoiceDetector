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
