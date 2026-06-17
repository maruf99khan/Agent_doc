import { useState, useCallback } from 'react'
import { chatSend, parseSSE } from '../api/client.js'

const TOOL_LABELS = {
  web_search: (d) => `🔍 Searching: ${d}...`,
  create_file: (d) => `📄 Creating ${d}...`,
  read_file: (d) => `📖 Reading ${d}...`,
  list_files: () => '📁 Listing files...',
}

export function useChat() {
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)

  const addMessage = useCallback((role, content, extra = {}) => {
    setMessages(prev => [...prev, { role, content, ...extra, id: Date.now() + Math.random() }])
  }, [])

  const history = messages.map(m => ({ role: m.role, content: m.content }))

  const sendMessage = useCallback(async (text, fileContent = '', attachedFiles = []) => {
    if (!text.trim() && !fileContent) return
    setIsLoading(true)
    addMessage('user', text, attachedFiles.length ? { files: attachedFiles.map(name => ({ filename: name })) } : {})

    const marker = { role: 'assistant', content: '', id: 'streaming' }
    setMessages(prev => [...prev, marker])

    try {
      const res = await chatSend(text, history, fileContent)
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let fullContent = ''
      let hasContent = false
      let toolMode = false

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        for (const line of lines) {
          const event = parseSSE(line)
          if (!event) continue
          if (event.type === 'tool_progress') {
            toolMode = true
            const label = (TOOL_LABELS[event.tool] || (() => `⚙️ Running ${event.tool}...`))(event.detail)
            setMessages(msgs => msgs.map(m =>
              m.id === 'streaming' ? { ...m, content: label, _toolMode: true } : m
            ))
          } else if (event.type === 'text') {
            if (toolMode) {
              toolMode = false
              fullContent = event.content
            } else {
              fullContent += event.content
            }
            hasContent = true
            setMessages(msgs => msgs.map(m =>
              m.id === 'streaming' ? { ...m, content: fullContent, _toolMode: false } : m
            ))
          } else if (event.type === 'file_created') {
            setMessages(msgs => msgs.map(m =>
              m.id === 'streaming'
                ? { ...m, files: [...(m.files || []), { filename: event.filename, url: event.url }] }
                : m
            ))
          } else if (event.type === 'warning') {
            setMessages(msgs => msgs.map(m =>
              m.id === 'streaming' ? { ...m, content: (m.content || '') + '\n\n⚠️ ' + event.content } : m
            ))
          } else if (event.type === 'error') {
            setMessages(msgs => msgs.map(m =>
              m.id === 'streaming' ? { ...m, content: `⚠ ${event.content}`, id: Date.now() } : m
            ))
          }
        }
      }

      setMessages(msgs => msgs.map(m =>
        m.id === 'streaming'
          ? { ...m, id: Date.now() + Math.random(), ...(!hasContent && !toolMode ? { content: '(no response)' } : {}) }
          : m
      ))
    } catch (err) {
      setMessages(msgs => msgs.map(m =>
        m.id === 'streaming' ? { ...m, content: `⚠ Error: ${err.message}`, id: Date.now() } : m
      ))
    }
    setIsLoading(false)
  }, [addMessage, history])

  const clearChat = useCallback(() => setMessages([]), [])

  const addAgentMessage = useCallback((content) => {
    addMessage('assistant', content)
  }, [addMessage])

  return { messages, isLoading, sendMessage, clearChat, addAgentMessage }
}
