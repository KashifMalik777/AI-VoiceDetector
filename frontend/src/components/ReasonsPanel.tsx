import React from 'react'
import type { ScoreMsg } from '../lib/types'

export default function ReasonsPanel({ latest }: { latest: ScoreMsg | null }) {
  const reasons = latest?.state === 'SCORED' ? (latest.reasons ?? []) : []

  return (
    <section className="panel-reasons glass-panel">
      <div className="card-top-row">
        <div>
          <span className="section-eyebrow">Acoustic Forensics</span>
          <h3 className="card-title">Evidence & Attribution</h3>
        </div>
        <span className="count-pill">{reasons.length} Signals</span>
      </div>

      {reasons.length === 0 ? (
        <div className="reasons-empty">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="16" x2="12" y2="12" />
            <line x1="12" y1="8" x2="12.01" y2="8" />
          </svg>
          <p>
            {latest?.state === 'ABSTAIN'
              ? 'Window abstained by Evidence Gate — zero speculative attribution.'
              : 'Awaiting first scored audio window to extract spectral markers.'}
          </p>
        </div>
      ) : (
        <ul className="reasons-list">
          {reasons.map((r) => (
            <li key={r.code} className="reason-item">
              <div className="reason-header">
                <span className="reason-label">{r.label}</span>
                <span className="reason-weight-val">{(r.weight * 100).toFixed(0)}% Impact</span>
              </div>
              <div className="reason-track">
                <div
                  className="reason-fill"
                  style={{ width: `${Math.min(r.weight * 150, 100)}%` }}
                />
              </div>
              <div className="reason-footer">
                <span className="reason-code-badge">{r.code}</span>
              </div>
            </li>
          ))}
        </ul>
      )}

      {latest?.detectors && (
        <div className="detectors-footer-strip">
          <span className="strip-title">Detector Telemetry:</span>
          <div className="detector-chips">
            {Object.entries(latest.detectors).map(([key, val]) => (
              <span key={key} className="det-chip">
                <span className="det-name">{key}:</span>
                <span className="det-score">{val.toFixed(2)}</span>
              </span>
            ))}
          </div>
        </div>
      )}
    </section>
  )
}
