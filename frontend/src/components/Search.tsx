'use client';

import React, { useState } from 'react';
import { useSession } from 'next-auth/react';
import { Search as SearchIcon, Filter, X, ExternalLink, Code2, FileText, Sparkles, Copy, Check, GitBranch } from 'lucide-react';
import { useAppConfig } from '@/lib/app-config';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface SearchResult {
  document_id: string;
  document_title: string;
  chunk_text: string;
  similarity_score: number;
  chunk_index: number;
  source_url?: string;
  vault_path?: string;
  doc_type?: string;
  language?: string;
  repository_id?: string;
  repository_name?: string;
  file_path?: string;
  chunk_type?: string;
  chunk_name?: string;
  start_line?: number;
  end_line?: number;
}

interface SearchResponse {
  query: string;
  results: SearchResult[];
  total_results: number;
  ai_answer?: string;
}

interface FilterOptions {
  doc_types: string[];
  authors: string[];
  tags: string[];
  date_range: { min: string; max: string };
}

// Simple in-memory cache
interface CacheEntry {
  results: SearchResult[];
  totalResults: number;
  aiAnswer: string | null;
  timestamp: number;
}

const searchCache = new Map<string, CacheEntry>();
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

export default function Search() {
  const { data: session } = useSession();
  const { obsidianEnabled } = useAppConfig();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [totalResults, setTotalResults] = useState(0);
  const [error, setError] = useState('');
  const [aiAnswer, setAiAnswer] = useState<string | null>(null);
  const [streamingAnswer, setStreamingAnswer] = useState(false);
  const [answerSources, setAnswerSources] = useState<any[]>([]);
  
  // Filters
  const [showFilters, setShowFilters] = useState(false);
  const [filterOptions, setFilterOptions] = useState<FilterOptions | null>(null);
  const [selectedDocType, setSelectedDocType] = useState<string>('');
  const [selectedAuthor, setSelectedAuthor] = useState<string>('');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [dateFrom, setDateFrom] = useState<string>('');
  const [dateTo, setDateTo] = useState<string>('');
  const [selectedCollection, setSelectedCollection] = useState<string>('');
  const [collections, setCollections] = useState<Array<{id: string; name: string; icon: string}>>([]);
  
  // Debounce timer ref
  const debounceTimerRef = React.useRef<NodeJS.Timeout | null>(null);
  
  // Code modal state
  const [selectedCode, setSelectedCode] = useState<SearchResult | null>(null);
  const [copied, setCopied] = useState(false);

  // Handle ESC key for modal
  React.useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && selectedCode) {
        setSelectedCode(null);
      }
    };
    
    window.addEventListener('keydown', handleEsc);
    return () => {
      window.removeEventListener('keydown', handleEsc);
    };
  }, [selectedCode]);

  // Load filter options and collections on mount
  React.useEffect(() => {
    const loadFilters = async () => {
      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/v1/search/filters`,
          {
            headers: {
              'Authorization': `Bearer ${session?.accessToken}`
            }
          }
        );
        if (response.ok) {
          const data = await response.json();
          setFilterOptions(data);
        }
      } catch (err) {
        console.error('Failed to load filters:', err);
      }
    };
    
    const loadCollections = async () => {
      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/v1/collections/`
        );
        if (response.ok) {
          const data = await response.json();
          setCollections(data);
        }
      } catch (err) {
        console.error('Failed to load collections:', err);
      }
    };
    
    if (session?.accessToken) {
      loadFilters();
    }
    loadCollections();
  }, [session]);

  const handleSearch = async (e?: React.FormEvent, skipCache = false) => {
    if (e) {
      e.preventDefault();
    }
    
    if (!query.trim() || query.length < 3) {
      return;
    }

    // Build cache key
    const params = new URLSearchParams({
      q: query,
      limit: '20'
    });
    
    if (selectedDocType) params.append('doc_type', selectedDocType);
    if (selectedAuthor) params.append('author', selectedAuthor);
    if (selectedTags.length > 0) params.append('tags', selectedTags.join(','));
    if (dateFrom) params.append('date_from', dateFrom);
    if (dateTo) params.append('date_to', dateTo);
    
    const cacheKey = params.toString();

    // Check cache first
    if (!skipCache) {
      const cached = searchCache.get(cacheKey);
      if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
        setResults(cached.results);
        setTotalResults(cached.totalResults);
        setAiAnswer(cached.aiAnswer);
        return;
      }
    }

    setLoading(true);
    setError('');
    setAiAnswer(null);
    setAnswerSources([]);

    try {
      // First, get search results (without AI answer)
      params.set('generate_answer', 'false');
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/search?${params}`,
        {
          headers: {
            'Authorization': `Bearer ${session?.accessToken}`
          }
        }
      );

      if (!response.ok) {
        throw new Error(`Search failed: ${response.statusText}`);
      }

      const data: SearchResponse = await response.json();
      setResults(data.results);
      setTotalResults(data.total_results);
      
      // Then, stream AI answer
      if (data.results.length > 0) {
        streamAIAnswer(query);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const streamAIAnswer = async (searchQuery: string) => {
    setStreamingAnswer(true);
    setAiAnswer('');
    
    try {
      const params = new URLSearchParams({
        q: searchQuery,
        limit: '10',
        model: 'claude-code'
      });
      
      const eventSource = new EventSource(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/search/answer-stream?${params}`
      );
      
      eventSource.addEventListener('message', (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'content') {
            setAiAnswer((prev) => (prev || '') + data.text);
          } else if (data.type === 'sources') {
            setAnswerSources(data.sources);
          } else if (data.type === 'done') {
            setStreamingAnswer(false);
            eventSource.close();
          } else if (data.type === 'error') {
            setError(`AI Answer failed: ${data.message}`);
            setStreamingAnswer(false);
            eventSource.close();
          }
        } catch (err) {
          console.error('Failed to parse SSE data:', err);
        }
      });
      
      eventSource.onerror = () => {
        setStreamingAnswer(false);
        eventSource.close();
      };
    } catch (err) {
      console.error('Failed to stream AI answer:', err);
      setStreamingAnswer(false);
    }
  };

  // Auto-search when user stops typing (debounced)
  React.useEffect(() => {
    // Clear previous timer
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    if (query.length < 3) {
      setResults([]);
      setTotalResults(0);
      setAiAnswer(null);
      return;
    }

    // Set new timer
    debounceTimerRef.current = setTimeout(() => {
      handleSearch();
    }, 600); // Slightly longer debounce for better UX

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [query, selectedDocType, selectedAuthor, selectedTags, dateFrom, dateTo]);

  const handleInputChange = (value: string) => {
    setQuery(value);
    setError('');
  };
  
  const clearFilters = () => {
    setSelectedDocType('');
    setSelectedAuthor('');
    setSelectedTags([]);
    setDateFrom('');
    setDateTo('');
    setSelectedCollection('');
  };
  
  const activeFilterCount = [
    selectedCollection,
    selectedDocType,
    selectedAuthor,
    selectedTags.length > 0,
    dateFrom,
    dateTo
  ].filter(Boolean).length;

  const getResultIcon = (result: SearchResult) => {
    if (result.doc_type === 'code') {
      return <Code2 className="w-4 h-4" />;
    }
    return <FileText className="w-4 h-4" />;
  };

  const getLanguageBadgeColor = (language?: string) => {
    switch (language?.toLowerCase()) {
      case 'go': return 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20';
      case 'python': return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
      case 'typescript': case 'javascript': return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20';
      default: return 'bg-gray-500/10 text-gray-400 border-gray-500/20';
    }
  };

  const handleResultClick = (result: SearchResult) => {
    if (result.doc_type === 'code') {
      setSelectedCode(result);
    } else if (result.source_url) {
      window.open(result.source_url, '_blank');
    } else if (obsidianEnabled && result.vault_path) {
      alert(`Document location: ${result.vault_path}\nOpen this file in your Obsidian vault.`);
    }
  };

  const handleCopyCode = async () => {
    if (!selectedCode) return;
    
    try {
      await navigator.clipboard.writeText(selectedCode.chunk_text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const extractCodeFromChunk = (chunkText: string) => {
    // The chunk_text contains formatted text like "Function: X\nFile: Y\nSignature: Z\nCode:\n..."
    // Extract just the code part
    const codeMatch = chunkText.match(/Code:\n([\s\S]*)/);
    return codeMatch ? codeMatch[1] : chunkText;
  };

  return (
    <div className="h-full flex flex-col w-full">
      {/* Search Bar */}
      <div className="mb-8">
        <form onSubmit={handleSearch} className="relative flex gap-2">
          <div className="relative flex-1">
            <SearchIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
            <input
              type="search"
              value={query}
              onChange={(e) => handleInputChange(e.target.value)}
              placeholder="Search docs and code..."
              className="w-full px-4 py-3.5 pl-12 pr-12 bg-card border border-border rounded-lg
                       text-foreground placeholder:text-muted-foreground
                       focus:outline-none focus:ring-2 focus:ring-primary-blue/20 focus:border-primary-blue
                       transition-all"
              autoFocus
            />
            {loading && (
              <div className="absolute right-12 top-1/2 -translate-y-1/2">
                <div className="animate-spin rounded-full h-4 w-4 border-2 border-primary-blue border-t-transparent"></div>
              </div>
            )}
            <button
              type="button"
              onClick={() => setShowFilters(!showFilters)}
              className={`absolute right-3 top-1/2 -translate-y-1/2 p-2 rounded-md
                       transition-colors ${showFilters ? 'bg-primary-blue/10 text-primary-blue' : 'hover:bg-muted text-muted-foreground'}`}
            >
              <Filter className="w-4 h-4" />
              {activeFilterCount > 0 && (
                <span className="absolute -top-1 -right-1 w-4 h-4 bg-primary-blue text-white text-[10px] rounded-full flex items-center justify-center font-medium">
                  {activeFilterCount}
                </span>
              )}
            </button>
          </div>
          
          <button
            type="submit"
            disabled={loading || query.length < 3}
            className="px-6 py-3.5 bg-primary-blue text-white rounded-lg font-medium
                     hover:bg-primary-blue/90 disabled:opacity-50 disabled:cursor-not-allowed
                     transition-all flex items-center gap-2"
          >
            <SearchIcon className="w-4 h-4" />
            Search
          </button>
        </form>

        {/* Query hint */}
        {query.length > 0 && query.length < 3 && (
          <p className="mt-2 text-xs text-muted-foreground">
            Type at least 3 characters to search
          </p>
        )}
        
        {/* Loading hint */}
        {loading && query.length >= 3 && (
          <p className="mt-2 text-xs">
            <span className="shimmer-text">
              Searching...
            </span>
          </p>
        )}
      </div>

      {/* Filter Panel */}
      {showFilters && filterOptions && (
        <div className="mb-6 p-4 bg-card/50 border border-border rounded-lg">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium text-foreground">Filters</span>
            <button
              onClick={clearFilters}
              disabled={activeFilterCount === 0}
              className="text-xs text-muted-foreground hover:text-foreground disabled:opacity-30 transition-colors"
            >
              Clear all
            </button>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <select
              value={selectedCollection}
              onChange={(e) => setSelectedCollection(e.target.value)}
              className="px-3 py-2 text-sm bg-background border border-border rounded-md
                       focus:outline-none focus:ring-2 focus:ring-primary-blue/20 focus:border-primary-blue"
            >
              <option value="">All collections</option>
              {collections.map((collection) => (
                <option key={collection.id} value={collection.id}>
                  {collection.icon} {collection.name}
                </option>
              ))}
            </select>

            <select
              value={selectedDocType}
              onChange={(e) => setSelectedDocType(e.target.value)}
              className="px-3 py-2 text-sm bg-background border border-border rounded-md
                       focus:outline-none focus:ring-2 focus:ring-primary-blue/20 focus:border-primary-blue"
            >
              <option value="">All types</option>
              {filterOptions.doc_types.map((type) => (
                <option key={type} value={type}>{type.toUpperCase()}</option>
              ))}
            </select>

            <select
              value={selectedAuthor}
              onChange={(e) => setSelectedAuthor(e.target.value)}
              className="px-3 py-2 text-sm bg-background border border-border rounded-md
                       focus:outline-none focus:ring-2 focus:ring-primary-blue/20 focus:border-primary-blue"
            >
              <option value="">All authors</option>
              {filterOptions.authors.map((author) => (
                <option key={author} value={author}>{author}</option>
              ))}
            </select>

            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              placeholder="From"
              className="px-3 py-2 text-sm bg-background border border-border rounded-md
                       focus:outline-none focus:ring-2 focus:ring-primary-blue/20 focus:border-primary-blue"
            />

            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              placeholder="To"
              className="px-3 py-2 text-sm bg-background border border-border rounded-md
                       focus:outline-none focus:ring-2 focus:ring-primary-blue/20 focus:border-primary-blue"
            />
          </div>
        </div>
      )}

      {/* Main Content - Split View */}
      {(aiAnswer || streamingAnswer || results.length > 0) && !loading && (
        <div className="flex-1 flex gap-6 min-h-0">
          {/* Left: AI Answer (Primary) */}
          <div className="flex-1 min-w-0 overflow-y-auto">
            {(aiAnswer || streamingAnswer) ? (
              <div className="p-6 bg-card border border-border rounded-lg">
                <div className="flex items-start gap-3 mb-4">
                  <Sparkles className={`w-6 h-6 text-primary-blue mt-0.5 flex-shrink-0 ${streamingAnswer ? 'animate-pulse' : ''}`} />
                  <div className="flex-1 min-w-0">
                    <div className="text-lg font-semibold text-foreground mb-1 flex items-center gap-2">
                      AI Answer
                      {streamingAnswer && (
                        <span className="text-xs text-muted-foreground shimmer-text font-normal">
                          Generating...
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Based on {answerSources.length || results.length} relevant documents
                    </div>
                  </div>
                </div>
                
                <div className="text-sm text-foreground leading-relaxed prose prose-invert max-w-none">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {aiAnswer || ''}
                  </ReactMarkdown>
                  {streamingAnswer && (
                    <span className="inline-block w-1.5 h-4 bg-primary-blue animate-pulse ml-0.5"></span>
                  )}
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-20 text-center">
                <Sparkles className="w-12 h-12 text-primary-blue mb-4 opacity-50" />
                <p className="text-sm text-muted-foreground">
                  AI answer will appear here...
                </p>
              </div>
            )}
          </div>

          {/* Right: Relevant Documents (Secondary) */}
          <div className="w-96 flex-shrink-0">
            <div className="sticky top-0">
              <div className="mb-3 flex items-center justify-between">
                <div className="text-sm font-medium text-foreground">
                  Relevant Documents
                </div>
                <div className="text-xs text-muted-foreground">
                  {totalResults} found
                </div>
              </div>
              
              <div className="space-y-2 max-h-[calc(100vh-16rem)] overflow-y-auto pr-2 custom-scrollbar">
                {results.slice(0, 10).map((result, idx) => (
                  <div
                    key={`${result.document_id}-${result.chunk_index}-${idx}`}
                    className="group p-3 bg-card/50 border border-border rounded-lg hover:border-primary-blue/50 
                             hover:bg-card transition-all cursor-pointer"
                    onClick={() => handleResultClick(result)}
                  >
                    <div className="flex items-start gap-2 mb-2">
                      <div className="mt-0.5 text-muted-foreground flex-shrink-0">
                        {getResultIcon(result)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="text-sm font-medium text-foreground truncate mb-1">
                          {result.document_title}
                        </h3>
                        <div className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
                          {result.chunk_text}
                        </div>
                      </div>
                    </div>
                    
                    {/* Relevance Score */}
                    <div className="flex items-center gap-2 mt-2">
                      <div className="flex-1 h-1 bg-muted rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-primary-blue to-green-500 rounded-full"
                          style={{ width: `${result.similarity_score * 100}%` }}
                        />
                      </div>
                      <span className="text-xs font-medium text-muted-foreground">
                        {(result.similarity_score * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Empty States */}
      {loading && (
        <div className="flex items-center justify-center py-20">
          <p className="text-sm shimmer-text">
            Searching your knowledge base...
          </p>
        </div>
      )}

      {query && !loading && results.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="text-6xl mb-4">🔍</div>
          <p className="text-lg font-medium text-foreground mb-2">
            No results found
          </p>
          <p className="text-sm text-muted-foreground max-w-md">
            Try different keywords or rephrase your query. Semantic search works best with natural language questions.
          </p>
        </div>
      )}

      {!loading && !query && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="text-6xl mb-4">💡</div>
          <p className="text-lg font-medium text-foreground mb-2">
            Search your knowledge base
          </p>
          <p className="text-sm text-muted-foreground max-w-md mb-6">
            Ask questions in natural language to get AI-powered answers
          </p>
          <div className="space-y-2 text-sm text-muted-foreground">
            <p className="font-medium text-foreground">Try asking:</p>
            <div className="space-y-1">
              <div className="px-3 py-1.5 bg-muted/50 rounded-md">&quot;Summarize the main decisions&quot;</div>
              <div className="px-3 py-1.5 bg-muted/50 rounded-md">&quot;How does [feature] work?&quot;</div>
              <div className="px-3 py-1.5 bg-muted/50 rounded-md">&quot;Key points from the docs&quot;</div>
            </div>
          </div>
        </div>
      )}

      {/* Code Detail Modal */}
      {selectedCode && (
        <div 
          className="z-50"
          onClick={() => setSelectedCode(null)}
          style={{ 
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'center',
            padding: '2rem 1rem',
            zIndex: 9999,
            overflowY: 'auto'
          }}
        >
          <div 
            className="bg-card border border-border rounded-lg flex flex-col"
            onClick={(e) => e.stopPropagation()}
            style={{ 
              width: '100%',
              maxWidth: '56rem',
              maxHeight: 'calc(100vh - 4rem)',
              overflow: 'hidden'
            }}
          >
            {/* Modal Header */}
            <div className="p-4 border-b border-border flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-2">
                  <Code2 className="w-5 h-5 text-primary-blue flex-shrink-0" />
                  <h2 className="text-lg font-semibold text-foreground truncate">
                    {selectedCode.chunk_name || selectedCode.document_title}
                  </h2>
                </div>
                
                {/* Metadata */}
                <div className="space-y-1 text-sm">
                  {selectedCode.repository_name && (
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <GitBranch className="w-4 h-4" />
                      <span className="font-medium">{selectedCode.repository_name}</span>
                    </div>
                  )}
                  {selectedCode.file_path && (
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <FileText className="w-4 h-4" />
                      <span className="font-mono text-xs">{selectedCode.file_path}</span>
                      {selectedCode.start_line && selectedCode.end_line && (
                        <span className="text-xs">
                          (Lines {selectedCode.start_line}-{selectedCode.end_line})
                        </span>
                      )}
                    </div>
                  )}
                  <div className="flex items-center gap-2 flex-wrap">
                    {selectedCode.chunk_type && (
                      <span className="px-2 py-0.5 bg-primary-blue/10 text-primary-blue border border-primary-blue/20 rounded-md text-xs">
                        {selectedCode.chunk_type}
                      </span>
                    )}
                    {selectedCode.language && (
                      <span className={`px-2 py-0.5 border rounded-md text-xs ${getLanguageBadgeColor(selectedCode.language)}`}>
                        {selectedCode.language}
                      </span>
                    )}
                  </div>
                </div>
              </div>
              
              <div className="flex items-center gap-2 ml-4">
                <button
                  onClick={handleCopyCode}
                  className="p-2 hover:bg-muted rounded-md transition-colors"
                  title="Copy code"
                >
                  {copied ? (
                    <Check className="w-4 h-4 text-green-500" />
                  ) : (
                    <Copy className="w-4 h-4 text-muted-foreground" />
                  )}
                </button>
                <button
                  onClick={() => setSelectedCode(null)}
                  className="p-2 hover:bg-muted rounded-md transition-colors"
                >
                  <X className="w-4 h-4 text-muted-foreground" />
                </button>
              </div>
            </div>

            {/* Code Content */}
            <div className="flex-1 overflow-auto bg-[#1e1e1e]">
              <SyntaxHighlighter
                language={selectedCode.language || 'text'}
                style={vscDarkPlus}
                showLineNumbers
                startingLineNumber={selectedCode.start_line || 1}
                customStyle={{
                  margin: 0,
                  padding: '1rem',
                  background: '#1e1e1e',
                  fontSize: '0.875rem',
                  lineHeight: '1.5',
                }}
                lineNumberStyle={{
                  minWidth: '3em',
                  paddingRight: '1em',
                  color: '#858585',
                  userSelect: 'none',
                }}
              >
                {extractCodeFromChunk(selectedCode.chunk_text)}
              </SyntaxHighlighter>
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-border bg-muted/30">
              <div className="flex items-center gap-4 text-xs text-muted-foreground">
                <span>Relevance: {(selectedCode.similarity_score * 100).toFixed(0)}%</span>
                {selectedCode.start_line && selectedCode.end_line && (
                  <span>{selectedCode.end_line - selectedCode.start_line + 1} lines</span>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

