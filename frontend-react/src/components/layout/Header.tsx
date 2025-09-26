import React from 'react'
import { Menu, Sun, Moon, Settings } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { useAppStore } from '@/store/appStore'

interface HeaderProps {
  onMenuClick?: () => void
}

const Header: React.FC<HeaderProps> = ({ onMenuClick }) => {
  const { theme, toggleTheme } = useAppStore()

  return (
    <header className="flex h-16 items-center justify-between border-b border-coffee-200 bg-gradient-to-r from-coffee-500 to-coffee-600 px-4 shadow-sm dark:border-coffee-700">
      <div className="flex items-center space-x-3">
        <Button
          variant="ghost"
          size="sm"
          onClick={onMenuClick}
          className="text-white hover:bg-coffee-600 dark:text-white dark:hover:bg-coffee-700"
        >
          <Menu className="h-5 w-5" />
        </Button>
        
        <div className="flex items-center space-x-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-white/20 text-white">
            <span className="text-lg font-bold">源</span>
          </div>
          <div>
            <h1 className="text-lg font-bold text-white">源來適你 - Apache Local Community Taipei</h1>
            <p className="text-sm text-coffee-100">小饅頭 AI 助手 - 基於 GitHub 與 Slack 資料的社群服務</p>
          </div>
        </div>
      </div>

      <div className="flex items-center space-x-2">
        <Button
          variant="ghost"
          size="sm"
          onClick={toggleTheme}
          className="text-white hover:bg-coffee-600 dark:text-white dark:hover:bg-coffee-700"
        >
          {theme === 'light' ? (
            <Moon className="h-4 w-4" />
          ) : (
            <Sun className="h-4 w-4" />
          )}
        </Button>
        
        <Button
          variant="ghost"
          size="sm"
          className="text-white hover:bg-coffee-600 dark:text-white dark:hover:bg-coffee-700"
        >
          <Settings className="h-4 w-4" />
        </Button>
      </div>
    </header>
  )
}

export { Header }
