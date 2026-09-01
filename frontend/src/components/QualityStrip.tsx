import React from 'react'
import type { ScoreMsg } from '../lib/types'

export default function QualityStrip({ latest }: { latest: ScoreMsg | null }) {
  const q = latest?.quality
  if (!q) return null

  return (
    <div className="quality-strip-bar">
      <div className="telemetry-item">
        <span className="telemetry-dot" />
        <span className="telemetry-label">Net Speech:</span>
        <span className="telemetry-value">{q.net_speech_s.toFixed(1)}s / 4.0s</span>
      </div>

      <div className="telemetry-item">
        <span className="telemetry-label">SNR:</span>
        <span className={`telemetry-value ${q.snr_db < 12 ? 'is-warning' : ''}`}>
          {q.snr_db.toFixed(0)} dB
        </span>
      </div>

      <div className="telemetry-item">
        <span className="telemetry-label">Packet Loss:</span>
        <span className="telemetry-value">{(q.pkt_loss * 100).toFixed(1)}%</span>
      </div>

      {q.enhancement_detected && (
        <div className="telemetry-item is-alert" title="Noise suppression (Krisp/Zoom) detected. Confidence is halved to protect against false positives.">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
            <line x1="12" y1="9" x2="12" y2="13" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
          <span>Noise Suppression Active (Confidence Discounted)</span>
        </div>
      )}
    </div>
  )
}
