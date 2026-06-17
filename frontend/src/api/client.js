const API = '/api'

function getSessionId() {
  const key = 'gonzo_session_id'
  let id = localStorage.getItem(key)
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem(key, id)
  }
  return id
}

function headers() {
  return { 'X-Session-ID': getSessionId() }
}

export async function uploadFile(file) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${API}/files/upload`, { method: 'POST', body: form, headers: headers() })
  if (!res.ok) throw new Error('Upload failed')
  return res.json()
}

export function getDownloadUrl(filename) {
  return `${API}/files/download/${encodeURIComponent(filename)}`
}

export async function listFiles() {
  const res = await fetch(`${API}/files/list`, { headers: headers() })
  if (!res.ok) throw new Error('Failed to list files')
  return res.json()
}

export async function deleteFile(fileId) {
  const res = await fetch(`${API}/files/${fileId}`, { method: 'DELETE', headers: headers() })
  if (!res.ok) throw new Error('Delete failed')
  return res.json()
}

export async function getMemory() {
  const res = await fetch(`${API}/memory`)
  if (!res.ok) throw new Error('Failed to get memory')
  return res.json()
}

export async function forgetMemory() {
  const res = await fetch(`${API}/memory/forget`, { method: 'POST' })
  return res.json()
}

export async function chatSend(message, history, fileContext = '') {
  const form = new FormData()
  form.append('message', message)
  form.append('history', JSON.stringify(history))
  if (fileContext) form.append('file_context', fileContext)
  const res = await fetch(`${API}/chat/stream`, { method: 'POST', body: form, headers: headers() })
  if (!res.ok) throw new Error('Chat failed')
  return res
}

export function parseSSE(line) {
  if (!line.startsWith('data: ')) return null
  try {
    return JSON.parse(line.slice(6))
  } catch {
    return null
  }
}
