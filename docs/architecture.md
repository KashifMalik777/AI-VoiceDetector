# Architecture (short form)

Full blueprint lives in the shared artifact. This is the version you keep in the repo.

```
CAPTURE            GATE                DETECT                 FUSE      SCORE        ACT
browser mic  ->  normalise +  ->  neural (XLS-R L7)  ->   calibrated -> risk    -> dashboard
audio upload     VAD +            codec & channel        logistic     engine      hold gate
replay           evidence check   speaker & trajectory                            audit ledger
                      |
                      +--> ABSTAIN (insufficient speech / SNR / packet loss)
```

- **16 kHz mono, 4 s window, 1 s hop.** First verdict ~4.4 s, then ~1.4 s lag.
- **One FastAPI process** holds API + WebSocket + ML. The single most important decision:
  a separate Node backend costs an extra hop, two deploys and an integration day we don't have.
- **Three scores, not one:** synthetic · replay · speaker-match. A clone is engineered to
  pass speaker match, so collapsing them into one number loses two thirds of the problem.
- **The system never cancels.** It holds and a human releases, in two clicks, logged.

## Why these three detectors
Each covers an attack the others structurally cannot see:

| Attack | neural | codec | speaker & trajectory |
|---|---|---|---|
| Pre-rendered TTS clone | strong | strong | strong |
| **Live voice conversion** | partial | partial | **strong** |
| Spliced / edited audio | weak | partial | **strong** |
| Replay through a speaker | weak | **strong** | partial |
| Reverb / laundering | **weak** | partial | partial |
| Adversarial perturbation | **weak** | partial | partial |

The honest weak cells are a strength in Q&A, not a hole.

## What was removed, and why
- **"No breath sounds"** — ElevenLabs v3 makes breathing on demand via `[exhales]` tags,
  and breath happens every 4–7 s so a short window cannot observe it at all.
- **"Flat pitch"** — best prosody-only paper: 93% accuracy but 24.7% EER; 18.92% against
  expressive TTS.
- **The popular HuggingFace detector** — card says "More information needed" for training
  data, reports accuracy with no EER; comparable architectures ~38% EER out of domain.

Both heuristics survive as low-weight auxiliary features. Neither is ever a headline reason.
