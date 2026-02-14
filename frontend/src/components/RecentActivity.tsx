'use client';

import { useEffect, useState } from 'react';

interface Activity {
  sha: string;
  message: string;
  author: string;
  repository: string;
  date: string;
}

export default function RecentActivity() {
  const [activities, setActivities] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchActivity();
  }, []);

  const fetchActivity = async () => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/code/activity`);
      if (res.ok) {
        const data = await res.json();
        setActivities(data);
      }
    } catch (err) {
      console.error('Failed to fetch activity:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now.getTime() - date.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays <= 7) return `${diffDays} days ago`;
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const getInitials = (name: string) => {
    return name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
  };

  if (loading) {
    return (
      <div className="bg-card/50 backdrop-blur-sm border border-border/50 rounded-xl p-6">
        <div className="text-sm text-muted-foreground">Loading activity...</div>
      </div>
    );
  }

  return (
    <div className="bg-card/50 backdrop-blur-sm border border-border/50 rounded-xl p-6">
      <h3 className="text-lg font-semibold text-foreground mb-4">Recent Activity</h3>
      
      <div className="space-y-4">
        {activities.slice(0, 5).map((activity) => (
          <div key={activity.sha} className="flex items-start space-x-3">
            <div className="w-8 h-8 bg-gradient-to-br from-success-green to-primary-blue rounded-full flex items-center justify-center text-white font-semibold text-xs">
              {getInitials(activity.author)}
            </div>
            
            <div className="flex-1 min-w-0">
              <div className="flex items-center space-x-2 mb-1">
                <span className="text-sm font-medium text-foreground">
                  {activity.author}
                </span>
                <span className="text-xs text-muted-foreground">
                  {formatDate(activity.date)}
                </span>
              </div>
              
              <p className="text-sm text-muted-foreground mb-1">
                {activity.message.length > 60 
                  ? activity.message.substring(0, 60) + '...' 
                  : activity.message}
              </p>
              
              <div className="flex items-center space-x-2 text-xs text-muted-foreground">
                <span>{activity.repository}</span>
                <span>•</span>
                <span className="font-mono">{activity.sha}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
      
      {activities.length === 0 && (
        <div className="text-center py-8">
          <p className="text-muted-foreground text-sm">No recent activity</p>
          <p className="text-xs text-muted-foreground mt-1">
            Commit activity will appear here
          </p>
        </div>
      )}
    </div>
  );
}

