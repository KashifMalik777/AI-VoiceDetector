import React from 'react'

export interface ScenarioConfig {
  caller_id: string
  known_contact: boolean
  channel: 'voip' | 'cellular' | 'landline'
  intent: 'transfer' | 'enquiry' | 'payout_redirect'
  transaction_amount: number
  fri_tier: 'NONE' | 'MEDIUM' | 'HIGH' | 'VERY_HIGH'
}

interface ScenarioDrawerProps {
  config: ScenarioConfig
  onChange: (cfg: ScenarioConfig) => void
  onClose: () => void
  isOpen: boolean
}

export default function ScenarioDrawer({ config, onChange, onClose, isOpen }: ScenarioDrawerProps) {
  if (!isOpen) return null

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content glass-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <span className="section-eyebrow">Simulation Context</span>
            <h3>Scenario & Threat Parameters</h3>
          </div>
          <button className="btn-close" onClick={onClose}>×</button>
        </div>

        <div className="modal-body">
          <p className="modal-desc">
            Adjust caller attributes and financial transaction values to test how the Risk Engine weights context alongside acoustic voice signals.
          </p>

          <div className="form-group">
            <label>Transaction Intent</label>
            <div className="segmented-control">
              {(['enquiry', 'transfer', 'payout_redirect'] as const).map((intent) => (
                <button
                  key={intent}
                  type="button"
                  className={`segment-btn ${config.intent === intent ? 'active' : ''}`}
                  onClick={() => onChange({ ...config, intent })}
                >
                  {intent === 'enquiry' ? 'Balance Enquiry' : intent === 'transfer' ? 'Wire Transfer' : 'Payout Redirect'}
                </button>
              ))}
            </div>
          </div>

          <div className="form-group">
            <div className="label-row">
              <label>Transaction Amount</label>
              <span className="value-preview">₹ {config.transaction_amount.toLocaleString('en-IN')}</span>
            </div>
            <input
              type="range"
              min="10000"
              max="10000000"
              step="50000"
              value={config.transaction_amount}
              onChange={(e) => onChange({ ...config, transaction_amount: Number(e.target.value) })}
              className="apple-slider"
            />
            <div className="range-ticks">
              <span>₹10k</span>
              <span>₹25L</span>
              <span>₹50L</span>
              <span>₹1 Cr</span>
            </div>
          </div>

          <div className="form-grid">
            <div className="form-group">
              <label>Fraud Risk Index (FRI)</label>
              <select
                value={config.fri_tier}
                onChange={(e) => onChange({ ...config, fri_tier: e.target.value as any })}
                className="apple-select"
              >
                <option value="NONE">None (Clean History)</option>
                <option value="MEDIUM">Medium (Unusual IP/Device)</option>
                <option value="HIGH">High (Recent SIM Swap / Mule)</option>
                <option value="VERY_HIGH">Very High (Reported Scam Flag)</option>
              </select>
            </div>

            <div className="form-group">
              <label>Communication Channel</label>
              <select
                value={config.channel}
                onChange={(e) => onChange({ ...config, channel: e.target.value as any })}
                className="apple-select"
              >
                <option value="voip">VoIP / WebRTC (High risk channel)</option>
                <option value="cellular">Cellular (VoLTE / GSM)</option>
                <option value="landline">PSTN Landline</option>
              </select>
            </div>
          </div>

          <div className="form-group">
            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={config.known_contact}
                onChange={(e) => onChange({ ...config, known_contact: e.target.checked })}
                className="apple-checkbox"
              />
              <span>Registered CLI / Known Trusted Contact (Lowers prior suspicion)</span>
            </label>
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn-primary" onClick={onClose}>
            Apply & Save Parameters
          </button>
        </div>
      </div>
    </div>
  )
}
