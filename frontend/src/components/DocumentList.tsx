'use client'

import { useState, useEffect } from 'react'
import { FileText, ExternalLink, Calendar, Tag } from 'lucide-react'
import { useAppConfig } from '@/lib/app-config'

interface Document {
  id: string
  title: string
  source_url: string | null
  source_type: string
  doc_type: string
  status: string
  author: string | null
  created_at: string
  vault_path?: string
}

export default function DocumentList() {
  const { obsidianEnabled } = useAppConfig()
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchDocuments()
  }, [])

  const fetchDocuments = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/documents/`)
      if (!response.ok) {
        throw new Error('Failed to fetch documents')
      }
      const data = await response.json()
      setDocuments(data)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      year: 'numeric' 
    })
  }

  const getDocTypeColor = (type: string) => {
    switch (type?.toLowerCase()) {
      case 'prd': return 'bg-purple-500/10 text-purple-400 border-purple-500/20'
      case 'tech-spec': return 'bg-blue-500/10 text-blue-400 border-blue-500/20'
      case 'kt': return 'bg-green-500/10 text-green-400 border-green-500/20'
      case 'meeting': return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'
      case 'runbook': return 'bg-red-500/10 text-red-400 border-red-500/20'
      default: return 'bg-gray-500/10 text-gray-400 border-gray-500/20'
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-primary-blue border-t-transparent"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
        <p className="text-sm text-red-400">Error: {error}</p>
      </div>
    )
  }

  if (documents.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="text-6xl mb-4">📄</div>
        <h3 className="text-lg font-medium text-foreground mb-2">No documents yet</h3>
        <p className="text-sm text-muted-foreground max-w-md">
          Get started by importing a Google Doc or using bulk import to add multiple documents.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-foreground">Documents</h2>
          <p className="text-sm text-muted-foreground mt-1">
            {documents.length} document{documents.length !== 1 ? 's' : ''} in your knowledge base
          </p>
        </div>
      </div>

      {/* Document List */}
      <div className="space-y-3">
        {documents.map((doc) => (
          <div
            key={doc.id}
            className="group p-4 bg-card border border-border rounded-lg hover:border-primary-blue/50 
                     transition-all cursor-pointer"
            onClick={() => {
              if (doc.source_url) {
                window.open(doc.source_url, '_blank')
              }
            }}
          >
            <div className="flex items-start gap-4">
              {/* Icon */}
              <div className="mt-0.5 text-muted-foreground">
                <FileText className="w-5 h-5" />
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                {/* Title */}
                <div className="flex items-center gap-2 mb-2">
                  <h3 className="font-medium text-foreground truncate">
                    {doc.title}
                  </h3>
                  {doc.source_url && (
                    <ExternalLink className="w-3 h-3 text-muted-foreground flex-shrink-0" />
                  )}
                </div>

                {/* Metadata */}
                <div className="flex items-center gap-3 flex-wrap text-xs">
                  {doc.doc_type && (
                    <span className={`px-2 py-0.5 border rounded-md ${getDocTypeColor(doc.doc_type)}`}>
                      {doc.doc_type}
                    </span>
                  )}
                  
                  {doc.author && (
                    <span className="text-muted-foreground flex items-center gap-1">
                      <Tag className="w-3 h-3" />
                      {doc.author}
                    </span>
                  )}
                  
                  {doc.created_at && (
                    <span className="text-muted-foreground flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      {formatDate(doc.created_at)}
                    </span>
                  )}
                </div>

                {/* Vault Path (only when Obsidian is enabled) */}
                {obsidianEnabled && doc.vault_path && (
                  <div className="mt-2 text-xs text-muted-foreground/70 font-mono truncate">
                    {doc.vault_path}
                  </div>
                )}
              </div>

              {/* Status Badge */}
              <div className="flex-shrink-0">
                <span className={`px-2 py-1 text-xs rounded-md ${
                  doc.status === 'completed' 
                    ? 'bg-green-500/10 text-green-400 border border-green-500/20' 
                    : doc.status === 'processing'
                    ? 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20'
                    : 'bg-gray-500/10 text-gray-400 border border-gray-500/20'
                }`}>
                  {doc.status}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
