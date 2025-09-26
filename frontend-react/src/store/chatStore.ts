import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { ChatState, Message, Conversation } from '@/types'
import { generateId } from '@/lib/utils'

interface ChatStore extends ChatState {
  // Actions
  addMessage: (message: Omit<Message, 'id' | 'timestamp'>) => void
  updateMessage: (id: string, updates: Partial<Message>) => void
  setLoading: (loading: boolean) => void
  setCurrentQuestion: (question: string) => void
  setError: (error: string | null) => void
  clearMessages: () => void
  addConversation: (conversation: Conversation) => void
  updateConversation: (id: string, updates: Partial<Conversation>) => void
  deleteConversation: (id: string) => void
  setActiveConversation: (id: string | null) => void
  loadConversation: (id: string) => void
  saveCurrentConversation: () => void
}

export const useChatStore = create<ChatStore>()(
  persist(
    (set, get) => ({
      // Initial state
      messages: [],
      isLoading: false,
      currentQuestion: '',
      conversations: [],
      activeConversationId: null,
      error: null,

      // Actions
      addMessage: (messageData) => {
        const message: Message = {
          ...messageData,
          id: generateId(),
          timestamp: new Date(),
        }
        
        set((state) => ({
          messages: [...state.messages, message],
        }))

        // Auto-save to current conversation
        const { activeConversationId } = get()
        if (activeConversationId) {
          const { conversations } = get()
          const conversation = conversations.find(c => c.id === activeConversationId)
          if (conversation) {
            get().updateConversation(activeConversationId, {
              messages: [...conversation.messages, message],
              updatedAt: new Date(),
            })
          }
        }
      },

      updateMessage: (id, updates) => {
        set((state) => ({
          messages: state.messages.map((msg) =>
            msg.id === id ? { ...msg, ...updates } : msg
          ),
        }))
      },

      setLoading: (loading) => {
        set({ isLoading: loading })
      },

      setCurrentQuestion: (question) => {
        set({ currentQuestion: question })
      },

      setError: (error) => {
        set({ error })
      },

      clearMessages: () => {
        set({ messages: [], currentQuestion: '', error: null })
      },

      addConversation: (conversation) => {
        set((state) => ({
          conversations: [conversation, ...state.conversations],
        }))
      },

      updateConversation: (id, updates) => {
        set((state) => ({
          conversations: state.conversations.map((conv) =>
            conv.id === id ? { ...conv, ...updates } : conv
          ),
        }))
      },

      deleteConversation: (id) => {
        set((state) => ({
          conversations: state.conversations.filter((conv) => conv.id !== id),
          activeConversationId: state.activeConversationId === id ? null : state.activeConversationId,
        }))
      },

      setActiveConversation: (id) => {
        set({ activeConversationId: id })
      },

      loadConversation: (id) => {
        const { conversations } = get()
        const conversation = conversations.find(c => c.id === id)
        if (conversation) {
          set({
            messages: conversation.messages,
            activeConversationId: id,
            error: null,
          })
        }
      },

      saveCurrentConversation: () => {
        const { messages, activeConversationId } = get()
        
        if (messages.length === 0) return

        const title = messages[0]?.content?.substring(0, 50) + '...' || 'New Conversation'
        
        if (activeConversationId) {
          // Update existing conversation
          get().updateConversation(activeConversationId, {
            messages,
            title,
            updatedAt: new Date(),
          })
        } else {
          // Create new conversation
          const newConversation: Conversation = {
            id: generateId(),
            title,
            messages,
            createdAt: new Date(),
            updatedAt: new Date(),
          }
          get().addConversation(newConversation)
          set({ activeConversationId: newConversation.id })
        }
      },
    }),
    {
      name: 'chat-storage',
      partialize: (state) => ({
        conversations: state.conversations,
        activeConversationId: state.activeConversationId,
      }),
      serialize: (state) => {
        // 確保日期對象被正確序列化
        const serializedState = JSON.parse(JSON.stringify(state))
        return JSON.stringify(serializedState)
      },
      deserialize: (str) => {
        const parsed = JSON.parse(str)
        // 將字符串日期轉換回Date對象
        if (parsed.conversations) {
          parsed.conversations = parsed.conversations.map((conv: any) => ({
            ...conv,
            createdAt: conv.createdAt ? new Date(conv.createdAt) : new Date(),
            updatedAt: conv.updatedAt ? new Date(conv.updatedAt) : new Date(),
            messages: conv.messages ? conv.messages.map((msg: any) => ({
              ...msg,
              timestamp: msg.timestamp ? new Date(msg.timestamp) : new Date(),
            })) : [],
          }))
        }
        return parsed
      },
    }
  )
)
