import React, { useEffect, useState } from 'react'
import type { ScoreMsg, Band } from '../lib/types'

const LABEL: Record<Band, string> = {
  SAFE: 'Legitimate Voice',
  WATCH: 'Anomalous Signature',
  VERIFY: 'Verification Required',
  HOLD: 'Impersonation Suspected',
}

const BAND_SUBTITLE: Record<Band, string> = {
  SAFE: 'Spectral & neural features match natural human vocal tract dynamics.',
  WATCH: 'Minor synthesis or codec artifacts detected in sliding window.',
  VERIFY: 'Acoustic anomalies detected. Officer step-up challenge required.',
  HOLD: 'High-confidence deepfake / voice clone detected. Action held.',
}

export default function RiskMeter({ latest, running }: { latest: ScoreMsg | null; running: boolean }) {
  const abstain = !latest || latest.state === 'ABSTAIN'
  const risk = latest?.risk ?? 0
  const band = (latest?.band ?? 'SAFE') as Band
  const confidence = latest?.confidence ?? 0
  const acoustic = latest?.scores?.synthetic ?? 0
  const context = latest?.context ?? 0

  // Live idle timer: shows elapsed seconds since the session started without speech
  const [idleSec, setIdleSec] = useState(0)
  useEffect(() => {
    if (!running) { setIdleSec(0); return }
    if (!abstain) { setIdleSec(0); return }
    const iv = setInterval(() => setIdleSec(s => s + 1), 1000)
    return () => clearInterval(iv)
  }, [running, abstain])

  // Determine which visual mode we're in
  const idle = !running && !latest         // no session active, never scored
  const listening = running && abstain     // session active but no speech yet
  const scored = !abstain                  // got a real verdict

  // SVG Gauge calculations
  const radius = 80
  const stroke = 11
  const normalizedRadius = radius - stroke * 2
  const circumference = normalizedRadius * 2 * Math.PI
  const strokeDashoffset = scored ? circumference - (risk / 100) * circumference : circumference

  const getThemeClass = () => {
    if (!scored) return 'meter-abstain'
    switch (band) {
      case 'SAFE': return 'meter-safe'
      case 'WATCH': return 'meter-watch'
      case 'VERIFY': return 'meter-verify'
      case 'HOLD': return 'meter-hold'
      default: return 'meter-safe'
    }
  }

  const getGaugeColor = () => {
    if (!scored) return 'var(--hair)'
    switch (band) {
      case 'SAFE': return 'url(#gradient-safe)'
      case 'WATCH': return 'url(#gradient-watch)'
      case 'VERIFY': return 'url(#gradient-watch)'
      case 'HOLD': return 'url(#gradient-crit)'
      default: return 'url(#gradient-safe)'
    }
  }

  const formatIdle = (s: number) => {
    if (s < 60) return `${s}s`
    return `${Math.floor(s / 60)}m ${s % 60}s`
  }

  return (
    <div className={`risk-card glass-panel ${getThemeClass()}`}>
      <div className="card-top-row">
        <div className="status-indicator-group">
          <span className={`pulsing-dot ${listening ? 'dot-listening' : scored ? `dot-${band.toLowerCase()}` : 'dot-idle'}`} />
          <span className="card-eyebrow">Real-Time Threat Assessment</span>
        </div>
        {latest?.model_version && (
          <span className="model-chip" title="Model Engine Architecture">
            {latest.model_version}
          </span>
        )}
      </div>

      <div className="risk-display-grid">
        <div className="gauge-wrapper gauge-lg">
          <svg height={radius * 2} width={radius * 2} className="radial-gauge">
            <defs>
              <linearGradient id="gradient-safe" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#30D158" />
                <stop offset="100%" stopColor="#34C759" />
              </linearGradient>
              <linearGradient id="gradient-watch" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#FFD60A" />
                <stop offset="100%" stopColor="#FF9F0A" />
              </linearGradient>
              <linearGradient id="gradient-crit" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#FF453A" />
                <stop offset="100%" stopColor="#FF3B30" />
              </linearGradient>
            </defs>
            <circle
              stroke="var(--hair-2)"
              fill="transparent"
              strokeWidth={stroke}
              r={normalizedRadius}
              cx={radius}
              cy={radius}
            />
            <circle
              stroke={getGaugeColor()}
              fill="transparent"
              strokeWidth={stroke}
              strokeDasharray={`${circumference} ${circumference}`}
              style={{ strokeDashoffset, transition: 'stroke-dashoffset 0.6s cubic-bezier(0.16, 1, 0.3, 1)' }}
              strokeLinecap="round"
              r={normalizedRadius}
              cx={radius}
              cy={radius}
              transform={`rotate(-90 ${radius} ${radius})`}
            />
          </svg>

          <div className="gauge-center-text">
            {scored ? (
              <>
                <span className="gauge-number">{risk}</span>
                <span className="gauge-unit">/100</span>
              </>
            ) : listening ? (
              <span className="gauge-listening-icon">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" opacity="0.5">
                  <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z" />
                  <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                  <line x1="12" y1="19" x2="12" y2="22" />
                </svg>
              </span>
            ) : (
              <span className="gauge-idle-icon">—</span>
            )}
          </div>
        </div>

        <div className="risk-info-pane">
          {/* === STATE: Idle — no session running === */}
          {idle && (
            <div className="state-hero">
              <span className="verdict-pill pill-idle">STANDBY</span>
              <h3 className="verdict-title-lg">Ready to Analyze</h3>
              <p className="verdict-desc-lg">
                Press <strong>Start Live Call</strong> to begin real-time voice analysis, or switch to <strong>Audio File Lab</strong> to analyze a recording.
              </p>
            </div>
          )}

          {/* === STATE: Listening — mic active but no speech detected === */}
          {listening && (
            <div className="state-hero">
              <span className="verdict-pill pill-listening">LISTENING</span>
              <h3 className="verdict-title-lg">Waiting for Speech</h3>
              <p className="verdict-desc-lg">
                Microphone active — speak or play audio into the mic to begin analysis.
                {idleSec > 3 && (
                  <span className="idle-counter"> No speech detected for <strong>{formatIdle(idleSec)}</strong>.</span>
                )}
              </p>
              {latest?.detail && (
                <div className="abstain-detail-box">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="12" y1="16" x2="12" y2="12" />
                    <line x1="12" y1="8" x2="12.01" y2="8" />
                  </svg>
                  <span>{latest.detail}</span>
                </div>
              )}
              <div className="abstain-guarantee">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                </svg>
                <span>Zero-False-Positive Guarantee: Insufficient speech never triggers a transaction hold.</span>
              </div>
            </div>
          )}

          {/* === STATE: Scored — real verdict from the detectors === */}
          {scored && (
            <div className="state-hero">
              <div className="verdict-badge-row">
                <span className={`verdict-pill pill-${band.toLowerCase()}`}>{band}</span>
                <span className="verdict-headline-lg">{LABEL[band]}</span>
              </div>
              <p className="verdict-desc-lg">{BAND_SUBTITLE[band]}</p>

              <div className="metrics-sub-strip">
                <div className="sub-metric">
                  <span className="sub-lbl">Acoustic Score</span>
                  <span className="sub-val">{(acoustic * 100).toFixed(0)}%</span>
                </div>
                <div className="sub-metric">
                  <span className="sub-lbl">Context Risk</span>
                  <span className="sub-val">{(context * 100).toFixed(0)}%</span>
                </div>
                <div className="sub-metric">
                  <span className="sub-lbl">Engine Confidence</span>
                  <span className="sub-val">{(confidence * 100).toFixed(0)}%</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
