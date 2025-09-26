import React from 'react'
import { MessageList } from '@/components/chat/MessageList'
import { ChatInput } from '@/components/chat/ChatInput'
import { Sidebar } from '@/components/layout/Sidebar'
import { useChat } from '@/hooks/useChat'

const ChatPage: React.FC = () => {
  const { messages, isLoading, error, sendMessage } = useChat()

  return (
    <div className="flex h-full bg-gray-50 dark:bg-gray-900">
      <Sidebar />
      
      <div className="flex flex-1 flex-col">
        <div className="flex-1 flex flex-col overflow-hidden">
          <MessageList 
            messages={messages} 
            isLoading={isLoading}
          />
          
          {error && (
            <div className="mx-4 mb-2 rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900 dark:text-red-300">
              {error}
            </div>
          )}
          
          <ChatInput 
            onSendMessage={sendMessage}
            isLoading={isLoading}
            placeholder="例如：嘉平帥哥是誰？"
          />
        </div>
      </div>
    </div>
  )
}

export { ChatPage }
