import React, { useCallback, useEffect, useState } from 'react'
import Header from './components/Header.jsx'
import ChatView from './components/ChatView.jsx'
import InputBar from './components/InputBar.jsx'
import { useChat } from './hooks/useChat.js'

export default function App() {
  const { messages, isLoading, sendMessage, clearChat, addAgentMessage } = useChat()
  const [waking, setWaking] = useState(true)

  useEffect(() => {
    const controller = new AbortController()
    const timeout = setTimeout(() => {
      if (!controller.signal.aborted) setWaking(false)
    }, 3000)
    fetch('/api/health', { signal: controller.signal })
      .then(r => r.ok && setWaking(false))
      .catch(() => {})
      .finally(() => clearTimeout(timeout))
    return () => controller.abort()
  }, [])

  const handleSend = useCallback((text, fileContext, attachedFiles) => {
    sendMessage(text, fileContext, attachedFiles)
  }, [sendMessage])

  const handleAgentAction = useCallback(async (action, text, extra = {}) => {
    let endpoint, body
    if (action === 'check') {
      endpoint = '/api/agent/check'
      body = { text }
    } else if (action === 'summarize') {
      endpoint = '/api/agent/summarize'
      body = { text, style: extra.style || 'full' }
    } else if (action === 'extract') {
      endpoint = '/api/agent/extract'
      body = { text, type: extra.type || 'entities', topic: extra.topic || '' }
    } else {
      return
    }
    addAgentMessage(`⚙️ Running *${action}* agent...`)
    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await res.json()
      if (data.status === 'success') {
        addAgentMessage(data.result)
      } else {
        addAgentMessage(`⚠ Agent error: ${data.error_message}`)
      }
    } catch (err) {
      addAgentMessage(`⚠ Request failed: ${err.message}`)
    }
  }, [addAgentMessage])

  return (
    <>
      <div className="gradient-bg" />
      <div className="shapes-container">
        <div className="shape shape-1" />
        <div className="shape shape-2" />
        <div className="shape shape-3" />
        <div className="shape shape-4" />
        <div className="shape shape-5" />
        <div className="shape shape-6" />
      </div>
      <div className="floating-root">
        {waking && (
          <div className="wake-banner floating-card">
            Gonzo is waking up, this may take ~15 seconds…
            <button className="wake-dismiss" onClick={() => setWaking(false)}>x</button>
          </div>
        )}
        <Header className="floating-card header" onClear={clearChat} />
        <ChatView className="floating-card chat-view" messages={messages} isLoading={isLoading} />
        <InputBar className="floating-card input-bar" onSend={handleSend} onAgentAction={handleAgentAction} isLoading={isLoading} />
      </div>
    </>
  )
}
