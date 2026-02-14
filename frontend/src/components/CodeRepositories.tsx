'use client';

import { useState, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import dynamic from 'next/dynamic';
import { Plus, Trash2 } from 'lucide-react';
import TopContributors from './TopContributors';
import RecentActivity from './RecentActivity';
import AddRepositoryModal from './AddRepositoryModal';

const CodeNetworkGraph = dynamic(() => import('./CodeNetworkGraph'), { ssr: false });

interface CodeRepository {
  id: string;
  name: string;
  local_path: string;
  primary_language: string | null;
  total_files: number;
  total_functions: number;
  total_classes: number;
  lines_of_code: number;
  total_commits: number;
  last_synced: string | null;
}

interface CodeStats {
  total_repositories: number;
  total_chunks: number;
  total_functions: number;
  total_classes: number;
  total_lines_of_code: number;
  languages: Record<string, number>;
}

interface NetworkData {
  nodes: Array<{ id: string; data: { label: string; type: string; [key: string]: any }; position: { x: number; y: number } }>;
  edges: Array<{ id: string; source: string; target: string; type: string }>;
}

export default function CodeRepositories() {
  const { data: session } = useSession();
  const [repositories, setRepositories] = useState<CodeRepository[]>([]);
  const [stats, setStats] = useState<CodeStats | null>(null);
  const [networkData, setNetworkData] = useState<NetworkData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [ingesting, setIngesting] = useState(false);
  const [showGraph, setShowGraph] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError('');
      
      const [reposRes, statsRes, graphRes] = await Promise.all([
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/code/repositories`),
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/code/stats`),
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/code/network-graph`)
      ]);

      if (!reposRes.ok || !statsRes.ok) {
        throw new Error('Failed to fetch data');
      }

      const reposData = await reposRes.json();
      const statsData = await statsRes.json();
      const graphData = graphRes.ok ? await graphRes.json() : null;

      setRepositories(reposData);
      setStats(statsData);
      setNetworkData(graphData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleAddRepository = async (repoData: { repo_path: string; repo_name: string }) => {
    setIngesting(true);
    setError('');

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/code/ingest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(repoData),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Ingestion failed');
      }

      // Refresh data after a delay for backend processing
      setTimeout(() => {
        fetchData();
      }, 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ingestion failed');
      throw err;
    } finally {
      setIngesting(false);
    }
  };

  const handleDeleteRepository = async (repoId: string) => {
    if (!confirm('Are you sure you want to delete this repository?')) {
      return;
    }

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/code/repositories/${repoId}`, {
        method: 'DELETE',
      });

      if (!res.ok) {
        throw new Error('Failed to delete repository');
      }

      fetchData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete repository');
    }
  };

  const getLanguageIcon = (lang: string | null) => {
    if (!lang) return '📁';
    switch (lang.toLowerCase()) {
      case 'python': return '🐍';
      case 'javascript': return '📜';
      case 'typescript': return '📘';
      case 'go': return '🐹';
      case 'java': return '☕';
      default: return '📁';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-muted-foreground">Loading repositories...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header with Add Repository Button */}
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-foreground">Code Repositories</h1>
        <button
          onClick={() => setShowAddModal(true)}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-blue hover:bg-primary-blue/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-blue"
        >
          <Plus className="h-5 w-5 mr-2" />
          Add Repository
        </button>
      </div>

      {error && (
        <div className="bg-red-500/20 text-red-400 p-4 rounded-md border border-red-500/30">
          Error: {error}
        </div>
      )}

      {/* Stats Overview */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div className="bg-card/50 backdrop-blur-sm border border-border/50 rounded-xl p-4">
            <div className="text-sm text-muted-foreground">Repositories</div>
            <div className="text-2xl font-bold text-foreground">{stats.total_repositories}</div>
          </div>
          <div className="bg-card/50 backdrop-blur-sm border border-border/50 rounded-xl p-4">
            <div className="text-sm text-muted-foreground">Code Chunks</div>
            <div className="text-2xl font-bold text-foreground">{stats.total_chunks}</div>
          </div>
          <div className="bg-card/50 backdrop-blur-sm border border-border/50 rounded-xl p-4">
            <div className="text-sm text-muted-foreground">Functions</div>
            <div className="text-2xl font-bold text-foreground">{stats.total_functions}</div>
          </div>
          <div className="bg-card/50 backdrop-blur-sm border border-border/50 rounded-xl p-4">
            <div className="text-sm text-muted-foreground">Classes</div>
            <div className="text-2xl font-bold text-foreground">{stats.total_classes}</div>
          </div>
          <div className="bg-card/50 backdrop-blur-sm border border-border/50 rounded-xl p-4">
            <div className="text-sm text-muted-foreground">Lines of Code</div>
            <div className="text-2xl font-bold text-foreground">{stats.total_lines_of_code.toLocaleString()}</div>
          </div>
        </div>
      )}

      {/* Network Graph */}
      {networkData && networkData.nodes.length > 0 && (
        <div className="bg-card/50 backdrop-blur-sm border border-border/50 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-foreground">Code Network</h2>
            <button
              onClick={() => setShowGraph(!showGraph)}
              className="px-3 py-1 text-sm bg-primary-blue/20 text-primary-blue rounded-md hover:bg-primary-blue/30"
            >
              {showGraph ? 'Hide Graph' : 'Show Graph'}
            </button>
          </div>
          {showGraph && (
            <div className="h-[500px] bg-background/50 rounded-lg border border-border overflow-hidden">
              <CodeNetworkGraph data={networkData} />
            </div>
          )}
        </div>
      )}

      {/* Contributors and Activity */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <TopContributors />
        <RecentActivity />
      </div>

      {/* Repositories List */}
      <div className="bg-card/50 backdrop-blur-sm border border-border/50 rounded-xl p-6">
        <h2 className="text-xl font-semibold text-foreground mb-4">Repositories</h2>
        {repositories.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            No repositories ingested yet. Click "Add Repository" to get started.
          </div>
        ) : (
          <div className="space-y-3">
            {repositories.map((repo) => (
              <div
                key={repo.id}
                className="bg-background/50 border border-border rounded-lg p-4 hover:border-primary-blue/50 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-2xl">{getLanguageIcon(repo.primary_language)}</span>
                      <h3 className="text-lg font-medium text-foreground">{repo.name}</h3>
                      {repo.primary_language && (
                        <span className="px-2 py-0.5 bg-primary-blue/20 text-primary-blue text-xs rounded-full">
                          {repo.primary_language}
                        </span>
                      )}
                    </div>
                    <div className="text-sm text-muted-foreground mb-2">{repo.local_path}</div>
                    <div className="flex items-center gap-4 text-xs text-muted-foreground">
                      <span>{repo.total_files} files</span>
                      <span>{repo.total_functions} functions</span>
                      <span>{repo.total_classes} classes</span>
                      <span>{repo.lines_of_code.toLocaleString()} LOC</span>
                      <span>{repo.total_commits} commits</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {repo.last_synced && (
                      <div className="text-xs text-muted-foreground">
                        Synced {new Date(repo.last_synced).toLocaleDateString()}
                      </div>
                    )}
                    <button
                      onClick={() => handleDeleteRepository(repo.id)}
                      className="p-2 text-red-400 hover:bg-red-500/10 rounded-md transition-colors"
                      title="Delete repository"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Add Repository Modal */}
      <AddRepositoryModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onAdd={handleAddRepository}
      />
    </div>
  );
}
