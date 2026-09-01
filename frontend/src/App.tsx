import React, { useEffect, useState } from 'react'
import { useCall } from './lib/useCall'
import type { ScoreMsg } from './lib/types'
import RiskMeter from './components/RiskMeter'
import Waveform from './components/Waveform'
import ReasonsPanel from './components/ReasonsPanel'
import QualityStrip from './components/QualityStrip'
import Timeline from './components/Timeline'
import TransactionGate from './components/TransactionGate'
import AlertFeed from './components/AlertFeed'
import AudioAnalyzer from './components/AudioAnalyzer'
import ScenarioDrawer, { ScenarioConfig } from './components/ScenarioDrawer'
import AuditModal from './components/AuditModal'

export default function App() {
  const call = useCall()
  const [health, setHealth] = useState<any>(null)
  const [mode, setMode] = useState<'live' | 'file'>('live')
  const [isScenarioOpen, setIsScenarioOpen] = useState(false)
  const [isAuditOpen, setIsAuditOpen] = useState(false)
  const [selectedFileScore, setSelectedFileScore] = useState<ScoreMsg | null>(null)

  const [scenario, setScenario] = useState<ScenarioConfig>({
    caller_id: '+91 98123 45678',
    known_contact: false,
    channel: 'voip',
    intent: 'transfer',
    transaction_amount: 5000000,
    fri_tier: 'HIGH',
  })

  useEffect(() => {
    fetch('/health')
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => setHealth({ down: true }))
  }, [])

  const holdAlert = call.alerts.find((a) => a.band === 'HOLD') ?? null

  const override = async (reason: string) => {
    if (!holdAlert) return
    await fetch(`/api/alerts/${holdAlert.alert_id}/override`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason, by: 'officer' }),
    }).catch(() => {})
  }

  const handleStartCall = () => {
    call.start({
      caller_id: scenario.caller_id,
      known_contact: scenario.known_contact,
      channel: scenario.channel,
      intent: scenario.intent,
      transaction_amount: scenario.transaction_amount,
      fri_tier: scenario.fri_tier,
    })
  }

  const stubs = (health?.detectors ?? []).filter((d: any) => d.stub).map((d: any) => d.name)
  const activeLatest = mode === 'live' ? call.latest : selectedFileScore

  return (
    <div className="app-shell">
      {/* Apple-Style Navigation Header */}
      <header className="apple-header">
        <div className="header-brand">
          <div className="brand-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
              <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" y1="19" x2="12" y2="22" />
            </svg>
          </div>
          <div>
            <div className="brand-title-row">
              <h1 className="brand-title">SatyaVaani</h1>
              <span className="brand-badge">SIH PS 26104</span>
            </div>
            <p className="brand-subtitle">Real-Time Voice Cloning & Impersonation Defense</p>
          </div>
        </div>

        {/* Mode Selector & Action Tools */}
        <div className="header-actions">
          <div className="segmented-control mode-switcher">
            <button
              type="button"
              className={`segment-btn ${mode === 'live' ? 'active' : ''}`}
              onClick={() => setMode('live')}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
                <path d="M19 10v1a7 7 0 0 1-14 0v-1" />
              </svg>
              <span>Live Mic Stream</span>
            </button>
            <button
              type="button"
              className={`segment-btn ${mode === 'file' ? 'active' : ''}`}
              onClick={() => {
                if (call.running) call.stop()
                setMode('file')
              }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
              <span>Audio File Lab</span>
            </button>
          </div>

          <button
            type="button"
            className="btn-header-tool"
            onClick={() => setIsScenarioOpen(true)}
            title="Configure Threat & Transaction Scenario"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
            </svg>
            <span>Scenario</span>
          </button>

          <button
            type="button"
            className="btn-header-tool"
            onClick={() => setIsAuditOpen(true)}
            title="Inspect Cryptographic SHA-256 Ledger"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
              <polyline points="10 9 9 9 8 9" />
            </svg>
            <span>Audit Ledger</span>
          </button>

          {mode === 'live' && (
            <div className="call-btn-wrapper">
              {!call.running ? (
                <button type="button" className="btn-call-start" onClick={handleStartCall}>
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor">
                    <polygon points="5 3 19 12 5 21 5 3" />
                  </svg>
                  <span>Start Live Call</span>
                </button>
              ) : (
                <button type="button" className="btn-call-stop" onClick={call.stop}>
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor">
                    <rect x="6" y="6" width="12" height="12" rx="2" />
                  </svg>
                  <span>End Call Session</span>
                </button>
              )}
            </div>
          )}
        </div>
      </header>

      {/* Status & Banner Alerts */}
      {health?.down && (
        <div className="banner-toast banner-error">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <span>Backend service unreachable at <code>:8000</code>. Verify FastAPI service status.</span>
        </div>
      )}

      {stubs.length > 0 && (
        <div className="banner-toast banner-warning">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
            <line x1="12" y1="9" x2="12" y2="13" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
          <span>
            <b>Modular Day-1 Mode:</b> Active detectors: <code>{stubs.join(', ')}</code> (Stubbed) + <code>codec</code> (Active Heuristic).
          </span>
        </div>
      )}

      {call.error && (
        <div className="banner-toast banner-error">
          <span>{call.error}</span>
        </div>
      )}

      {/* Main Dashboard Layout */}
      <main className="dashboard-grid">
        {/* Left Column: Voice Forensics & Telemetry */}
        <section className="dashboard-col col-forensics">
          {mode === 'file' && (
            <AudioAnalyzer onTimelineSelect={(score) => setSelectedFileScore(score)} />
          )}

          <RiskMeter latest={activeLatest} running={mode === 'live' && call.running} />

          {mode === 'live' && (
            <>
              <QualityStrip latest={call.latest} />
              <Waveform levels={call.levels} live={call.running} />
              <Timeline history={call.history} />
            </>
          )}
        </section>

        {/* Right Column: Transaction Authorization & Evidence */}
        <section className="dashboard-col col-protection">
          <TransactionGate
            band={mode === 'live' ? call.band : (activeLatest?.band || 'SAFE')}
            alert={holdAlert}
            onOverride={override}
            amount={scenario.transaction_amount}
            callerId={scenario.caller_id}
          />
          <ReasonsPanel latest={activeLatest} />
          {mode === 'live' && <AlertFeed alerts={call.alerts} />}
        </section>
      </main>

      {/* Apple-Style Glass Footer */}
      <footer className="apple-footer">
        <div className="footer-left">
          {call.sessionId && (
            <span className="session-tag">
              Session: <code>{call.sessionId}</code>
            </span>
          )}
          <span className="spec-tag">16 kHz Mono · 4.0s Window · 1.0s Hop</span>
        </div>
        <div className="footer-right">
          <span>Privacy Assured: No voice audio saved to disk. Features and hashes only.</span>
        </div>
      </footer>

      {/* Context Modals */}
      <ScenarioDrawer
        isOpen={isScenarioOpen}
        onClose={() => setIsScenarioOpen(false)}
        config={scenario}
        onChange={setScenario}
      />

      <AuditModal
        isOpen={isAuditOpen}
        onClose={() => setIsAuditOpen(false)}
      />
    </div>
  )
}
