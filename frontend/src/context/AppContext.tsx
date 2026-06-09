import React, { createContext, useContext, useState, useCallback, useEffect } from "react";
import { User } from "@supabase/supabase-js";
import {
  DocumentMetadata,
  DocumentStats,
  ProgressResponse,
  RevisionSuggestion,
} from "../types/types";

import {
  uploadDocument,
  listDocuments,
  deleteDocument,
  getStorageStats,
  getAccountProgress,
  getRevisionSuggestions,
} from "../api/api";
import { supabase } from "../lib/supabase";

// ================================
// Context Types
// ================================

interface AppContextType {
  user: User | null;
  authLoading: boolean;
  documents: DocumentMetadata[];
  selectedDocument: DocumentMetadata | null;
  stats: DocumentStats | null;
  progress: ProgressResponse | null;
  suggestions: RevisionSuggestion[];
  loading: boolean;
  error: string | null;

  // Actions
  fetchDocuments: () => Promise<void>;
  selectDocument: (doc: DocumentMetadata | null) => void;
  removeDocument: (documentId: string) => Promise<void>;
  uploadNewDocument: (file: File) => Promise<void>;
  fetchStats: () => Promise<void>;
  fetchProgress: () => Promise<void>;
  fetchSuggestions: () => Promise<void>;
  clearError: () => void;
  signOut: () => Promise<void>;
}

// ================================
// Create Context
// ================================

const AppContext = createContext<AppContextType | undefined>(undefined);

// ================================
// Provider Component
// ================================

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [documents, setDocuments] = useState<DocumentMetadata[]>([]);
  const [selectedDocument, setSelectedDocument] = useState<DocumentMetadata | null>(null);
  const [stats, setStats] = useState<DocumentStats | null>(null);
  const [progress, setProgress] = useState<ProgressResponse | null>(null);
  const [suggestions, setSuggestions] = useState<RevisionSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ── Auth ──────────────────────────────────────────────────────────────────

  useEffect(() => {
    // Get initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null);
      setAuthLoading(false);
    });

    // Listen for auth changes (login, logout, token refresh)
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_, session) => {
      setUser(session?.user ?? null);
    });

    return () => subscription.unsubscribe();
  }, []);

  const signOut = useCallback(async () => {
    await supabase.auth.signOut();
    setDocuments([]);
    setSelectedDocument(null);
    setStats(null);
    setProgress(null);
    setSuggestions([]);
  }, []);

  // ── Documents ─────────────────────────────────────────────────────────────

  const fetchDocuments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listDocuments();
      if (res.success) {
        setDocuments(res.documents);
      } else {
        setError(res.error || "Failed to fetch documents");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, []);

  const selectDocument = useCallback((doc: DocumentMetadata | null) => {
    setSelectedDocument(doc);
  }, []);

  const removeDocument = useCallback(async (documentId: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await deleteDocument(documentId);
      if (res.success) {
        setDocuments((prev) => prev.filter((d) => d.document_id !== documentId));
        if (selectedDocument?.document_id === documentId) {
          setSelectedDocument(null);
        }
      } else {
        setError(res.error || "Failed to delete document");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [selectedDocument]);

  const uploadNewDocument = useCallback(async (file: File) => {
    setLoading(true);
    setError(null);
    try {
      const res = await uploadDocument(file);
      if (res.success) {
        await fetchDocuments();
      } else {
        setError(res.error || "Failed to upload document");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [fetchDocuments]);

  // ── Stats / Progress ──────────────────────────────────────────────────────

  const fetchStats = useCallback(async () => {
    try {
      const res = await getStorageStats();
      if (res.success) setStats(res.stats);
    } catch (e) {
      console.error("Failed to fetch stats:", e);
    }
  }, []);

  const fetchProgress = useCallback(async () => {
    try {
      const res = await getAccountProgress();
      if (res.success) setProgress(res.progress);
    } catch (e) {
      console.error("Failed to fetch progress:", e);
    }
  }, []);

  const fetchSuggestions = useCallback(async () => {
    try {
      const res = await getRevisionSuggestions();
      if (res.success) setSuggestions(res.suggestions);
    } catch (e) {
      console.error("Failed to fetch suggestions:", e);
    }
  }, []);

  const clearError = useCallback(() => setError(null), []);

  // ── Value ─────────────────────────────────────────────────────────────────

  const value: AppContextType = {
    user,
    authLoading,
    documents,
    selectedDocument,
    stats,
    progress,
    suggestions,
    loading,
    error,
    fetchDocuments,
    selectDocument,
    removeDocument,
    uploadNewDocument,
    fetchStats,
    fetchProgress,
    fetchSuggestions,
    clearError,
    signOut,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
};

// ================================
// Hook to use context
// ================================

export const useApp = () => {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error("useApp must be used within an AppProvider");
  }
  return context;
};

export default AppContext;