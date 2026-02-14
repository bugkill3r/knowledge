'use client'

import React, { useState } from 'react'
import { X } from 'lucide-react'

interface AddRepositoryModalProps {
  isOpen: boolean
  onClose: () => void
  onAdd: (repoData: { repo_path: string; repo_name: string }) => void
}

export default function AddRepositoryModal({ isOpen, onClose, onAdd }: AddRepositoryModalProps) {
  const [repoPath, setRepoPath] = useState('')
  const [repoName, setRepoName] = useState('')
  const [loading, setLoading] = useState(false)

  if (!isOpen) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!repoPath || !repoName) return

    setLoading(true)
    try {
      await onAdd({ repo_path: repoPath, repo_name: repoName })
      setRepoPath('')
      setRepoName('')
      onClose()
    } catch (error) {
      console.error('Failed to add repository:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <h3 className="text-lg font-semibold">Add Repository</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label htmlFor="repoName" className="block text-sm font-medium text-gray-700 mb-1">
              Repository Name
            </label>
            <input
              type="text"
              id="repoName"
              value={repoName}
              onChange={(e) => setRepoName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              placeholder="e.g., my-repo"
              required
            />
          </div>

          <div>
            <label htmlFor="repoPath" className="block text-sm font-medium text-gray-700 mb-1">
              Local Path
            </label>
            <input
              type="text"
              id="repoPath"
              value={repoPath}
              onChange={(e) => setRepoPath(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              placeholder="/path/to/repository"
              required
            />
            <p className="mt-1 text-xs text-gray-500">
              Full path to the Git repository on your local machine
            </p>
          </div>

          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !repoPath || !repoName}
              className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? 'Adding...' : 'Add Repository'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

