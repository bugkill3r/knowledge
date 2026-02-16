'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function Settings() {
  const [vaultPath, setVaultPath] = useState('')
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [obsidianEnabled, setObsidianEnabled] = useState(false)

  useEffect(() => {
    fetch(`${API_URL}/api/v1/config`)
      .then((r) => r.json())
      .then((d) => {
        setObsidianEnabled(d.obsidian_enabled ?? false)
        if (d.obsidian_vault_path) {
          setVaultPath(d.obsidian_vault_path)
        }
      })
      .catch(() => {})
  }, [])

  const handleSave = async () => {
    setError(null)
    const path = vaultPath.trim()
    if (!path) {
      setError('Enter an absolute path to your vault folder.')
      return
    }
    if (!path.startsWith('/')) {
      setError('Path must be absolute (e.g. /Users/you/Documents/MyVault).')
      return
    }
    try {
      const res = await fetch(`${API_URL}/api/v1/config/vault-path`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        setError(data.detail || 'Failed to save path.')
        return
      }
      setSaved(true)
    } catch {
      setError('Could not reach the server. Is the backend running?')
    }
  }

  return (
    <div className="space-y-8 max-w-xl">
      <h2 className="text-lg font-semibold text-foreground">Settings</h2>

      <div className="rounded-lg border border-border bg-muted/20 p-6 space-y-4">
        <div>
          <h3 className="font-medium text-foreground mb-1">Obsidian vault path</h3>
          <p className="text-sm text-muted-foreground mb-3">
            Absolute path to your Obsidian vault folder. Imported docs will be saved here.
          </p>
          <div className="flex gap-2">
            <input
              type="text"
              value={vaultPath}
              onChange={(e) => {
                setVaultPath(e.target.value)
                setSaved(false)
              }}
              placeholder="/Users/you/Documents/MyVault"
              className="flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm"
            />
            <Button onClick={handleSave} variant={saved ? 'secondary' : 'default'}>
              {saved ? 'Saved' : 'Save'}
            </Button>
          </div>
          {error && <p className="text-destructive text-sm mt-2">{error}</p>}
          {obsidianEnabled && vaultPath && (
            <p className="text-muted-foreground text-xs mt-2">Vault sync is enabled.</p>
          )}
        </div>
      </div>
    </div>
  )
}
