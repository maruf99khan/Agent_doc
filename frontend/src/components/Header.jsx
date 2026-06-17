import React from 'react'

export default function Header({ onClear, viewMode, onToggleView, className }) {
  const isFile = viewMode === 'file'
  return (
    <header className={`header ${className || ''}`}>
      <div className="header-left">
        <div className="gonzo-logo">Gonzo</div>
        <span className="status-badge">
          <span className="status-dot online" />
          openrouter · llama
        </span>
        <label className="mode-toggle" title="Toggle Chat / File" onClick={onToggleView}>
          <span className={`mode-toggle-track ${isFile ? 'mode-toggle-on' : ''}`}>
            <span className="mode-toggle-knob" />
          </span>
          <span className="mode-toggle-label">{isFile ? 'File' : 'Chat'}</span>
        </label>
      </div>
      <div className="header-actions">
        <button className="header-btn" onClick={onToggleView} title="Toggle Chat / File">
          {isFile ? 'chat' : 'file'}
        </button>
        <button className="header-btn" onClick={onClear} title="Clear conversation">
          clear
        </button>
      </div>
    </header>
  )
}