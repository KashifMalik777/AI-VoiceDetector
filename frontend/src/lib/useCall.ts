import { useCallback, useRef, useState } from 'react'
import type { ScoreMsg, AlertMsg, ServerMsg, Band } from './types'

const SR = 16000

/** Linear resample to 16 kHz. Good enough for a 1 s frame and dependency-free. */
function resample(x: Float32Array, from: number, to = SR): Float32Array {
  if (from === to) return x
  const n = Math.round((x.length * to) / from)
  const out = new Float32Array(n)
  const ratio = (x.length - 1) / Math.max(n - 1, 1)
  for (let i = 0; i < n; i++) {
    const p = i * ratio, i0 = Math.floor(p), i1 = Math.min(i0 + 1, x.length - 1)
    out[i] = x[i0] + (p - i0) * (x[i1] - x[i0])
  }
  return out
}

export interface CallState {
  running: boolean
  sessionId: string | null
  latest: ScoreMsg | null
  history: ScoreMsg[]
  alerts: AlertMsg[]
  band: Band | 'ABSTAIN'
  error: string | null
  levels: number[]
}

export function useCall() {
  const [s, setS] = useState<CallState>({
    running: false, sessionId: null, latest: null, history: [], alerts: [],
    band: 'ABSTAIN', error: null, levels: new Array(64).fill(0),
  })
  const ws = useRef<WebSocket | null>(null)
  const ctx = useRef<AudioContext | null>(null)
  const stream = useRef<MediaStream | null>(null)

  // Session ID ref to guard against stale socket callbacks from a previous session
  // firing after a new session has started (the "starts/stops/freaks out" race condition).
  const activeSession = useRef<string | null>(null)

  // Teardown helper: cleans up all resources for the current session.
  // Idempotent — safe to call multiple times.
  const teardown = useCallback(() => {
    try { ws.current?.send(JSON.stringify({ type: 'stop' })) } catch {}
    try { ws.current?.close() } catch {}
    ws.current = null
    stream.current?.getTracks().forEach(t => t.stop())
    stream.current = null
    try { ctx.current?.close() } catch {}
    ctx.current = null
    activeSession.current = null
  }, [])

  const stop = useCallback(() => {
    teardown()
    setS(p => ({ ...p, running: false, latest: null, band: 'ABSTAIN' }))
  }, [teardown])

  const start = useCallback(async (meta: Record<string, unknown>) => {
    // ALWAYS clean up the previous session first. Without this, re-starting a
    // call leaks the old AudioContext + MediaStream + WebSocket. The old socket's
    // onclose then fires and sets running=false on the new session. This is the
    // "freaks out / starts stops" bug.
    teardown()

    try {
      setS(p => ({ ...p, error: null, history: [], alerts: [], latest: null, band: 'ABSTAIN', running: false }))

      const r = await fetch('/api/sessions', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(meta),
      })
      const { session_id } = await r.json()
      activeSession.current = session_id

      const proto = location.protocol === 'https:' ? 'wss' : 'ws'
      const sock = new WebSocket(`${proto}://${location.host}/ws/session/${session_id}`)
      sock.binaryType = 'arraybuffer'
      ws.current = sock

      // Capture the session_id at creation time. If a newer session has started
      // by the time a callback fires, the callback is stale and must be ignored.
      const mySession = session_id

      sock.onmessage = (e) => {
        if (activeSession.current !== mySession) return // stale socket, ignore
        const m: ServerMsg = JSON.parse(e.data)
        if (m.type === 'score') {
          if (m.state === 'ABSTAIN') {
            // ABSTAIN windows: update the latest readout (so the UI shows
            // "Calibrating Audio Stream") but DON'T flood the history array.
            // Pushing 38+ ABSTAIN entries into history caused O(n) React
            // re-renders with zero useful information → UI lag.
            setS(p => ({ ...p, latest: m, band: 'ABSTAIN' }))
          } else {
            // SCORED windows: update everything including history.
            setS(p => ({
              ...p, latest: m, history: [...p.history, m].slice(-300),
              band: m.band as Band,
            }))
          }
        } else if (m.type === 'alert') {
          if (activeSession.current !== mySession) return
          setS(p => ({ ...p, alerts: [m, ...p.alerts].slice(0, 20) }))
        }
      }
      sock.onerror = () => {
        if (activeSession.current !== mySession) return // stale socket, ignore
        setS(p => ({ ...p, error: 'WebSocket error — is the backend running on :8000?' }))
      }
      sock.onclose = () => {
        // CRITICAL GUARD: only set running=false if THIS socket is still the
        // active one. Without this, ending session A and starting session B
        // causes A's onclose to fire AFTER B has started, setting running=false
        // on B's UI state — the "freaks out / starts stops" race condition.
        if (activeSession.current !== mySession) return
        setS(p => ({ ...p, running: false }))
      }

      await new Promise<void>((res, rej) => {
        sock.onopen = () => res()
        setTimeout(() => rej(new Error('WebSocket did not open')), 5000)
      })
      sock.send(JSON.stringify({ type: 'start', meta }))

      const ms = await navigator.mediaDevices.getUserMedia({
        // Ask the browser NOT to clean the audio: enhancement strips the very artifacts
        // detection relies on and makes real people look fake. Tap as early as possible.
        audio: { channelCount: 1, echoCancellation: false, noiseSuppression: false, autoGainControl: false },
      })
      stream.current = ms

      const ac = new AudioContext()
      ctx.current = ac
      await ac.audioWorklet.addModule('/pcm-worklet.js')
      const src = ac.createMediaStreamSource(ms)
      const node = new AudioWorkletNode(ac, 'pcm-worklet', {
        processorOptions: { frameSamples: Math.round(ac.sampleRate) },   // 1.0 s
      })
      node.port.onmessage = (ev) => {
        if (activeSession.current !== mySession) return // stale, don't send
        const d = ev.data as { level?: number; pcm?: Float32Array }
        // Fast path: ~20 ms level tick — keeps the meter live without touching the socket.
        if (d.level !== undefined) {
          setS(p => ({ ...p, levels: [...p.levels.slice(1), d.level as number] }))
          return
        }
        // Slow path: 1 s PCM frame for the detector.
        if (d.pcm) {
          const pcm = resample(d.pcm, ac.sampleRate)
          if (sock.readyState === WebSocket.OPEN) sock.send(pcm.buffer)
        }
      }
      src.connect(node)
      // Keep the worklet pulling without echoing the mic to the speakers.
      const sink = ac.createGain(); sink.gain.value = 0
      node.connect(sink); sink.connect(ac.destination)

      setS(p => ({ ...p, running: true, sessionId: session_id }))
    } catch (e: any) {
      setS(p => ({ ...p, error: e?.message || String(e), running: false }))
      teardown()
    }
  }, [teardown])

  const sendContext = useCallback((ctxMsg: Record<string, unknown>) => {
    if (ws.current?.readyState === WebSocket.OPEN)
      ws.current.send(JSON.stringify({ type: 'context', ...ctxMsg }))
  }, [])

  return { ...s, start, stop, sendContext }
}
