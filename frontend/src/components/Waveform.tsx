import React, { useEffect, useRef } from 'react'

interface WaveformProps {
  levels: number[]
  live: boolean
}

export default function Waveform({ levels, live }: WaveformProps) {
  const ref = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = ref.current
    if (!canvas) return

    const dpr = window.devicePixelRatio || 1
    const width = canvas.clientWidth
    const height = canvas.clientHeight

    canvas.width = width * dpr
    canvas.height = height * dpr

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    ctx.scale(dpr, dpr)
    ctx.clearRect(0, 0, width, height)

    // Center guideline
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.07)'
    ctx.lineWidth = 1
    ctx.beginPath()
    ctx.moveTo(0, height / 2)
    ctx.lineTo(width, height / 2)
    ctx.stroke()

    const n = levels.length
    const barWidth = width / n
    const gap = 1.5

    // Gradient fill for waveform
    const gradient = ctx.createLinearGradient(0, 0, 0, height)
    gradient.addColorStop(0, '#4CD0D4')
    gradient.addColorStop(0.5, '#0A6E7C')
    gradient.addColorStop(1, '#054A54')

    ctx.fillStyle = gradient

    levels.forEach((val, i) => {
      const amp = Math.min(val * 2.8, 1) * (height / 2 - 3)
      ctx.globalAlpha = live ? 0.35 + 0.65 * (i / n) : 0.2
      const barH = Math.max(amp * 2, 2)
      const x = i * barWidth
      const y = height / 2 - amp

      // Rounded rectangle bars
      const radius = 1
      ctx.beginPath()
      ctx.roundRect(x, y, Math.max(barWidth - gap, 1.5), barH, radius)
      ctx.fill()
    })

    ctx.globalAlpha = 1
  }, [levels, live])

  return (
    <div className="waveform-container glass-panel">
      <div className="wave-header">
        <div className="wave-tag">
          <span className={`live-badge ${live ? 'is-live' : ''}`}>
            {live ? 'LIVE MIC INGESTION' : 'STREAM STANDBY'}
          </span>
          <span className="wave-spec">16.0 kHz Mono · 20ms Frames</span>
        </div>
        <span className="wave-cutoff-note">Rolloff Check &gt;7.0 kHz</span>
      </div>
      <canvas ref={ref} className="waveform-canvas" aria-label="Audio stream visualizer" />
    </div>
  )
}
