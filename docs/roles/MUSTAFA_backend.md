# MUSTAFA — Backend Developer

> Paste this whole file as the first message in your own Claude chat, then say what you're working on.

**You own:** `backend/`  ·  **Never edit:** ml/, frontend/, data/, attacks/, contracts/

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

You own the one FastAPI process that holds the API, the WebSocket hub and the ML boundary.

**The most important architectural decision in this project:** there is no second service.
A Node backend plus a Python ML service would mean an extra hop, two deploys, two dependency
trees and a full integration day we do not have.

You import exactly one thing from ML:
```python
from ml.registry import get_detectors
```
Nothing else. If Faazil's detectors aren't ready, registry hands you stubs and everything runs.

## What already works
| File | What it does |
|---|---|
| `main.py` | app, CORS, startup, `/health`, WS route |
| `ws_hub.py` | live path — 4 s window / 1 s hop, ring buffer, per-session state |
| `risk.py` | fusion → EMA → **K-of-N persistence** → context lift → bands |
| `db.py` | SQLite; **features + hashes only, zero audio** |
| `audit.py` | hash-chained ledger + verify |
| `routes/api.py` | sessions, analyze, enroll, alerts, override, metrics, config, audit |
| `config.py` | runtime-editable thresholds; DB path prober |

Verified working: WS streams, gate abstains then scores, alerts fire on band escalation,
audit chain verifies **and detects tampering**, DB confirmed to hold no audio.

---

## TASK 1 — Speaker enrolment end-to-end ⏱ 30 min

`POST /api/enroll` exists but 503s until resemblyzer is installed (Faazil's task).
Your side: once a voiceprint exists, `ws_hub.LiveSession.enrolled` must be **populated** so
`WindowContext.enrolled_embedding` reaches the speaker detector.

Right now it's hard-coded `None` — so speaker drift can never fire. Wire it:
- accept a `voiceprint_id` in the WS `start` message
- load the embedding from the `voiceprints` table
- set `live.enrolled`

**This is the difference between the speaker detector working and being decorative.**

---

## TASK 2 — Neural detector scheduling ⏱ 20 min

The neural detector costs 127 ms; codec + gate + features cost ~13 ms. Today all three run
every hop inside one executor call. That's fine at 142 ms total — but if the model ever gets
heavier (layer 7 → a bigger backbone, or a slower demo laptop), the 1 s hop backs up
unboundedly and the meter falls behind.

Add a `neural_every_n` config knob (default 1):
- codec + gate + speaker run **every hop**
- neural runs every Nth hop; between runs, reuse its last score

Then it degrades gracefully instead of collapsing. Honest framing for the pitch:
*"the fast detectors run every second, the heavy one every two — the meter never goes stale."*

---

## TASK 3 — Session history + report export ⏱ 45 min

- `GET /api/sessions` and `GET /api/sessions/{id}` already return the timeline
- Add `GET /api/sessions/{id}/report` → a JSON evidence packet: session meta, score
  timeline, alerts, overrides, model version, ledger hashes
- That's the **I4C / CFCFRMS evidence packet** on the impact slide. Real-world framing:
  forensic-grade, exportable, no audio.

---

## TASK 4 — Admin config endpoint polish ⏱ 20 min

`GET/PUT /api/config` works. Make sure **every** threshold in `contracts/fixtures/config.json`
is live-editable and takes effect on the **next window** without a restart:
bands, fusion weights, risk weights, context weights, gate floors, smoothing, intent thresholds.

**Why this matters:** retuning a threshold live in front of a judge is worth more than any
single point of accuracy. Miqdaad is building the UI for it — you make it actually work.

---

## TASK 5 — Alert channels ⏱ 20 min

Alerts currently push over WS and land in the DB. Add mock SMS/email: a `notifications` table
+ `GET /api/notifications`. Logged, not sent. Renders as a feed in the UI.

Slide 4 says "multi-channel alerts" — this is the honest minimum that makes it true.

---

## THE RULES YOUR CODE ENCODES — do not soften them
1. **The system never cancels.** It holds and a human releases. At HOLD the Approve button
   does not disappear — it *changes*. `risk.py` `RECOMMENDATION` / `ACTION` maps encode this.
2. **Abstain never escalates.** `gate.check()` fails → no score, no band, no alert.
3. **Low confidence can reach VERIFY, never HOLD.** Guard is in `RiskEngine.step()`.
4. **K-of-N persistence, not a mean.** A mean can be gamed by splicing in real speech to
   dilute the average. Keep `persist_k` / `persist_n`.
5. **No audio on disk. Ever.** `Frame.features_json`, never bytes. This is the DPDP answer,
   the CERT-In answer ("we log decisions, not voices"), and a 20-second live demo moment.
6. **Every verdict carries `model_version`.** A score with no model version isn't auditable.

## Bugs already found and fixed here — don't reintroduce
- **SQLite dies on mounted/network/OneDrive/WSL drives** ("disk I/O error"). `config.py`
  `_pick_db_path()` probes cwd → `~/.satyavaani` → tempdir. Keep it.
- **The audit chain failed its own verification.** SQLite has no timezone type: a tz-aware
  datetime goes in as `+00:00` and comes back naive, so hashing the raw isoformat never
  matched. `audit._ts()` normalises both sides. **This would have failed live on stage.**

## Handoffs
- **← Faazil** detectors via `get_detectors()` — you are never blocked on him
- **→ Miqdaad** any WS/REST change goes through `contracts/` first, then you tell him
- **→ MrDexxo** anything touching `contracts/`
