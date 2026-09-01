#!/usr/bin/env bash
# Kick off dataset downloads. RUN THIS FIRST, TONIGHT.
# It is the only hard external dependency and it must not sit on tomorrow's critical path.
set -e
cd "$(dirname "$0")"
mkdir -p datasets && cd datasets

echo "=== SatyaVaani dataset fetch ==="
echo "Several of these need a manual accept / login. Open them NOW in a browser"
echo "and start the big ones before you sleep."
echo

command -v huggingface-cli >/dev/null || pip install -q "huggingface_hub[cli]"

echo "-- IndicSynth (12 Indian languages, ~4000 h, CC BY-NC 4.0)"
huggingface-cli download vdivyasharma/IndicSynth --repo-type dataset \
  --local-dir ./indicsynth || echo "   -> needs `huggingface-cli login`"

echo
echo "-- MANUAL, open these now:"
echo "   ASVspoof 5      https://www.asvspoof.org/                (registration)"
echo "   In-the-Wild     https://deepfake-total.com/in_the_wild   (HOLD OUT — never train)"
echo "   CodecFake       search 'CodecFake dataset' — the backbone set"
echo "   Indic-CodecFake https://helixometry.github.io/IndicFake/ (CC BY 4.0)"
echo
echo "Storage: budget ~200 GB if you take everything. Subsample aggressively —"
echo "training-data BREADTH matters far more than volume."
