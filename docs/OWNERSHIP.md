# Ownership — one owner per directory

Git conflicts in a hackathon come almost entirely from two people editing the same file
at 2 am. This layout makes that structurally difficult.

| Directory | Owner | Never touched by |
|---|---|---|
| `contracts/`, `mocks/` | **frozen day 0** | anyone, without full team agreement |
| `backend/` | Backend dev | ML, Frontend |
| `ml/` | AI/ML dev | Backend, Frontend |
| `frontend/` | Frontend dev | Backend, ML |
| `data/`, `attacks/` | Data analyst | Frontend |
| `docs/` | Team lead | — |
| `scripts/` | shared, small changes only | — |

**Need something from another directory? Change the CONTRACT, announce it, and both
sides adapt inside their own folder.** Do not reach across.

## The one seam
```python
from ml.registry import get_detectors     # the ONLY thing backend imports from ml/
```
Everything else is private to its directory.

## Integration checkpoints — 30 minutes each, non-negotiable
- **Day 1, end of day** — everyone pulls `main`, runs the demo script
- **Day 2, noon**
- **Day 2, end of day**

Integration failure is the single most cited reason SIH teams lose. Never leave it to day 3.

## Git
- `main` is always demoable
- small PRs, feature branches
- nothing merges that breaks `docs/demo_script.md`
- **Day 3, 11:00** — last merge for anything new
- **Day 3, 14:00** — code freeze, everyone off keyboards
