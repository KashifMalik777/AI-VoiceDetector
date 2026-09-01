// Mirrors contracts/schemas.json. If you change these, change the contract first.
export type Band = 'SAFE' | 'WATCH' | 'VERIFY' | 'HOLD'

export interface Reason { code: string; label: string; weight: number }

export interface Quality {
  net_speech_s: number; snr_db: number; pkt_loss: number; enhancement_detected: boolean
}

export interface ScoreMsg {
  type: 'score'; seq: number; t_ms: number
  state: 'SCORED' | 'ABSTAIN'
  risk?: number; band?: Band
  scores?: { synthetic: number; replay: number
             speaker: { enrolled: boolean; similarity: number | null; match: boolean | null } }
  context?: number; confidence?: number
  quality: Quality
  detectors?: Record<string, number>
  reasons?: Reason[]
  model_version?: string
  reason?: string; detail?: string          // ABSTAIN only
}

export interface AlertMsg {
  type: 'alert'; alert_id: string; seq: number; risk: number; band: Band
  action: 'NONE' | 'FLAG' | 'ADVISE_VERIFY' | 'HOLD_TRANSACTION'
  recommendation: string; ts: string
}

export type ServerMsg = ScoreMsg | AlertMsg | { type: 'transcript'; seq: number; text: string; keywords: string[] }

export const BAND_COLOR: Record<Band, string> = {
  SAFE: 'var(--safe)', WATCH: 'var(--watch)', VERIFY: 'var(--watch)', HOLD: 'var(--crit)',
}
