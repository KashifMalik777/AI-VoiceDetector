# Team & Roles — SatyaVaani

| Person | Role | Owns | Never edits |
|---|---|---|---|
| **Annam** | Team Lead · PPT · Pitch | `docs/`, the deck, the schedule, the gates | feature code |
| **Fouziya** | Data Analyst | `data/`, `attacks/` | backend, ml, frontend |
| **Faazil** | AI/ML | `ml/` | backend, frontend, data |
| **Mustafa** | Backend | `backend/` | ml, frontend, data |
| **Miqdaad** | Frontend | `frontend/` | backend, ml, data |
| **MrDexxo** | Contracts · Integration | `contracts/`, `mocks/`, `scripts/`, the repo | everyone's feature code |

## Individual briefs — paste into your own Claude chat
- `docs/roles/ANNAM_lead.md`
- `docs/roles/FOUZIYA_data.md`
- `docs/roles/FAAZIL_ml.md`
- `docs/roles/MUSTAFA_backend.md`
- `docs/roles/MIQDAAD_frontend.md`
- `docs/roles/DEXXO_integration.md`

## The one seam
```python
from ml.registry import get_detectors   # the ONLY thing backend imports from ml/
```

## The rules
1. One owner per directory. Never edit another person's.
2. `contracts/` is frozen — changes go through MrDexxo, everyone agrees.
3. `main` is always demoable.
4. Never invent a number. If it isn't in `data/results.json`, it isn't said.
5. Integrate 3×: Day1-end, Day2-noon, Day2-end. 30 min each.

## Critical path right now
```
Fouziya: recordings + clones  ->  Faazil: train probe  ->  neural detector participates
                              ->  Fouziya: results.json -> Annam: metrics slide
```
**Everything ML is blocked on the audio. That is the one thing to unblock first.**

## Gates
| When | Gate |
|---|---|
| Day 1 end | end-to-end green; RTF measured |
| Day 2 6pm | model decision — winner ships, decided by NUMBER |
| Day 3 11am | last merge for anything new |
| Day 3 2pm | **CODE FREEZE** — everyone off keyboards |
