'use client'

import { useState, useEffect } from 'react'
import { CheckCircle2, AlertCircle, ExternalLink, Terminal, Loader2 } from 'lucide-react'

interface CursorStatus {
  installed: boolean
  authenticated: boolean
  version: string | null
  user_email: string | null
  message: string
}

export default function CursorSetup() {
  const [status, setStatus] = useState<CursorStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    checkStatus()
  }, [])

  const checkStatus = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/cursor/status`)
      if (response.ok) {
        const data = await response.json()
        setStatus(data)
      } else {
        setError('Failed to check Cursor status')
      }
    } catch (err) {
      setError('Failed to connect to backend')
    } finally {
      setLoading(false)
    }
  }

  const handleLogin = async () => {
    setActionLoading(true)
    setError(null)
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/cursor/login`, {
        method: 'POST'
      })
      if (response.ok) {
        // Wait a bit then recheck status
        setTimeout(() => {
          checkStatus()
          setActionLoading(false)
        }, 3000)
      } else {
        const data = await response.json()
        setError(data.detail || 'Login failed')
        setActionLoading(false)
      }
    } catch (err) {
      setError('Failed to start login process')
      setActionLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="bg-card/50 backdrop-blur-sm border border-border/50 rounded-lg p-6">
        <div className="flex items-center gap-3">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          <p className="text-sm text-muted-foreground">Checking Cursor Agent status...</p>
        </div>
      </div>
    )
  }

  if (!status) {
    return null
  }

  return (
    <div className="bg-card/50 backdrop-blur-sm border border-border/50 rounded-lg p-6 space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-lg font-medium text-foreground flex items-center gap-2">
            <Terminal className="h-5 w-5" />
            Cursor Agent Setup
          </h3>
          <p className="text-sm text-muted-foreground mt-1">
            Required for AI-powered document reviews
          </p>
        </div>
        <button
          onClick={checkStatus}
          disabled={loading}
          className="text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          Refresh
        </button>
      </div>

      {/* Status */}
      <div className="space-y-3">
        {/* Installation Status */}
        <div className="flex items-start gap-3 p-3 bg-muted/30 rounded-lg">
          {status.installed ? (
            <CheckCircle2 className="h-5 w-5 text-emerald-400 flex-shrink-0 mt-0.5" />
          ) : (
            <AlertCircle className="h-5 w-5 text-orange-400 flex-shrink-0 mt-0.5" />
          )}
          <div className="flex-1">
            <p className="text-sm font-medium text-foreground">
              {status.installed ? 'Cursor Agent Installed' : 'Cursor Agent Not Installed'}
            </p>
            {status.version && (
              <p className="text-xs text-muted-foreground mt-1">Version: {status.version}</p>
            )}
          </div>
        </div>

        {/* Authentication Status */}
        {status.installed && (
          <div className="flex items-start gap-3 p-3 bg-muted/30 rounded-lg">
            {status.authenticated ? (
              <CheckCircle2 className="h-5 w-5 text-emerald-400 flex-shrink-0 mt-0.5" />
            ) : (
              <AlertCircle className="h-5 w-5 text-orange-400 flex-shrink-0 mt-0.5" />
            )}
            <div className="flex-1">
              <p className="text-sm font-medium text-foreground">
                {status.authenticated ? 'Authenticated' : 'Not Authenticated'}
              </p>
              {status.user_email && (
                <p className="text-xs text-muted-foreground mt-1">{status.user_email}</p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Actions */}
      {!status.installed && (
        <div className="p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg">
          <p className="text-sm text-blue-400 mb-3">
            Install Cursor Agent to enable AI reviews
          </p>
          <div className="bg-black/30 rounded p-3 font-mono text-xs text-foreground mb-3">
            curl https://cursor.com/install -fsS | bash
          </div>
          <p className="text-xs text-muted-foreground">
            Run this command in your terminal, then refresh this page
          </p>
        </div>
      )}

      {status.installed && !status.authenticated && (
        <div className="space-y-3">
          <button
            onClick={handleLogin}
            disabled={actionLoading}
            className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {actionLoading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Opening browser...
              </>
            ) : (
              <>
                <ExternalLink className="h-4 w-4" />
                Authenticate with Cursor
              </>
            )}
          </button>
          <p className="text-xs text-muted-foreground text-center">
            This will open your browser to complete authentication
          </p>
        </div>
      )}

      {status.authenticated && (
        <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
            <p className="text-sm text-emerald-400">
              Ready to use! You can now create AI reviews.
            </p>
          </div>
        </div>
      )}

      {error && (
        <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      {/* Help */}
      <div className="pt-3 border-t border-border/30">
        <p className="text-xs text-muted-foreground">
          Need help? Check the{' '}
          <a
            href="https://cursor.com/docs/cli/headless"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-400 hover:text-blue-300 underline"
          >
            Cursor CLI documentation
          </a>
        </p>
      </div>
    </div>
  )
}

