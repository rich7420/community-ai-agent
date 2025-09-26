import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { AppState, UserSettings } from '@/types'

interface AppStore extends AppState {
  // Actions
  setTheme: (theme: 'light' | 'dark') => void
  toggleTheme: () => void
  setSidebarOpen: (open: boolean) => void
  toggleSidebar: () => void
  updateSettings: (settings: Partial<UserSettings>) => void
}

const defaultSettings: UserSettings = {
  autoSave: true,
  showSources: true,
  enableNotifications: true,
  language: 'zh-TW',
}

export const useAppStore = create<AppStore>()(
  persist(
    (set, get) => ({
      // Initial state
      theme: 'light',
      sidebarOpen: true,
      settings: defaultSettings,

      // Actions
      setTheme: (theme) => {
        set({ theme })
        // Update document class for theme
        document.documentElement.classList.remove('light', 'dark')
        document.documentElement.classList.add(theme)
      },

      toggleTheme: () => {
        const { theme } = get()
        const newTheme = theme === 'light' ? 'dark' : 'light'
        get().setTheme(newTheme)
      },

      setSidebarOpen: (open) => {
        set({ sidebarOpen: open })
      },

      toggleSidebar: () => {
        const { sidebarOpen } = get()
        set({ sidebarOpen: !sidebarOpen })
      },

      updateSettings: (newSettings) => {
        set((state) => ({
          settings: { ...state.settings, ...newSettings },
        }))
      },
    }),
    {
      name: 'app-storage',
      partialize: (state) => ({
        theme: state.theme,
        settings: state.settings,
      }),
    }
  )
)
