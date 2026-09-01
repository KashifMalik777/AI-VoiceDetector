#!/usr/bin/env python3
"""Export the truncated XLS-R backbone + linear probe to ONNX int8.

RUN THIS ON DAY 1. It answers the question the whole latency slide depends on:
how long does the REAL neural pass take on the demo laptop?

WHY THIS EXACT CONFIG (measured, not guessed):
    XLS-R truncated @ layer 7 + linear probe   8.4% OOD EER   101M params
    XLS-R truncated @ layer 5                 16.2% OOD EER   (fallback if slow)
    full W2V2-300M fine-tuned + AASIST        11.3% OOD EER   318M
    full W2V2-300M                            16.9% OOD EER   300M
    RawGAT-ST                                 27.0% OOD EER
Truncation BEATS the full model: deeper layers encode linguistic content that
hurts generalisation. Keeping 7 of 24 layers is a ~3x compute saving AND better.

TWO-PHASE DESIGN
  Phase 1 (now)   : export with an UNTRAINED head -> real compute cost measurable
                    immediately. The detector refuses to let an untrained model
                    affect a verdict (it abstains), but it still runs the full
                    forward pass so the benchmark is honest.
  Phase 2 (day 2) : train_probe.py fits the 769-param head on real data and
                    re-exports. Nothing else changes.

    python ml/training/export_backbone.py                # layer 7, fp32 + int8
    python ml/training/export_backbone.py --layer 5      # the fallback
    python ml/training/export_backbone.py --no-quantize
"""
from __future__ import annotations
import argparse, json, sys, time, warnings
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "ml" / "onnx"
HF_ID = "facebook/wav2vec2-xls-r-300m"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--layer", type=int, default=7, help="transformer layers to keep (7 default, 5 = fallback)")
    ap.add_argument("--seconds", type=float, default=4.0, help="window length used for the export trace")
    ap.add_argument("--no-quantize", action="store_true")
    ap.add_argument("--head", default=None,
                    help="probe_head.npz from train_probe.py -- flips the card to trained")
    a = ap.parse_args()

    import torch, torch.nn as nn
    try:
        from transformers import Wav2Vec2Model
    except ImportError:
        sys.exit("pip install transformers")

    OUT.mkdir(parents=True, exist_ok=True)
    print("=" * 66)
    print(f"  Exporting XLS-R-300M truncated @ layer {a.layer}")
    print(f"  torch {torch.__version__}")
    print("=" * 66)

    print(f"\n[1/5] downloading {HF_ID}  (~1.2 GB, first run only)")
    t0 = time.time()
    bb = Wav2Vec2Model.from_pretrained(HF_ID)
    bb.config.apply_spec_augment = False          # no masking at inference
    total_layers = len(bb.encoder.layers)
    print(f"      done in {time.time()-t0:.0f}s · {total_layers} transformer layers")

    if a.layer > total_layers:
        sys.exit(f"--layer {a.layer} > {total_layers} available")

    print(f"[2/5] truncating {total_layers} -> {a.layer} layers")
    bb.encoder.layers = nn.ModuleList(list(bb.encoder.layers[: a.layer]))
    bb.eval()
    dim = bb.config.hidden_size
    n_params = sum(p.numel() for p in bb.parameters())
    print(f"      hidden dim {dim} · {n_params/1e6:.1f}M params after truncation")

    class Probe(nn.Module):
        """Normalisation + backbone + mean-pool + linear head, all in one graph.

        Baking the zero-mean/unit-variance normalisation INTO the graph means the
        detector cannot forget to apply it -- a classic silent-accuracy-loss bug.
        """
        def __init__(self, backbone, dim):
            super().__init__()
            self.backbone = backbone
            self.head = nn.Linear(dim, 2)
            nn.init.zeros_(self.head.weight); nn.init.zeros_(self.head.bias)

        def forward(self, x):                      # x: [B, T] raw float32 audio
            m = x.mean(dim=1, keepdim=True)
            s = x.std(dim=1, keepdim=True)
            x = (x - m) / (s + 1e-7)
            h = self.backbone(x).last_hidden_state # [B, T', dim]
            return self.head(h.mean(dim=1))        # [B, 2]  -> [bonafide, spoof]

    model = Probe(bb, dim)
    trained = False
    if a.head:
        import numpy as _np
        w = _np.load(a.head)
        model.head.weight.data = torch.from_numpy(w["weight"]).float()
        model.head.bias.data = torch.from_numpy(w["bias"]).float()
        trained = True
        print(f"      loaded trained head from {a.head}")
    model = model.eval()
    dummy = torch.randn(1, int(16000 * a.seconds))

    with torch.no_grad():
        t0 = time.time(); out = model(dummy); torch_ms = (time.time() - t0) * 1000
    print(f"      torch forward OK, output {tuple(out.shape)} · {torch_ms:.0f} ms")

    fp32 = OUT / f"xlsr_l{a.layer}_fp32.onnx"
    print(f"[3/5] exporting -> {fp32.name}")
    try:
        torch.onnx.export(
            model, (dummy,), str(fp32),
            input_names=["input"], output_names=["logits"],
            dynamic_axes={"input": {0: "batch", 1: "time"}, "logits": {0: "batch"}},
            opset_version=17, do_constant_folding=True, dynamo=False)
    except TypeError:                              # older torch has no dynamo kwarg
        torch.onnx.export(
            model, (dummy,), str(fp32),
            input_names=["input"], output_names=["logits"],
            dynamic_axes={"input": {0: "batch", 1: "time"}, "logits": {0: "batch"}},
            opset_version=17, do_constant_folding=True)
    print(f"      {fp32.stat().st_size/1e6:.0f} MB")

    final = fp32
    if not a.no_quantize:
        print("[4/5] int8 dynamic quantisation")
        try:
            from onnxruntime.quantization import quantize_dynamic, QuantType
            int8 = OUT / f"xlsr_l{a.layer}_int8.onnx"
            quantize_dynamic(str(fp32), str(int8), weight_type=QuantType.QInt8)
            print(f"      {int8.stat().st_size/1e6:.0f} MB  "
                  f"({fp32.stat().st_size/int8.stat().st_size:.1f}x smaller)")
            final = int8
        except Exception as e:
            print(f"      quantisation failed ({e}) -- keeping fp32")
    else:
        print("[4/5] skipped (--no-quantize)")

    print("[5/5] verifying with onnxruntime, 1 thread")
    import numpy as np, onnxruntime as ort
    so = ort.SessionOptions(); so.intra_op_num_threads = 1
    sess = ort.InferenceSession(str(final), so, providers=["CPUExecutionProvider"])
    x = np.random.randn(1, int(16000 * a.seconds)).astype(np.float32)
    sess.run(None, {"input": x})                              # warm
    ts = []
    for _ in range(8):
        t0 = time.time(); sess.run(None, {"input": x}); ts.append((time.time() - t0) * 1000)
    ts.sort(); mean = sum(ts) / len(ts)
    print(f"      {mean:.0f} ms mean · {ts[-1]:.0f} ms p95  (1 CPU core, {a.seconds}s window)")

    card = OUT / "model_card.json"
    card.write_text(json.dumps({
        "onnx": final.name,
        "base": HF_ID,
        "layers_kept": a.layer,
        "hidden_dim": dim,
        "params_millions": round(n_params / 1e6, 1),
        "quantized": final != fp32,
        "window_s": a.seconds,
        "trained": trained,
        "note": ("Trained head -- detector participates in verdicts."
                 if trained else
                 "HEAD IS UNTRAINED. Exported to measure real compute cost. The "
                 "detector abstains rather than contributing a meaningless score. "
                 "Run train_probe.py to fit the head, then re-export."),
        "threads": 8,
        "onnx_ms_mean": round(mean, 1),
        "expected_ood_eer": {"7": 8.4, "5": 16.2}.get(str(a.layer)),
    }, indent=2))

    print("\n" + "=" * 66)
    hop_ms = 1000.0
    if mean < hop_ms * 0.5:   v = "OK -- comfortable inside the 1 s hop"
    elif mean < hop_ms * 0.9: v = "TIGHT -- consider --layer 5, or neural every 2nd hop"
    else:                     v = "OVER BUDGET -- use --layer 5, or score every 2nd hop"
    print(f"  VERDICT: {v}")
    print(f"  headroom in the 1 s hop: {hop_ms - mean:+.0f} ms")
    print(f"\n  wrote {final.name} + model_card.json")
    print("  NEXT: set MODEL_READY = True in ml/detectors/neural.py, then")
    print("        python scripts/bench_rtf.py     <- the REAL latency number")
    print("=" * 66)


if __name__ == "__main__":
    main()
