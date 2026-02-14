'use client'

import { useState } from 'react'
import { useSession } from 'next-auth/react'
import { Upload, Link as LinkIcon, CheckCircle2, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface ImportFormProps {
  accessToken: string
}

export default function ImportForm({ accessToken }: ImportFormProps) {
  const { data: session } = useSession()
  const [url, setUrl] = useState('')
  const [recursive, setRecursive] = useState(true)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/imports/google-docs`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          url,
          recursive,
          user_email: session?.user?.email,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Import failed')
      }

      const data = await response.json()
      setResult(data)
      setUrl('')
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-foreground mb-2">
          Import Google Docs
        </h2>
        <p className="text-muted-foreground">
          Paste a Google Docs URL to import the document and all linked documents into your knowledge base.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="space-y-2">
          <label htmlFor="url" className="text-sm font-medium text-foreground">
            Google Docs URL
          </label>
          <div className="relative">
            <LinkIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
            <input
              type="url"
              id="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://docs.google.com/document/d/..."
              required
              className="w-full pl-11 pr-4 py-3 bg-input border border-border rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent transition-all"
            />
          </div>
        </div>

        <div className="flex items-center space-x-3 p-4 bg-muted/30 rounded-lg border border-border/30">
          <input
            type="checkbox"
            id="recursive"
            checked={recursive}
            onChange={(e) => setRecursive(e.target.checked)}
            className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-2 focus:ring-ring"
          />
          <label htmlFor="recursive" className="text-sm text-foreground cursor-pointer">
            Import linked documents recursively
          </label>
        </div>

        <Button
          type="submit"
          disabled={loading || !url}
          className="w-full h-12 text-base font-medium gap-2"
          size="lg"
        >
          {loading ? (
            <>
              <div className="h-4 w-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
              Importing...
            </>
          ) : (
            <>
              <Upload className="h-5 w-5" />
              Import Document
            </>
          )}
        </Button>
      </form>

      {result && (
        <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
          <div className="flex items-start gap-3">
            <CheckCircle2 className="h-5 w-5 text-emerald-400 flex-shrink-0 mt-0.5" />
            <div className="space-y-2 flex-1">
              <h3 className="text-sm font-medium text-emerald-400">
                Import Started Successfully
              </h3>
              <div className="text-sm text-emerald-400/80 space-y-1">
                <p>Job ID: <code className="px-1.5 py-0.5 bg-emerald-500/10 rounded font-mono text-xs">{result.job_id}</code></p>
                <p>Status: {result.status}</p>
                <p>{result.message}</p>
              </div>
              <p className="text-xs text-emerald-400/60 mt-2">
                Check the "History" tab to monitor progress.
              </p>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0 mt-0.5" />
            <div className="space-y-2 flex-1">
              <h3 className="text-sm font-medium text-red-400">
                Import Failed
              </h3>
              <p className="text-sm text-red-400/80">{error}</p>
            </div>
          </div>
        </div>
      )}

      <div className="p-6 bg-blue-500/5 border border-blue-500/10 rounded-lg">
        <h3 className="text-sm font-medium text-blue-400 mb-3 flex items-center gap-2">
          <span className="text-lg">ℹ️</span>
          How it works
        </h3>
        <ul className="text-sm text-blue-400/70 space-y-2">
          <li className="flex items-start gap-2">
            <span className="text-blue-400 mt-0.5">•</span>
            <span>Paste the URL of any Google Doc you have access to</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-blue-400 mt-0.5">•</span>
            <span>The system will read the document content and metadata</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-blue-400 mt-0.5">•</span>
            <span>If recursive import is enabled, all linked Google Docs will also be imported</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-blue-400 mt-0.5">•</span>
            <span>Documents are converted to Markdown and saved to your Obsidian vault</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-blue-400 mt-0.5">•</span>
            <span>Metadata is automatically generated for better organization</span>
          </li>
        </ul>
      </div>
    </div>
  )
}
