import React from 'react'

export default function Header({ onClear, onForget }) {
  return (
    <header className="header">
      <div className="header-left">
        <div className="gonzo-logo">GONZO</div>
        <span className="status-badge">
          <span className="status-dot" />
          groq · mixtral
        </span>
      </div>
      <div className="header-actions">
        <button className="header-btn" onClick={onClear}>clear</button>
        <button className="header-btn" onClick={onForget}>forget</button>
      </div>
    </header>
  )
}
