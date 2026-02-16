'use client'

import { useSession, signOut } from 'next-auth/react'
import { redirect } from 'next/navigation'
import Link from 'next/link'
import { 
  Upload, 
  FileText, 
  History,
  ArrowRight,
  LogOut,
  Search as SearchIcon,
  FolderInput,
  Folder,
  Network,
  Sparkles,
  Settings as SettingsIcon
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import ImportForm from '@/components/ImportForm'
import DocumentList from '@/components/DocumentList'
import JobsList from '@/components/JobsList'
import Search from '@/components/Search'
import BulkImport from '@/components/BulkImport'
import CodeRepositories from '@/components/CodeRepositories'
import Collections from '@/components/Collections'
import KnowledgeGraph from '@/components/KnowledgeGraph'
import DocumentReview from '@/components/DocumentReview'
import Settings from '@/components/Settings'
import { useState, useRef, useEffect } from 'react'
import { cn } from '@/lib/utils'
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts'

export default function DashboardPage() {
  const { data: session, status } = useSession()
  const [activeTab, setActiveTab] = useState<'import' | 'documents' | 'jobs' | 'search' | 'bulk-import' | 'code' | 'collections' | 'graph' | 'review' | 'settings'>('search')
  const [showShortcuts, setShowShortcuts] = useState(false)
  const searchInputRef = useRef<HTMLInputElement>(null)

  // Keyboard shortcuts
  useKeyboardShortcuts([
    {
      key: 'k',
      metaKey: true,
      handler: () => {
        setActiveTab('search');
        setTimeout(() => {
          const searchInput = document.querySelector('input[type="search"], input[placeholder*="Search"]') as HTMLInputElement;
          searchInput?.focus();
        }, 100);
      },
      description: 'Focus search'
    },
    {
      key: 'i',
      metaKey: true,
      handler: () => setActiveTab('import'),
      description: 'Go to import'
    },
    {
      key: 'd',
      metaKey: true,
      handler: () => setActiveTab('documents'),
      description: 'Go to documents'
    },
    {
      key: '?',
      shiftKey: true,
      handler: () => setShowShortcuts(true),
      description: 'Show shortcuts'
    },
    {
      key: 'Escape',
      handler: () => setShowShortcuts(false),
      description: 'Close modals'
    }
  ])

  if (status === 'loading') {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="text-sm text-muted-foreground">Loading...</div>
      </div>
    )
  }

  if (!session) {
    redirect('/')
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card/50 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-3">
              <div className="h-8 w-8 bg-muted rounded-lg flex items-center justify-center">
                <Folder className="h-4 w-4 text-muted-foreground" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-foreground">
                  {process.env.NEXT_PUBLIC_APP_NAME || 'Knowledge System'}
                </h1>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-sm text-muted-foreground">
                {session.user?.email}
              </span>
              <Button
                onClick={() => signOut()}
                variant="ghost"
                size="sm"
                className="gap-2"
              >
                <LogOut className="h-4 w-4" />
                Sign out
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Welcome Section */}
        <div className="mb-12">
          <div className="flex items-center space-x-3 mb-4">
            <h1 className="text-2xl font-semibold text-foreground">
              Welcome back
            </h1>
          </div>
          <p className="text-muted-foreground text-lg leading-relaxed max-w-2xl">
            Import Google Docs, convert to markdown, and build your knowledge base.
          </p>
        </div>

        {/* Tabs */}
        <div className="mb-6">
          <div className="flex space-x-1 bg-muted/30 p-1 rounded-lg inline-flex">
            <button
              onClick={() => setActiveTab('search')}
              className={cn(
                "px-6 py-2 rounded-md text-sm font-medium transition-all",
                activeTab === 'search'
                  ? 'bg-card text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              <SearchIcon className="h-4 w-4 inline mr-2" />
              Search
            </button>
            <button
              onClick={() => setActiveTab('import')}
              className={cn(
                "px-6 py-2 rounded-md text-sm font-medium transition-all",
                activeTab === 'import'
                  ? 'bg-card text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              <Upload className="h-4 w-4 inline mr-2" />
              Import
            </button>
            <button
              onClick={() => setActiveTab('bulk-import')}
              className={cn(
                "px-6 py-2 rounded-md text-sm font-medium transition-all",
                activeTab === 'bulk-import'
                  ? 'bg-card text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              <FolderInput className="h-4 w-4 inline mr-2" />
              Bulk Import
            </button>
            <button
              onClick={() => setActiveTab('documents')}
              className={cn(
                "px-6 py-2 rounded-md text-sm font-medium transition-all",
                activeTab === 'documents'
                  ? 'bg-card text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              <FileText className="h-4 w-4 inline mr-2" />
              Documents
            </button>
            <button
              onClick={() => setActiveTab('jobs')}
              className={cn(
                "px-6 py-2 rounded-md text-sm font-medium transition-all",
                activeTab === 'jobs'
                  ? 'bg-card text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              <History className="h-4 w-4 inline mr-2" />
              History
            </button>
            <button
              onClick={() => setActiveTab('code')}
              className={cn(
                "px-6 py-2 rounded-md text-sm font-medium transition-all",
                activeTab === 'code'
                  ? 'bg-card text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              💻 Code
            </button>
            <button
              onClick={() => setActiveTab('collections')}
              className={cn(
                "px-6 py-2 rounded-md text-sm font-medium transition-all",
                activeTab === 'collections'
                  ? 'bg-card text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              <Folder className="h-4 w-4 inline mr-2" />
              Collections
            </button>
            <button
              onClick={() => setActiveTab('graph')}
              className={cn(
                "px-6 py-2 rounded-md text-sm font-medium transition-all",
                activeTab === 'graph'
                  ? 'bg-card text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              <Network className="h-4 w-4 inline mr-2" />
              Graph
            </button>
            <button
              onClick={() => setActiveTab('review')}
              className={cn(
                "px-6 py-2 rounded-md text-sm font-medium transition-all",
                activeTab === 'review'
                  ? 'bg-card text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              <Sparkles className="h-4 w-4 inline mr-2" />
              AI Review
            </button>
            <button
              onClick={() => setActiveTab('settings')}
              className={cn(
                "px-6 py-2 rounded-md text-sm font-medium transition-all",
                activeTab === 'settings'
                  ? 'bg-card text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              <SettingsIcon className="h-4 w-4 inline mr-2" />
              Settings
            </button>
          </div>
        </div>

        {/* Content */}
        <div className={cn(
          "bg-card/50 backdrop-blur-sm border border-border/50 rounded-2xl",
          activeTab === 'graph' ? 'p-0 h-[calc(100vh-12rem)]' : 'p-8'
        )}>
          {activeTab === 'search' && <Search />}
          {activeTab === 'import' && <ImportForm accessToken={session.accessToken!} />}
          {activeTab === 'bulk-import' && <BulkImport accessToken={session.accessToken!} />}
          {activeTab === 'documents' && <DocumentList />}
          {activeTab === 'jobs' && <JobsList />}
          {activeTab === 'code' && <CodeRepositories />}
          {activeTab === 'collections' && <Collections />}
          {activeTab === 'graph' && <KnowledgeGraph />}
          {activeTab === 'review' && <DocumentReview />}
          {activeTab === 'settings' && <Settings />}
        </div>

        {/* Keyboard Shortcuts Help Modal */}
        {showShortcuts && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50"
               onClick={() => setShowShortcuts(false)}>
            <div className="bg-card border border-border rounded-2xl p-8 max-w-md w-full mx-4"
                 onClick={(e) => e.stopPropagation()}>
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold text-foreground">Keyboard Shortcuts</h2>
                <button 
                  onClick={() => setShowShortcuts(false)}
                  className="text-muted-foreground hover:text-foreground"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between py-2 border-b border-border">
                  <span className="text-foreground">Focus Search</span>
                  <kbd className="px-3 py-1 bg-muted text-muted-foreground rounded-md text-sm font-mono">
                    Cmd/Ctrl + K
                  </kbd>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-border">
                  <span className="text-foreground">Go to Import</span>
                  <kbd className="px-3 py-1 bg-muted text-muted-foreground rounded-md text-sm font-mono">
                    Cmd/Ctrl + I
                  </kbd>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-border">
                  <span className="text-foreground">Go to Documents</span>
                  <kbd className="px-3 py-1 bg-muted text-muted-foreground rounded-md text-sm font-mono">
                    Cmd/Ctrl + D
                  </kbd>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-border">
                  <span className="text-foreground">Show Shortcuts</span>
                  <kbd className="px-3 py-1 bg-muted text-muted-foreground rounded-md text-sm font-mono">
                    Shift + ?
                  </kbd>
                </div>
                <div className="flex items-center justify-between py-2">
                  <span className="text-foreground">Close Modal</span>
                  <kbd className="px-3 py-1 bg-muted text-muted-foreground rounded-md text-sm font-mono">
                    Esc
                  </kbd>
                </div>
              </div>

              <p className="mt-6 text-sm text-muted-foreground text-center">
                Press <kbd className="px-2 py-0.5 bg-muted rounded">?</kbd> anytime to show this help
              </p>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

