# data/ — where borrowed numbers become ours

**Until `results.json` exists, every number in the deck belongs to someone else.**
A judge asking "what is *your* EER?" gets nothing. Closing that gap is this directory's job.

## Datasets — start downloading TONIGHT

| Dataset | Role | Licence | Get it |
|---|---|---|---|
| **CodecFake** | **backbone** — most transferable set measured (22.3% macro EER) | research | see paper repo |
| **ASVspoof 5** | benchmark + train | research | asvspoof.org |
| **In-the-Wild** | **held out, never trained on** | research | Fraunhofer AISEC |
| **IndicSynth** | 12 Indian languages, 4000 h | **CC BY-NC 4.0 — non-commercial** | huggingface.co/datasets/vdivyasharma/IndicSynth |
| **Indic-CodecFake** | Indic + neural codecs, seen/unseen splits | CC BY 4.0 | helixometry.github.io/IndicFake |
| **our clones** | modern generators | ours | `attacks/` |

⚠ **IndicSynth is CC BY-NC.** Fine for the hackathon; check it before any commercial claim.
⚠ **Do NOT quote ASVspoof 2019 LA numbers.** It is saturated (0.2–0.8% EER is routine) and
quoting it signals you have not read the field.

## Protocol — non-negotiable

1. **Speaker-disjoint splits, stated explicitly.** Detectors frequently learn speaker
   identity rather than synthesis artifacts. Without this our numbers are fiction.
2. **Leave-one-generator-out.** Hold one generator family out entirely.
3. **Never train on In-the-Wild.** It is the honesty check.
4. **Report the degraded conditions**: clean → 8 kHz telephony → reverb → noise-suppressed
   → adversarial. Publish all of them.
5. **Report the abstain rate.** What fraction of windows we decline to score.

## Metrics — report all of these, never accuracy alone

| Metric | Why |
|---|---|
| EER | expected and comparable — but do not lead with it |
| minDCF | ASVspoof 5 primary; weights a rejected genuine caller ~1.9× a missed spoof |
| **actDCF + C_llr** | **the differentiator.** minDCF uses an oracle threshold, actDCF one fixed in advance. The gap IS deployment risk. |
| FAR @ FRR=1% | the business operating point |
| per-language EER **and FPR** | the fairness table nobody else will have |
| RTF, RAM, cores | first-class for a real-time problem statement |

`ml/fusion/calibrate.py` implements all of them.

**The actDCF trap:** in ASVspoof 5, strong systems posted minDCF ≈ 0.1 with **actDCF = 1.0000**
— great separation, worthless calibration; the organisers said such systems are "no better
than a coin toss" at their operating point.

## Output

Write `data/results.json` in the shape of `contracts/fixtures/metrics.json`.
`GET /api/metrics/model` serves it automatically once it exists.

**Empty cells are honest. Invented cells are the one mistake a technical panel will not
forgive.** "We did not measure that, here is how we would" is a good answer.
