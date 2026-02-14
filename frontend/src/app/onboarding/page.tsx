'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { ArrowRight, BookOpen, Check } from 'lucide-react'

const ONBOARDING_KEY = 'knowledge_onboarding_done'

export default function OnboardingPage() {
  const router = useRouter()
  const [step, setStep] = useState(1)
  const [useObsidian, setUseObsidian] = useState<boolean | null>(null)

  const totalSteps = 3

  const finishOnboarding = () => {
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(ONBOARDING_KEY, 'true')
    }
    router.push('/')
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
              className={`h-1.5 flex-1 max-w-24 rounded-full transition-colors ${
                i + 1 <= step ? 'bg-foreground/80' : 'bg-muted'
              }`}
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
              You can optionally sync with Obsidian—or use the app without it.
            </p>
            <Button onClick={() => setStep(2)} className="gap-2">
              Get started
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        )}

        {/* Step 2: Obsidian? */}
        {step === 2 && (
          <div className="space-y-6">
            <h2 className="text-xl font-semibold text-foreground text-center">
              Do you use Obsidian?
            </h2>
            <p className="text-muted-foreground text-sm text-center">
              If yes, we can save imported docs and reviews into your vault. If not, you can still use search, chat, and reviews—everything stays in this app.
            </p>
            <div className="grid grid-cols-2 gap-3">
              <Button
                variant={useObsidian === true ? 'default' : 'outline'}
                onClick={() => setUseObsidian(true)}
                className="h-auto py-4"
              >
                Yes, I use Obsidian
              </Button>
              <Button
                variant={useObsidian === false ? 'default' : 'outline'}
                onClick={() => setUseObsidian(false)}
                className="h-auto py-4"
              >
                No, skip Obsidian
              </Button>
            </div>

            {useObsidian === true && (
              <div className="rounded-lg border border-border bg-muted/30 p-4 text-sm text-muted-foreground space-y-2">
                <p className="font-medium text-foreground">Set up vault sync</p>
                <p>In your backend <code className="bg-muted px-1 rounded">.env</code>, set:</p>
                <pre className="bg-background p-3 rounded overflow-x-auto text-xs">
                  OBSIDIAN_VAULT_PATH=/absolute/path/to/your/vault
                </pre>
                <p>Then restart the backend. You can change this later.</p>
              </div>
            )}

            {useObsidian !== null && (
              <Button onClick={() => setStep(3)} className="w-full gap-2">
                Continue
                <ArrowRight className="h-4 w-4" />
              </Button>
            )}
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
                ? 'When your vault path is set and the backend is restarted, imported docs will sync to Obsidian.'
                : 'Use search, chat, and doc review without Obsidian. You can enable vault sync later in backend .env if you want.'}
            </p>
            <Button onClick={finishOnboarding} className="gap-2">
              Go to app
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        )}
      </div>
    </main>
  )
}
