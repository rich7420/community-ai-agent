import React, { useState, useRef, useEffect } from 'react'
import { Send, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { cn } from '@/lib/utils'

interface ChatInputProps {
  onSendMessage: (message: string) => void
  isLoading?: boolean
  placeholder?: string
  disabled?: boolean
}

const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  isLoading = false,
  placeholder = '請輸入您的問題...',
  disabled = false,
}) => {
  const [message, setMessage] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (message.trim() && !isLoading && !disabled) {
      onSendMessage(message.trim())
      setMessage('')
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`
    }
  }, [message])

  return (
    <div className="border-t border-coffee-200 bg-white p-4 dark:border-coffee-700 dark:bg-gray-800">
      <form onSubmit={handleSubmit} className="flex items-end space-x-3">
        <div className="flex-1">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled || isLoading}
            className={cn(
              'w-full resize-none rounded-lg border-2 border-coffee-200 px-3 py-2 text-base placeholder-gray-400 transition-colors focus:border-coffee-500 focus:outline-none focus:ring-2 focus:ring-coffee-500 focus:ring-offset-2 disabled:bg-gray-50 disabled:text-gray-500 dark:border-coffee-700 dark:bg-gray-700 dark:text-white dark:placeholder-gray-500 dark:focus:border-coffee-400',
              'min-h-[44px] max-h-32'
            )}
            rows={1}
          />
        </div>
        <Button
          type="submit"
          size="md"
          loading={isLoading}
          disabled={!message.trim() || disabled}
          className="flex-shrink-0"
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </Button>
      </form>
      
      <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
        按 Enter 發送，Shift + Enter 換行
      </div>
    </div>
  )
}

export { ChatInput }
