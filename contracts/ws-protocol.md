# WebSocket protocol

Endpoint: `ws://localhost:8000/ws/session/{session_id}`

## Client → server

**Binary frame** — raw audio, no envelope:
- `Float32Array` little-endian, **16000 Hz, mono**
- Send **16000 samples (1.0 s)** per frame. The server keeps a rolling 4 s buffer.

**Text frames** (JSON):
```json
{"type":"start","meta":{"caller_id":"+919812345678","known_contact":false,"channel":"voip"}}
{"type":"context","transaction_amount":5000000,"intent":"transfer"}
{"type":"stop"}
```

## Server → client

Every message has `type`. Three types.

### `score` — emitted once per hop (~1/s)
```json
{
  "type":"score","seq":42,"t_ms":42000,
  "state":"SCORED",
  "risk":78,"band":"HOLD",
  "scores":{"synthetic":0.91,"replay":0.12,
            "speaker":{"enrolled":true,"similarity":0.31,"match":false}},
  "context":0.44,"confidence":0.86,
  "quality":{"net_speech_s":6.2,"snr_db":21.4,"pkt_loss":0.01,"enhancement_detected":false},
  "detectors":{"neural":0.94,"codec":0.88,"trajectory":0.79},
  "reasons":[{"code":"CODEC_FINGERPRINT","label":"...","weight":0.34}],
  "model_version":"stub-v0"
}
```

`state` is `SCORED` or `ABSTAIN`. On `ABSTAIN` there is **no** `risk`/`band` — do not render a number:
```json
{"type":"score","seq":7,"t_ms":7000,"state":"ABSTAIN",
 "reason":"INSUFFICIENT_SPEECH","detail":"1.2 s of net speech; 3.0 s required",
 "quality":{"net_speech_s":1.2,"snr_db":18.0,"pkt_loss":0.0,"enhancement_detected":false}}
```

Abstain reason codes: `INSUFFICIENT_SPEECH` · `LOW_SNR` · `PACKET_LOSS` · `BUFFER_WARMING`

### `alert` — emitted on band transition upward
```json
{"type":"alert","alert_id":"a_7f2c","seq":42,"risk":78,"band":"HOLD",
 "action":"HOLD_TRANSACTION",
 "recommendation":"Call back on the registered number ending 4417",
 "ts":"2026-08-28T17:04:11Z"}
```
`action` ∈ `NONE` | `FLAG` | `ADVISE_VERIFY` | `HOLD_TRANSACTION`

### `transcript` — optional, ~every 5 s
```json
{"type":"transcript","seq":42,"text":"...transfer it right now",
 "keywords":["right now","transfer"]}
```

## Bands

| risk | band | Approve button | who decides |
|---|---|---|---|
| — | `ABSTAIN` | enabled | — |
| 0–29 | `SAFE` | enabled | — |
| 30–54 | `WATCH` | enabled | — |
| 55–74 | `VERIFY` | **enabled** + advisory banner | officer |
| 75–100 | `HOLD` | becomes "Verify caller to continue" | officer releases |

**The system never cancels. It only ever adds a verification step.**
