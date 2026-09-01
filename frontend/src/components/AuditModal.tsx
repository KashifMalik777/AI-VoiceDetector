import React, { useEffect, useState } from 'react'

interface AuditSession {
  id: string
  started_at: string
  ended_at: string | null
  peak_risk: number
  final_band: string
  frames: number
  abstained: number
}

interface AuditEntry {
  idx: number
  ts: string
  kind: string
  hash: string
  prev_hash: string
  payload?: any
}

interface AuditModalProps {
  isOpen: boolean
  onClose: () => void
}

export default function AuditModal({ isOpen, onClose }: AuditModalProps) {
  const [tab, setTab] = useState<'sessions' | 'ledger'>('sessions')
  const [sessions, setSessions] = useState<AuditSession[]>([])
  const [entries, setEntries] = useState<AuditEntry[]>([])
  const [verifyStatus, setVerifyStatus] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!isOpen) return
    setLoading(true)

    Promise.all([
      fetch('/api/sessions').then(r => r.json()).catch(() => ({ sessions: [] })),
      fetch('/api/audit/entries').then(r => r.json()).catch(() => ({ entries: [] })),
      fetch('/api/audit/verify').then(r => r.json()).catch(() => null),
    ]).then(([sessData, entryData, vData]) => {
      setSessions(sessData.sessions || [])
      setEntries(entryData.entries || [])
      setVerifyStatus(vData)
      setLoading(false)
    })
  }, [isOpen])

  if (!isOpen) return null

  const getBandBadgeClass = (band: string) => {
    switch (band?.toUpperCase()) {
      case 'SAFE': return 'badge-safe'
      case 'WATCH': return 'badge-watch'
      case 'VERIFY': return 'badge-verify'
      case 'HOLD': return 'badge-hold'
      default: return 'badge-neutral'
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content glass-modal modal-wide" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <span className="section-eyebrow">Tamper-Evident Security Log</span>
            <h3>Audit Ledger & Session Records</h3>
          </div>
          <button className="btn-close" onClick={onClose}>×</button>
        </div>

        <div className="modal-tabs">
          <button
            className={`tab-btn ${tab === 'sessions' ? 'active' : ''}`}
            onClick={() => setTab('sessions')}
          >
            Past Voice Sessions ({sessions.length})
          </button>
          <button
            className={`tab-btn ${tab === 'ledger' ? 'active' : ''}`}
            onClick={() => setTab('ledger')}
          >
            Cryptographic SHA-256 Ledger ({entries.length})
          </button>
        </div>

        <div className="modal-body">
          {loading ? (
            <div className="modal-loading">
              <div className="analyzer-spinner" />
              <p>Fetching encrypted ledger records from SQLite...</p>
            </div>
          ) : tab === 'sessions' ? (
            <div className="table-responsive">
              {sessions.length === 0 ? (
                <p className="empty-state">No call sessions recorded yet. Start a call or run an offline analysis to generate records.</p>
              ) : (
                <table className="apple-table">
                  <thead>
                    <tr>
                      <th>Session ID</th>
                      <th>Timestamp (UTC)</th>
                      <th>Scored Windows</th>
                      <th>Peak Risk</th>
                      <th>Final Verdict</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sessions.map(s => (
                      <tr key={s.id}>
                        <td><code>{s.id}</code></td>
                        <td>{new Date(s.started_at).toLocaleString()}</td>
                        <td>{s.frames} scored ({s.abstained} abstained)</td>
                        <td>
                          <span className="risk-pill">{s.peak_risk}/100</span>
                        </td>
                        <td>
                          <span className={`status-pill ${getBandBadgeClass(s.final_band)}`}>
                            {s.final_band}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          ) : (
            <div>
              {verifyStatus && (
                <div className={`ledger-verification-banner ${verifyStatus.valid ? 'is-valid' : 'is-invalid'}`}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    {verifyStatus.valid ? (
                      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14 M22 4L12 14.01l-3-3" />
                    ) : (
                      <circle cx="12" cy="12" r="10" />
                    )}
                  </svg>
                  <span>
                    {verifyStatus.valid
                      ? `Cryptographic Hash Chain Verified (${verifyStatus.count || entries.length} entries intact — zero tampering detected)`
                      : 'Chain Verification Warning: Potential ledger discontinuity'}
                  </span>
                </div>
              )}

              <div className="table-responsive">
                {entries.length === 0 ? (
                  <p className="empty-state">No ledger entries recorded yet.</p>
                ) : (
                  <table className="apple-table">
                    <thead>
                      <tr>
                        <th>Idx</th>
                        <th>Event Kind</th>
                        <th>Timestamp</th>
                        <th>Current Hash (SHA-256)</th>
                        <th>Previous Hash</th>
                      </tr>
                    </thead>
                    <tbody>
                      {entries.map(e => (
                        <tr key={e.idx}>
                          <td>#{e.idx}</td>
                          <td><span className="kind-tag">{e.kind}</span></td>
                          <td>{new Date(e.ts).toLocaleTimeString()}</td>
                          <td><code title={e.hash}>{e.hash?.slice(0, 16)}...</code></td>
                          <td><code title={e.prev_hash}>{e.prev_hash?.slice(0, 16)}...</code></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="modal-footer flex-between">
          <span className="footer-note">Privacy by Design: No voice or audio bytes are ever stored in the database.</span>
          <button className="btn-secondary" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  )
}
