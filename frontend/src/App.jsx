import React, { useCallback, useEffect, useState } from 'react'
import Header from './components/Header.jsx'
import ChatView from './components/ChatView.jsx'
import InputBar from './components/InputBar.jsx'
import AgentTabs from './components/AgentTabs.jsx'
import { useChat } from './hooks/useChat.js'

export default function App() {
  const { messages, isLoading, sendMessage, clearChat, addAgentMessage } = useChat()
  const [waking, setWaking] = useState(true)
  const [results, setResults] = useState({})
  const [docText, setDocText] = useState('')
  const [agentMode, setAgentMode] = useState(false)

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

  const handleDocumentText = useCallback((text) => {
    setDocText(text)
    setAgentMode(true)
  }, [])

  const toggleAgentMode = useCallback(() => {
    setAgentMode(prev => !prev)
  }, [])

  const clearDocument = useCallback(() => {
    setDocText('')
    setResults({})
  }, [])

  const handleAgentAction = useCallback(async (action, text, extra = {}) => {
    let endpoint, body
    if (action === 'check') {
      endpoint = '/api/agent/check'
      body = { text, quick: extra.quick || false }
    } else if (action === 'check_quick') {
      endpoint = '/api/agent/check'
      body = { text, quick: true }
    } else if (action === 'summarize') {
      endpoint = '/api/agent/summarize'
      body = { text, style: extra.style || 'full' }
    } else if (action === 'extract') {
      endpoint = '/api/agent/extract'
      body = { text, type: extra.type || 'entities', topic: extra.topic || '' }
      if (body.type === 'research' && !body.topic) return
    } else {
      return
    }
    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await res.json()
      if (data.status === 'success') {
        let key
        if (action === 'check' || action === 'check_quick') key = 'review'
        else if (action === 'summarize') {
          key = extra.style === 'bullet' ? 'bulletSummary' : extra.style === 'quick' ? 'quickSummary' : 'summary'
        } else if (action === 'extract') {
          key = extra.type === 'report' ? 'report' : extra.type === 'research' ? 'research' : 'extract'
        }
        setResults(prev => ({ ...prev, [key]: data.result }))
      }
    } catch (err) {
      console.error('Agent action failed:', err)
    }
  }, [])

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
        <Header className="floating-card header" onClear={clearChat} agentMode={agentMode} onToggleAgent={toggleAgentMode} />
        <AgentTabs
          docText={docText}
          onDocText={handleDocumentText}
          onClearDoc={clearDocument}
          forceShow={agentMode}
          results={results}
          onAgentAction={handleAgentAction}
          isLoading={isLoading}
        >
          <ChatView className="chat-view" messages={messages} isLoading={isLoading} />
          <InputBar className="input-bar" onSend={handleSend} onDocumentText={handleDocumentText} isLoading={isLoading} />
        </AgentTabs>
      </div>
    </>
  )
}
