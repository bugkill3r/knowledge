'use client'

import { useState, useEffect, useRef } from 'react'
import { X, Save, Copy, ChevronLeft, ChevronRight } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface StreamingReviewProps {
  documentId: string
  documentTitle: string
  originalContent: string
  reviewType: string
  personas: string[]
  model: string
  onClose: () => void
}

export default function StreamingReview({
  documentId,
  documentTitle,
  originalContent,
  reviewType,
  personas,
  model,
  onClose
}: StreamingReviewProps) {
  const [streamedContent, setStreamedContent] = useState('')
  const [status, setStatus] = useState<'connecting' | 'streaming' | 'completed' | 'error'>('connecting')
  const [error, setError] = useState<string | null>(null)
  const [showOriginal, setShowOriginal] = useState(true)
  const contentRef = useRef<HTMLDivElement>(null)
  const eventSourceRef = useRef<EventSource | null>(null)

  useEffect(() => {
    // Connect to SSE endpoint
    const personasStr = personas.join(',')
    const url = `${process.env.NEXT_PUBLIC_API_URL}/api/v1/review/stream/${documentId}?review_type=${reviewType}&personas=${personasStr}&model=${model}`
    
    const eventSource = new EventSource(url)
    eventSourceRef.current = eventSource

    eventSource.onopen = () => {
      setStatus('streaming')
    }

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        
        switch (data.type) {
          case 'start':
          case 'info':
            setStatus('streaming')
            break
          case 'content':
            setStreamedContent(prev => prev + data.content)
            
            // Auto-scroll to bottom
            setTimeout(() => {
              if (contentRef.current) {
                contentRef.current.scrollTop = contentRef.current.scrollHeight
              }
            }, 0)
            break
          case 'complete':
            setStatus('completed')
            eventSource.close()
            break
          case 'error':
            setError(data.message)
            setStatus('error')
            eventSource.close()
            break
        }
      } catch (e) {
        console.error('Failed to parse SSE message:', e)
      }
    }

    eventSource.onerror = () => {
      setError('AI connection lost. This document may be too large for a single review. Try using "Quick" review type for faster processing.')
      setStatus('error')
      eventSource.close()
    }
    
    // Add timeout for long-running reviews
    const timeout = setTimeout(() => {
      if (status === 'streaming' && streamedContent.length === 0) {
        setError('Review is taking too long. The document may be too large. Try "Quick" review or a smaller document.')
        setStatus('error')
        eventSource.close()
      }
    }, 120000) // 2 minutes

    return () => {
      clearTimeout(timeout)
      eventSource.close()
    }
  }, [documentId, reviewType, personas, model])

  const handleSave = async () => {
    try {
      
      // Create the reviewed document with inline comments
      const reviewedContent = streamedContent
      
      // Save to backend (which will save to Obsidian vault)
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/review/save`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          document_id: documentId,
          document_title: documentTitle,
          review_type: reviewType,
          reviewed_content: reviewedContent,
          personas: personas,
          model: model
        })
      })
      
      if (!response.ok) {
        throw new Error('Failed to save reviewed document')
      }
      
      const result = await response.json()
      console.log('✅ Saved:', result.vault_path ?? 'review saved')
      
      // Show success notification
      if (result.vault_path) {
        alert(`✅ Reviewed document saved to:\n${result.vault_path}`)
      } else {
        alert('✅ Review saved.')
      }
      
      // Close the streaming view
      onClose()
      
    } catch (err: any) {
      console.error('❌ Save error:', err)
      alert(`Failed to save: ${err.message}`)
    }
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(streamedContent)
    console.log('📋 Copied to clipboard')
  }

  return (
    <div className="fixed inset-0 z-50 bg-background flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-border/50 bg-card/50 backdrop-blur-sm">
        <div className="flex items-center gap-4">
          <div>
            <h2 className="text-lg font-semibold text-foreground">{documentTitle}</h2>
            <p className="text-sm text-muted-foreground">AI Review - {reviewType}</p>
          </div>
          {/* Toggle Original Document */}
          <button
            onClick={() => setShowOriginal(!showOriginal)}
            className="px-3 py-1.5 bg-muted/50 hover:bg-muted border border-border/50 text-foreground rounded-lg text-xs font-medium transition-all flex items-center gap-2"
            title={showOriginal ? "Hide original" : "Show original"}
          >
            {showOriginal ? (
              <>
                <ChevronLeft className="h-3 w-3" />
                Hide Original
              </>
            ) : (
              <>
                <ChevronRight className="h-3 w-3" />
                Show Original
              </>
            )}
          </button>
        </div>
        <div className="flex items-center gap-2">
          {status === 'completed' && (
            <>
              <button
                onClick={handleCopy}
                className="px-4 py-2 bg-card hover:bg-muted/50 border border-border text-foreground rounded-lg text-sm font-medium transition-all flex items-center gap-2"
              >
                <Copy className="h-4 w-4" />
                Copy
              </button>
              <button
                onClick={handleSave}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-all flex items-center gap-2"
              >
                <Save className="h-4 w-4" />
                Save to Vault
              </button>
            </>
          )}
          <button
            onClick={onClose}
            className="p-2 hover:bg-muted/50 rounded-lg transition-all"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* Split View */}
      <div className="flex-1 flex overflow-hidden">
        {/* Original Document */}
        {showOriginal && (
          <div className="w-1/2 border-r border-border/50 flex flex-col">
            <div className="px-6 py-3 border-b border-border/30 bg-muted/20">
              <h3 className="text-sm font-medium text-foreground">Original Document</h3>
            </div>
            <div className="flex-1 overflow-y-auto p-6 bg-background">
              {!originalContent ? (
                <div className="flex items-center justify-center h-full">
                  <div className="text-center">
                    <p className="text-sm text-muted-foreground animate-shimmer bg-gradient-to-r from-muted-foreground via-foreground to-muted-foreground bg-[length:200%_100%] bg-clip-text text-transparent">
                      Loading document...
                    </p>
                  </div>
                </div>
              ) : (
                <div className="prose prose-invert prose-sm max-w-none">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {originalContent}
                  </ReactMarkdown>
                </div>
              )}
            </div>
          </div>
        )}

        {/* AI Review (Streaming) */}
        <div className={showOriginal ? "w-1/2 flex flex-col" : "w-full flex flex-col"}>
          <div className="px-6 py-3 border-b border-border/30 bg-muted/20 flex items-center justify-between">
            <h3 className="text-sm font-medium text-foreground">AI Review</h3>
            {status === 'streaming' && (
              <div className="flex items-center gap-2 text-xs text-blue-400">
                <div className="h-2 w-2 bg-blue-400 rounded-full animate-pulse" />
                <span>Streaming...</span>
              </div>
            )}
            {status === 'completed' && (
              <div className="flex items-center gap-2 text-xs text-emerald-400">
                <div className="h-2 w-2 bg-emerald-400 rounded-full" />
                <span>Completed</span>
              </div>
            )}
          </div>
          <div 
            ref={contentRef}
            className="flex-1 overflow-y-auto p-6 bg-background"
          >
            {status === 'connecting' && (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <p className="text-sm text-muted-foreground animate-shimmer bg-gradient-to-r from-muted-foreground via-foreground to-muted-foreground bg-[length:200%_100%] bg-clip-text text-transparent">
                    Connecting to AI...
                  </p>
                </div>
              </div>
            )}
            
            {status === 'error' && (
              <div className="flex items-center justify-center h-full">
                <div className="text-center space-y-2">
                  <p className="text-sm text-red-400">{error}</p>
                </div>
              </div>
            )}
            
            {(status === 'streaming' || status === 'completed') && (
              <div className="prose prose-invert prose-sm max-w-none">
                {status === 'streaming' ? (
                  // Plain text during streaming for performance
                  <>
                    <pre className="whitespace-pre-wrap text-sm text-foreground/90 font-mono">
                      {streamedContent || '(waiting for content...)'}
                      <span className="inline-block w-2 h-4 bg-blue-400 animate-pulse ml-1" />
                    </pre>
                    <p className="text-xs text-muted-foreground mt-2">
                      Content length: {streamedContent.length} | Status: {status}
                    </p>
                  </>
                ) : (
                  // Markdown when completed
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {streamedContent}
                  </ReactMarkdown>
                )}
              </div>
            )}
          </div>
          
          {/* Character Count */}
          {streamedContent && (
            <div className="px-6 py-2 border-t border-border/30 bg-muted/20">
              <p className="text-xs text-muted-foreground text-right">
                {streamedContent.length} characters
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

