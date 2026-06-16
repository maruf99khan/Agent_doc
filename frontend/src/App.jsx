import React, { useCallback } from 'react'
import Header from './components/Header.jsx'
import ChatView from './components/ChatView.jsx'
import InputBar from './components/InputBar.jsx'
import { useChat } from './hooks/useChat.js'
import { forgetMemory } from './api/client.js'

export default function App() {
  const {
    messages,
    isLoading,
    sendMessage,
    doSummarize,
    doWrite,
    doRewrite,
    doReport,
    doListFiles,
    clearChat,
  } = useChat()

  const handleSend = useCallback((text, fileContext) => {
    sendMessage(text, fileContext)
  }, [sendMessage])

  const handleForget = useCallback(async () => {
    await forgetMemory()
    clearChat()
  }, [clearChat])

  return (
    <>
      <div className="gradient-bg" />
      <div className="shapes-container">
        <div className="shape shape-1" />
        <div className="shape shape-2" />
        <div className="shape shape-3" />
        <div className="shape shape-4" />
        <div className="shape shape-5" />
      </div>
      <div className="floating-root">
        <Header className="floating-card header" onClear={clearChat} onForget={handleForget} />
        <ChatView
          className="floating-card chat-view"
          messages={messages}
          isLoading={isLoading}
        />
        <InputBar
          className="floating-card input-bar"
          onSend={handleSend}
          isLoading={isLoading}
          doSummarize={doSummarize}
          doWrite={doWrite}
          doRewrite={doRewrite}
          doReport={doReport}
          doListFiles={doListFiles}
        />
      </div>
    </>
  )
}
