import React from 'react'
import { Plus, Trash2, Calendar, X } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { useChatStore } from '@/store/chatStore'
import { useAppStore } from '@/store/appStore'
import { cn, formatDate } from '@/lib/utils'

interface SidebarProps {
  className?: string
}

const Sidebar: React.FC<SidebarProps> = ({ className }) => {
  const {
    conversations,
    activeConversationId,
    setActiveConversation,
    loadConversation,
    deleteConversation,
    clearMessages,
  } = useChatStore()

  const { sidebarOpen, setSidebarOpen } = useAppStore()

  const handleNewChat = () => {
    clearMessages()
    setActiveConversation(null)
    // Close sidebar on mobile after creating new chat
    if (window.innerWidth < 640) {
      setSidebarOpen(false)
    }
  }

  const handleSelectConversation = (id: string) => {
    setActiveConversation(id)
    loadConversation(id)
    // Close sidebar on mobile after selecting conversation
    if (window.innerWidth < 640) {
      setSidebarOpen(false)
    }
  }

  const handleDeleteConversation = (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    deleteConversation(id)
  }

  const handleCloseSidebar = () => {
    setSidebarOpen(false)
  }

  if (!sidebarOpen) return null

  return (
    <>
      {/* Mobile overlay */}
      <div 
        className="fixed inset-0 z-40 bg-black bg-opacity-50 sm:hidden"
        onClick={handleCloseSidebar}
      />
      
      {/* Sidebar */}
      <aside className={cn(
        'fixed left-0 top-0 z-50 flex h-full w-80 flex-col bg-white dark:bg-gray-800 sm:relative sm:z-auto',
        'transform transition-transform duration-300 ease-in-out',
        sidebarOpen ? 'translate-x-0' : '-translate-x-full sm:translate-x-0',
        className
      )}>
        {/* Mobile close button */}
        <div className="flex items-center justify-between border-b border-coffee-200 p-4 dark:border-coffee-700 sm:hidden">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">選單</h2>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleCloseSidebar}
            className="h-8 w-8 p-0"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="border-b border-coffee-200 p-4 dark:border-coffee-700">
          <Button
            onClick={handleNewChat}
            className="w-full justify-start"
            size="sm"
          >
            <Plus className="mr-2 h-4 w-4" />
            新對話
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          <div className="space-y-2">
            <h3 className="mb-3 text-sm font-medium text-gray-700 dark:text-gray-300">
              對話記錄
            </h3>
            
            {conversations.length === 0 ? (
              <div className="text-center text-sm text-gray-500 dark:text-gray-400">
                還沒有對話記錄
              </div>
            ) : (
              conversations.map((conversation) => (
                <Card
                  key={conversation.id}
                  className={cn(
                    'cursor-pointer transition-all hover:shadow-md',
                    activeConversationId === conversation.id
                      ? 'border-coffee-500 bg-coffee-50 dark:bg-coffee-900'
                      : 'hover:border-coffee-300'
                  )}
                  onClick={() => handleSelectConversation(conversation.id)}
                >
                  <div className="p-3">
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0 pr-2">
                        <h4 className="text-sm font-medium text-gray-900 dark:text-white break-words overflow-wrap-anywhere">
                          {conversation.title}
                        </h4>
                        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400 truncate">
                          {formatDate(conversation.updatedAt)}
                        </p>
                        <p className="mt-1 text-xs text-gray-400 dark:text-gray-500 truncate">
                          {conversation.messages.length} 條訊息
                        </p>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => handleDeleteConversation(conversation.id, e)}
                        className="ml-2 h-6 w-6 p-0 text-gray-400 hover:text-red-500"
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>
                </Card>
              ))
            )}
          </div>
        </div>

        <div className="border-t border-coffee-200 p-4 dark:border-coffee-700">
          <div className="flex items-center space-x-2 text-xs text-gray-500 dark:text-gray-400">
            <Calendar className="h-3 w-3" />
            <span>最後更新: {new Date().toLocaleDateString('zh-TW')}</span>
          </div>
        </div>
      </aside>
    </>
  )
}

export { Sidebar }
