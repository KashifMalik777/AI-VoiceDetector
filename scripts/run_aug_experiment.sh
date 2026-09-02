#!/usr/bin/env bash
# Augmentation retrain experiment. Non-destructive: backs up the deployed head,
# measures baseline robustness, retrains augmented into a fresh head, re-measures.
# Decision to deploy (export ONNX) is made by a human after comparing the outputs.
set -e
cd "$(dirname "$0")/.."
PY=./.venv/Scripts/python.exe    # the 3.11 venv (torch cu124 + transformers); NOT system 3.14

echo "===== [1/4] backup deployed (clean) head ====="
cp ml/onnx/probe_head.npz ml/onnx/probe_head_clean.npz
cp data/probe_results.json data/probe_results_clean.json

echo "===== [2/4] baseline robustness (clean head) ====="
"$PY" scripts/eval_robustness.py --out data/robustness_baseline.json

echo "===== [3/4] augmented retrain (writes new probe_head.npz + probe_results.json) ====="
"$PY" ml/training/train_probe.py \
  --real attacks/genuine \
  --fake attacks/out/clones/asvspoof attacks/out/clones/indicsynth_hi attacks/out/clones/kikicore \
  --augment --aug-passes 1

echo "===== [4/4] robustness with augmented head ====="
"$PY" scripts/eval_robustness.py --out data/robustness_results.json

echo "===== DONE ====="
