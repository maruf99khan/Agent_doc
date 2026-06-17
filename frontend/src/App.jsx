import React, { useCallback, useEffect, useState } from 'react'
import Header from './components/Header.jsx'
import ChatView from './components/ChatView.jsx'
import InputBar from './components/InputBar.jsx'
import { useChat } from './hooks/useChat.js'

export default function App() {
  const { messages, isLoading, sendMessage, clearChat } = useChat()
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
        <InputBar className="floating-card input-bar" onSend={handleSend} isLoading={isLoading} />
      </div>
    </>
  )
}
