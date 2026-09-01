import React from 'react'
import type { AlertMsg } from '../lib/types'

interface AlertFeedProps {
  alerts: AlertMsg[]
}

export default function AlertFeed({ alerts }: AlertFeedProps) {
  if (!alerts.length) return null

  return (
    <section className="alerts-panel glass-panel">
      <div className="card-top-row">
        <div>
          <span className="section-eyebrow">Incident Stream</span>
          <h3 className="card-title">Triggered Security Alerts</h3>
        </div>
        <span className="count-pill alert-count">{alerts.length}</span>
      </div>

      <ul className="alerts-stream-list">
        {alerts.map((a) => (
          <li key={a.alert_id} className={`alert-item-card alert-${a.band.toLowerCase()}`}>
            <div className="alert-item-header">
              <span className={`alert-band-chip chip-${a.band.toLowerCase()}`}>
                {a.band}
              </span>
              <span className="alert-action-tag">{a.action}</span>
              <span className="alert-time">{new Date(a.ts).toLocaleTimeString()}</span>
            </div>
            <p className="alert-recommendation">
              {a.recommendation || 'Initiate verification protocol.'}
            </p>
            <div className="alert-footer-code">
              <span>Incident ID: <code>{a.alert_id}</code></span>
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}
