import { useState, useRef } from 'react'
import type { ScoreMsg, Band } from '../lib/types'

interface AnalyzeResponse {
  filename: string
  duration_s: number
  windows: number
  abstained: number
  abstain_rate: number
  peak_risk: number | null
  final_band: Band | 'ABSTAIN'
  model_version: string
  timeline: Array<{
    seq: number
    t_ms: number
    state: 'SCORED' | 'ABSTAIN'
    risk?: number
    band?: Band
    confidence?: number
    reasons?: Array<{ code: string; label: string; weight: number }>
    quality?: {
      net_speech_s: number
      snr_db: number
      pkt_loss: number
      enhancement_detected: boolean
    }
  }>
}

interface AudioAnalyzerProps {
  onTimelineSelect?: (item: ScoreMsg) => void
}

export default function AudioAnalyzer({ onTimelineSelect }: AudioAnalyzerProps) {
  const [analyzing, setAnalyzing] = useState(false)
  const [result, setResult] = useState<AnalyzeResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [selectedSeq, setSelectedSeq] = useState<number | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileUpload = async (file: File) => {
    if (!file) return
    setAnalyzing(true)
    setError(null)
    setResult(null)
    setSelectedSeq(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await fetch('/api/analyze', {
        method: 'POST',
        body: formData,
      })

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.detail || `Server error: ${res.statusText}`)
      }

      const data: AnalyzeResponse = await res.json()
      setResult(data)
    } catch (err: any) {
      setError(err.message || 'Failed to analyze audio file. Please ensure it is a valid audio file.')
    } finally {
      setAnalyzing(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0])
    }
  }

  const bandColor = (band: Band | 'ABSTAIN') => {
    switch (band) {
      case 'SAFE': return 'var(--safe)'
      case 'WATCH': return 'var(--watch)'
      case 'VERIFY': return 'var(--watch)'
      case 'HOLD': return 'var(--crit)'
      default: return 'var(--muted)'
    }
  }

  return (
    <div className="analyzer-card glass-panel">
      <div className="analyzer-header">
        <div>
          <span className="section-eyebrow">Offline Forensics Lab</span>
          <h3>Audio File Deepfake Analyzer</h3>
        </div>
        {result && (
          <button className="btn-ghost-sm" onClick={() => setResult(null)}>
            Clear Analysis
          </button>
        )}
      </div>

      {!result ? (
        <div
          className={`dropzone ${analyzing ? 'is-analyzing' : ''}`}
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".wav,.mp3,.ogg,.m4a"
            style={{ display: 'none' }}
            onChange={(e) => e.target.files?.[0] && handleFileUpload(e.target.files[0])}
          />
          
          <div className="dropzone-icon">
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
          </div>

          <div className="dropzone-text">
            <h4>{analyzing ? 'Analyzing audio spectrum & neural artifacts...' : 'Drop audio file here or click to browse'}</h4>
            <p>Supports WAV, MP3, and M4A · Evaluates sliding 4s windows with 1s hops</p>
          </div>

          {analyzing && <div className="analyzer-spinner" />}
        </div>
      ) : (
        <div className="analysis-results">
          <div className="results-summary-grid">
            <div className="summary-item">
              <span className="summary-label">Audio File</span>
              <span className="summary-value truncate" title={result.filename}>{result.filename}</span>
            </div>
            <div className="summary-item">
              <span className="summary-label">Duration</span>
              <span className="summary-value">{result.duration_s.toFixed(1)}s</span>
            </div>
            <div className="summary-item">
              <span className="summary-label">Peak Risk</span>
              <span className="summary-value risk-val" style={{ color: bandColor(result.final_band) }}>
                {result.peak_risk !== null ? `${result.peak_risk}/100` : 'Abstained'}
              </span>
            </div>
            <div className="summary-item">
              <span className="summary-label">Verdict Band</span>
              <span className={`summary-badge band-${result.final_band.toLowerCase()}`}>
                {result.final_band}
              </span>
            </div>
          </div>

          <div className="file-timeline-wrapper">
            <div className="timeline-title-row">
              <span className="summary-label">Scored Windows ({result.windows} total · {(result.abstain_rate * 100).toFixed(0)}% abstained)</span>
              <span className="summary-label text-right">Click a window to inspect</span>
            </div>

            <div className="file-timeline-bars">
              {result.timeline.map((item) => {
                const isAbstain = item.state === 'ABSTAIN'
                const height = isAbstain ? 10 : Math.max(item.risk ?? 0, 8)
                const isSelected = selectedSeq === item.seq
                const color = isAbstain ? 'var(--hair)' : bandColor(item.band || 'SAFE')

                return (
                  <button
                    key={item.seq}
                    type="button"
                    className={`file-timeline-bar ${isSelected ? 'is-selected' : ''}`}
                    style={{
                      height: `${height}%`,
                      backgroundColor: color,
                    }}
                    onClick={() => {
                      setSelectedSeq(item.seq)
                      if (onTimelineSelect) {
                        onTimelineSelect({
                          type: 'score',
                          seq: item.seq,
                          t_ms: item.t_ms,
                          state: item.state,
                          risk: item.risk,
                          band: item.band,
                          confidence: item.confidence,
                          quality: item.quality || { net_speech_s: 0, snr_db: 0, pkt_loss: 0, enhancement_detected: false },
                          reasons: item.reasons,
                          model_version: result.model_version,
                        })
                      }
                    }}
                    title={`Window #${item.seq} (${(item.t_ms / 1000).toFixed(1)}s): ${isAbstain ? 'Abstain' : `Risk ${item.risk} [${item.band}]`}`}
                  />
                )
              })}
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="error-toast">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <span>{error}</span>
        </div>
      )}
    </div>
  )
}
