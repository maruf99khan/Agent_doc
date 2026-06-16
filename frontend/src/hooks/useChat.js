import { useState, useRef, useCallback } from 'react'
import { chatSend, parseSSE, jobSummarize, jobWrite, jobRewrite, readFile } from '../api/client.js'

async function readSSEStream(response, onText, onError) {
  const reader = response.body.getReader()
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
      if (event.type === 'text') onText(event.content)
      else if (event.type === 'error') onError(event.content)
    }
  }
}

export function useChat() {
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)

  const addMessage = useCallback((role, content) => {
    setMessages(prev => [...prev, { role, content, id: Date.now() + Math.random() }])
  }, [])

  const history = messages.map(m => ({ role: m.role, content: m.content }))

  const sendMessage = useCallback(async (text, fileContent = '') => {
    if (!text.trim()) return
    setIsLoading(true)
    addMessage('user', text)

    // Detect commands
    const trimmed = text.trim()
    const parts = trimmed.split(/\s+/)
    const cmd = parts[0].toLowerCase()

    // /summarize <filename>
    if (cmd === '/summarize') {
      if (!parts[1]) {
        addMessage('assistant', '⚠ Usage: `/summarize <filename>`\nExample: `/summarize notes.txt`')
        setIsLoading(false)
        return
      }
      const filename = parts.slice(1).join(' ')
      const marker = { role: 'assistant', content: '', id: 'streaming' }
      setMessages(prev => [...prev, marker])
      try {
        const res = await jobSummarize(filename)
        let fullContent = ''
        await readSSEStream(res,
          (chunk) => {
            fullContent += chunk
            setMessages(msgs => msgs.map(m => m.id === 'streaming' ? { ...m, content: fullContent } : m))
          },
          (err) => {
            setMessages(msgs => msgs.map(m => m.id === 'streaming' ? { ...m, content: `⚠ Error: ${err}`, id: Date.now() } : m))
          }
        )
        setMessages(msgs => msgs.map(m => m.id === 'streaming' ? { ...m, id: Date.now() + Math.random() } : m))
      } catch (err) {
        setMessages(msgs => msgs.map(m => m.id === 'streaming' ? { ...m, content: `⚠ Error: ${err.message}`, id: Date.now() } : m))
      }
      setIsLoading(false)
      return
    }

    // /write <filename> | <content>
    if (cmd === '/write') {
      const pipeIdx = trimmed.indexOf('|')
      if (!parts[1] || pipeIdx < 0) {
        addMessage('assistant', '⚠ Usage: `/write <filename> | <content>`\nExample: `/write notes.txt | This is the file content`')
        setIsLoading(false)
        return
      }
      const filename = trimmed.slice(7, pipeIdx).trim()
      const content = trimmed.slice(pipeIdx + 1).trim()
      if (!filename || !content) {
        addMessage('assistant', '⚠ Both filename and content are required.\nUsage: `/write <filename> | <content>`')
        setIsLoading(false)
        return
      }
      try {
        const result = await jobWrite(filename, content)
        addMessage('assistant', `✓ Wrote **${result.file}**`)
      } catch (err) {
        addMessage('assistant', `⚠ Write failed: ${err.message}`)
      }
      setIsLoading(false)
      return
    }

    // /rewrite <filename> | <instructions>
    if (cmd === '/rewrite') {
      const pipeIdx = trimmed.indexOf('|')
      if (!parts[1] || pipeIdx < 0) {
        addMessage('assistant', '⚠ Usage: `/rewrite <filename> | <instructions>`\nExample: `/rewrite notes.txt | make this more formal`')
        setIsLoading(false)
        return
      }
      const filename = trimmed.slice(9, pipeIdx).trim()
      const instructions = trimmed.slice(pipeIdx + 1).trim()
      if (!filename || !instructions) {
        addMessage('assistant', '⚠ Both filename and instructions are required.\nUsage: `/rewrite <filename> | <instructions>`')
        setIsLoading(false)
        return
      }
      const marker = { role: 'assistant', content: '', id: 'streaming' }
      setMessages(prev => [...prev, marker])
      try {
        const res = await jobRewrite(filename, instructions)
        let fullContent = ''
        await readSSEStream(res,
          (chunk) => {
            fullContent += chunk
            setMessages(msgs => msgs.map(m => m.id === 'streaming' ? { ...m, content: fullContent } : m))
          },
          (err) => {
            setMessages(msgs => msgs.map(m => m.id === 'streaming' ? { ...m, content: `⚠ Error: ${err}`, id: Date.now() } : m))
          }
        )
        setMessages(msgs => msgs.map(m => m.id === 'streaming' ? { ...m, id: Date.now() + Math.random() } : m))
      } catch (err) {
        setMessages(msgs => msgs.map(m => m.id === 'streaming' ? { ...m, content: `⚠ Error: ${err.message}`, id: Date.now() } : m))
      }
      setIsLoading(false)
      return
    }

    // /list files
    if (cmd === '/list') {
      try {
        const files = await (await fetch('/api/files/list')).json()
        if (files.length === 0) {
          addMessage('assistant', 'No files in workspace.')
        } else {
          const list = files.map(f => `- **${f.name}** (${f.size} bytes)`).join('\n')
          addMessage('assistant', `**Files in workspace:**\n${list}`)
        }
      } catch {
        addMessage('assistant', '⚠ Failed to list files.')
      }
      setIsLoading(false)
      return
    }

    // Regular chat
    const marker = { role: 'assistant', content: '', id: 'streaming' }
    setMessages(prev => [...prev, marker])

    try {
      const res = await chatSend(text, history, fileContent)
      let fullContent = ''
      await readSSEStream(res,
        (chunk) => {
          fullContent += chunk
          setMessages(msgs => msgs.map(m => m.id === 'streaming' ? { ...m, content: fullContent } : m))
        },
        (err) => {
          setMessages(msgs => msgs.map(m => m.id === 'streaming' ? { ...m, content: `⚠ Error: ${err}`, id: Date.now() } : m))
        }
      )
      setMessages(msgs => msgs.map(m => m.id === 'streaming' ? { ...m, id: Date.now() + Math.random() } : m))
    } catch (err) {
      setMessages(msgs => msgs.map(m =>
        m.id === 'streaming' ? { ...m, content: `⚠ Connection error: ${err.message}`, id: Date.now() } : m
      ))
    }

    setIsLoading(false)
  }, [addMessage, history])

  const clearChat = useCallback(() => {
    setMessages([])
  }, [])

  return { messages, isLoading, sendMessage, clearChat }
}
