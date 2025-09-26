import React, { useEffect, useRef } from 'react'
import { Message } from '@/types'
import { MessageBubble } from './MessageBubble'
import apacheBadge from '@/assets/apache-badge.jpg'

interface MessageListProps {
  messages: Message[]
  isLoading?: boolean
  isTyping?: boolean
}

const MessageList: React.FC<MessageListProps> = ({ messages, isLoading, isTyping }) => {
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isLoading, isTyping])

  return (
    <div className="flex h-full flex-col overflow-y-auto p-4">
      <div className="space-y-4">
        {messages.length === 0 && !isLoading && (
          <div className="flex min-h-0 flex-1 items-center justify-center">
            <div className="text-center">
              <div className="mb-4 flex justify-center">
                <img 
                  src={apacheBadge} 
                  alt="Apache Local Community Taipei" 
                  className="h-24 w-24 rounded-full object-cover shadow-lg"
                />
              </div>
              <h3 className="mb-2 text-lg font-semibold text-gray-700 dark:text-gray-300">
                歡迎使用 源來適你 AI Agent
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                我是小饅頭，Apache Local Community Taipei 的專屬AI助手！請輸入您的問題開始對話。
              </p>
            </div>
          </div>
        )}

        {messages.map((message, index) => (
          <MessageBubble
            key={message.id}
            message={message}
            showAvatar={index === 0 || messages[index - 1]?.role !== message.role}
          />
        ))}

      </div>
      <div ref={messagesEndRef} />
    </div>
  )
}

export { MessageList }
