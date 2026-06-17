import React from 'react'

export default function Header({ onClear, className }) {
  return (
    <header className={`header ${className || ''}`}>
      <div className="header-left">
        <div className="gonzo-logo">Gonzo</div>
        <span className="status-badge">
          <span className="status-dot online" />
          openrouter · llama
        </span>
      </div>
      <div className="header-actions">
        <button className="header-btn" onClick={onClear} title="Clear conversation">
          clear
        </button>
      </div>
    </header>
  )
}