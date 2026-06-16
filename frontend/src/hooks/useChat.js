import { useState, useRef, useCallback } from 'react'
import { chatSend, parseSSE, getDownloadUrl } from '../api/client.js'

export function useChat() {
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [currentAiText, setCurrentAiText] = useState('')
  const [currentToolStatus, setCurrentToolStatus] = useState(null)
  const [currentToolResult, setCurrentToolResult] = useState(null)
  const [currentFileCreated, setCurrentFileCreated] = useState(null)
  const abortRef = useRef(null)

  const addMessage = useCallback((role, content, extra = {}) => {
    setMessages(prev => [...prev, { role, content, ...extra, id: Date.now() + Math.random() }])
  }, [])

  const history = messages
    .filter(m => m.role !== 'tool_status' && m.role !== 'tool_result')
    .map(m => ({ role: m.role, content: m.content }))

  const sendMessage = useCallback(async (text, fileContent = '') => {
    if (!text.trim()) return
    setIsLoading(true)
    setCurrentAiText('')
    setCurrentToolStatus(null)
    setCurrentToolResult(null)
    setCurrentFileCreated(null)

    addMessage('user', text, { files: fileContent ? [{ name: 'attached file' }] : [] })

    const textMarker = { role: 'assistant', content: '', id: 'streaming' }
    setMessages(prev => [...prev, textMarker])

    try {
      const res = await chatSend(text, history, fileContent)
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

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
            setCurrentAiText(prev => {
              const updated = prev + event.content
              setMessages(msgs => msgs.map(m =>
                m.id === 'streaming' ? { ...m, content: updated } : m
              ))
              return updated
            })
            setCurrentToolStatus(null)
          } else if (event.type === 'tool_call') {
            setCurrentToolStatus({ name: event.name, args: event.args })
            setCurrentToolResult(null)
            setCurrentFileCreated(null)
          } else if (event.type === 'tool_result') {
            setCurrentToolResult({ name: event.name, content: event.content })
            if (event.file) {
              setCurrentFileCreated({ name: event.file, url: getDownloadUrl(event.file) })
            }
          } else if (event.type === 'error') {
            setMessages(msgs => msgs.map(m =>
              m.id === 'streaming' ? { ...m, content: `⚠ Error: ${event.content}` } : m
            ))
            setCurrentToolStatus(null)
          } else if (event.type === 'done') {
            setMessages(msgs => msgs.map(m =>
              m.id === 'streaming' ? { ...m, id: Date.now() + Math.random() } : m
            ))
          }
        }
      }
    } catch (err) {
      setMessages(msgs => msgs.map(m =>
        m.id === 'streaming'
          ? { ...m, content: `⚠ Connection error: ${err.message}`, id: Date.now() }
          : m
      ))
    }

    setCurrentAiText('')
    setCurrentToolStatus(null)
    setCurrentToolResult(null)
    setCurrentFileCreated(null)
    setIsLoading(false)
  }, [addMessage, history])

  const clearChat = useCallback(() => {
    setMessages([])
    setCurrentAiText('')
    setCurrentToolStatus(null)
    setCurrentToolResult(null)
    setCurrentFileCreated(null)
  }, [])

  return {
    messages,
    isLoading,
    currentToolStatus,
    currentToolResult,
    currentFileCreated,
    sendMessage,
    clearChat,
  }
}
