# Pushing to GitHub

⚠ A partial `.git/` exists (created from a mounted drive, which can't hold lock files).
**Delete it first, then init from Windows PowerShell.**

## One-time setup — MrDexxo only

```powershell
cd C:\Users\mohdk\Downloads\SIH104\satyavaani

# clear the half-initialised repo
Remove-Item -Recurse -Force .git

git init
git branch -M main
git add -A
git status --short          # sanity check: ~86 files, no .onnx, no node_modules
git commit -m "SatyaVaani: real-time voice-clone detection for live calls (SIH PS 26104)"
```

Create an **empty** repo on github.com (no README, no .gitignore — we have both), then:

```powershell
git remote add origin https://github.com/<you>/satyavaani.git
git push -u origin main
```

## What is NOT committed, and why
| Excluded | Why | How to regenerate |
|---|---|---|
| `ml/onnx/*.onnx` | 405 MB + 102 MB — GitHub caps at 100 MB/file | `python ml/training/export_backbone.py` |
| `frontend/node_modules/` | 68 packages | `npm install` |
| `.venv/` | platform-specific | `pip install -r requirements.txt` |
| `data/datasets/` | ~200 GB | `bash data/download_datasets.sh` |
| `*.wav` | recordings are large and often personal | recorded per Fouziya's brief |
| `*.db` | regenerated on first run | automatic |

**`ml/onnx/model_card.json` IS committed** — it records which model, how many threads, and
*why* (fp32 over int8, layer 7 over 5). That reasoning is worth more than the weights.

**`data/results.json` IS committed** — it is the deliverable. Every number on the metrics
slide comes from it.

## Team workflow

```powershell
git clone https://github.com/<you>/satyavaani.git
cd satyavaani
.\scripts\setup.ps1
pip install torch --index-url https://download.pytorch.org/whl/cpu
python ml\training\export_backbone.py      # rebuild the ONNX locally
```

Then read your brief in `docs/roles/`.

### Branch per person
```powershell
git checkout -b faazil/train-probe
# ... work only inside your own directory ...
git add ml/ ; git commit -m "train probe on team clones" ; git push -u origin faazil/train-probe
```

**Rules:** `main` is always demoable · one owner per directory · nothing merges that breaks
`docs/demo_script.md` · **Day 3 11:00 last merge, 14:00 code freeze.**

## Make the repo pitch-worthy
GitHub is on slide 5 as a QR code. Judges may open it. Worth 10 minutes:
- **Description:** "Real-time voice-cloning detection for live calls — SIH 2025 PS 26104"
- **Topics:** `deepfake-detection` `speech` `audio-ml` `fastapi` `onnx` `sih2025` `cybersecurity`
- The README already opens with the pitch and the architecture.
