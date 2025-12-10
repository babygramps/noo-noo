'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { clsx } from 'clsx';
import {
  Download,
  FileSpreadsheet,
  FileJson,
  Trash2,
  Search,
  X,
  Calendar,
  User,
  Beaker,
  HardDrive,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  FolderOpen,
  AlertCircle,
  CheckCircle,
  Info,
} from 'lucide-react';
import * as api from '@/lib/api';
import type { TestDataFile } from '@/lib/api';

interface TestDataBrowserProps {
  isOpen: boolean;
  onClose: () => void;
}

type SortField = 'date' | 'name' | 'size';
type SortDirection = 'asc' | 'desc';

export function TestDataBrowser({ isOpen, onClose }: TestDataBrowserProps) {
  const [files, setFiles] = useState<TestDataFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortField, setSortField] = useState<SortField>('date');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [expandedFile, setExpandedFile] = useState<string | null>(null);
  const [metadata, setMetadata] = useState<Record<string, unknown> | null>(null);
  const [loadingMetadata, setLoadingMetadata] = useState(false);
  const [deletingFile, setDeletingFile] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Fetch files list
  const loadFiles = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listTestData();
      setFiles(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load test data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isOpen) {
      loadFiles();
      setSearchQuery('');
      setExpandedFile(null);
      setMetadata(null);
      setConfirmDelete(null);
    }
  }, [isOpen, loadFiles]);

  // Load metadata when expanding a file
  const handleFileExpand = useCallback(async (filename: string) => {
    if (expandedFile === filename) {
      setExpandedFile(null);
      setMetadata(null);
      return;
    }

    setExpandedFile(filename);
    setMetadata(null);
    setLoadingMetadata(true);

    try {
      const meta = await api.getTestMetadata(filename);
      setMetadata(meta);
    } catch {
      // Metadata might not exist, that's okay
      setMetadata(null);
    } finally {
      setLoadingMetadata(false);
    }
  }, [expandedFile]);

  // Handle download
  const handleDownload = useCallback((filename: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    const url = api.getTestDataDownloadUrl(filename);
    
    // Create a temporary link and trigger download
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }, []);

  // Handle delete
  const handleDelete = useCallback(async (filename: string) => {
    setDeletingFile(filename);
    try {
      await api.deleteTestData(filename);
      setFiles(prev => prev.filter(f => f.filename !== filename));
      setConfirmDelete(null);
      setSuccessMessage(`Deleted ${filename}`);
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete file');
    } finally {
      setDeletingFile(null);
    }
  }, []);

  // Sort and filter files
  const filteredFiles = useMemo(() => {
    let result = [...files];

    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      result = result.filter(file =>
        file.filename.toLowerCase().includes(query) ||
        file.test_name?.toLowerCase().includes(query) ||
        file.operator?.toLowerCase().includes(query) ||
        file.sequence_name?.toLowerCase().includes(query) ||
        file.test_id?.toLowerCase().includes(query)
      );
    }

    // Sort
    result.sort((a, b) => {
      let comparison = 0;
      switch (sortField) {
        case 'date':
          comparison = a.modified_timestamp - b.modified_timestamp;
          break;
        case 'name':
          comparison = a.filename.localeCompare(b.filename);
          break;
        case 'size':
          comparison = a.size_bytes - b.size_bytes;
          break;
      }
      return sortDirection === 'asc' ? comparison : -comparison;
    });

    return result;
  }, [files, searchQuery, sortField, sortDirection]);

  // Toggle sort
  const toggleSort = useCallback((field: SortField) => {
    if (sortField === field) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  }, [sortField]);

  // Format date for display
  const formatDate = useCallback((isoString: string) => {
    const date = new Date(isoString);
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  }, []);

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm animate-fade-in"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="fixed inset-4 md:inset-8 lg:inset-12 z-50 flex items-center justify-center">
        <div 
          className="relative w-full max-w-4xl max-h-full bg-panel-surface rounded-2xl border border-panel-border shadow-2xl overflow-hidden animate-slide-up flex flex-col"
          onClick={e => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-5 border-b border-panel-border bg-gradient-to-r from-panel-surface to-panel-bg">
            <div className="flex items-center gap-4">
              <div className="flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-br from-cyan-500/20 to-teal-500/20 border border-cyan-500/30">
                <HardDrive className="w-6 h-6 text-cyan-400" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-slate-100">Test Data Library</h2>
                <p className="text-sm text-slate-500">
                  {files.length} test{files.length !== 1 ? 's' : ''} recorded
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="flex items-center justify-center w-10 h-10 rounded-xl text-slate-400 hover:text-slate-200 hover:bg-slate-700/50 transition-all"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Search and Sort Bar */}
          <div className="px-6 py-4 border-b border-panel-border/50 bg-panel-bg/30">
            <div className="flex flex-col sm:flex-row gap-4">
              {/* Search */}
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  type="text"
                  placeholder="Search by name, operator, sequence..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="form-input pl-10 pr-10 w-full"
                />
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery('')}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>

              {/* Sort buttons */}
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500 uppercase tracking-wider mr-2">Sort by</span>
                {(['date', 'name', 'size'] as const).map((field) => (
                  <button
                    key={field}
                    onClick={() => toggleSort(field)}
                    className={clsx(
                      'px-3 py-2 rounded-lg text-sm font-medium transition-all',
                      sortField === field
                        ? 'bg-teal-500/20 text-teal-300 border border-teal-500/40'
                        : 'bg-slate-800/50 text-slate-400 border border-slate-700 hover:border-slate-600'
                    )}
                  >
                    {field.charAt(0).toUpperCase() + field.slice(1)}
                    {sortField === field && (
                      <span className="ml-1 text-xs">{sortDirection === 'asc' ? '↑' : '↓'}</span>
                    )}
                  </button>
                ))}
                
                {/* Refresh button */}
                <button
                  onClick={loadFiles}
                  disabled={loading}
                  className="ml-2 p-2 rounded-lg bg-slate-800/50 text-slate-400 border border-slate-700 hover:border-slate-600 hover:text-slate-300 transition-all disabled:opacity-50"
                >
                  <RefreshCw className={clsx('w-4 h-4', loading && 'animate-spin')} />
                </button>
              </div>
            </div>
          </div>

          {/* Success Message */}
          {successMessage && (
            <div className="mx-6 mt-4 flex items-center gap-3 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 animate-fade-in">
              <CheckCircle className="w-5 h-5 text-emerald-400 flex-shrink-0" />
              <p className="text-sm text-emerald-300">{successMessage}</p>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="mx-6 mt-4 flex items-center gap-3 p-3 rounded-xl bg-red-500/10 border border-red-500/30">
              <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
              <p className="text-sm text-red-300">{error}</p>
              <button
                onClick={() => setError(null)}
                className="ml-auto text-red-400 hover:text-red-300"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* File List */}
          <div className="flex-1 overflow-y-auto p-6">
            {loading ? (
              <div className="flex flex-col items-center justify-center py-16">
                <RefreshCw className="w-10 h-10 text-teal-500 animate-spin mb-4" />
                <p className="text-slate-400">Loading test data...</p>
              </div>
            ) : filteredFiles.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16">
                <div className="flex items-center justify-center w-20 h-20 rounded-2xl bg-slate-800/50 border border-slate-700 mb-6">
                  <FolderOpen className="w-10 h-10 text-slate-600" />
                </div>
                <h3 className="text-lg font-medium text-slate-300 mb-2">
                  {searchQuery ? 'No matching files' : 'No test data yet'}
                </h3>
                <p className="text-sm text-slate-500 text-center max-w-xs">
                  {searchQuery
                    ? 'Try adjusting your search terms or clearing the filter'
                    : 'Run your first test sequence to generate data files that will appear here'}
                </p>
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery('')}
                    className="mt-4 px-4 py-2 rounded-lg bg-slate-700/50 text-slate-300 hover:bg-slate-700 transition-all"
                  >
                    Clear search
                  </button>
                )}
              </div>
            ) : (
              <div className="space-y-3">
                {filteredFiles.map((file) => (
                  <div
                    key={file.filename}
                    className={clsx(
                      'rounded-xl border transition-all duration-200',
                      expandedFile === file.filename
                        ? 'bg-slate-800/80 border-teal-500/40'
                        : 'bg-panel-bg/50 border-panel-border/50 hover:border-slate-600'
                    )}
                  >
                    {/* File row */}
                    <div
                      className="flex items-center gap-4 p-4 cursor-pointer"
                      onClick={() => handleFileExpand(file.filename)}
                    >
                      {/* Expand indicator */}
                      <div className="text-slate-500">
                        {expandedFile === file.filename ? (
                          <ChevronDown className="w-5 h-5" />
                        ) : (
                          <ChevronRight className="w-5 h-5" />
                        )}
                      </div>

                      {/* File icon */}
                      <div className={clsx(
                        'flex items-center justify-center w-10 h-10 rounded-lg',
                        file.file_type === 'csv'
                          ? 'bg-emerald-500/15 text-emerald-400'
                          : 'bg-amber-500/15 text-amber-400'
                      )}>
                        {file.file_type === 'csv' ? (
                          <FileSpreadsheet className="w-5 h-5" />
                        ) : (
                          <FileJson className="w-5 h-5" />
                        )}
                      </div>

                      {/* File info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <h4 className="font-medium text-slate-200 truncate">
                            {file.test_name || file.filename}
                          </h4>
                          {file.has_metadata && (
                            <span className="badge badge-info text-[10px]">
                              Metadata
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-4 mt-1">
                          <span className="text-xs text-slate-500 font-mono">
                            {file.filename}
                          </span>
                          {file.operator && (
                            <span className="text-xs text-slate-500 flex items-center gap-1">
                              <User className="w-3 h-3" />
                              {file.operator}
                            </span>
                          )}
                        </div>
                      </div>

                      {/* File metadata */}
                      <div className="hidden md:flex items-center gap-6 text-sm text-slate-400">
                        <div className="flex items-center gap-1.5">
                          <Calendar className="w-4 h-4 text-slate-500" />
                          <span>{formatDate(file.modified_time)}</span>
                        </div>
                        <div className="w-20 text-right font-mono text-xs">
                          {file.size_formatted}
                        </div>
                      </div>

                      {/* Actions */}
                      <div className="flex items-center gap-2">
                        <button
                          onClick={(e) => handleDownload(file.filename, e)}
                          className="flex items-center justify-center w-9 h-9 rounded-lg bg-teal-500/15 text-teal-400 border border-teal-500/30 hover:bg-teal-500/25 hover:border-teal-500/50 transition-all"
                          title="Download"
                        >
                          <Download className="w-4 h-4" />
                        </button>
                        
                        {confirmDelete === file.filename ? (
                          <div className="flex items-center gap-1">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDelete(file.filename);
                              }}
                              disabled={deletingFile === file.filename}
                              className="flex items-center justify-center w-9 h-9 rounded-lg bg-red-500/20 text-red-400 border border-red-500/40 hover:bg-red-500/30 transition-all"
                              title="Confirm delete"
                            >
                              {deletingFile === file.filename ? (
                                <RefreshCw className="w-4 h-4 animate-spin" />
                              ) : (
                                <CheckCircle className="w-4 h-4" />
                              )}
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setConfirmDelete(null);
                              }}
                              className="flex items-center justify-center w-9 h-9 rounded-lg bg-slate-700/50 text-slate-400 border border-slate-600 hover:bg-slate-700 transition-all"
                              title="Cancel"
                            >
                              <X className="w-4 h-4" />
                            </button>
                          </div>
                        ) : (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setConfirmDelete(file.filename);
                            }}
                            className="flex items-center justify-center w-9 h-9 rounded-lg bg-slate-700/30 text-slate-500 border border-slate-700 hover:bg-red-500/15 hover:text-red-400 hover:border-red-500/30 transition-all"
                            title="Delete"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Expanded metadata section */}
                    {expandedFile === file.filename && (
                      <div className="px-4 pb-4 pt-2 border-t border-panel-border/30">
                        <div className="pl-9">
                          {loadingMetadata ? (
                            <div className="flex items-center gap-2 text-slate-500 py-4">
                              <RefreshCw className="w-4 h-4 animate-spin" />
                              <span className="text-sm">Loading metadata...</span>
                            </div>
                          ) : metadata ? (
                            <div className="space-y-4">
                              {/* Quick info cards */}
                              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                                {file.sequence_name && (
                                  <InfoCard
                                    icon={<Beaker className="w-4 h-4" />}
                                    label="Sequence"
                                    value={file.sequence_name}
                                    color="teal"
                                  />
                                )}
                                {file.test_id && (
                                  <InfoCard
                                    icon={<Info className="w-4 h-4" />}
                                    label="Test ID"
                                    value={file.test_id}
                                    color="blue"
                                  />
                                )}
                                {file.operator && (
                                  <InfoCard
                                    icon={<User className="w-4 h-4" />}
                                    label="Operator"
                                    value={file.operator}
                                    color="purple"
                                  />
                                )}
                                <InfoCard
                                  icon={<HardDrive className="w-4 h-4" />}
                                  label="Size"
                                  value={file.size_formatted}
                                  color="slate"
                                />
                              </div>

                              {/* Full metadata */}
                              <div className="mt-4">
                                <details className="group">
                                  <summary className="cursor-pointer text-xs text-slate-500 uppercase tracking-wider hover:text-slate-400 transition-colors flex items-center gap-1">
                                    <ChevronRight className="w-3 h-3 group-open:rotate-90 transition-transform" />
                                    View full metadata
                                  </summary>
                                  <div className="mt-3 p-4 rounded-lg bg-lcd-bg border border-panel-border/30 font-mono text-xs overflow-x-auto">
                                    <pre className="text-slate-400 whitespace-pre-wrap">
                                      {JSON.stringify(metadata, null, 2)}
                                    </pre>
                                  </div>
                                </details>
                              </div>

                              {/* Download buttons */}
                              <div className="flex items-center gap-3 pt-2">
                                <button
                                  onClick={() => handleDownload(file.filename)}
                                  className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-teal-500/15 text-teal-300 border border-teal-500/40 hover:bg-teal-500/25 hover:border-teal-500/60 transition-all font-medium text-sm"
                                >
                                  <Download className="w-4 h-4" />
                                  Download {file.file_type.toUpperCase()}
                                </button>
                                {file.has_metadata && file.file_type === 'csv' && (
                                  <button
                                    onClick={() => handleDownload(file.filename.replace('.csv', '.json'))}
                                    className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-amber-500/15 text-amber-300 border border-amber-500/40 hover:bg-amber-500/25 hover:border-amber-500/60 transition-all font-medium text-sm"
                                  >
                                    <FileJson className="w-4 h-4" />
                                    Download Metadata
                                  </button>
                                )}
                              </div>
                            </div>
                          ) : (
                            <div className="flex items-center gap-3 text-slate-500 py-4">
                              <Info className="w-4 h-4" />
                              <span className="text-sm">No metadata available for this file</span>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="px-6 py-4 border-t border-panel-border bg-panel-bg/50 flex items-center justify-between">
            <div className="text-xs text-slate-500">
              {filteredFiles.length} of {files.length} file{files.length !== 1 ? 's' : ''}
              {searchQuery && ' (filtered)'}
            </div>
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg bg-slate-700/50 text-slate-300 hover:bg-slate-700 transition-all font-medium text-sm"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

// Info card subcomponent
interface InfoCardProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  color: 'teal' | 'blue' | 'purple' | 'slate' | 'amber';
}

function InfoCard({ icon, label, value, color }: InfoCardProps) {
  const colorClasses = {
    teal: 'bg-teal-500/10 border-teal-500/30 text-teal-400',
    blue: 'bg-blue-500/10 border-blue-500/30 text-blue-400',
    purple: 'bg-purple-500/10 border-purple-500/30 text-purple-400',
    slate: 'bg-slate-500/10 border-slate-500/30 text-slate-400',
    amber: 'bg-amber-500/10 border-amber-500/30 text-amber-400',
  };

  return (
    <div className={clsx('rounded-lg p-3 border', colorClasses[color])}>
      <div className="flex items-center gap-2 text-xs opacity-70 mb-1">
        {icon}
        <span className="uppercase tracking-wider">{label}</span>
      </div>
      <div className="text-sm font-medium text-slate-200 truncate">{value}</div>
    </div>
  );
}

export default TestDataBrowser;

