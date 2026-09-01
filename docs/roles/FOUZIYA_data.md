# FOUZIYA — Data Analyst

> Paste this whole file as the first message in your own Claude chat, then say what you're working on.

**You own:** `data/` and `attacks/`  ·  **Never edit:** backend/, ml/, frontend/, contracts/

**You are on the critical path.** Nothing in ML can be trained until your audio and clones exist.

---

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

You produce the **evidence**. Every number on the metrics slide comes from you.
Right now every figure we have belongs to someone else's paper. Your job is to make them ours.

## TASK 1 — Collect the recordings (BLOCKER, do first) ⏱ 1 hr

7 takes × at least 2 people, ideally 4. **Phone recording is fine.** Quiet room, fan/AC off,
phone 20–25 cm from mouth.

| # | Take | Length | Purpose | Save to |
|---|---|---|---|---|
| 1 | Clone reference, English | 90 s | what the cloners copy | `attacks/refs/<name>_ref_en.wav` |
| 2 | Clone reference, Hindi/regional | 60 s | the per-language table | `attacks/refs/<name>_ref_hi.wav` |
| 3 | The fraud line | 15 s | demo A/B | `attacks/refs/<name>_fraudline.wav` |
| 4 | Genuine, continuous | 30 s | false-positive test | `attacks/genuine/<name>_continuous.wav` |
| 5 | Genuine, with pauses | 30 s | false-positive test | `attacks/genuine/<name>_pauses.wav` |
| 6 | Genuine, stressed/urgent | 20 s | answers "what if upset?" | `attacks/genuine/<name>_emotional.wav` |
| 7 | On the **demo laptop mic** | 30 s | deployment condition | `attacks/genuine/<name>_demomic.wav` |
| + | Two 3-second clips | 6 s | the abstain demo | `attacks/genuine/<name>_short_1.wav` |

**THE ONE RULE THAT MATTERS:** audio you *clone from* (takes 1–3) and audio you *test on*
(takes 4–7) must be **different recordings**. Otherwise the detector is tested on its own
reference material and the false-positive rate is fiction. A judge will ask.

**NAMING:** `<name>_<what>.wav`. The part before the first underscore is the speaker ID —
the training script uses it to hold one speaker out entirely. Get this right and the
speaker-disjoint split happens automatically.

### Scripts to read

**Take 1 (English, ~90 s)** — phonetically varied on purpose: numbers, questions, plosives.
> My name is [name] and I'm a final year engineering student. I've been working on this
> project for about three weeks now, mostly in the evenings after class. The weather here has
> been strange lately — hot in the afternoon, then suddenly cold by eight o'clock.
> Yesterday I walked to the market to buy vegetables and ended up spending four hundred and
> fifty rupees, which is much more than I expected. My friend Rajesh called around six and
> asked whether I wanted to join them for dinner, but I had to finish some work.
> Sometimes I think we spend too much time in front of screens. Anyway, the project itself
> involves audio processing, machine learning, and quite a lot of debugging. Last Thursday the
> whole thing crashed twice before I found a single missing bracket.
> Zero, one, two, three, four, five, six, seven, eight, nine. Question — do you think this
> will actually work? I believe it will, though I'm not entirely certain yet.

**Take 2 (Hindi, ~60 s)** — any regional language works. More languages = stronger slide.
> मेरा नाम [नाम] है और मैं इंजीनियरिंग का छात्र हूँ। पिछले तीन हफ़्तों से मैं इस प्रोजेक्ट पर काम कर रहा हूँ,
> ज़्यादातर शाम को क्लास के बाद। कल मैं बाज़ार गया था सब्ज़ी लेने और लगभग चार सौ पचास रुपये
> ख़र्च हो गए, जो मैंने सोचा था उससे कहीं ज़्यादा है। मेरे दोस्त ने छह बजे फ़ोन किया और पूछा कि
> क्या मैं खाने के लिए आऊँगा। एक, दो, तीन, चार, पाँच, छह, सात, आठ, नौ, दस।
> क्या आपको लगता है कि यह काम करेगा? मुझे पूरा भरोसा है कि करेगा।

**Take 3 (the fraud line, ~15 s)** — matches the mock banking screen exactly.
> Listen, I need you to move fifty lakh rupees to Ramesh Trading Company today. The account
> ends four four one seven. It's urgent — the deal closes this evening. And please don't
> discuss this with anyone in the office, I'll explain everything tomorrow.

**Take 4 (genuine, continuous, ~30 s)** — different content from Take 1. **No pauses.**
> I usually wake up around seven, though on weekends it's closer to nine or ten. Breakfast is
> normally whatever's left over from the night before, which is not ideal but saves time. The
> commute takes roughly forty minutes each way depending on traffic near the flyover. I've
> been meaning to start cycling instead but haven't managed it yet. My laptop battery lasts
> about five hours now, down from eight when I bought it two years ago.

**Take 5** — same idea, pause 2–3 s between sentences. Talk about your day, no script.

**Take 6 (stressed, ~20 s)** — deliver fast, tense, raised voice.
> No no listen to me, I already told them twice, the deadline is tomorrow morning not next
> week, and if we don't submit tonight the whole thing is finished. Can you please just call
> him right now?

**Take 7** — demo laptop mic, normal room, read anything.
**Bonus** — "Hello? Yes, speaking." twice, separate files.

Convert phone recordings if needed:
```
ffmpeg -i input.m4a -ar 16000 -ac 1 output.wav
```

---

## TASK 2 — Generate the clones ⏱ 1 hr

Clone each Take-1 reference with **at least three generators**. Not one — three.
The failure mode in this field is **synthesis-method mismatch**: a detector that has only
seen one generator learns that generator's fingerprint and nothing else.

| Generator | How | Ref needed |
|---|---|---|
| **ElevenLabs** | elevenlabs.io free tier, "Instant Voice Clone" | ~60 s |
| **XTTS-v2** | `pip install TTS`, local, free | 6 s |
| **F5-TTS** | GitHub, open weights, local | ~10 s |
| Fish Speech | optional 4th | ~10 s |

Have each clone say the **Take 3 fraud line** plus a couple of the Take 4 sentences.

```
attacks/out/clones/elevenlabs/<name>_fraudline.wav
attacks/out/clones/xttsv2/<name>_fraudline.wav
attacks/out/clones/f5tts/<name>_fraudline.wav
```

The **folder name is the generator ID** — the training script uses it for
leave-one-generator-out. That's the honest number: performance against something never seen.

---

## TASK 3 — Seed-VC, the live conversion attack ⏱ 30 min · HIGHEST VALUE ITEM YOU HAVE

```
git clone https://github.com/Plachtaa/seed-vc
cd seed-vc && pip install -r requirements.txt
python real-time-gui.py
```
Convert one teammate's live voice into another's. Record the output to
`attacks/out/seedvc/<name>_converted.wav`.

**Why this matters more than anything else on your list:** in live voice conversion a *real
human is speaking* — real lungs, real prosody, real breathing. Only the timbre is synthetic.
Every prosody and breath signal correctly answers "human" and passes the attacker. It is the
attack that beats two thirds of naive detectors by construction.

Whoever demos this first owns the room. If a judge demos it first, we lose.

No GPU? Use offline conversion mode, or run it on Colab and download the output. A recorded
conversion is enough — it does not need to be live on stage.

---

## TASK 4 — Laundering + codec chain ⏱ 20 min, mostly waiting

```
python attacks/laundering.py  attacks/out/clones  attacks/out/laundered
python attacks/codec_chain.py attacks/out/clones  attacks/out/telephony
```
(codec_chain needs ffmpeg on PATH: `winget install Gyan.FFmpeg`)

These reproduce the degradations we must be able to answer for:

| Attack | Published effect on AASIST |
|---|---|
| Reverb RT60 0.9 s | 0.83% → **58.9%** EER |
| MP3 @ 16 kbit/s | 3.7% → **55.4%** EER |
| Resample 44.1 kHz | 1.06% → **39.6%** EER |
| Noise suppression (on **real** audio) | accuracy → **~0–11.8%** |

That last row is not an adversary — it's Zoom/Teams/Krisp making **real people look fake**.
It is the sleeper false-positive killer and almost nobody measures it.

---

## TASK 5 — Datasets (start downloading NOW, walk away) ⏱ 10 min clicking

```
bash data/download_datasets.sh
```
Then open in a browser and start the big ones:
- **ASVspoof 5** — asvspoof.org (registration)
- **In-the-Wild** — deepfake-total.com/in_the_wild — **HOLD OUT, never train on it**
- **CodecFake** — the backbone set, most transferable (22.3% macro EER)
- **Indic-CodecFake** — helixometry.github.io/IndicFake (CC BY 4.0)
- **IndicSynth** — needs `huggingface-cli login` (⚠ CC BY-NC, non-commercial)

Budget ~200 GB for everything. **Subsample aggressively** — breadth of generators matters
far more than hours of audio.

---

## TASK 6 — Fill `data/results.json` ⏱ ongoing, the real deliverable

This is the single most important artifact in the project. Until it exists, every number in
the deck belongs to someone else and "what's *your* EER?" has no answer.

Shape: copy `contracts/fixtures/metrics.json`. `GET /api/metrics/model` serves it
automatically once it exists.

Rows to fill:
| Condition | Source |
|---|---|
| ASVspoof 5 eval (in-domain) | dataset |
| In-the-Wild (held out) | dataset — **the honesty number** |
| Our clones, unseen generator | leave-one-generator-out |
| 8 kHz µ-law + packet loss | `attacks/out/telephony` |
| Reverb RT60 0.9 s | `attacks/out/laundered` |
| Noise-suppressed **bona fide** | `attacks/out/laundered/noise_suppression` |
| Seed-VC live conversion | `attacks/out/seedvc` |
| Per language: hi / ta / bn / en | your recordings + IndicSynth |

Columns: **EER · minDCF · actDCF · C_llr · FAR@1%FRR · abstain rate**. Never accuracy alone.

Run anything through `POST /api/analyze` (multipart wav) to get scores back.

**Empty cells are honest. Invented cells are the one mistake a technical panel will not
forgive.**

### The actDCF trap — worth understanding, it's our sophistication signal
minDCF uses an *oracle* threshold. actDCF uses one *fixed in advance*. In ASVspoof 5 many
strong systems posted minDCF ≈ 0.1 with **actDCF = 1.0000** — excellent separation, worthless
calibration; the organisers said such systems are "no better than a coin toss" at their real
operating point. **The gap between them IS deployment risk.** We report both.

---

## PROTOCOL RULES — a judge will ask about these
1. **Speaker-disjoint splits.** Detectors often learn speaker identity instead of synthesis
   artifacts. Without this the numbers are fiction. (Naming convention handles it.)
2. **Leave-one-generator-out.** Hold one generator family out entirely.
3. **Never train on In-the-Wild.**
4. **Report the degraded conditions**, all of them.
5. **Report the abstain rate** — what fraction of windows we decline to score.

## Handoffs
- **→ Faazil** the moment `attacks/refs/` and `attacks/out/clones/` have files
- **→ Annam** `data/results.json` as it fills, for the metrics slide
- **→ MrDexxo** if you need anything outside `data/` or `attacks/`
