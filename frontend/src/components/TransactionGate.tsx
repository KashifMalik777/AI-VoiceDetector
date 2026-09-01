import React, { useState } from 'react'
import type { Band, AlertMsg } from '../lib/types'

interface TransactionGateProps {
  band: Band | 'ABSTAIN'
  alert: AlertMsg | null
  onOverride: (reason: string) => void
  amount?: number
  callerId?: string
}

export default function TransactionGate({
  band,
  alert,
  onOverride,
  amount = 5000000,
  callerId = '+91 98123 45678',
}: TransactionGateProps) {
  const [released, setReleased] = useState(false)
  const [asking, setAsking] = useState(false)
  const held = band === 'HOLD' && !released
  const advise = band === 'VERIFY'

  const REASONS = [
    'Verified via Callback on Registered Phone Number',
    'Passed Shared-Knowledge Security Challenge',
    'In-Branch / Multi-Factor Authenticated Confirmation',
    'False Alarm — High Background Line Noise',
  ]

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(val)
  }

  return (
    <section className={`banking-card glass-panel ${held ? 'is-held' : advise ? 'is-advise' : 'is-safe'}`}>
      <div className="card-top-row">
        <div className="sim-badge">
          <span className="sim-dot" />
          <span>SIMULATED BANKING PROTECTION GATE</span>
        </div>
        <div className="channel-chip">Voice Channel</div>
      </div>

      <div className="virtual-card">
        <div className="vcard-header">
          <div className="vcard-brand">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="2" y="5" width="20" height="14" rx="3" />
              <line x1="2" y1="10" x2="22" y2="10" />
            </svg>
            <span>Priority Wire Authorization</span>
          </div>
          <span className="vcard-chip" />
        </div>

        <div className="vcard-body">
          <div className="vcard-row">
            <span className="vcard-label">Beneficiary</span>
            <span className="vcard-value highlight">RAMESH TRADING CO</span>
          </div>
          <div className="vcard-row">
            <span className="vcard-label">Account Routing</span>
            <span className="vcard-value mono">HDFC •••• 4417</span>
          </div>
          <div className="vcard-row">
            <span className="vcard-label">Authorization Amount</span>
            <span className="vcard-amount">{formatCurrency(amount)}</span>
          </div>
          <div className="vcard-row">
            <span className="vcard-label">Caller CLI</span>
            <span className="vcard-value mono">{callerId}</span>
          </div>
        </div>
      </div>

      {held && (
        <div className="gate-notice notice-held">
          <div className="notice-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
          </div>
          <div className="notice-text">
            <strong>Transaction Placed on Protection Hold (Not Cancelled)</strong>
            <p>{alert?.recommendation || 'Initiate callback on registered phone number before authorizing fund transfer.'}</p>
          </div>
        </div>
      )}

      {advise && !held && (
        <div className="gate-notice notice-advise">
          <div className="notice-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
          </div>
          <div className="notice-text">
            <strong>Elevated Risk Warning</strong>
            <p>Acoustic or context anomalies detected. Ask a shared-knowledge challenge before approving.</p>
          </div>
        </div>
      )}

      <div className="gate-actions">
        {!held ? (
          <button className={`btn-action ${released ? 'btn-released' : 'btn-approve'}`}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
              <polyline points="22 4 12 14.01 9 11.01" />
            </svg>
            <span>{released ? 'Transfer Released by Officer' : 'Approve Wire Transfer'}</span>
          </button>
        ) : !asking ? (
          <button className="btn-action btn-held" onClick={() => setAsking(true)}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </svg>
            <span>Verify Caller to Release Hold</span>
          </button>
        ) : (
          <div className="override-panel">
            <span className="override-title">Officer Resolution Required:</span>
            <div className="override-list">
              {REASONS.map((r) => (
                <button
                  key={r}
                  type="button"
                  className="btn-override-option"
                  onClick={() => {
                    onOverride(r)
                    setReleased(true)
                    setAsking(false)
                  }}
                >
                  <span>{r}</span>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="9 18 15 12 9 6" />
                  </svg>
                </button>
              ))}
            </div>
            <button className="btn-ghost-sm full-width" onClick={() => setAsking(false)}>
              Keep Transaction Held
            </button>
          </div>
        )}
      </div>

      {released && (
        <div className="released-footer">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="20 6 9 17 4 12" />
          </svg>
          <span>Override record cryptographically sealed in SQLite audit ledger.</span>
        </div>
      )}
    </section>
  )
}
