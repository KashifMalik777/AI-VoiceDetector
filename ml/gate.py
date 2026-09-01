"""Evidence gate — the abstain state.

Almost nobody ships this. It is the most defensible feature in the system:
below a floor of usable speech we say so instead of guessing.
"""
from __future__ import annotations
import numpy as np

MIN_NET_SPEECH_S = 2.5   # 2.5s of speech in a 4s window. 3.0 (75% density) over-
                         # abstained on natural conversational speech with pauses;
                         # 2.5 still requires a clear majority of real speech.
MIN_SNR_DB = 4.0        # weak gate: SNR mainly reduces CONFIDENCE, see below
MAX_PKT_LOSS = 0.15

# Frame-level energy VAD. Deliberately dependency-free so this runs anywhere on day 1.
# Swap for silero-vad when torch lands; keep this signature.
_FRAME = 320             # 20 ms at 16 kHz
_REL_DB = 32.0           # a frame within 32 dB of the window peak counts as speech
_ABS_FLOOR_DB = -58.0    # nothing quieter than this counts as speech, ever


class NoiseTracker:
    """Session-level noise floor, because a single window often has no silence in it.

    A caller who talks continuously gives you no quiet frames to measure noise from --
    so a within-window SNR reads ~0 dB and the gate rejects the cleanest possible audio.
    Track the floor ACROSS the session instead: adapt down fast (we just heard something
    quieter, that is the real floor) and up very slowly (rooms get noisier gradually).
    """

    def __init__(self):
        self.floor: float | None = None
        self.confident = False        # have we ever seen a genuinely quiet frame?

    def update(self, db) -> float:
        p10 = float(np.percentile(db, 10))
        p95 = float(np.percentile(db, 95))
        if self.floor is None:
            self.floor = p10
        elif p10 < self.floor:
            self.floor = 0.3 * self.floor + 0.7 * p10      # fast down
        else:
            self.floor = 0.995 * self.floor + 0.005 * p10  # very slow up
        # "Confident" = we have seen frames well below the loud ones, so the floor is
        # really noise and not just quiet speech.
        if p95 - self.floor > 20.0:
            self.confident = True
        return self.floor

# WHY PEAK-RELATIVE AND NOT NOISE-FLOOR-RELATIVE
# ---------------------------------------------
# v1 estimated the noise floor as the 15th percentile of frame energy WITHIN the window
# and called anything 9 dB above it speech. That is catastrophically wrong for the case
# we care about most: if the speaker talks CONTINUOUSLY, the 15th percentile is itself
# speech, so almost nothing clears floor+9 dB and net_speech collapses to ~0.
#
# Symptom in the wild: "I was speaking properly but it barely reached 3 s and kept
# dropping to 0" -- i.e. THE BETTER YOU SPEAK, THE WORSE IT SCORES. Caught on day 0 by
# a human talking into a real microphone, which is exactly why you test with one.
#
# Anchoring to the window PEAK is well-behaved in all four regimes:
#   all speech      -> most frames sit within 32 dB of the peak -> counted   (was broken)
#   speech + pauses -> pauses fall below peak-32 dB             -> excluded  (still right)
#   quiet room      -> peak is under the absolute floor         -> zero      (still right)
#   loud noise      -> passes VAD but fails the SNR check below -> abstain


def _frame_energy_db(pcm: np.ndarray) -> np.ndarray:
    n = len(pcm) // _FRAME
    if n == 0:
        return np.array([])
    f = pcm[: n * _FRAME].reshape(n, _FRAME)
    rms = np.sqrt(np.mean(f.astype(np.float64) ** 2, axis=1) + 1e-12)
    return 20.0 * np.log10(rms + 1e-12)


def analyse(pcm: np.ndarray, sr: int = 16000, tracker: 'NoiseTracker | None' = None) -> dict:
    """Return quality metrics for a window. Cheap: a few ms."""
    if pcm.size == 0:
        return {"net_speech_s": 0.0, "snr_db": 0.0, "pkt_loss": 0.0,
                "enhancement_detected": False}

    db = _frame_energy_db(pcm)
    if db.size == 0:
        return {"net_speech_s": 0.0, "snr_db": 0.0, "pkt_loss": 0.0,
                "enhancement_detected": False}

    peak_db = float(np.percentile(db, 95))          # robust peak, ignores single spikes

    # Feed the tracker FIRST. Silent windows are the most valuable evidence about the
    # room's noise floor, so returning early without updating it means the floor is
    # never learned -- and every later SNR reads ~0 dB. (Bug found in the fix itself.)
    if tracker is not None:
        tracker.update(db)

    if peak_db < _ABS_FLOOR_DB:                      # the whole window is silence
        return {"net_speech_s": 0.0, "snr_db": 0.0,
                "pkt_loss": float((np.abs(pcm) < 1e-7).mean()),
                "enhancement_detected": False, "snr_measurable": False}

    # DYNAMIC RANGE GATE (added for the ambient-noise bug):
    # Human speech has 20-40 dB of dynamic range (loud syllables vs consonants/pauses).
    # Steady ambient room noise has <6 dB of variation across all frames.
    # If the window has too little dynamic range, it's just noise -- no actual speech.
    # Without this, the peak-relative VAD counts every ambient noise frame as "speech"
    # and net_speech hits 4.0 s, letting pure silence through the evidence gate.
    _MIN_DYNAMIC_RANGE_DB = 12.0
    dynamic_range = float(np.percentile(db, 95) - np.percentile(db, 10))
    if dynamic_range < _MIN_DYNAMIC_RANGE_DB:
        return {"net_speech_s": 0.0, "snr_db": round(dynamic_range, 1),
                "pkt_loss": float((np.abs(pcm) < 1e-7).mean()),
                "enhancement_detected": False, "snr_measurable": False,
                "gate_reason": "NO_SPEECH_DYNAMICS"}

    thr = max(peak_db - _REL_DB, _ABS_FLOOR_DB)
    speech_mask = db > thr
    net_speech_s = float(speech_mask.sum() * _FRAME / sr)

    # SNR from the energy distribution rather than a speech/silence split, so it stays
    # meaningful when there is no silence in the window at all.
    speech_db = float(np.percentile(db[speech_mask], 60)) if speech_mask.any() else peak_db
    if tracker is not None:
        noise_db = tracker.floor if tracker.floor is not None else float(np.percentile(db, 10))
        snr_measurable = tracker.confident
    else:
        noise_db = float(np.percentile(db, 10))
        snr_measurable = (peak_db - noise_db) > 20.0
    snr_db = float(speech_db - noise_db)

    # Digital silence runs = dropped packets (a real gap is never bit-exact zero).
    zeros = np.abs(pcm) < 1e-7
    pkt_loss = float(zeros.mean())

    return {
        "net_speech_s": round(net_speech_s, 2),
        "snr_db": round(snr_db, 1),
        "pkt_loss": round(pkt_loss, 4),
        "enhancement_detected": _detect_enhancement(pcm, sr),
        "snr_measurable": bool(snr_measurable),
    }


def _detect_enhancement(pcm: np.ndarray, sr: int) -> bool:
    """Heuristic for aggressive noise suppression (Krisp / Teams / Zoom RNNoise-class).

    WHY THIS MATTERS: published work shows speech enhancement drives bona-fide accuracy
    to ~0-11.79% -- it strips the very artifacts detection relies on and makes REAL
    people look FAKE. When we see it, confidence drops and the score cannot reach HOLD.

    Signature: unnaturally deep, spectrally flat noise floor between speech segments.
    """
    db = _frame_energy_db(pcm)
    if db.size < 12:
        return False
    floor = float(np.percentile(db, 10))
    spread = float(np.percentile(db, 25) - np.percentile(db, 5))
    # A real room floor sits well above -75 dB and has texture (spread > ~3 dB).
    return floor < -72.0 and spread < 3.0


def check(quality: dict) -> tuple[bool, str | None, str | None]:
    """(sufficient, reason_code, detail)"""
    if quality["net_speech_s"] < MIN_NET_SPEECH_S:
        return False, "INSUFFICIENT_SPEECH", (
            f"{quality['net_speech_s']:.1f} s of net speech; "
            f"{MIN_NET_SPEECH_S:.1f} s required")
    # SNR is deliberately a WEAK gate. It only blocks when we can actually measure it
    # (we have seen genuinely quiet frames this session). Otherwise a clean, continuously
    # speaking caller -- the best possible input -- would be rejected. Low SNR mainly
    # reduces CONFIDENCE in the risk engine, which is what stops it reaching HOLD.
    if quality.get("snr_measurable", True) and quality["snr_db"] < MIN_SNR_DB:
        return False, "LOW_SNR", f"SNR {quality['snr_db']:.1f} dB below {MIN_SNR_DB:.0f} dB floor"
    if quality["pkt_loss"] > MAX_PKT_LOSS:
        return False, "PACKET_LOSS", f"{quality['pkt_loss']*100:.0f}% of the window is dropped audio"
    return True, None, None
