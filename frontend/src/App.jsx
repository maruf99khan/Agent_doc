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
    currentToolStatus,
    currentToolResult,
    currentFileCreated,
    sendMessage,
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
      <div className="app-bg" />
      <div className="app-overlay">
        <Header onClear={clearChat} onForget={handleForget} />
        <ChatView
          messages={messages}
          isLoading={isLoading}
          currentToolStatus={currentToolStatus}
          currentToolResult={currentToolResult}
          currentFileCreated={currentFileCreated}
        />
        <InputBar onSend={handleSend} isLoading={isLoading} />
      </div>
    </>
  )
}
