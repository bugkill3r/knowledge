'use client'

import { useSession, signIn } from 'next-auth/react'
import { redirect } from 'next/navigation'
import { useEffect, useState } from 'react'
import { ArrowRight } from 'lucide-react'
import { Button } from '@/components/ui/button'

const ONBOARDING_KEY = 'knowledge_onboarding_done'
const appName = process.env.NEXT_PUBLIC_APP_NAME || 'Knowledge System'

export default function Home() {
  const { data: session, status } = useSession()
  const [onboardingDone, setOnboardingDone] = useState<boolean | null>(null)

  useEffect(() => {
    try {
      setOnboardingDone(typeof window !== 'undefined' && window.localStorage.getItem(ONBOARDING_KEY) === 'true')
    } catch {
      setOnboardingDone(false)
    }
  }, [])

  // Wait for localStorage read (client-only)
  if (onboardingDone === null) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="text-sm text-muted-foreground">Loading...</div>
      </div>
    )
  }

  // Send to onboarding first; don't block on session
  if (!onboardingDone) {
    redirect('/onboarding')
  }

  // Onboarding done: now need session to show sign-in vs dashboard
  if (status === 'loading') {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="text-sm text-muted-foreground">Loading...</div>
      </div>
    )
  }

  if (session) {
    redirect('/dashboard')
  }

  return (
    <main className="min-h-screen bg-background flex flex-col items-center justify-center px-4">
      <div className="max-w-md text-center">
        <h1 className="text-2xl font-semibold text-foreground mb-2">
          {appName}
        </h1>
        <p className="text-muted-foreground text-sm mb-8">
          Import docs, search and chat over your knowledge base.
        </p>
        <Button
          onClick={() => signIn('google')}
          size="lg"
          className="gap-2"
        >
          Sign in with Google
          <ArrowRight className="h-4 w-4" />
        </Button>
      </div>
    </main>
  )
}
