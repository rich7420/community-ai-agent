import React from 'react'
import { Message } from '@/types'
import { cn, formatTime } from '@/lib/utils'
import { User } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { tomorrow } from 'react-syntax-highlighter/dist/esm/styles/prism'
import apacheBadge from '@/assets/apache-badge.jpg'

interface MessageBubbleProps {
  message: Message
  showAvatar?: boolean
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message, showAvatar = true }) => {
  const isUser = message.role === 'user'
  const isError = message.status === 'error'

  return (
    <div className={cn('flex gap-2 sm:gap-3', isUser ? 'flex-row-reverse' : 'flex-row')}>
      {showAvatar && (
        <div className={cn('flex-shrink-0', isUser ? 'ml-2 sm:ml-3' : 'mr-2 sm:mr-3')}>
          <div
            className={cn(
              'flex h-6 w-6 sm:h-8 sm:w-8 items-center justify-center rounded-full overflow-hidden',
              isUser
                ? 'bg-coffee-500 text-white'
                : ''
            )}
          >
            {isUser ? (
              <User size={12} className="sm:w-4 sm:h-4" />
            ) : (
              <img 
                src={apacheBadge} 
                alt="小饅頭" 
                className="h-full w-full object-cover"
              />
            )}
          </div>
        </div>
      )}

      <div className={cn('flex max-w-[85%] sm:max-w-[80%] flex-col', isUser ? 'items-end' : 'items-start')}>
        <div
          className={cn(
            'rounded-xl sm:rounded-2xl px-3 py-2 sm:px-4 shadow-sm break-words overflow-hidden',
            isUser
              ? 'bg-coffee-500 text-white'
              : 'bg-white text-gray-900 dark:bg-gray-700 dark:text-white',
            isError && 'border-2 border-red-500 bg-red-50 text-red-700 dark:bg-red-900 dark:text-red-300',
            message.status === 'sending' && 'opacity-70'
          )}
        >
          {message.status === 'sending' ? (
            <div className="flex items-center space-x-2 text-gray-500 dark:text-gray-400">
              <div className="flex items-center space-x-1">
                <div className="h-1.5 w-1.5 sm:h-2 sm:w-2 animate-bounce rounded-full bg-coffee-500"></div>
                <div className="h-1.5 w-1.5 sm:h-2 sm:w-2 animate-bounce rounded-full bg-coffee-500 animation-delay-200"></div>
                <div className="h-1.5 w-1.5 sm:h-2 sm:w-2 animate-bounce rounded-full bg-coffee-500 animation-delay-400"></div>
              </div>
              <span className="text-xs sm:text-sm">小饅頭正在思考中...</span>
            </div>
          ) : (
            <div className="prose prose-xs sm:prose-sm max-w-none dark:prose-invert break-words overflow-wrap-anywhere">
              <ReactMarkdown
                components={{
                  code({ className, children }) {
                    const match = /language-(\w+)/.exec(className || '')
                    return match ? (
                      <SyntaxHighlighter
                        style={tomorrow as any}
                        language={match[1]}
                        PreTag="div"
                        className="overflow-x-auto"
                      >
                        {String(children).replace(/\n$/, '')}
                      </SyntaxHighlighter>
                    ) : (
                      <code className={className}>
                        {children}
                      </code>
                    )
                  },
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>

        <div className="mt-1 flex items-center space-x-2 text-xs text-gray-500 dark:text-gray-400">
          <span className="text-xs">{formatTime(message.timestamp)}</span>
          {message.status === 'error' && (
            <span className="text-red-500 text-xs">發送失敗</span>
          )}
        </div>

      </div>
    </div>
  )
}

export { MessageBubble }
