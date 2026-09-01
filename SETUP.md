# SETUP — do these in order

Everything a machine could do is already done. This is what needs **you**.

Times are honest. Total: about 2.5 hours tonight, most of it waiting on downloads.

---

## STEP 1 · Get it running (10 minutes) — do this first, alone

Prove the thing works on your machine before you show anyone.

### Windows (PowerShell, in the SIH104 folder)
```powershell
cd satyavaani
.\scripts\setup.ps1
```
If PowerShell blocks the script:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### WSL / Linux / macOS / Git Bash
```bash
cd satyavaani
bash scripts/setup.sh
```

Then **two terminals**:

```bash
# terminal 1
.venv\Scripts\activate            # Windows
source .venv/bin/activate         # everywhere else
uvicorn backend.main:app --reload --port 8000

# terminal 2
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**, click **Start call**, allow the microphone.

**What you should see:** the meter says INSUFFICIENT EVIDENCE for the first ~5 seconds,
then starts scoring. An amber banner says stub detectors are active — that is correct
and expected on day 1.

> Not working? Jump to Troubleshooting at the bottom.

---

## STEP 2 · Benchmark the demo laptop (5 minutes) — **BLOCKER**

Decide now which machine is *the* demo laptop. Every benchmark and dry run happens on it.

```bash
python scripts/bench_rtf.py
```

Write down the **TOTAL per window** and **headroom** numbers. It writes
`data/rtf_bench.json` automatically.

**Why this is a blocker:** the published measurement for our model is real-time factor
0.68–0.84 — real-time on one core with almost no headroom. If your laptop is slower you
need three days to react, not three hours. The fallback ladder is in the script's docstring.

Re-run this the moment the neural detector is wired. That is the number the latency slide
depends on.

---

## STEP 3 · Start the dataset downloads (10 minutes of clicking, then leave it) — **BLOCKER**

This is the only hard external dependency. It must not sit on tomorrow's critical path.

```bash
bash data/download_datasets.sh
```

Then open these four in a browser and start them **before you sleep**:

| Dataset | Where | Note |
|---|---|---|
| ASVspoof 5 | asvspoof.org | needs registration |
| In-the-Wild | deepfake-total.com/in_the_wild | **hold out — never train on it** |
| CodecFake | search "CodecFake dataset" | the backbone set, most transferable |
| Indic-CodecFake | helixometry.github.io/IndicFake | CC BY 4.0 |

For IndicSynth you need a HuggingFace account: `huggingface-cli login`, then the script
handles it. Budget ~200 GB if you take everything — subsample aggressively, breadth of
generators matters far more than volume.

---

## STEP 4 · Record and clone two voices (30 minutes) — **BLOCKER**

The demo audio must exist from day one, not day three.

1. Record **30–60 seconds of clean speech** from two teammates.
   Phone voice memo is fine. Save as `attacks/refs/<name>.wav`.

2. Clone each voice with **at least three generators**:

   | Generator | How | Time |
   |---|---|---|
   | **ElevenLabs** | elevenlabs.io free tier, web UI, "Instant Voice Clone" | 10 min |
   | **XTTS-v2** | `pip install TTS` then the Coqui CLI | 10 min |
   | **F5-TTS** | GitHub, open weights | 10 min |

   Save into `attacks/out/clones/<generator>/`.

   Have them say something demo-appropriate: *"I need you to transfer fifty lakh to the
   account I'm about to give you. It's urgent, and please don't discuss this with anyone."*

3. Why three and not one: the failure mode in this field is **synthesis-method mismatch**.
   A detector that has only seen one generator learns that generator's fingerprint.

---

## STEP 5 · Get Seed-VC running (30 minutes) — **BLOCKER, and the highest-value item here**

This is the attack that beats prosody entirely, and the one we demo ourselves on stage.

```bash
git clone https://github.com/Plachtaa/seed-vc
cd seed-vc
pip install -r requirements.txt
python real-time-gui.py
```

Feed a teammate's live mic in, convert to the other teammate's voice, record the output
into `attacks/out/seedvc/`.

**If it needs a GPU you don't have:** use the offline conversion mode, or run it on Colab
and download the output. A recorded conversion is enough for the demo — you do not need it
live on stage.

**Why this matters more than anything else in this list:** whoever demos the real-time
voice-conversion attack first owns the room. If a judge demos it first, you lose.

---

## STEP 6 · Team kickoff — the 20-minute contract review (20 minutes, all six)

Get everyone on a call. Screen-share `contracts/`.

1. Walk through `contracts/ws-protocol.md` together — the message shapes.
2. Walk through the `DetectorResult` block in `contracts/schemas.json` — the one seam.
3. Show `docs/OWNERSHIP.md` — **one owner per directory, never edit someone else's**.
4. Agree out loud: **contracts are frozen.** Changing one needs everyone.
5. Everyone runs Step 1 on their own machine before they hang up.

Then have each person start their directory. They cannot block each other — that is the
entire point of the mock server and the stub detectors.

---

## STEP 7 · Two things only you can do (10 minutes)

- **Get your college's internal SIH rubric from the SPOC.** It is not standardised
  nationally and it is the only rubric actually scoring you this round.
- **Download the official SIH idea-submission template** from sih.gov.in. It is a
  **6-slide PDF**. Third-party 10-slide templates circulating on blogs are not official,
  and following one is an unforced error.

---

## Troubleshooting

**`python` not found (Windows)** — install from python.org and tick *"Add Python to PATH"*.
Or use `py` instead of `python`.

**`npm install` fails** — check `node -v` is 18+. Delete `frontend/node_modules` and
`package-lock.json`, retry.

**Microphone permission denied** — the mic only works on `localhost` or HTTPS. Use
`http://localhost:5173`, not the LAN IP.

**"WebSocket error — is the backend running?"** — terminal 1 must be running. Check
http://localhost:8000/health in a browser.

**Meter never leaves INSUFFICIENT EVIDENCE** — the gate needs 3 seconds of *net speech*
in the 4-second window. Speak continuously. If it still abstains, your mic is very quiet:
check input level in OS sound settings.

**`disk I/O error` on startup, or `venv` creation fails** — you are running from a
mounted, network or cloud-synced folder (WSL `/mnt/c`, OneDrive, a network share).
SQLite needs file locking those cannot provide. The app now detects this and falls back
automatically, but the clean fix is to copy the repo onto a local disk:
```bash
cp -r satyavaani ~/satyavaani && cd ~/satyavaani
```
Or point the DB somewhere local: `export SATYAVAANI_DB=sqlite:////tmp/sv.db`

**Port 8000 already in use**
```bash
uvicorn backend.main:app --port 8010     # then update frontend/vite.config.ts
```

**Everything is broken and you need the demo to work** — run the mock:
```bash
python mocks/mock_server.py
```
Real routes, fixture data, no dependencies. The frontend works against it unchanged.

---

## What "done for tonight" looks like

- [ ] App runs on your machine, meter moves
- [ ] `data/rtf_bench.json` exists with a real number
- [ ] Datasets downloading
- [ ] Two voices cloned by three generators each
- [ ] Seed-VC produced at least one converted clip
- [ ] All six have read `contracts/` and run Step 1
- [ ] College rubric + official 6-slide template in hand

Tick them in the Pre-Flight artifact so the team can see.
