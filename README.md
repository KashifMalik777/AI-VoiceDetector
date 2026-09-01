# SatyaVaani

Real-time voice-cloning detection for live calls. SIH 2025 · PS 26104 (AICTE, Cyber Security Cell).

**Scores a caller while they are still talking. Holds the transaction. Never cancels it.**

---

## Quick start (60 seconds)

```bash
bash scripts/setup.sh        # Linux / macOS / WSL / Git Bash
# or on Windows PowerShell:  .\scripts\setup.ps1
```

Then two terminals:

```bash
# terminal 1 — backend (real server, stub detectors)
bash scripts/run_backend.sh          # http://localhost:8000

# terminal 2 — frontend
cd frontend && npm install && npm run dev    # http://localhost:5173
```

Open http://localhost:5173, click **Start call**, allow the mic. The meter moves.

Don't have the backend yet? Point the frontend at the mock instead:

```bash
python mocks/mock_server.py          # http://localhost:8000, same routes, fake data
```

---

## The one rule that makes six people work in parallel

`contracts/` is **frozen**. The backend imports exactly one thing from ML:

```python
from ml.registry import get_detectors
```

Every detector returns a `DetectorResult`. On day 1 they return plausible random scores, and the
whole system still runs end to end. From then on you are only ever *improving* a working system,
never *assembling* one at 2am.

**One owner per top-level directory. Never edit another directory — change the contract instead.**

See `docs/OWNERSHIP.md`.

---

## Directory map

| Dir | Owner | What lives here |
|---|---|---|
| `contracts/` | frozen day 0 | schemas, WS protocol, fixtures |
| `mocks/` | frozen day 0 | mock server serving fixtures on real routes |
| `backend/` | Backend dev | FastAPI, WS hub, DB, rules, alerts, audit chain |
| `ml/` | AI/ML dev | detectors, features, fusion, gate, training |
| `frontend/` | Frontend dev | Vite + React app |
| `data/` | Data analyst | dataset prep, augmentation, eval, `results.json` |
| `attacks/` | Data analyst + ML | clone generation, laundering, codec chain |
| `docs/` | Team lead | architecture, demo script, deck assets |
| `scripts/` | shared | setup, run, benchmark |

---

## The three documents

- **Build Blueprint** — architecture, detector design, evaluation protocol
- **Judge Battlecard** — 26 questions with researched answers
- **Pre-Flight Checklist** — the 48 things that must be true before the pitch

## Hard gates

- **Day 1** — end-to-end green with stub scores; **RTF benchmarked on the demo laptop**
- **Day 2, 6pm** — fine-tune vs baseline on held-out set; the winner ships, decided by number
- **Day 3, 11am** — last merge for anything new
- **Day 3, 2pm** — code freeze. Everyone off keyboards.
