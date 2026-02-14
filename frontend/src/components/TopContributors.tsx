'use client';

import { useEffect, useState } from 'react';

interface Contributor {
  id: string;
  name: string | null;
  email: string;
  commit_count: number;
}

export default function TopContributors() {
  const [contributors, setContributors] = useState<Contributor[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchContributors();
  }, []);

  const fetchContributors = async () => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/code/contributors`);
      if (res.ok) {
        const data = await res.json();
        setContributors(data);
      }
    } catch (err) {
      console.error('Failed to fetch contributors:', err);
    } finally {
      setLoading(false);
    }
  };

  const getInitials = (name: string | null, email: string) => {
    if (name && name.trim()) {
      return name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
    }
    return email.substring(0, 2).toUpperCase();
  };

  const getDisplayName = (name: string | null, email: string) => {
    return name && name.trim() ? name : email.split('@')[0];
  };

  if (loading) {
    return (
      <div className="bg-card/50 backdrop-blur-sm border border-border/50 rounded-xl p-6">
        <div className="text-sm text-muted-foreground">Loading contributors...</div>
      </div>
    );
  }

  return (
    <div className="bg-card/50 backdrop-blur-sm border border-border/50 rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-foreground">Top Contributors</h3>
      </div>
      
      <div className="space-y-3">
        {contributors.slice(0, 5).map((contributor, index) => (
          <div
            key={contributor.id}
            className="flex items-center space-x-3 p-2 rounded-lg hover:bg-background/50 transition-colors"
          >
            <div className="relative">
              <div className="w-10 h-10 bg-gradient-to-br from-primary-blue to-primary-purple rounded-full flex items-center justify-center text-white font-semibold text-sm">
                {getInitials(contributor.name, contributor.email)}
              </div>
              <div className="absolute -top-1 -right-1 w-5 h-5 bg-background rounded-full flex items-center justify-center text-xs font-bold text-foreground border-2 border-card">
                {index + 1}
              </div>
            </div>
            
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground truncate">
                {getDisplayName(contributor.name, contributor.email)}
              </p>
              <p className="text-xs text-muted-foreground truncate">
                {contributor.commit_count} commits
              </p>
            </div>
          </div>
        ))}
      </div>
      
      {contributors.length === 0 && (
        <div className="text-center py-8">
          <p className="text-muted-foreground text-sm">No contributors yet</p>
          <p className="text-xs text-muted-foreground mt-1">
            Ingest a Git repository to see contributors
          </p>
        </div>
      )}
    </div>
  );
}

