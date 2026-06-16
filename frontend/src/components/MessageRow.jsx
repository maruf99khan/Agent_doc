import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

function DownloadBadge({ filename, url }) {
  return (
    <a href={url} className="download-badge" download>
      <span className="download-icon">↓</span>
      {filename}
    </a>
  )
}

function ToolStatus({ toolStatus }) {
  if (!toolStatus) return null
  const icons = {
    web_search: '🌐',
    fetch_page: '📄',
    create_pdf: '📕',
    create_docx: '📘',
    create_txt: '📄',
    read_file: '📖',
    write_file: '✏️',
    run_code: '⚙️',
    list_files: '📁',
    download_file: '⬇️',
  }
  return (
    <div className="tool-status">
      <span className="tool-icon">{icons[toolStatus.name] || '🔧'}</span>
      <span className="tool-spinner" />
      <span className="tool-label">{toolStatus.name.replace(/_/g, ' ')}</span>
      <span className="tool-arg">{JSON.stringify(toolStatus.args).slice(0, 80)}</span>
    </div>
  )
}

function ToolResult({ result }) {
  if (!result) return null
  const isError = result.content?.startsWith('Error') || result.content?.startsWith('{"error"')
  return (
    <div className={`tool-result-badge ${isError ? 'error' : 'success'}`}>
      <span>{isError ? '⚠' : '✓'}</span>
      <span>{result.content?.slice(0, 100)}{result.content?.length > 100 ? '...' : ''}</span>
    </div>
  )
}

export default function MessageRow({ message, toolStatus, toolResult, fileCreated }) {
  const isUser = message.role === 'user'
  const isLoading = message.id === 'streaming'
  const content = message.content || ''

  return (
    <div className={`message-row ${isUser ? 'user-msg' : 'ai-msg'}`}>
      <div className={`message-separator ${isUser ? 'user-sep' : 'ai-sep'}`}>
        {isUser ? 'you' : 'gonzo'}
      </div>

      <div className="message-content">
        {isUser ? (
          <div className="msg-prefix">
            <span>&gt;</span>
            {content}
          </div>
        ) : isLoading && !content ? (
          <div className="typing-indicator">
            <span className="typing-dot" />
            <span className="typing-dot" />
            <span className="typing-dot" />
          </div>
        ) : (
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              a: ({ href, children }) => {
                if (href?.startsWith('/api/')) {
                  return <a href={href} target="_blank" rel="noopener">{children}</a>
                }
                return <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>
              }
            }}
          >
            {content}
          </ReactMarkdown>
        )}
      </div>

      {isLoading && <ToolStatus toolStatus={toolStatus} />}
      {isLoading && <ToolResult result={toolResult} />}
      {isLoading && fileCreated && (
        <DownloadBadge filename={fileCreated.name} url={fileCreated.url} />
      )}
    </div>
  )
}
