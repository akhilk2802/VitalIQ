import { createContext, useContext, useState, useEffect, ReactNode } from 'react'

const STORAGE_KEY = 'vitaliq_settings'

interface Settings {
  mockDataEnabled: boolean
}

interface SettingsContextType {
  settings: Settings
  updateSettings: (updates: Partial<Settings>) => void
  toggleMockData: () => void
}

const defaultSettings: Settings = {
  mockDataEnabled: false,
}

const SettingsContext = createContext<SettingsContextType | undefined>(undefined)

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<Settings>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored) {
        return { ...defaultSettings, ...JSON.parse(stored) }
      }
    } catch (e) {
      console.error('Failed to load settings from localStorage:', e)
    }
    return defaultSettings
  })

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(settings))
    } catch (e) {
      console.error('Failed to save settings to localStorage:', e)
    }
  }, [settings])

  const updateSettings = (updates: Partial<Settings>) => {
    setSettings((prev) => ({ ...prev, ...updates }))
  }

  const toggleMockData = () => {
    setSettings((prev) => ({ ...prev, mockDataEnabled: !prev.mockDataEnabled }))
  }

  return (
    <SettingsContext.Provider value={{ settings, updateSettings, toggleMockData }}>
      {children}
    </SettingsContext.Provider>
  )
}

export function useSettings() {
  const context = useContext(SettingsContext)
  if (context === undefined) {
    throw new Error('useSettings must be used within a SettingsProvider')
  }
  return context
}
