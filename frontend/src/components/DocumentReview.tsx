'use client'

import { useState, useEffect } from 'react'
import { Sparkles, FileText, Clock, CheckCircle2, AlertCircle, ExternalLink, Copy } from 'lucide-react'
import dynamic from 'next/dynamic'
import { useAppConfig } from '@/lib/app-config'

const StreamingReview = dynamic(() => import('./StreamingReview'), { ssr: false })

interface ReviewJob {
  review_id: string
  status: string
  review_type: string
  original_document_id: string
  original_document_title: string | null
  reviewed_document_id: string | null
  reviewed_document_title: string | null
  reviewed_document_path: string | null
  streaming_content?: string | null
  total_comments: number
  comment_categories: Record<string, number> | null
  ai_model: string | null
  error_message: string | null
  started_at: string
  completed_at: string | null
  created_by: string | null
}

interface Document {
  id: string
  title: string
  source_url: string | null
  source_type: string
  doc_type: string
  status: string
  created_at: string
}

export default function DocumentReview() {
  const { obsidianEnabled } = useAppConfig()
  const [documentId, setDocumentId] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [documents, setDocuments] = useState<Document[]>([])
  const [filteredDocuments, setFilteredDocuments] = useState<Document[]>([])
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null)
  const [showDocumentList, setShowDocumentList] = useState(false)
  const [reviewType, setReviewType] = useState('comprehensive')
  const [selectedModel, setSelectedModel] = useState('claude-code')
  const [selectedPersonas, setSelectedPersonas] = useState<string[]>(['engineering-leader', 'principal-engineer'])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showStreamingReview, setShowStreamingReview] = useState(false)
  const [originalDocContent, setOriginalDocContent] = useState('')
  const [currentReview, setCurrentReview] = useState<ReviewJob | null>(null)
  const [reviewHistory, setReviewHistory] = useState<ReviewJob[]>([])
  const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null)
  const [showSetup, setShowSetup] = useState(false)
  const [cursorStatus, setCursorStatus] = useState<'checking' | 'authenticated' | 'not_authenticated' | 'not_installed'>('checking')

  // Fetch documents and review history on mount
  useEffect(() => {
    fetchDocuments()
    fetchReviewHistory()
    
    // Request notification permission if not already granted
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission()
    }
  }, [])

  // Filter documents based on search query
  useEffect(() => {
    if (!searchQuery.trim()) {
      setFilteredDocuments(documents)
      if (!selectedDocument) {
        setDocumentId('')
      }
      return
    }

    const query = searchQuery.toLowerCase()
    const filtered = documents.filter(doc => 
      doc.title.toLowerCase().includes(query) ||
      (doc.source_url && doc.source_url.toLowerCase().includes(query))
    )
    
    setFilteredDocuments(filtered)
  }, [searchQuery, documents])

  const fetchDocuments = async () => {
    try {
      const url = `${process.env.NEXT_PUBLIC_API_URL}/api/v1/documents/`
      const response = await fetch(url)
      
      if (response.ok) {
        const data = await response.json()
        setDocuments(data)
        setFilteredDocuments(data)
      }
    } catch (err) {
      // Silently fail - documents will be empty
    }
  }

  // Poll for review status if there's an active review
  // Uses progressive backoff: 2s → 5s → 10s → 15s
  useEffect(() => {
    if (currentReview && currentReview.status === 'processing') {
      let pollCount = 0
      
      const poll = () => {
        checkReviewStatus(currentReview.review_id)
        pollCount++
        
        // Progressive backoff
        let nextDelay = 2000 // Start with 2 seconds
        if (pollCount > 10) nextDelay = 15000 // After 10 polls, every 15s
        else if (pollCount > 5) nextDelay = 10000 // After 5 polls, every 10s
        else if (pollCount > 2) nextDelay = 5000 // After 2 polls, every 5s
        
        const timeout = setTimeout(poll, nextDelay)
        setPollingInterval(timeout as any)
      }
      
      // Start first poll immediately
      poll()
      
      return () => {
        if (pollingInterval) clearTimeout(pollingInterval)
      }
    } else if (pollingInterval) {
      clearTimeout(pollingInterval)
      setPollingInterval(null)
    }
  }, [currentReview?.review_id, currentReview?.status])

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as HTMLElement
      if (!target.closest('#documentSearch') && !target.closest('.document-dropdown')) {
        setShowDocumentList(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const fetchReviewHistory = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/review/history`)
      if (response.ok) {
        const data = await response.json()
        setReviewHistory(data)
      }
    } catch (err) {
      // Silently fail
    }
  }

  const checkReviewStatus = async (reviewId: string) => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/review/jobs/${reviewId}`)
      if (response.ok) {
        const data = await response.json()
        const previousStatus = currentReview?.status
        setCurrentReview(data)
        
        // Show notification when review completes
        if (previousStatus === 'processing' && data.status === 'completed') {
          // Browser notification if supported
          if ('Notification' in window && Notification.permission === 'granted') {
            new Notification('Review Completed!', {
              body: `AI review of "${data.original_document_title}" is ready`,
              icon: '/favicon.ico'
            })
          }
        }
        
        if (data.status === 'completed' || data.status === 'failed') {
          fetchReviewHistory()
        }
      }
    } catch (err) {
      // Silently fail
    }
  }

  const selectDocument = (doc: Document) => {
    setSelectedDocument(doc)
    setDocumentId(doc.id)
    setSearchQuery(doc.title)
    setShowDocumentList(false)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!documentId || !selectedDocument) {
      setError('Please select a document')
      return
    }

    setLoading(true)
    setError(null)

    try {
      // Fetch the full document content
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/documents/${documentId}`)
      if (!response.ok) {
        throw new Error('Failed to fetch document')
      }
      
      const doc = await response.json()
      const content = doc.content_md || doc.content || ''
      
      if (!content || content.trim().length === 0) {
        throw new Error(`Document "${doc.title}" appears to be empty. Please check the document in the Documents tab.`)
      }
      
      // Set content and show UI
      setOriginalDocContent(content)
      setShowStreamingReview(true)
      
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const togglePersona = (persona: string) => {
    setSelectedPersonas(prev => 
      prev.includes(persona) 
        ? prev.filter(p => p !== persona)
        : [...prev, persona]
    )
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="h-5 w-5 text-emerald-400" />
      case 'processing':
        return <Clock className="h-5 w-5 text-blue-400 animate-spin" />
      case 'failed':
        return <AlertCircle className="h-5 w-5 text-red-400" />
      default:
        return <Clock className="h-5 w-5 text-gray-400" />
    }
  }

  return (
    <>
      {/* Streaming Review Fullscreen */}
      {showStreamingReview && selectedDocument && (
        <StreamingReview
          documentId={documentId}
          documentTitle={selectedDocument.title}
          originalContent={originalDocContent}
          reviewType={reviewType}
          personas={selectedPersonas}
          model={selectedModel}
          onClose={() => setShowStreamingReview(false)}
        />
      )}
      
      {/* Main Review Form */}
      <div className="space-y-6">
        {/* Header */}
        <div>
        <h2 className="text-2xl font-semibold text-foreground mb-2 flex items-center gap-2">
          <Sparkles className="h-6 w-6 text-blue-400" />
          AI Document Review
        </h2>
        <p className="text-muted-foreground">
          Get AI-powered review with inline comments based on Saurabh's engineering leadership persona
        </p>
      </div>

      {/* Review Form */}
      <form onSubmit={handleSubmit} className="space-y-6 bg-card/50 backdrop-blur-sm border border-border/50 rounded-lg p-6">
        <div className="space-y-2 relative">
          <label htmlFor="documentSearch" className="text-sm font-medium text-foreground">
            Select Document
          </label>
          <div className="relative">
            <input
              type="text"
              id="documentSearch"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value)
                setShowDocumentList(true)
              }}
              onFocus={() => setShowDocumentList(true)}
              placeholder="Search by title or URL..."
              autoComplete="off"
              autoCorrect="off"
              autoCapitalize="off"
              spellCheck="false"
              className="w-full px-4 py-3 bg-input border border-border rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent transition-all"
            />
            {selectedDocument && (
              <div className="absolute right-3 top-1/2 -translate-y-1/2">
                <CheckCircle2 className="h-5 w-5 text-emerald-400" />
              </div>
            )}
          </div>
          
          {/* Document Dropdown */}
          {showDocumentList && filteredDocuments.length > 0 && (
            <div className="document-dropdown absolute z-50 w-full mt-1 bg-card border border-border rounded-lg shadow-lg max-h-64 overflow-y-auto">
              {filteredDocuments.slice(0, 10).map((doc) => (
                <button
                  key={doc.id}
                  type="button"
                  onClick={() => selectDocument(doc)}
                  className="w-full px-4 py-3 text-left hover:bg-muted/30 transition-colors border-b border-border/30 last:border-b-0"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-foreground truncate">
                        {doc.title}
                      </p>
                      {doc.source_url && (
                        <p className="text-xs text-muted-foreground truncate mt-1">
                          {doc.source_url}
                        </p>
                      )}
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs px-2 py-0.5 bg-muted/50 rounded text-muted-foreground">
                          {doc.doc_type}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {new Date(doc.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                    {selectedDocument?.id === doc.id && (
                      <CheckCircle2 className="h-5 w-5 text-emerald-400 flex-shrink-0" />
                    )}
                  </div>
                </button>
              ))}
              {filteredDocuments.length > 10 && (
                <div className="px-4 py-2 text-xs text-muted-foreground text-center border-t border-border/30">
                  Showing 10 of {filteredDocuments.length} documents
                </div>
              )}
            </div>
          )}
          
          {showDocumentList && filteredDocuments.length === 0 && searchQuery && (
            <div className="absolute z-50 w-full mt-1 bg-card border border-border rounded-lg shadow-lg p-4 text-center">
              <p className="text-sm text-muted-foreground">No documents found</p>
            </div>
          )}
          
          <p className="text-xs text-muted-foreground">
            {documents.length} documents available • Search by title or paste URL
          </p>
        </div>

        <div className="space-y-3">
          <label className="text-sm font-medium text-foreground">Review Type</label>
          <div className="grid grid-cols-2 gap-3">
            {[
              { 
                type: 'comprehensive', 
                label: 'Comprehensive',
                desc: 'All aspects • Deep analysis • Thorough',
                icon: '📋'
              },
              { 
                type: 'quick', 
                label: 'Quick',
                desc: 'Critical issues only • Fast • High-level',
                icon: '⚡'
              },
              { 
                type: 'technical', 
                label: 'Technical',
                desc: 'Architecture & scalability • Engineering focus',
                icon: '🔧'
              },
              { 
                type: 'strategic', 
                label: 'Strategic',
                desc: 'Business & market impact • ROI focus',
                icon: '🎯'
              }
            ].map(({ type, label, desc, icon }) => (
              <button
                key={type}
                type="button"
                onClick={() => setReviewType(type)}
                className={`px-4 py-3 rounded-lg border transition-all text-left ${
                  reviewType === type
                    ? 'bg-primary/10 border-primary'
                    : 'bg-card/50 backdrop-blur-sm border-border/50 hover:border-border'
                }`}
              >
                <div className="flex items-start gap-2">
                  <span className="text-lg">{icon}</span>
                  <div className="flex-1 min-w-0">
                    <div className={`text-sm font-medium ${
                      reviewType === type ? 'text-primary' : 'text-foreground'
                    }`}>
                      {label}
                    </div>
                    <div className="text-xs text-muted-foreground mt-0.5 line-clamp-2">
                      {desc}
                    </div>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-2">
          <label htmlFor="modelSelect" className="text-sm font-medium text-foreground">AI Model</label>
          <select
            id="modelSelect"
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            className="w-full px-4 py-3 bg-card/50 backdrop-blur-sm border border-border/50 rounded-lg text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary/50 transition-all hover:border-border cursor-pointer appearance-none bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2224%22%20height%3D%2224%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22%23666%22%20stroke-width%3D%222%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Cpolyline%20points%3D%226%209%2012%2015%2018%209%22%3E%3C%2Fpolyline%3E%3C%2Fsvg%3E')] bg-[length:20px] bg-[right_12px_center] bg-no-repeat pr-12"
            style={{
              colorScheme: 'dark'
            }}
          >
            <optgroup label="Claude Code (Local)" className="bg-card text-foreground">
              <option value="claude-code" className="bg-card text-foreground py-2">Claude Code CLI (Installed Locally)</option>
            </optgroup>
            <optgroup label="Claude API (Stable)" className="bg-card text-foreground">
              <option value="claude-sonnet-4.5-20250514" className="bg-card text-foreground py-2">Claude 4.5 Sonnet (Direct API - Stable)</option>
            </optgroup>
            <optgroup label="Cursor Agent (Beta)" className="bg-card text-foreground">
              <option value="sonnet-4.5" className="bg-card text-foreground py-2">Claude 4.5 Sonnet - Balanced</option>
              <option value="sonnet-4.5-thinking" className="bg-card text-foreground py-2">Claude 4.5 Sonnet Thinking - Deep Analysis</option>
              <option value="opus-4.5" className="bg-card text-foreground py-2">Claude 4.5 Opus - Most Capable</option>
              <option value="opus-4.5-thinking" className="bg-card text-foreground py-2">Claude 4.5 Opus Thinking - Maximum Depth</option>
            </optgroup>
            <optgroup label="GPT" className="bg-card text-foreground">
              <option value="gpt-5.2" className="bg-card text-foreground py-2">GPT 5.2 - Latest</option>
              <option value="gpt-5.1" className="bg-card text-foreground py-2">GPT 5.1</option>
              <option value="gpt-5.1-codex" className="bg-card text-foreground py-2">GPT 5.1 Codex - Code Focused</option>
              <option value="gpt-5.1-codex-max" className="bg-card text-foreground py-2">GPT 5.1 Codex Max - Maximum Context</option>
            </optgroup>
            <optgroup label="Other" className="bg-card text-foreground">
              <option value="gemini-3-pro" className="bg-card text-foreground py-2">Gemini 3 Pro</option>
              <option value="composer-1" className="bg-card text-foreground py-2">Composer 1 - Fast</option>
              <option value="auto" className="bg-card text-foreground py-2">Auto - Let Cursor Choose</option>
            </optgroup>
          </select>
          <p className="text-xs text-muted-foreground">
            Claude 4.5 Sonnet provides the best balance of quality and speed
          </p>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium text-foreground">Review Personas</label>
          <p className="text-xs text-muted-foreground mb-2">
            Select one or more perspectives for the review
          </p>
          <div className="grid grid-cols-2 gap-2">
            {[
              { id: 'engineering-leader', label: 'Engineering Leader', icon: '👔', desc: 'Team, execution, delivery' },
              { id: 'principal-engineer', label: 'Principal Engineer', icon: '🔧', desc: 'Architecture, scalability' },
              { id: 'product-strategist', label: 'Product Strategist', icon: '📊', desc: 'Business impact, competition' },
              { id: 'startup-founder', label: 'Startup Founder', icon: '🚀', desc: 'MVP, speed, efficiency' },
              { id: 'process-champion', label: 'Process Champion', icon: '📈', desc: 'Metrics, quality, compliance' },
              { id: 'innovation-driver', label: 'Innovation Driver', icon: '💡', desc: 'AI, automation, tech' },
            ].map((persona) => (
              <button
                key={persona.id}
                type="button"
                onClick={() => togglePersona(persona.id)}
                className={`px-3 py-2.5 rounded-lg border transition-all text-left ${
                  selectedPersonas.includes(persona.id)
                    ? 'bg-blue-500/10 border-blue-500/30'
                    : 'bg-card border-border hover:border-border/80'
                }`}
              >
                <div className="flex items-start gap-2">
                  <span className="text-lg">{persona.icon}</span>
                  <div className="flex-1 min-w-0">
                    <p className={`text-xs font-medium ${
                      selectedPersonas.includes(persona.id) ? 'text-blue-400' : 'text-foreground'
                    }`}>
                      {persona.label}
                    </p>
                    <p className="text-xs text-muted-foreground mt-0.5 truncate">
                      {persona.desc}
                    </p>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>

        <button
          type="submit"
          disabled={loading || !selectedDocument}
          className="w-full h-12 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {loading ? (
            <span className="animate-shimmer bg-gradient-to-r from-white/80 via-white to-white/80 bg-[length:200%_100%] bg-clip-text text-transparent">
              Preparing review...
            </span>
          ) : (
            <>
              <Sparkles className="h-5 w-5" />
              Request AI Review
            </>
          )}
        </button>
      </form>

      {/* Current Review Status */}
      {currentReview && (
        <div className="bg-card/50 backdrop-blur-sm border border-border/50 rounded-lg p-6 space-y-4">
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-3">
              {getStatusIcon(currentReview.status)}
              <div className="flex-1">
                <h3 className="text-lg font-medium text-foreground">
                  {currentReview.status === 'completed' ? 'Review Completed!' : 
                   currentReview.status === 'processing' ? 'Review in Progress...' :
                   currentReview.status === 'failed' ? 'Review Failed' : 'Review Pending'}
                </h3>
                <p className="text-sm text-muted-foreground mt-1">
                  {currentReview.original_document_title || 'Document'}
                </p>
                {currentReview.status === 'processing' && (
                  <div className="mt-4 space-y-3">
                    <div className="flex items-center gap-2 text-sm text-blue-400">
                      <div className="h-2 w-2 bg-blue-400 rounded-full animate-pulse" />
                      <span>AI is generating review in real-time...</span>
                    </div>
                    
                    {/* Streaming Content Preview */}
                    {currentReview.streaming_content && (
                      <div className="mt-4 p-4 bg-muted/20 border border-border/30 rounded-lg max-h-96 overflow-y-auto">
                        <div className="prose prose-invert prose-sm max-w-none">
                          <pre className="whitespace-pre-wrap text-xs text-foreground font-mono">
                            {currentReview.streaming_content}
                          </pre>
                        </div>
                        <div className="mt-2 text-xs text-muted-foreground text-right">
                          {currentReview.streaming_content.length} characters generated...
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>

          {currentReview.status === 'completed' && (
            <div className="space-y-3 pt-3 border-t border-border/30">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Total Comments:</span>
                <span className="text-sm font-medium text-foreground">{currentReview.total_comments}</span>
              </div>
              
              {currentReview.comment_categories && (
                <div className="grid grid-cols-2 gap-2 text-xs">
                  {Object.entries(currentReview.comment_categories).map(([category, count]) => (
                    count > 0 && (
                      <div key={category} className="flex items-center justify-between px-2 py-1 bg-muted/30 rounded">
                        <span className="text-muted-foreground capitalize">{category.replace('_', ' ')}:</span>
                        <span className="font-medium text-foreground">{count}</span>
                      </div>
                    )
                  ))}
                </div>
              )}

              {obsidianEnabled && currentReview.reviewed_document_path && (
                <div className="flex items-center gap-2 pt-2">
                  <button
                    onClick={() => copyToClipboard(currentReview.reviewed_document_path!)}
                    className="flex-1 px-4 py-2 bg-card hover:bg-muted/50 border border-border text-foreground rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2"
                  >
                    <Copy className="h-4 w-4" />
                    Copy Vault Path
                  </button>
                  <a
                    href={`obsidian://open?vault=${process.env.NEXT_PUBLIC_OBSIDIAN_VAULT_NAME || 'vault'}&file=${encodeURIComponent(currentReview.reviewed_document_path)}`}
                    className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2"
                  >
                    <ExternalLink className="h-4 w-4" />
                    Open in Obsidian
                  </a>
                </div>
              )}
            </div>
          )}

          {currentReview.error_message && (
            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
              <p className="text-sm text-red-400">{currentReview.error_message}</p>
            </div>
          )}
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="text-sm font-medium text-red-400">Review Failed</h3>
              <p className="text-sm text-red-400/80 mt-1">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Review History */}
      {reviewHistory.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-lg font-medium text-foreground">Review History</h3>
          <div className="space-y-2">
            {reviewHistory.map((review) => (
              <div
                key={review.review_id}
                className="bg-card/50 backdrop-blur-sm border border-border/50 rounded-lg p-4 hover:border-border hover:bg-card transition-all cursor-pointer"
                onClick={() => setCurrentReview(review)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3 flex-1">
                    {getStatusIcon(review.status)}
                    <div className="flex-1 min-w-0">
                      <h4 className="text-sm font-medium text-foreground truncate">
                        {review.original_document_title || 'Untitled Document'}
                      </h4>
                      <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                        <span className="capitalize">{review.review_type}</span>
                        <span>•</span>
                        <span>{review.total_comments} comments</span>
                        <span>•</span>
                        <span>{new Date(review.started_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      </div>
    </>
  )
}

