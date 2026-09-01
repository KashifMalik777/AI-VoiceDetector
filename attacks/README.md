# attacks/ — we attack ourselves, first

**Whoever demos the real-time voice-conversion attack first owns the room. If a judge
demos it first, we lose.**

This directory is a build dependency, not a nice-to-have. Every number in the "degraded
conditions" rows of `data/results.json` comes from here.

## 1. Clone our own voices — TONIGHT

Record 30–60 s of clean speech from two team members (`attacks/refs/<name>.wav`), then
generate clones with **at least three current generators**:

| Generator | How | Ref audio needed |
|---|---|---|
| **XTTS-v2** (Coqui) | `pip install TTS`, local, free | 6 s |
| **F5-TTS** | open weights, local | ~10 s |
| **Fish Speech** | open weights, local | ~10 s |
| **ElevenLabs** | free tier, web UI | ~60 s |

Why three and not one: the failure mode in this field is **synthesis-method mismatch**.
A detector that has only seen one generator learns that generator's fingerprint.

## 2. Seed-VC — the attack that matters most

Real-time voice conversion converts a **live** voice in ~430 ms from 1–30 s of reference.
In that attack a real human is speaking: real lungs, real prosody, real breathing, real
conversational timing. **Only the timbre is synthetic.**

This is why prosody and breath were removed as decision rules, and why the third detector
is speaker-embedding drift — VC changes timbre, which is exactly what an embedding measures.

```bash
git clone https://github.com/Plachtaa/seed-vc && cd seed-vc
pip install -r requirements.txt
python real-time-gui.py     # feed our mic in, route output to a virtual cable
```

Record the converted output into `attacks/out/seedvc/` and run it through `POST /api/analyze`.
**Report the number you get, whatever it is.**

## 3. Laundering and codec chain

```bash
python attacks/laundering.py  attacks/out/clones  attacks/out/laundered
python attacks/codec_chain.py attacks/out/clones  attacks/out/telephony
```

These reproduce the published degradations we must be able to answer for:

| Attack | Published effect on AASIST |
|---|---|
| Reverb RT60 0.9 s | 0.83% → **58.9%** EER |
| MP3 @ 16 kbit/s | 3.7% → **55.4%** EER |
| Resample to 44.1 kHz | 1.06% → **39.6%** EER |
| Replay + re-record | 4.7% → **18.2%** EER (W2V2-AASIST) |
| Noise suppression (bona fide) | accuracy → **~0–11.8%** |

That last row is not an adversary. It is Zoom, Teams and Krisp making **real people look
fake** — the sleeper false-positive killer.

## 4. The rule
Everything generated here is **held out of training** except where `train_probe.py`
explicitly pools it, and at least one generator family is held out entirely so we can
report leave-one-generator-out. Self-generated test sets leak fingerprints and inflate
every number.
