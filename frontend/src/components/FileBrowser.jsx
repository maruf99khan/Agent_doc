import React, { useState, useEffect, useCallback } from 'react'
import { uploadFile } from '../api/client.js'

function getSessionId() {
  const key = 'gonzo_session_id'
  let id = localStorage.getItem(key)
  if (!id) { id = crypto.randomUUID(); localStorage.setItem(key, id) }
  return id
}
function sessHeaders() { return { 'X-Session-ID': getSessionId() } }

function formatSize(bytes) {
  if (!bytes || bytes === 0) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function extColor(ext) {
  const colors = {
    pdf: 'purple', docx: 'blue', txt: 'teal',
    py: 'cyan', js: 'cyan', json: 'cyan', md: 'teal',
  }
  return colors[ext] || 'cyan'
}

export default function FileBrowser() {
  const [files, setFiles] = useState([])
  const [loading, setLoading] = useState(true)

  const loadFiles = useCallback(async () => {
    try {
      const res = await fetch('/api/files/list', { headers: sessHeaders() })
      const data = await res.json()
      if (Array.isArray(data)) setFiles(data)
      else if (data.files) setFiles(data.files)
    } catch (err) {
      console.error('Failed to load files:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadFiles() }, [loadFiles])

  const handleUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      await uploadFile(file)
      e.target.value = ''
      loadFiles()
    } catch (err) {
      console.error('Upload failed:', err)
    }
  }

  const handleDelete = async (name) => {
    if (!confirm(`Delete ${name}?`)) return
    try {
      await fetch(`/api/files/${encodeURIComponent(name)}`, { method: 'DELETE', headers: sessHeaders() })
      loadFiles()
    } catch (err) {
      console.error('Delete failed:', err)
    }
  }

  return (
    <div className="agent-tabs floating-card" style={{ flex: 1, minHeight: 0 }}>
      <div className="tabs-header">
        <div className="tabs-header-left">
          <span className="tab-btn tab-active" style={{ flex: 'none', padding: '10px 20px', cursor: 'default' }}>
            📁 File Browser
          </span>
        </div>
        <div style={{ padding: '4px 8px' }}>
          <input type="file" id="filebrowser-upload" onChange={handleUpload} hidden />
          <label htmlFor="filebrowser-upload" className="upload-label" style={{ margin: 0 }}>📎 Upload</label>
        </div>
      </div>
      <div className="tab-content">
        {loading ? (
          <div className="download-empty" style={{ padding: '40px' }}>Loading files...</div>
        ) : files.length === 0 ? (
          <div className="download-empty" style={{ padding: '40px' }}>
            No files in workspace. Upload a file to get started.
          </div>
        ) : (
          <div className="download-items">
            {files.map(f => {
              const ext = f.name?.split('.').pop()?.toLowerCase() || ''
              const ts = f.modified ? new Date(f.modified * 1000).toLocaleString() : ''
              return (
                <div key={f.name} className="download-row">
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{
                      fontSize: 9, textTransform: 'uppercase', letterSpacing: 1,
                      color: `var(--gonzo-${extColor(ext)})`, opacity: 0.6, minWidth: 32
                    }}>.{ext}</span>
                    <div>
                      <div className="download-row-label" style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)' }}>
                        {f.name}
                      </div>
                      <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.08)' }}>
                        {formatSize(f.size)} · {ts}
                      </div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 4 }}>
                    <a
                      href={`/api/files/download/${encodeURIComponent(f.name)}`}
                      className="download-row-btn"
                      style={{ textDecoration: 'none' }}
                    >
                      📥
                    </a>
                    <button className="download-row-btn" onClick={() => handleDelete(f.name)}
                      style={{ borderColor: 'rgba(240,106,106,0.06)', color: 'rgba(240,106,106,0.5)' }}>
                      🗑
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
