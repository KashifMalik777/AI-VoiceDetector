import React from 'react'
import type { ScoreMsg } from '../lib/types'

interface TimelineProps {
  history: ScoreMsg[]
}

export default function Timeline({ history }: TimelineProps) {
  const rows = history.slice(-75)

  return (
    <section className="timeline-panel glass-panel">
      <div className="card-top-row">
        <div>
          <span className="section-eyebrow">Sliding Window Sequence</span>
          <h3 className="card-title">Session Threat Timeline</h3>
        </div>
        <span className="count-pill">{rows.length} Windows</span>
      </div>

      <div className="timeline-container">
        {rows.length === 0 ? (
          <div className="timeline-empty">
            <span>No windows scored yet. Timeline populates at 1.0s hop rate.</span>
          </div>
        ) : (
          <div className="timeline-bars-track">
            {rows.map((m) => {
              const isAbstain = m.state === 'ABSTAIN'
              const height = isAbstain ? 12 : Math.max(m.risk ?? 0, 8)
              const bandClass = isAbstain ? 'bar-abstain' : `bar-${(m.band ?? 'SAFE').toLowerCase()}`

              return (
                <div
                  key={m.seq}
                  className={`timeline-bar-node ${bandClass}`}
                  style={{ height: `${height}%` }}
                  title={
                    isAbstain
                      ? `Window #${m.seq} — ABSTAIN (${m.detail || 'Insufficient Speech'})`
                      : `Window #${m.seq} — Risk ${m.risk}/100 [${m.band}]`
                  }
                />
              )
            })}
          </div>
        )}
      </div>

      <div className="timeline-legend-row">
        <div className="legend-item"><span className="legend-dot safe" /><span>Safe (0–29)</span></div>
        <div className="legend-item"><span className="legend-dot watch" /><span>Watch (30–54)</span></div>
        <div className="legend-item"><span className="legend-dot verify" /><span>Verify (55–74)</span></div>
        <div className="legend-item"><span className="legend-dot hold" /><span>Hold (75+)</span></div>
        <div className="legend-item"><span className="legend-dot abstain" /><span>Abstain</span></div>
      </div>
    </section>
  )
}
