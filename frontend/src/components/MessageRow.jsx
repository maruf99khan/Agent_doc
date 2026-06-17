import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

function DownloadBadge({ file }) {
  if (!file || !file.url) return null
  const ext = file.filename ? file.filename.split('.').pop().toLowerCase() : ''
  return (
    <a href={file.url} className="download-badge" data-ext={ext} download>
      <span className="download-icon">↓</span>
      <span className="download-name">{file.filename}</span>
      <span className="download-hint">download</span>
    </a>
  )
}

export default function MessageRow({ message }) {
  const isUser = message.role === 'user'
  const isLoading = message.id === 'streaming'
  const content = message.content || ''

  return (
    <div className={`message-row ${isUser ? 'user-msg' : 'ai-msg'}`}>
      <div className={`message-sep ${isUser ? 'user-sep' : 'ai-sep'}`}>
        <span className="message-sep-line" />
        <span className="message-sep-text">{isUser ? 'you' : 'gonzo'}</span>
        <span className="message-sep-line" />
      </div>

      <div className="msg-content">
        {isUser ? (
          <div className="msg-text">
            <span className="prefix">&gt;</span>
            {content}
            {(message.files || []).map((f, i) => (
              <span key={i} className="file-chip msg-file-chip" data-ext={f.filename?.split('.').pop()?.toLowerCase()}>
                📎 {f.filename}
              </span>
            ))}
          </div>
        ) : isLoading && !content ? (
          <div className="typing-indicator">
            <span className="typing-dot" />
            <span className="typing-dot" />
            <span className="typing-dot" />
          </div>
        ) : (
          <div className="msg-body">
            {content ? (
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {content}
              </ReactMarkdown>
            ) : (
              <span style={{ opacity: 0.3, fontStyle: 'italic' }}>no response</span>
            )}
            {(message.files || []).map((f, i) => <DownloadBadge key={i} file={f} />)}
          </div>
        )}
      </div>
    </div>
  )
}
