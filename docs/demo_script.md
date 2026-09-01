# Demo script — rehearse until it is muscle memory

A demo is a performance with a script, not an improvisation. Three clean dry runs on the
**actual demo laptop**, with **its own mic**, at the **room's real volume**.

## Setup before you start
- Backend on `localhost:8000`, frontend on `localhost:5173`. **Wifi physically off.**
- Clone clip of the volunteering judge (or a teammate) pre-loaded and one keystroke away
- Seed-VC output clip pre-loaded — the self-attack
- Reverb-laundered clip pre-loaded
- Replay-mode fallback bound to one key
- Browser zoom set so the meter is readable from the back of the room

## The two minutes

| Time | What happens | What you say |
|---|---|---|
| 0:00 | Judge speaks into the mic. Meter green, 8–15. | "Scoring every second on a rolling four-second window." |
| 0:15 | Judge speaks for **one second only** → **ABSTAIN**. | **"Most systems would guess here. We say we don't have enough evidence. An abstain can never escalate."** |
| 0:30 | ₹50,00,000 transfer appears. Approve is live. | "This is our own mock banking screen — not connected to any real system." |
| 0:40 | Play the cloned voice of that same person. | "Same speaker. Cloned." |
| 0:44 | Meter climbs green → amber → red within ~4 s. Reasons flip. | "Codec fingerprint, speaker drift, high-frequency rolloff." |
| 0:50 | Approve becomes **"Verify caller to continue"**. | **"The transfer is held. Not cancelled."** |
| 1:00 | **PREEMPT.** "But what if we're wrong?" → Release, pick a reason, done. | "Two clicks. Eight seconds. And it's logged." |
| 1:05 | Open the audit ledger — the override is chained. | "Tamper-evident append-only log. Not a blockchain — a chained log." |
| 1:15 | **ATTACK OURSELVES.** Run the Seed-VC live conversion clip. | **"Here's the attack that beats prosody entirely — a real human speaking through live voice conversion. Real lungs, real breathing. Only the timbre is fake. Speaker-embedding drift is what catches it, not prosody."** |
| 1:35 | Metrics tab. EER, minDCF, **actDCF**, per-language, degraded rows. | "Our numbers, on our data. Including the ones where we degrade." |
| 1:50 | Open the database. | "No audio. Features and hashes only. We log decisions, not voices." |

## If something breaks
Press the replay key. Say **"this is a replay"** — out loud, immediately. Same pipeline,
so it is honest. A team that hides a fallback loses more than one that names it.

## Never say
- "99% accurate" · "it can't be fooled" · "it's blockchain-based"
- "it works in all 22 languages" (say the number you measured)
- "it's connected to real banking"
- **any number that is not in `data/results.json`**
