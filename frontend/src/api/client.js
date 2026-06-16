const API = '/api'

export async function uploadFile(file) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${API}/files/upload`, { method: 'POST', body: form })
  if (!res.ok) throw new Error('Upload failed')
  return res.json()
}

export function getDownloadUrl(filename) {
  return `${API}/files/download/${encodeURIComponent(filename)}`
}

export async function listFiles() {
  const res = await fetch(`${API}/files/list`)
  if (!res.ok) throw new Error('Failed to list files')
  return res.json()
}

export async function deleteFile(fileId) {
  const res = await fetch(`${API}/files/${fileId}`, { method: 'DELETE' })
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
  const res = await fetch(`${API}/chat/stream`, { method: 'POST', body: form })
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

// ── Job API ──

export async function jobSummarize(filename) {
  const form = new FormData()
  form.append('filename', filename)
  return fetch(`${API}/jobs/summarize`, { method: 'POST', body: form })
}

export async function jobWrite(filename, content) {
  const form = new FormData()
  form.append('filename', filename)
  form.append('content', content)
  const res = await fetch(`${API}/jobs/write`, { method: 'POST', body: form })
  if (!res.ok) throw new Error('Write failed')
  return res.json()
}

export function jobRewrite(filename, instructions = '') {
  const form = new FormData()
  form.append('filename', filename)
  form.append('instructions', instructions)
  return fetch(`${API}/jobs/rewrite`, { method: 'POST', body: form })
}

export async function readFile(filename) {
  const res = await fetch(`${API}/files/read/${encodeURIComponent(filename)}`)
  if (!res.ok) throw new Error('File not found')
  return res.json()
}
