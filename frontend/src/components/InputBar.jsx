import React, { useState, useRef, useCallback } from 'react'
import { uploadFile, jobWrite } from '../api/client.js'

export default function InputBar({ onSend, isLoading, className }) {
  const [text, setText] = useState('')
  const [attachedFiles, setAttachedFiles] = useState([])
  const [fileContexts, setFileContexts] = useState([])
  const textareaRef = useRef(null)
  const fileInputRef = useRef(null)

  const handleSend = useCallback(() => {
    const content = [...fileContexts, text].join('\n\n').trim()
    if (!content) return
    onSend(text, fileContexts.join('\n\n---\n\n'))
    setText('')
    setAttachedFiles([])
    setFileContexts([])
  }, [text, fileContexts, onSend])

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
        setAttachedFiles(prev => [...prev, { name: file.name, id: result.file_id }])

        const ext = file.name.split('.').pop()?.toLowerCase()
        if (['txt', 'md', 'py', 'js', 'json', 'csv', 'html', 'css', 'xml', 'yaml', 'yml'].includes(ext)) {
          const text = await file.text()
          setFileContexts(prev => [...prev, `--- File: ${file.name} ---\n${text}`])
        } else {
          setFileContexts(prev => [...prev, `[File attached: ${file.name} — analyze it if needed]`])
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

  return (
    <div className={`input-bar ${className || ''}`}>
      {attachedFiles.length > 0 && (
        <div className="file-attachments">
          {attachedFiles.map((f, i) => (
            <span key={i} className="file-chip">
              📎 {f.name}
              <span className="chip-remove" onClick={() => removeFile(i)}>x</span>
            </span>
          ))}
        </div>
      )}

      <div className="input-row">
        <textarea
          ref={textareaRef}
          className="input-textarea"
          rows={1}
          placeholder="ask anything..."
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

        <button
          className="input-btn"
          onClick={() => fileInputRef.current?.click()}
          disabled={isLoading}
          title="Attach file"
        >
          📎
        </button>

        <button
          className={`input-btn ${text.trim() ? 'send-active' : ''}`}
          onClick={handleSend}
          disabled={isLoading || (!text.trim() && fileContexts.length === 0)}
          title="Send"
        >
          {isLoading ? '⋯' : '➔'}
        </button>
      </div>

      <div className="action-bar">
        <button className="action-btn" onClick={() => setText(prev => prev + '/summarize ')} disabled={isLoading}>
          <span className="action-icon">📝</span> Summarize
        </button>
        <button className="action-btn" onClick={() => setText(prev => prev + '/write ')} disabled={isLoading}>
          <span className="action-icon">📄</span> Write
        </button>
        <button className="action-btn" onClick={() => setText(prev => prev + '/rewrite ')} disabled={isLoading}>
          <span className="action-icon">🔄</span> Rewrite
        </button>
        <button className="action-btn" onClick={() => setText('/list files')} disabled={isLoading}>
          <span className="action-icon">📁</span> Files
        </button>
      </div>
    </div>
  )
}
