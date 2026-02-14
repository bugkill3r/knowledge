'use client'

import { SessionProvider } from 'next-auth/react'
import { AppConfigProvider } from '@/lib/app-config'

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <SessionProvider>
      <AppConfigProvider>{children}</AppConfigProvider>
    </SessionProvider>
  )
}

