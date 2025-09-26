import { useCallback } from 'react'
import { useChatStore } from '@/store/chatStore'
import { apiClient } from '@/services/api'
import { Message } from '@/types'

export function useChat() {
  const {
    messages,
    isLoading,
    error,
    addMessage,
    updateMessage,
    setLoading,
    setError,
    saveCurrentConversation,
  } = useChatStore()

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim()) return

    // Add user message
    const userMessage: Omit<Message, 'id' | 'timestamp'> = {
      content,
      role: 'user',
      status: 'sent',
    }
    addMessage(userMessage)

    // Add assistant message placeholder and get its ID
    const assistantMessage: Omit<Message, 'id' | 'timestamp'> = {
      content: '',
      role: 'assistant',
      status: 'sending',
    }
    addMessage(assistantMessage)

    setLoading(true)
    setError(null)

    try {
      const response = await apiClient.askQuestion(content)
      
      // Get the current messages to find the assistant message ID
      const currentMessages = useChatStore.getState().messages
      const assistantMessageId = currentMessages[currentMessages.length - 1]?.id
      
      // Update assistant message with response
      if (assistantMessageId) {
        updateMessage(assistantMessageId, {
          content: response.answer,
          sources: response.sources,
          status: 'sent',
        })
      }

      // Save conversation
      saveCurrentConversation()
    } catch (err: any) {
      // Get the current messages to find the assistant message ID
      const currentMessages = useChatStore.getState().messages
      const assistantMessageId = currentMessages[currentMessages.length - 1]?.id
      
      // Update assistant message with error
      if (assistantMessageId) {
        updateMessage(assistantMessageId, {
          content: `抱歉，發生了錯誤：${err.message || '未知錯誤'}`,
          status: 'error',
        })
      }
      setError(err.message || '發送訊息失敗')
    } finally {
      setLoading(false)
    }
  }, [addMessage, updateMessage, setLoading, setError, saveCurrentConversation])

  const clearConversation = useCallback(async () => {
    try {
      await apiClient.clearConversation()
      useChatStore.getState().clearMessages()
    } catch (err: any) {
      setError(err.message || '清除對話失敗')
    }
  }, [setError])

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    clearConversation,
  }
}
