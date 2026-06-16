import React, { useRef, useEffect } from 'react'
import MessageRow from './MessageRow.jsx'

export default function ChatView({
  messages,
  isLoading,
  currentToolStatus,
  currentToolResult,
  currentFileCreated,
}) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, currentToolStatus, currentToolResult])

  const hasMessages = messages.length > 0

  const suggestions = [
    'search for latest AI news and save as report.pdf',
    'summarize the attached file',
    'create a docx report about web frameworks',
    'search for Python 3.14 features and save as notes.txt',
    'write and run a python script that shows system info',
  ]

  return (
    <div className="chat-view">
      {!hasMessages ? (
        <div className="chat-empty">
          <div className="empty-icon">🌀</div>
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
              <MessageRow
                key="streaming"
                message={msg}
                toolStatus={currentToolStatus}
                toolResult={currentToolResult}
                fileCreated={currentFileCreated}
              />
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
