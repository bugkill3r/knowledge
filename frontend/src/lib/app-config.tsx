'use client'

import React, { createContext, useContext, useEffect, useState } from 'react'

type AppConfig = {
  projectName: string
  obsidianEnabled: boolean
}

const defaultConfig: AppConfig = {
  projectName: process.env.NEXT_PUBLIC_APP_NAME || 'Knowledge System',
  obsidianEnabled: false,
}

const AppConfigContext = createContext<AppConfig>(defaultConfig)

export function AppConfigProvider({ children }: { children: React.ReactNode }) {
  const [config, setConfig] = useState<AppConfig>(defaultConfig)

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    fetch(`${apiUrl}/api/v1/config`)
      .then((res) => res.ok ? res.json() : null)
      .then((data) => {
        if (data) {
          setConfig({
            projectName: data.project_name ?? defaultConfig.projectName,
            obsidianEnabled: Boolean(data.obsidian_enabled),
          })
        }
      })
      .catch(() => {})
  }, [])

  return (
    <AppConfigContext.Provider value={config}>
      {children}
    </AppConfigContext.Provider>
  )
}

export function useAppConfig() {
  return useContext(AppConfigContext)
}
