import React, { useState, useRef, useCallback } from 'react'
import { uploadFile } from '../api/client.js'

export default function InputBar({ onSend, onAgentAction, isLoading, className }) {
  const [text, setText] = useState('')
  const [attachedFiles, setAttachedFiles] = useState([])
  const [fileContexts, setFileContexts] = useState([])
  const [activeText, setActiveText] = useState('')
  const textareaRef = useRef(null)
  const fileInputRef = useRef(null)

  const handleSend = () => {
    const content = [...fileContexts, text].join('\n\n').trim()
    if (!content) return
    onSend(text, fileContexts.join('\n\n---\n\n'), attachedFiles.map(f => f.name))
    setText('')
    setAttachedFiles([])
    setFileContexts([])
    setActiveText('')
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleFilePick = async (e) => {
    const files = Array.from(e.target.files)
    for (const file of files) {
      try {
        const result = await uploadFile(file)
        const ext = file.name.split('.').pop()?.toLowerCase()
        setAttachedFiles(prev => [...prev, { name: file.name, id: result.file_id }])
        if (result.extracted_text) {
          const ctx = `--- File: ${file.name} ---\n${result.extracted_text}`
          setFileContexts(prev => [...prev, ctx])
          setActiveText(prev => prev + (prev ? '\n\n' : '') + ctx)
        } else if (['txt', 'md', 'py', 'js', 'json', 'csv', 'html', 'css', 'xml', 'yaml', 'yml'].includes(ext)) {
          const t = await file.text()
          const ctx = `--- File: ${file.name} ---\n${t}`
          setFileContexts(prev => [...prev, ctx])
          setActiveText(prev => prev + (prev ? '\n\n' : '') + ctx)
        } else {
          setFileContexts(prev => [...prev, `[File attached: ${file.name}]`])
          setActiveText(prev => prev + (prev ? '\n\n' : '') + `[File attached: ${file.name}]`)
        }
      } catch (err) {
        console.error('Upload failed:', err)
      }
    }
    e.target.value = ''
  }

  const removeFile = (index) => {
    setAttachedFiles(prev => prev.filter((_, i) => i !== index))
    setFileContexts(prev => prev.filter((_, i) => i !== index))
  }

  const handleSuggestion = (suggestion) => {
    setText(suggestion)
    textareaRef.current?.focus()
  }

  React.useEffect(() => {
    window.__gonzoSuggestion = handleSuggestion
  }, [])

  const docText = fileContexts.length > 0 ? fileContexts.join('\n\n') : ''

  return (
    <div className={`input-bar ${className || ''}`}>
      {attachedFiles.length > 0 && (
        <div className="file-attachments">
          {attachedFiles.map((f, i) => (
            <span key={i} className="file-chip" data-ext={f.name.split('.').pop().toLowerCase()}>
              📎 {f.name}
              <span className="chip-remove" onClick={() => removeFile(i)}>x</span>
            </span>
          ))}
        </div>
      )}

      {attachedFiles.length > 0 && (
        <div className="agent-actions">
          <button className="agent-btn agent-review" onClick={() => onAgentAction('check', docText)} disabled={isLoading}>
            📝 Review
          </button>
          <button className="agent-btn agent-summarize" onClick={() => onAgentAction('summarize', docText)} disabled={isLoading}>
            📋 Summarize
          </button>
          <button className="agent-btn agent-extract" onClick={() => onAgentAction('extract', docText)} disabled={isLoading}>
            🔍 Extract
          </button>
        </div>
      )}

      <div className="input-row">
        <textarea
          ref={textareaRef}
          className="input-textarea"
          rows={1}
          placeholder="ask anything — or upload a file and chat about it..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
          autoFocus
        />

        <input
          ref={fileInputRef}
          type="file"
          multiple
          onChange={handleFilePick}
          style={{ display: 'none' }}
          accept=".txt,.md,.py,.js,.json,.csv,.html,.css,.xml,.docx,.pdf,.png,.jpg,.jpeg,.gif,.zip"
        />

        <button className="input-btn" onClick={() => fileInputRef.current?.click()} disabled={isLoading} title="Upload file">
          📎
        </button>

        <button
          className={`input-btn ${text.trim() || fileContexts.length > 0 ? 'send-active' : ''}`}
          onClick={handleSend}
          disabled={isLoading || !(text.trim() || fileContexts.length > 0)}
          title="Send"
        >
          {isLoading ? '⋯' : '➔'}
        </button>
      </div>
    </div>
  )
}
