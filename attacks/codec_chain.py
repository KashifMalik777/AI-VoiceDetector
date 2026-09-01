#!/usr/bin/env python3
"""Telephony codec chain — needs ffmpeg on PATH.

Narrowband codecs are the SECOND-hardest condition in ASVspoof 5; neural codecs are the
hardest. That is awkward and worth saying on stage: modern TTS is itself codec-based, so
codec artifacts are simultaneously the attack signature and the channel noise.

Indian telephony is 8 kHz G.711 / AMR-NB with packet loss and jitter -- exactly the regime
where published accuracy evaporates. Train through this chain, then report the number.

    python attacks/codec_chain.py IN_DIR OUT_DIR
"""
from __future__ import annotations
import subprocess, shutil, argparse, sys
from pathlib import Path

# (label, ffmpeg args to encode, container)
CODECS = [
    ("g711_ulaw",  ["-ar", "8000", "-ac", "1", "-acodec", "pcm_mulaw"], "wav"),
    ("g711_alaw",  ["-ar", "8000", "-ac", "1", "-acodec", "pcm_alaw"],  "wav"),
    ("adpcm",      ["-ar", "8000", "-ac", "1", "-acodec", "adpcm_ima_wav"], "wav"),
    ("gsm",        ["-ar", "8000", "-ac", "1", "-acodec", "gsm"], "wav"),
    ("amr_nb",     ["-ar", "8000", "-ac", "1", "-acodec", "libopencore_amrnb", "-b:a", "12.2k"], "amr"),
    ("g722",       ["-ar", "16000", "-ac", "1", "-acodec", "g722"], "wav"),
    ("opus_16k",   ["-ar", "16000", "-ac", "1", "-acodec", "libopus", "-b:a", "16k"], "ogg"),
    ("mp3_16k",    ["-ar", "16000", "-ac", "1", "-acodec", "libmp3lame", "-b:a", "16k"], "mp3"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("indir"); ap.add_argument("outdir")
    a = ap.parse_args()

    if not shutil.which("ffmpeg"):
        print("ffmpeg not found on PATH.\n"
              "  Ubuntu/WSL : sudo apt install ffmpeg\n"
              "  Windows    : winget install Gyan.FFmpeg\n"
              "  macOS      : brew install ffmpeg")
        sys.exit(1)

    src, dst = Path(a.indir), Path(a.outdir)
    files = sorted(src.rglob("*.wav"))
    if not files:
        print(f"no .wav under {src}"); sys.exit(1)

    for label, args, ext in CODECS:
        out = dst / label; out.mkdir(parents=True, exist_ok=True)
        ok = 0
        for f in files:
            tmp = out / (f.stem + "." + ext)
            final = out / (f.stem + ".wav")
            try:
                # encode through the codec...
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(f)]
                               + args + [str(tmp)], check=True)
                # ...then straight back to 16 kHz PCM, which is what the model sees.
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp),
                                "-ar", "16000", "-ac", "1", str(final)], check=True)
                if tmp != final:
                    tmp.unlink(missing_ok=True)
                ok += 1
            except subprocess.CalledProcessError:
                pass
        print(f"  {label:12} {ok:4}/{len(files)} -> {out}"
              + ("   (codec unavailable in this ffmpeg build)" if ok == 0 else ""))

    print("\nRun each directory through POST /api/analyze and fill the 8 kHz row in results.json.")


if __name__ == "__main__":
    main()
