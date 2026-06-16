import React, { useState, useRef, useCallback } from 'react'
import { uploadFile } from '../api/client.js'

export default function InputBar({ onSend, isLoading, className }) {
  const [text, setText] = useState('')
  const [attachedFiles, setAttachedFiles] = useState([])
  const [fileContexts, setFileContexts] = useState([])
  const [jobMode, setJobMode] = useState(null)
  const [jobFilename, setJobFilename] = useState('')
  const [jobExtra, setJobExtra] = useState('')
  const textareaRef = useRef(null)
  const fileInputRef = useRef(null)

  const clear = () => {
    setText('')
    setAttachedFiles([])
    setFileContexts([])
    setJobMode(null)
    setJobFilename('')
    setJobExtra('')
  }

  const handleSend = useCallback(() => {
    if (jobMode) {
      if (!jobFilename.trim()) return
      const cmd = `/${jobMode} ${jobFilename.trim()}`
      const extra = jobExtra.trim()
      onSend(extra ? `${cmd} | ${extra}` : cmd, '')
      clear()
      return
    }
    const content = [...fileContexts, text].join('\n\n').trim()
    if (!content) return
    onSend(text, fileContexts.join('\n\n---\n\n'))
    setText('')
    setAttachedFiles([])
    setFileContexts([])
  }, [text, fileContexts, onSend, jobMode, jobFilename, jobExtra])

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
          setFileContexts(prev => [...prev, `[File attached: ${file.name}]`])
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

  const startJob = (mode) => {
    setJobMode(mode)
    setJobFilename('')
    setJobExtra('')
    setText('')
  }

  const handleSuggestion = (suggestion) => {
    setText(suggestion)
    textareaRef.current?.focus()
  }

  React.useEffect(() => {
    window.__gonzoSuggestion = handleSuggestion
  }, [])

  const canSend = jobMode
    ? jobFilename.trim()
    : text.trim() || fileContexts.length > 0

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

      {jobMode && (
        <div className="job-form">
          <div className="job-form-row">
            <span className="job-label">{jobMode === 'summarize' ? 'File' : jobMode === 'write' ? 'Filename' : 'File'}</span>
            <input
              className="job-input"
              placeholder={jobMode === 'write' ? 'myfile.txt' : 'filename.txt'}
              value={jobFilename}
              onChange={e => setJobFilename(e.target.value)}
              autoFocus
            />
            <button className="job-cancel" onClick={() => setJobMode(null)}>x</button>
          </div>
          {jobMode === 'write' && (
            <div className="job-form-row">
              <span className="job-label">Content</span>
              <textarea
                className="job-input job-textarea"
                placeholder="write whatever you want..."
                value={jobExtra}
                onChange={e => setJobExtra(e.target.value)}
                rows={3}
              />
            </div>
          )}
          {jobMode === 'rewrite' && (
            <div className="job-form-row">
              <span className="job-label">Changes</span>
              <textarea
                className="job-input job-textarea"
                placeholder="what to change..."
                value={jobExtra}
                onChange={e => setJobExtra(e.target.value)}
                rows={2}
              />
            </div>
          )}
          {jobMode === 'summarize' && (
            <div className="job-form-hint">The file content will be summarized by AI.</div>
          )}
        </div>
      )}

      {!jobMode && (
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

          <button className="input-btn" onClick={() => fileInputRef.current?.click()} disabled={isLoading} title="Attach file">
            📎
          </button>

          <button
            className={`input-btn ${canSend ? 'send-active' : ''}`}
            onClick={handleSend}
            disabled={isLoading || !canSend}
            title="Send"
          >
            {isLoading ? '⋯' : '➔'}
          </button>
        </div>
      )}

      {jobMode ? (
        <div className="action-bar" style={{ justifyContent: 'flex-end' }}>
          <button className="action-btn action-primary" onClick={handleSend} disabled={!canSend || isLoading}>
            {jobMode === 'summarize' ? 'Summarize' : jobMode === 'write' ? 'Save file' : 'Rewrite'}
          </button>
        </div>
      ) : (
        <div className="action-bar">
          <button className="action-btn" onClick={() => startJob('summarize')} disabled={isLoading}>
            <span className="action-icon">📝</span> Summarize
          </button>
          <button className="action-btn" onClick={() => startJob('write')} disabled={isLoading}>
            <span className="action-icon">📄</span> Write
          </button>
          <button className="action-btn" onClick={() => startJob('rewrite')} disabled={isLoading}>
            <span className="action-icon">🔄</span> Rewrite
          </button>
          <button className="action-btn" onClick={() => onSend('/list files', '')} disabled={isLoading}>
            <span className="action-icon">📁</span> Files
          </button>
        </div>
      )}
    </div>
  )
}
