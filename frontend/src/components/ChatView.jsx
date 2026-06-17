import React, { useRef, useEffect } from 'react'
import MessageRow from './MessageRow.jsx'

export default function ChatView({
  messages,
  isLoading,
  className,
}) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const hasMessages = messages.length > 0

  const suggestions = [
    'search the internet for latest AI news',
    'summarize the file I uploaded',
    'create a report about quantum computing',
    'read my file and suggest improvements',
    'save this conversation as a markdown file',
  ]

  return (
    <div className={`chat-view ${className || ''}`}>
      {!hasMessages ? (
        <div className="chat-empty">
          <div className="big-icon">🌀</div>
          <div className="empty-title">Gonzo Agent</div>
          <div className="empty-sub">ask me anything — research, write, create</div>
          <div className="welcome-hints">
            {suggestions.map((s, i) => (
              <span key={i} className="welcome-hint" onClick={() => window.__gonzoSuggestion?.(s)}>{s}</span>
            ))}
          </div>
        </div>
      ) : (
        <>
          {messages.map((msg) => (
            msg.id === 'streaming' ? (
              <MessageRow key="streaming" message={msg} />
            ) : (
              <MessageRow key={msg.id} message={msg} />
            )
          ))}
          <div ref={bottomRef} />
        </>
      )}
    </div>
  )
}
