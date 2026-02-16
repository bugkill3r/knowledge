'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useSession, signIn } from 'next-auth/react'
import { Button } from '@/components/ui/button'
import { ArrowRight, BookOpen, Check } from 'lucide-react'
import {
  ONBOARDING_KEY,
  NOTE_TAKING_APP_KEY,
  NOTE_TAKING_APP_OPTIONS,
} from '@/lib/onboarding'
import { cn } from '@/lib/utils'

export default function OnboardingPage() {
  const router = useRouter()
  const { data: session, status } = useSession()
  const [step, setStep] = useState(1)
  const [obsidianSelected, setObsidianSelected] = useState(true)

  const totalSteps = 3
  const useObsidian = obsidianSelected

  const markOnboardingDone = () => {
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(ONBOARDING_KEY, 'true')
      if (obsidianSelected) {
        window.localStorage.setItem(NOTE_TAKING_APP_KEY, 'obsidian')
      } else {
        window.localStorage.removeItem(NOTE_TAKING_APP_KEY)
      }
    }
  }

  const handleFinish = () => {
    markOnboardingDone()
    if (session) {
      router.push('/dashboard')
    } else {
      signIn('google', { callbackUrl: '/dashboard' })
    }
  }

  const appName = process.env.NEXT_PUBLIC_APP_NAME || 'Knowledge System'

  return (
    <main className="min-h-screen bg-background flex flex-col items-center justify-center px-4 py-8">
      <div className="max-w-lg w-full space-y-8">
        {/* Progress */}
        <div className="flex gap-2 justify-center">
          {Array.from({ length: totalSteps }).map((_, i) => (
            <div
              key={i}
              className={cn(
                'h-1.5 flex-1 max-w-24 rounded-full transition-colors',
                i + 1 <= step ? 'bg-foreground/80' : 'bg-muted'
              )}
            />
          ))}
        </div>

        {/* Step 1: Welcome */}
        {step === 1 && (
          <div className="text-center space-y-6">
            <div className="flex justify-center">
              <BookOpen className="h-12 w-12 text-muted-foreground" />
            </div>
            <h1 className="text-2xl font-semibold text-foreground">
              Welcome to {appName}
            </h1>
            <p className="text-muted-foreground text-sm">
              Import docs, search with natural language, and chat over your knowledge base.
              You can optionally sync with a note-taking app—or use this app only.
            </p>
            <Button onClick={() => setStep(2)} className="gap-2">
              Get started
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        )}

        {/* Step 2: Where do you keep notes? */}
        {step === 2 && (
          <div className="space-y-6">
            <h2 className="text-xl font-semibold text-foreground text-center">
              Where do you keep notes?
            </h2>
            <p className="text-muted-foreground text-sm text-center">
              We can sync imported docs to your vault. Uncheck Obsidian if you don’t use it.
            </p>
            <div className="space-y-2">
              {NOTE_TAKING_APP_OPTIONS.map((option) => {
                const isSelected = option.id === 'obsidian' && obsidianSelected
                const disabled = !option.supported
                return (
                  <button
                    key={option.id}
                    type="button"
                    disabled={disabled}
                    onClick={() =>
                      option.supported && setObsidianSelected((v) => !v)
                    }
                    className={cn(
                      'w-full text-left rounded-lg border p-4 transition-colors',
                      'flex items-center gap-3',
                      disabled && 'opacity-50 cursor-not-allowed',
                      !disabled && 'cursor-pointer hover:bg-muted/50',
                      isSelected && 'border-foreground bg-muted/50',
                      !isSelected && !disabled && 'border-border'
                    )}
                  >
                    {option.logoUrl && (
                      <span className="flex-shrink-0 w-8 h-8 rounded overflow-hidden bg-muted flex items-center justify-center">
                        <img
                          src={option.logoUrl}
                          alt=""
                          width={24}
                          height={24}
                          className="object-contain"
                        />
                      </span>
                    )}
                    <span className="font-medium text-foreground flex-1">
                      {option.label}
                    </span>
                    {option.comingSoon && (
                      <span className="text-xs text-muted-foreground">
                        Coming soon
                      </span>
                    )}
                    {isSelected && (
                      <span
                        className="h-2 w-2 rounded-full bg-foreground flex-shrink-0"
                        aria-hidden
                      />
                    )}
                  </button>
                )
              })}
            </div>

            {useObsidian && (
              <p className="text-muted-foreground text-sm text-center">
                Set your vault path in Settings after you sign in.
              </p>
            )}

            <Button onClick={() => setStep(3)} className="w-full gap-2">
              Continue
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        )}

        {/* Step 3: Done */}
        {step === 3 && (
          <div className="text-center space-y-6">
            <div className="flex justify-center">
              <Check className="h-12 w-12 text-green-600" />
            </div>
            <h2 className="text-xl font-semibold text-foreground">
              You&apos;re all set
            </h2>
            <p className="text-muted-foreground text-sm">
              {useObsidian
                ? 'Set your Obsidian vault path in Settings after you sign in.'
                : 'You can enable vault sync later in Settings if you want.'}
            </p>
            {status === 'loading' ? (
              <p className="text-sm text-muted-foreground">Loading...</p>
            ) : session ? (
              <Button onClick={handleFinish} className="gap-2">
                Go to app
                <ArrowRight className="h-4 w-4" />
              </Button>
            ) : (
              <Button onClick={handleFinish} className="gap-2">
                Sign in with Google
                <ArrowRight className="h-4 w-4" />
              </Button>
            )}
          </div>
        )}
      </div>
    </main>
  )
}
