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
    'list my files',
    'summarize the attached file',
    'create a pdf report about web frameworks',
    'read notes.txt and summarize it',
    'create a docx file with a project overview',
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
