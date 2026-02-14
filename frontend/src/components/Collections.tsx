'use client';

import React, { useState, useEffect } from 'react';
import { Folder, Plus, Edit2, Trash2, FileText, Code2, ExternalLink, X } from 'lucide-react';

interface Collection {
  id: string;
  name: string;
  description: string | null;
  color: string;
  icon: string;
  document_count: number;
  repository_count: number;
  created_at: string;
  updated_at: string;
}

interface DocumentSummary {
  id: string;
  title: string;
  doc_type: string | null;
  created_at: string;
}

interface RepositorySummary {
  id: string;
  name: string;
  primary_language: string | null;
  created_at: string;
}

interface CollectionItems {
  documents: DocumentSummary[];
  repositories: RepositorySummary[];
}

export default function Collections() {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [selectedCollection, setSelectedCollection] = useState<Collection | null>(null);
  const [collectionItems, setCollectionItems] = useState<CollectionItems | null>(null);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchCollections();
  }, []);

  useEffect(() => {
    if (selectedCollection) {
      fetchCollectionItems(selectedCollection.id);
    }
  }, [selectedCollection]);

  const fetchCollections = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/collections/`);
      if (!res.ok) throw new Error('Failed to fetch collections');
      const data = await res.json();
      setCollections(data);
      if (data.length > 0 && !selectedCollection) {
        setSelectedCollection(data[0]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load collections');
    } finally {
      setLoading(false);
    }
  };

  const fetchCollectionItems = async (collectionId: string) => {
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/collections/${collectionId}/items`
      );
      if (!res.ok) throw new Error('Failed to fetch collection items');
      const data = await res.json();
      setCollectionItems(data);
    } catch (err) {
      console.error('Error fetching collection items:', err);
    }
  };

  const handleDeleteCollection = async (collectionId: string, collectionName: string) => {
    if (!window.confirm(`Are you sure you want to delete "${collectionName}"?`)) {
      return;
    }

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/collections/${collectionId}`,
        { method: 'DELETE' }
      );
      if (!res.ok) throw new Error('Failed to delete collection');
      
      await fetchCollections();
      if (selectedCollection?.id === collectionId) {
        setSelectedCollection(null);
        setCollectionItems(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete collection');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-muted-foreground shimmer-text">Loading collections...</div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {error && (
        <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}

      <div className="grid grid-cols-12 gap-6 flex-1 overflow-hidden">
        {/* Collections Sidebar */}
        <div className="col-span-3 flex flex-col space-y-4 overflow-hidden">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-foreground">Collections</h2>
            <button
              onClick={() => setShowCreateModal(true)}
              className="p-2 hover:bg-muted rounded-md transition-colors"
              title="Create Collection"
            >
              <Plus className="w-5 h-5 text-foreground" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto space-y-2 pr-2">
            {collections.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground text-sm">
                No collections yet. Create one to get started!
              </div>
            ) : (
              collections.map((collection) => (
                <div
                  key={collection.id}
                  onClick={() => setSelectedCollection(collection)}
                  className={`p-3 rounded-lg cursor-pointer transition-all ${
                    selectedCollection?.id === collection.id
                      ? 'bg-primary-blue/10 border border-primary-blue'
                      : 'bg-card hover:bg-card-hover border border-border'
                  }`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-2xl">{collection.icon}</span>
                    <span className="font-medium text-foreground text-sm truncate flex-1">
                      {collection.name}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <FileText className="w-3 h-3" />
                      {collection.document_count}
                    </span>
                    <span className="flex items-center gap-1">
                      <Code2 className="w-3 h-3" />
                      {collection.repository_count}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Collection Detail */}
        <div className="col-span-9 flex flex-col overflow-hidden">
          {selectedCollection ? (
            <>
              {/* Header */}
              <div className="flex items-start justify-between mb-6">
                <div>
                  <div className="flex items-center gap-3 mb-2">
                    <span className="text-4xl">{selectedCollection.icon}</span>
                    <h1 className="text-3xl font-bold text-foreground">
                      {selectedCollection.name}
                    </h1>
                  </div>
                  {selectedCollection.description && (
                    <p className="text-muted-foreground">{selectedCollection.description}</p>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <button
                    className="p-2 hover:bg-muted rounded-md transition-colors"
                    title="Edit Collection"
                  >
                    <Edit2 className="w-4 h-4 text-muted-foreground" />
                  </button>
                  <button
                    onClick={() =>
                      handleDeleteCollection(selectedCollection.id, selectedCollection.name)
                    }
                    className="p-2 hover:bg-muted rounded-md transition-colors"
                    title="Delete Collection"
                  >
                    <Trash2 className="w-4 h-4 text-red-500" />
                  </button>
                </div>
              </div>

              {/* Content */}
              <div className="flex-1 overflow-y-auto space-y-6 pr-2">
                {/* Documents */}
                <div>
                  <h2 className="text-xl font-semibold text-foreground mb-3 flex items-center gap-2">
                    <FileText className="w-5 h-5" />
                    Documents ({collectionItems?.documents.length || 0})
                  </h2>
                  {collectionItems && collectionItems.documents.length > 0 ? (
                    <div className="grid grid-cols-2 gap-3">
                      {collectionItems.documents.map((doc) => (
                        <div
                          key={doc.id}
                          className="bg-card border border-border rounded-lg p-3 hover:border-primary-blue/50 transition-colors"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-1">
                                <FileText className="w-4 h-4 text-primary-blue flex-shrink-0" />
                                <span className="font-medium text-sm truncate">{doc.title}</span>
                              </div>
                              {doc.doc_type && (
                                <span className="text-xs text-muted-foreground">
                                  {doc.doc_type}
                                </span>
                              )}
                            </div>
                            <button className="p-1 hover:bg-muted rounded">
                              <ExternalLink className="w-3.5 h-3.5 text-muted-foreground" />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8 text-muted-foreground text-sm bg-card border border-border rounded-lg">
                      No documents in this collection yet.
                    </div>
                  )}
                </div>

                {/* Repositories */}
                <div>
                  <h2 className="text-xl font-semibold text-foreground mb-3 flex items-center gap-2">
                    <Code2 className="w-5 h-5" />
                    Repositories ({collectionItems?.repositories.length || 0})
                  </h2>
                  {collectionItems && collectionItems.repositories.length > 0 ? (
                    <div className="grid grid-cols-2 gap-3">
                      {collectionItems.repositories.map((repo) => (
                        <div
                          key={repo.id}
                          className="bg-card border border-border rounded-lg p-3 hover:border-primary-blue/50 transition-colors"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-1">
                                <Code2 className="w-4 h-4 text-primary-blue flex-shrink-0" />
                                <span className="font-medium text-sm truncate">{repo.name}</span>
                              </div>
                              {repo.primary_language && (
                                <span className="text-xs text-muted-foreground">
                                  {repo.primary_language}
                                </span>
                              )}
                            </div>
                            <button className="p-1 hover:bg-muted rounded">
                              <ExternalLink className="w-3.5 h-3.5 text-muted-foreground" />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8 text-muted-foreground text-sm bg-card border border-border rounded-lg">
                      No repositories in this collection yet.
                    </div>
                  )}
                </div>
              </div>
            </>
          ) : (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              Select a collection to view details
            </div>
          )}
        </div>
      </div>

      {/* Create Collection Modal */}
      {showCreateModal && (
        <CreateCollectionModal
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => {
            setShowCreateModal(false);
            fetchCollections();
          }}
        />
      )}
    </div>
  );
}

// Create Collection Modal Component
function CreateCollectionModal({
  onClose,
  onSuccess,
}: {
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [icon, setIcon] = useState('📁');
  const [color, setColor] = useState('#3B82F6');
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');

  const commonIcons = ['📁', '🛒', '📦', '🚀', '💡', '🔧', '📊', '🎯', '⚡', '🌟'];
  const commonColors = [
    '#3B82F6', // Blue
    '#8B5CF6', // Purple
    '#EC4899', // Pink
    '#F59E0B', // Amber
    '#10B981', // Green
    '#EF4444', // Red
    '#6366F1', // Indigo
    '#14B8A6', // Teal
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Collection name is required');
      return;
    }

    setCreating(true);
    setError('');

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/collections/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name.trim(),
          description: description.trim() || null,
          icon,
          color,
        }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to create collection');
      }

      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create collection');
    } finally {
      setCreating(false);
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-card border border-border rounded-lg max-w-md w-full p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-foreground">Create Collection</h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-muted rounded transition-colors"
          >
            <X className="w-5 h-5 text-muted-foreground" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">
              Name *
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Project Alpha"
              className="w-full px-3 py-2 bg-input border border-border text-foreground rounded-md focus:outline-none focus:ring-2 focus:ring-primary-blue/20 focus:border-primary-blue"
              disabled={creating}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-foreground mb-1">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional description..."
              rows={2}
              className="w-full px-3 py-2 bg-input border border-border text-foreground rounded-md focus:outline-none focus:ring-2 focus:ring-primary-blue/20 focus:border-primary-blue resize-none"
              disabled={creating}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-foreground mb-2">Icon</label>
            <div className="grid grid-cols-5 gap-2">
              {commonIcons.map((emoji) => (
                <button
                  key={emoji}
                  type="button"
                  onClick={() => setIcon(emoji)}
                  className={`text-2xl p-2 rounded-md transition-colors ${
                    icon === emoji
                      ? 'bg-primary-blue/20 border border-primary-blue'
                      : 'bg-muted hover:bg-muted/70 border border-border'
                  }`}
                >
                  {emoji}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-foreground mb-2">Color</label>
            <div className="grid grid-cols-4 gap-2">
              {commonColors.map((c) => (
                <button
                  key={c}
                  type="button"
                  onClick={() => setColor(c)}
                  className={`h-10 rounded-md transition-all ${
                    color === c ? 'ring-2 ring-foreground ring-offset-2 ring-offset-background' : ''
                  }`}
                  style={{ backgroundColor: c }}
                />
              ))}
            </div>
          </div>

          {error && (
            <div className="text-red-400 text-sm">{error}</div>
          )}

          <div className="flex items-center gap-3 pt-2">
            <button
              type="submit"
              disabled={creating}
              className="flex-1 px-4 py-2 bg-primary-blue text-white rounded-md hover:bg-primary-blue/90 disabled:opacity-50 transition-colors"
            >
              {creating ? 'Creating...' : 'Create Collection'}
            </button>
            <button
              type="button"
              onClick={onClose}
              disabled={creating}
              className="px-4 py-2 bg-muted text-foreground rounded-md hover:bg-muted/70 disabled:opacity-50 transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

