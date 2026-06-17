import React from 'react'

export default function Header({ onClear, agentMode, onToggleAgent, className }) {
  return (
    <header className={`header ${className || ''}`}>
      <div className="header-left">
        <div className="gonzo-logo">Gonzo</div>
        <span className="status-badge">
          <span className="status-dot online" />
          openrouter · llama
        </span>
        <label className="mode-toggle" title="Toggle Agent Mode" onClick={onToggleAgent}>
          <span className={`mode-toggle-track ${agentMode ? 'mode-toggle-on' : ''}`}>
            <span className="mode-toggle-knob" />
          </span>
          <span className="mode-toggle-label">{agentMode ? 'Agent' : 'Chat'}</span>
        </label>
      </div>
      <div className="header-actions">
        <button className="header-btn" onClick={onToggleAgent} title="Toggle Agent Mode">
          {agentMode ? 'chat' : 'agent'}
        </button>
        <button className="header-btn" onClick={onClear} title="Clear conversation">
          clear
        </button>
      </div>
    </header>
  )
}