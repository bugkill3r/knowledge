'use client';

import { useState } from 'react';

interface BulkImportProps {
  accessToken: string;
}

interface ImportJobResult {
  job_id?: string;
  document_name: string;
  document_id: string;
  error?: string;
}

export default function BulkImport({ accessToken }: BulkImportProps) {
  const [folderUrl, setFolderUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<ImportJobResult[] | null>(null);
  const [error, setError] = useState('');
  const [totalDocs, setTotalDocs] = useState(0);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!folderUrl.trim()) {
      setError('Please enter a folder URL');
      return;
    }

    setLoading(true);
    setError('');
    setResults(null);

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/imports/google-folder`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${accessToken}`
          },
          body: JSON.stringify({
            folder_url: folderUrl,
            include_subfolders: false
          })
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Import failed');
      }

      const data = await response.json();
      setResults(data.jobs);
      setTotalDocs(data.total_documents);
      
      if (data.total_documents === 0) {
        setError('No Google Docs found in this folder');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to import folder');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
          Bulk Import from Folder
        </h2>
        <p className="text-gray-600 dark:text-gray-400">
          Import all Google Docs from a shared Drive folder at once
        </p>
      </div>

      {/* Import Form */}
      <form onSubmit={handleSubmit} className="mb-8">
        <div className="space-y-4">
          <div>
            <label 
              htmlFor="folder-url" 
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
            >
              Google Drive Folder URL
            </label>
            <input
              id="folder-url"
              type="text"
              value={folderUrl}
              onChange={(e) => setFolderUrl(e.target.value)}
              placeholder="https://drive.google.com/drive/folders/YOUR_FOLDER_ID"
              className="w-full px-4 py-3 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600
                       rounded-lg text-gray-900 dark:text-gray-100 placeholder-gray-400
                       focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={loading}
            />
            <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
              📁 Example: https://drive.google.com/drive/folders/1ABC123xyz
            </p>
          </div>

          <button
            type="submit"
            disabled={loading || !folderUrl.trim()}
            className="w-full px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg
                     disabled:opacity-50 disabled:cursor-not-allowed transition-colors
                     flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Discovering documents...
              </>
            ) : (
              <>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                        d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10" />
                </svg>
                Import All Documents
              </>
            )}
          </button>
        </div>
      </form>

      {/* Error Message */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <div className="flex items-start gap-3">
            <svg className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
          </div>
        </div>
      )}

      {/* Results */}
      {results && results.length > 0 && (
        <div>
          <div className="mb-4 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
            <div className="flex items-center gap-2">
              <svg className="w-5 h-5 text-green-600 dark:text-green-400" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              <p className="text-sm font-medium text-green-800 dark:text-green-200">
                Successfully queued {totalDocs} document{totalDocs !== 1 ? 's' : ''} for import
              </p>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
            <div className="px-6 py-4 bg-gray-50 dark:bg-gray-700 border-b border-gray-200 dark:border-gray-600">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                Import Jobs ({results.length})
              </h3>
            </div>
            
            <div className="divide-y divide-gray-200 dark:divide-gray-700 max-h-96 overflow-y-auto">
              {results.map((result, index) => (
                <div key={index} className="px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <p className="font-medium text-gray-900 dark:text-gray-100">
                        {result.document_name}
                      </p>
                      {result.job_id && (
                        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                          Job ID: {result.job_id}
                        </p>
                      )}
                      {result.error && (
                        <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                          Error: {result.error}
                        </p>
                      )}
                    </div>
                    <div className="ml-4">
                      {result.job_id ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                          Queued
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">
                          Failed
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
            <p className="text-sm text-blue-800 dark:text-blue-200">
              💡 <strong>Tip:</strong> Check the "History" tab to monitor import progress. 
              Imports may take a few minutes depending on document size and linked content.
            </p>
          </div>
        </div>
      )}

      {/* Help Section */}
      <div className="mt-8 p-6 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-3">
          How to use Bulk Import
        </h3>
        <ol className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
          <li className="flex items-start gap-2">
            <span className="font-semibold text-blue-600 dark:text-blue-400">1.</span>
            <span>Open your Google Drive folder in a browser</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="font-semibold text-blue-600 dark:text-blue-400">2.</span>
            <span>Copy the folder URL (should contain <code className="px-1 py-0.5 bg-gray-200 dark:bg-gray-700 rounded">/folders/</code>)</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="font-semibold text-blue-600 dark:text-blue-400">3.</span>
            <span>Paste the URL above and click "Import All Documents"</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="font-semibold text-blue-600 dark:text-blue-400">4.</span>
            <span>All Google Docs in the folder will be queued for import</span>
          </li>
        </ol>
      </div>
    </div>
  );
}

