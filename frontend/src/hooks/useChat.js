import { useState, useCallback } from 'react'
import { chatSend, parseSSE, jobSummarize, jobWrite, jobRewrite } from '../api/client.js'

async function readSSEStream(response, handlers) {
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  const { onText, onError, onFileCreated } = handlers
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''
    for (const line of lines) {
      const event = parseSSE(line)
      if (!event) continue
      if (event.type === 'text') onText(event.content)
      else if (event.type === 'file_created') onFileCreated?.(event)
      else if (event.type === 'error') onError(event.content)
    }
  }
}

export function useChat() {
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)

  const addMessage = useCallback((role, content, extra = {}) => {
    setMessages(prev => [...prev, { role, content, ...extra, id: Date.now() + Math.random() }])
  }, [])

  const history = messages.map(m => ({ role: m.role, content: m.content }))

  function addStreaming() {
    const marker = { role: 'assistant', content: '', id: 'streaming' }
    setMessages(prev => [...prev, marker])
    return marker
  }

  function updateStreaming(text, fileEvent) {
    setMessages(msgs => msgs.map(m =>
      m.id === 'streaming'
        ? { ...m, content: text, ...(fileEvent ? { file: fileEvent } : {}) }
        : m
    ))
  }

  function finalizeStreaming() {
    setMessages(msgs => msgs.map(m =>
      m.id === 'streaming'
        ? { ...m, id: Date.now() + Math.random() }
        : m
    ))
  }

  function replaceStreaming(content) {
    setMessages(msgs => msgs.map(m =>
      m.id === 'streaming'
        ? { ...m, content, id: Date.now() + Math.random() }
        : m
    ))
  }

  const sendMessage = useCallback(async (text, fileContent = '') => {
    if (!text.trim()) return
    setIsLoading(true)
    addMessage('user', text)
    addStreaming()
    try {
      const res = await chatSend(text, history, fileContent)
      let fullContent = ''
      await readSSEStream(res, {
        onText: (chunk) => { fullContent += chunk; updateStreaming(fullContent) },
        onError: (err) => { replaceStreaming(`⚠ Error: ${err}`) },
      })
      finalizeStreaming()
    } catch (err) {
      replaceStreaming(`⚠ Error: ${err.message}`)
    }
    setIsLoading(false)
  }, [addMessage, history])

  const doSummarize = useCallback(async (filename) => {
    setIsLoading(true)
    addMessage('user', `/summarize ${filename}`)
    addStreaming()
    try {
      const res = await jobSummarize(filename)
      let content = ''
      await readSSEStream(res, {
        onText: (chunk) => { content += chunk; updateStreaming(content) },
        onError: (err) => { replaceStreaming(`⚠ Error: ${err}`) },
      })
      finalizeStreaming()
    } catch (err) {
      replaceStreaming(`⚠ Error: ${err.message}`)
    }
    setIsLoading(false)
  }, [addMessage])

  const doWrite = useCallback(async (filename, content) => {
    setIsLoading(true)
    addMessage('user', `/write ${filename}`)
    try {
      const result = await jobWrite(filename, content)
      addMessage('assistant', `✓ Wrote **${result.filename}**`, { file: result })
    } catch (err) {
      addMessage('assistant', `⚠ Write failed: ${err.message}`)
    }
    setIsLoading(false)
  }, [addMessage])

  const doRewrite = useCallback(async (filename, instructions) => {
    setIsLoading(true)
    addMessage('user', `/rewrite ${filename}`)
    addStreaming()
    try {
      const res = await jobRewrite(filename, instructions)
      let content = ''
      let createdFile = null
      await readSSEStream(res, {
        onText: (chunk) => { content += chunk; updateStreaming(content) },
        onFileCreated: (event) => { createdFile = event; updateStreaming(content, event) },
        onError: (err) => { replaceStreaming(`⚠ Error: ${err}`) },
      })
      finalizeStreaming()
    } catch (err) {
      replaceStreaming(`⚠ Error: ${err.message}`)
    }
    setIsLoading(false)
  }, [addMessage])

  const doReport = useCallback(async (topic) => {
    setIsLoading(true)
    addMessage('user', `/report ${topic}`)
    addStreaming()
    try {
      const form = new FormData()
      form.append('topic', topic)
      form.append('history', JSON.stringify(history.slice(-6)))
      const res = await fetch('/api/jobs/report', { method: 'POST', body: form })
      let content = ''
      let createdFile = null
      await readSSEStream(res, {
        onText: (chunk) => { content += chunk; updateStreaming(content) },
        onFileCreated: (event) => { createdFile = event; updateStreaming(content, event) },
        onError: (err) => { replaceStreaming(`⚠ Error: ${err}`) },
      })
      finalizeStreaming()
    } catch (err) {
      replaceStreaming(`⚠ Error: ${err.message}`)
    }
    setIsLoading(false)
  }, [addMessage, history])

  const doListFiles = useCallback(async () => {
    setIsLoading(true)
    try {
      const res = await fetch('/api/files/list')
      const files = await res.json()
      if (files.length === 0) {
        addMessage('assistant', 'No files in workspace.')
      } else {
        addMessage('assistant',
          '**Files:**\n' +
          files.map(f => `- **${f.name}** (${f.size} bytes)  [↓](/api/files/download/${f.name})`).join('\n')
        )
      }
    } catch {
      addMessage('assistant', '⚠ Failed to list files.')
    }
    setIsLoading(false)
  }, [addMessage])

  const clearChat = useCallback(() => setMessages([]), [])

  return { messages, isLoading, sendMessage, doSummarize, doWrite, doRewrite, doReport, doListFiles, clearChat }
}
