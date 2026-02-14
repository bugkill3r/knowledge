'use client'

import { useSession } from 'next-auth/react'
import { redirect } from 'next/navigation'
import { Copy, Check } from 'lucide-react'
import { useState } from 'react'

export default function TokenPage() {
  const { data: session, status } = useSession()
  const [copied, setCopied] = useState(false)

  if (status === 'loading') {
    return <div className="flex items-center justify-center min-h-screen">Loading...</div>
  }

  if (!session) {
    redirect('/')
  }

  const token = session.accessToken || 'No token found'
  const exportCommand = `export GOOGLE_ACCESS_TOKEN='${token}'`
  const scriptCommand = 'Run your image extraction script from the project root (path configurable).'

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="bg-card border border-border rounded-lg shadow-sm">
          <div className="p-6 border-b border-border">
            <h2 className="text-2xl font-bold">Google Access Token</h2>
          </div>
          <div className="p-6 space-y-6">
            <div>
              <h3 className="font-semibold mb-2">Access Token:</h3>
              <div className="bg-muted p-4 rounded-lg font-mono text-sm break-all flex items-start justify-between gap-4">
                <span className="flex-1">{token}</span>
                <button
                  onClick={() => copyToClipboard(token)}
                  className="flex-shrink-0 px-3 py-1 bg-primary text-primary-foreground rounded hover:bg-primary/90"
                >
                  {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <div>
              <h3 className="font-semibold mb-2">Step 1: Set Environment Variable</h3>
              <div className="bg-muted p-4 rounded-lg font-mono text-sm break-all flex items-start justify-between gap-4">
                <span className="flex-1">{exportCommand}</span>
                <button
                  onClick={() => copyToClipboard(exportCommand)}
                  className="flex-shrink-0 px-3 py-1 bg-primary text-primary-foreground rounded hover:bg-primary/90"
                >
                  {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <div>
              <h3 className="font-semibold mb-2">Step 2: Run Extraction Script</h3>
              <div className="bg-muted p-4 rounded-lg font-mono text-sm break-all flex items-start justify-between gap-4">
                <span className="flex-1">{scriptCommand}</span>
                <button
                  onClick={() => copyToClipboard(scriptCommand)}
                  className="flex-shrink-0 px-3 py-1 bg-primary text-primary-foreground rounded hover:bg-primary/90"
                >
                  {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <div className="bg-blue-50 dark:bg-blue-950 p-4 rounded-lg space-y-2">
              <h3 className="font-semibold">What This Will Do:</h3>
              <ul className="list-disc list-inside space-y-1 text-sm">
                <li>Download all 48 Google Docs as PDFs</li>
                <li>Extract real images using pdf2md</li>
                <li>Save images to Obsidian vault</li>
                <li>Update markdown files with embedded images</li>
                <li>Show progress for each document</li>
              </ul>
            </div>

            <div className="bg-yellow-50 dark:bg-yellow-950 p-4 rounded-lg">
              <p className="text-sm">
                <strong>Note:</strong> This token is valid for about 1 hour. If it expires, just refresh this page to get a new one.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

