'use client'

import { useState, useEffect } from 'react'
import { Clock, CheckCircle, XCircle, AlertCircle, RefreshCw } from 'lucide-react'

interface Job {
  job_id: string
  status: string
  total_docs: number
  processed_docs: number
  failed_docs: number
  progress_percentage: number
  error_message: string | null
  started_at: string
  completed_at: string | null
}

export default function JobsList() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => {
    fetchJobs()
    // Poll for updates every 5 seconds
    const interval = setInterval(fetchJobs, 5000)
    return () => clearInterval(interval)
  }, [])

  const fetchJobs = async (manual = false) => {
    if (manual) setRefreshing(true)
    
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/imports/jobs`)
      if (!response.ok) {
        throw new Error('Failed to fetch jobs')
      }
      const data = await response.json()
      setJobs(data)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
      if (manual) {
        setTimeout(() => setRefreshing(false), 500)
      }
    }
  }

  const getStatusConfig = (status: string) => {
    const configs: Record<string, { color: string; icon: any; label: string }> = {
      pending: { 
        color: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20', 
        icon: Clock,
        label: 'Pending'
      },
      processing: { 
        color: 'bg-blue-500/10 text-blue-400 border-blue-500/20', 
        icon: RefreshCw,
        label: 'Processing'
      },
      completed: { 
        color: 'bg-green-500/10 text-green-400 border-green-500/20', 
        icon: CheckCircle,
        label: 'Completed'
      },
      failed: { 
        color: 'bg-red-500/10 text-red-400 border-red-500/20', 
        icon: XCircle,
        label: 'Failed'
      },
      partial: { 
        color: 'bg-orange-500/10 text-orange-400 border-orange-500/20', 
        icon: AlertCircle,
        label: 'Partial'
      },
    }
    return configs[status] || { 
      color: 'bg-gray-500/10 text-gray-400 border-gray-500/20', 
      icon: Clock,
      label: status
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  if (loading && jobs.length === 0) {
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

  if (jobs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="text-6xl mb-4">⏱️</div>
        <h3 className="text-lg font-medium text-foreground mb-2">No import jobs yet</h3>
        <p className="text-sm text-muted-foreground max-w-md">
          Import history will appear here once you start importing documents.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-foreground">Import History</h2>
          <p className="text-sm text-muted-foreground mt-1">
            {jobs.length} import job{jobs.length !== 1 ? 's' : ''}
          </p>
        </div>
        <button
          onClick={() => fetchJobs(true)}
          disabled={refreshing}
          className="p-2 hover:bg-muted rounded-md transition-colors disabled:opacity-50"
          title="Refresh"
        >
          <RefreshCw className={`w-4 h-4 text-muted-foreground ${refreshing ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Jobs List */}
      <div className="space-y-3">
        {jobs.map((job) => {
          const statusConfig = getStatusConfig(job.status)
          const StatusIcon = statusConfig.icon
          
          return (
            <div
              key={job.job_id}
              className="p-4 bg-card border border-border rounded-lg hover:border-primary-blue/50 transition-all"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <span className={`px-2 py-1 text-xs rounded-md border flex items-center gap-1.5 ${statusConfig.color}`}>
                    <StatusIcon className="w-3 h-3" />
                    {statusConfig.label}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {formatDate(job.started_at)}
                  </span>
                </div>
              </div>

              {/* Progress */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-4">
                    <span className="text-muted-foreground">
                      Progress: <span className="font-medium text-foreground">{job.processed_docs} / {job.total_docs}</span>
                    </span>
                    {job.failed_docs > 0 && (
                      <span className="text-red-400">
                        Failed: <span className="font-medium">{job.failed_docs}</span>
                      </span>
                    )}
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {job.progress_percentage}%
                  </span>
                </div>

                {/* Progress bar */}
                <div className="w-full bg-muted rounded-full h-1.5 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${
                      job.status === 'completed'
                        ? 'bg-green-500'
                        : job.status === 'failed'
                        ? 'bg-red-500'
                        : job.status === 'processing'
                        ? 'bg-primary-blue'
                        : 'bg-gray-500'
                    }`}
                    style={{ width: `${job.progress_percentage}%` }}
                  />
                </div>

                {/* Error message */}
                {job.error_message && (
                  <div className="mt-2 p-2 bg-red-500/10 border border-red-500/20 rounded text-xs text-red-400">
                    {job.error_message}
                  </div>
                )}

                {/* Completion time */}
                {job.completed_at && (
                  <div className="text-xs text-muted-foreground">
                    Completed: {formatDate(job.completed_at)}
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
