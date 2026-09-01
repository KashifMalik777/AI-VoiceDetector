# ANNAM — Team Lead · PPT · Pitch

> Paste this whole file as the first message in your own Claude chat, then say what you're working on.

**You own:** `docs/`, the deck, the pitch, the schedule  ·  **You do not write feature code**

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

Two things nobody else can do: **the story**, and **holding the gates**.

The build is in good shape. Most SIH teams lose on presentation and integration, not on code.
That is your surface area.

---

## TASK 1 — The deck ⏱ 3 hrs · official format, 6 slides, PDF only

⚠ Download the template from **sih.gov.in**. Third-party 8/10/13-slide versions on blogs are
**not official** and following one is an unforced error.

**Slide 0 (title):** PS ID 26104 · PS title · Theme: Blockchain & Cybersecurity ·
Category: Software · Team ID & Team Name exactly as registered.

### Slide 1 — Proposed Solution
- Scores caller's voice **while they speak** — ~4 s verdict, 1 s refresh
- **Holds, never cancels** — officer releases in 2 clicks, logged
- **Abstains** when unsure — "insufficient evidence", never guesses
- **3 scores**: synthetic / replay / speaker-match
- **Explains itself** — ranked reasons, never a bare %

**Innovation box:** FRI scores the number · CNAP the registered name · KBA leaked secrets →
**nothing scores the human speaking**

**DIAGRAM — "The Unguarded Zone"** (this one earns its space): a horizontal call timeline.
CNAP, FRI and KBA all fire *before* the call connects, each with a down-arrow labelled
"authenticates the CHANNEL". Then a red shaded band — CALL IN PROGRESS, voice unguarded,
this is where the fraud happens. Our layer arrows *up* into that band.

### Slide 2 — Technical Approach
**DIAGRAM:** the 6-stage pipeline (from the shared context above) with the **red dashed
ABSTAIN branch**. That branch is the differentiator — almost nobody ships one.

Stack table + KPI strip: **8.4%** OOD EER · **101.3M** params · **127 ms/window** ·
**RTF 0.036** · **~4.4 s** first verdict · **73 files** already running

### Slide 3 — Feasibility & Viability
Feasible: prototype runs today · zero licence cost · free Colab T4 · SIPREC/AudioHook
integration path exists

**DIAGRAM — the credibility bar chart.** AASIST, same model, worsening conditions:
`0.82% → 43.0% → 58.9% → 58.1%` with a dashed line at 50% marked "coin flip".
Caption: real fraud calls, AUC 39 — worse than random.

Then risk → mitigation (6 rows): generalisation · live voice conversion · telephony/reverb ·
noise suppression making real people look fake · false positives · adversarial.

### Slide 4 — Impact & Benefits
Scale: **₹22,495 cr** · **28.15 lakh** complaints · **9%** digital arrest · **1 in 5**
Indians targeted · **69%** can't identify a clone

**DIAGRAM:** Source → Integration → Our layer → Beneficiaries
(bank/telecom/enterprise → SIPREC/AudioHook → SatyaVaani → officer/customer/I4C)

Three columns: Economic (~₹25/call vs ₹50 L loss) · Social & Equity (non-metro,
regional-language callers — measured FPR, not assumed) · Governance (RBI FRI, TRAI 1600,
RBI Auth Directions 2025, FREE-AI sutras, DPDP, CERT-In)

### Slide 5 — Research & References
Four groups, ~12 entries, name + one-line relevance + QR to the repo.
Most teams leave this slide thin. Don't.

**DECK RULES:** diagrams ≈ 50% of each slide · numbers in bold · never invent a figure ·
one topic per slide, never continue onto the next.

---

## TASK 2 — Hold the gates ⏱ this is the job nobody else will do

| When | Gate | What you do |
|---|---|---|
| Day 1 end | end-to-end green | 30 min: everyone pulls main, runs the demo script together |
| Day 2 noon | integration #2 | same |
| Day 2 6pm | **model decision** | fine-tune vs baseline on held-out set. **Winner ships, decided by the number, not by argument.** |
| Day 2 end | integration #3 | same |
| Day 3 11am | **last merge** | nothing new after this. Bug fixes only. |
| Day 3 2pm | **CODE FREEZE** | everyone off keyboards. Then three full dry runs. |

**Integration failure is the single most cited reason SIH teams lose.** Three 30-minute
checkpoints prevent it. You are the only person who will enforce these — everyone else will
be heads-down and will want "just five more minutes".

---

## TASK 3 — Own the Q&A ⏱ 1 hr

Assign each battlecard question a named owner so nobody freezes waiting for someone else.
Suggested: technical → Faazil, data/metrics → Fouziya, UX/demo → Miqdaad,
architecture/deployment → Mustafa, impact/regulation/business → you.

**Three habits that win Q&A:**
1. **Show, don't assert** — every answer has something on screen behind it
2. **Concede real limits** — "adversarial audio degrades it" makes everything else credible
3. **Never bluff a number** — "we didn't measure that, here's how we would" is a good answer;
   an invented figure ends the round

Everyone needs a **60-second version and a deep version** of every answer. Panels are mixed —
some judges want business, some want architecture.

---

## TASK 4 — Rehearse the demo ⏱ 1 hr, day 3

`docs/demo_script.md` has the timed beats. Three clean runs on the **actual demo laptop**,
with **its own mic**, at the **room's real volume**. A quiet room lies to you about levels.

Two beats matter most — they're where we preempt the hardest question:
- **1:00** — "But what if we're wrong?" → Release, pick a reason, done. Two clicks.
- **1:15** — run our own Seed-VC attack and name which detector catches it

If something breaks: press the replay key and say **"this is a replay"** out loud, immediately.
Same pipeline, so it's honest. Hiding a fallback costs more than naming one.

---

## TASK 5 — Two things only you can chase
1. **Your college's internal SIH rubric, from the SPOC.** It is not standardised nationally
   and it's the only rubric actually scoring this round.
2. **The official 6-slide template from sih.gov.in.**

---

## NEVER SAY THESE — brief the whole team
- ❌ "99% accurate" → quote EER, minDCF, FAR at a fixed FRR
- ❌ "it can't be fooled" → everything in this field can be fooled
- ❌ "it's blockchain-based" → it is a **hash-chained append-only log**. Say that.
  Precision reads as expertise; the buzzword reads as bluffing.
- ❌ "works in all 22 languages" → say the number you measured
- ❌ "connected to real banking" → the transaction screen is **our own mock**, labelled
  on screen and said out loud
- ❌ "runs on 1 CPU core" → measured, 1 thread = 5271 ms. Say **"127 ms per 4-second window
  on a laptop CPU, 8 threads, no GPU."**
- ❌ **any number not in `data/results.json`**

⚠ **Accuracy warning:** "83% of Indians lost money to voice scams" is a **misquote** — it is
83% of Indian *victims*. Use **"1 in 5 targeted"**. A Cyber Security Cell judge may know.

⚠ **Know your neighbour:** IIT Kharagpur has an IndiaAI-funded "Real-Time Voice Deepfake
Detection System" project. **Cite it as validation of the need**, then differentiate:
banking/telecom integration, FRI interoperability, Indic accent parity, DPDP-native
architecture. Pretending the space is empty is worse than acknowledging it.

## Lines worth memorising
- **Opening:** "Existing systems tell you a call was fake after the money is gone.
  SatyaVaani tells you while the caller is still speaking — and holds the transfer until a
  human verifies."
- **India framing:** "RBI has ordered every bank to ingest a fraud risk score for the phone
  number. Nobody produces one for the voice. We're the missing sensor in plumbing that
  legally already exists."
- **On accuracy:** "Every sub-1% number in this field is an in-domain number. We'd rather
  show you our out-of-domain number than a headline we can't defend."
- **On false positives:** "It holds. It never cancels. Thirty seconds of friction against
  fifty lakh rupees — and the officer clears it in two clicks, logged."
- **Closing:** "We're not claiming to solve deepfake detection. We're claiming to be the
  layer that raises the attacker's cost and gives a bank officer a real-time signal they
  currently do not have — with honest numbers about where it stops working."

## A process story worth telling if asked how you built it
Four real bugs were found by *running* the system, not reviewing it:
an O(n²) autocorrelation costing 759 ms/window (fixed, 70×); SQLite failing on mounted
drives; the audit chain failing its own verification (**would have failed live on stage**);
and a VAD that rejected *good* speech — **the better you spoke, the worse it scored**.
Three of the four were invisible to code review. That's the argument for testing early on
real hardware.

## Handoffs
- **← everyone** metrics, screenshots, status
- **→ everyone** the gates. Hold them.
