import { useState, useCallback } from 'react'
import { chatSend, parseSSE } from '../api/client.js'

export function useChat() {
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)

  const addMessage = useCallback((role, content, extra = {}) => {
    setMessages(prev => [...prev, { role, content, ...extra, id: Date.now() + Math.random() }])
  }, [])

  const history = messages.map(m => ({ role: m.role, content: m.content }))

  const sendMessage = useCallback(async (text, fileContent = '') => {
    if (!text.trim()) return
    setIsLoading(true)
    addMessage('user', text)

    const marker = { role: 'assistant', content: '', id: 'streaming' }
    setMessages(prev => [...prev, marker])

    try {
      const res = await chatSend(text, history, fileContent)
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let fullContent = ''
      let hasContent = false

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        for (const line of lines) {
          const event = parseSSE(line)
          if (!event) continue
          if (event.type === 'text') {
            hasContent = true
            fullContent += event.content
            setMessages(msgs => msgs.map(m =>
              m.id === 'streaming' ? { ...m, content: fullContent } : m
            ))
          } else if (event.type === 'file_created') {
            setMessages(msgs => msgs.map(m =>
              m.id === 'streaming'
                ? { ...m, files: [...(m.files || []), { filename: event.filename, url: event.url }] }
                : m
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
          ? { ...m, id: Date.now() + Math.random(), ...(!hasContent ? { content: '(no response)' } : {}) }
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

  return { messages, isLoading, sendMessage, clearChat }
}
