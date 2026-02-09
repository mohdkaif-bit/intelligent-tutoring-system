import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Loader } from "../components/common/Common";
import { DocumentMetadata } from "../types/types";

// Import the real API functions
import { 
  uploadDocument as apiUploadDocument, 
  listDocuments as apiListDocuments,
  getAccountProgress,
} from "../api/api";

const Home: React.FC = () => {
  const navigate = useNavigate();
  const [documents, setDocuments] = useState<DocumentMetadata[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [progressStats, setProgressStats] = useState<any>(null);

  useEffect(() => {
    loadDocuments();
    loadProgress();
  }, []);

  // Refresh progress when window regains focus (user returns from reader)
  useEffect(() => {
    const handleFocus = () => {
      console.log("Window focused - refreshing progress");
      loadProgress();
    };
    
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        console.log("Page became visible - refreshing progress");
        loadProgress();
      }
    };
    
    window.addEventListener('focus', handleFocus);
    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    return () => {
      window.removeEventListener('focus', handleFocus);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, []);

  const loadDocuments = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiListDocuments();
      if (res.success) {
        setDocuments(res.documents);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load documents");
    } finally {
      setLoading(false);
    }
  };

  const loadProgress = async () => {
    try {
      console.log("Loading progress stats...");
      const res = await getAccountProgress();
      // The API returns the progress data directly, not wrapped in success/progress
      console.log("Progress loaded:", res);
      setProgressStats(res);
    } catch (e) {
      console.error("Failed to load progress:", e);
    }
  };

  const handleFileUpload = async (file: File) => {
    if (!file.type.includes("pdf")) {
      setError("Please upload a PDF file");
      return;
    }

    setUploading(true);
    setError(null);
    try {
      const res = await apiUploadDocument(file);
      if (res.success) {
        await loadDocuments();
        // Refresh progress after upload
        await loadProgress();
        navigate(`/reader/${res.document.document_id}`, {
          state: { 
            totalPages: res.document.page_count
          }
        });
      } else {
        setError("Failed to upload document");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFileUpload(file);
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const file = e.dataTransfer.files?.[0];
    if (file) {
      handleFileUpload(file);
    }
  };

  const handleDocumentClick = (doc: DocumentMetadata) => {
    navigate(`/reader/${doc.document_id}`, {
      state: { 
        totalPages: doc.page_count
      }
    });
  };

  const formatStudyTime = (minutes: number) => {
    if (minutes === 0) return "0 min";
    if (minutes < 60) return `${minutes} min`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
  };

  return (
    <div style={styles.container}>
      {/* Header */}
      <header style={styles.header}>
        <div style={styles.headerContent}>
          <h1 style={styles.logo}>📚 Personalized Learning Buddy</h1>
          <p style={styles.tagline}>Personalized Learning, Powered by Pedagogy-Aware AI</p>
        </div>
      </header>

      {/* Main Layout - 3 columns */}
      <div style={styles.mainLayout}>
        {/* Left Sidebar - Progress & Stats */}
        <aside style={styles.leftSidebar}>
          <div style={styles.sidebarHeader}>
            <h3 style={styles.sidebarTitle}>📊 Your Progress</h3>
          </div>

          <div style={styles.progressContent}>
            {/* Study Time */}
            <div style={styles.statCard}>
              <div style={styles.statIcon}>⏱️</div>
              <div style={styles.statInfo}>
                <div style={styles.statValue}>
                  {progressStats ? formatStudyTime(progressStats.study_time_minutes) : '0 min'}
                </div>
                <div style={styles.statLabel}>Study Time</div>
              </div>
            </div>

            {/* Pages Viewed */}
            <div style={styles.statCard}>
              <div style={styles.statIcon}>📖</div>
              <div style={styles.statInfo}>
                <div style={styles.statValue}>
                  {progressStats?.total_pages_viewed || 0}
                </div>
                <div style={styles.statLabel}>Pages Viewed</div>
              </div>
            </div>

            {/* Questions Asked */}
            <div style={styles.statCard}>
              <div style={styles.statIcon}>💬</div>
              <div style={styles.statInfo}>
                <div style={styles.statValue}>
                  {progressStats?.total_questions_asked || 0}
                </div>
                <div style={styles.statLabel}>Questions Asked</div>
              </div>
            </div>

            {/* Quizzes Completed */}
            <div style={styles.statCard}>
              <div style={styles.statIcon}>📝</div>
              <div style={styles.statInfo}>
                <div style={styles.statValue}>
                  {progressStats?.total_quizzes_completed || 0}
                </div>
                <div style={styles.statLabel}>Quizzes Completed</div>
              </div>
            </div>

            {/* Average Quiz Score */}
            <div style={{...styles.statCard, ...styles.highlightCard}}>
              <div style={styles.statIcon}>🎯</div>
              <div style={styles.statInfo}>
                <div style={styles.statValue}>
                  {progressStats?.average_quiz_score 
                    ? `${Math.round(progressStats.average_quiz_score)}%`
                    : 'N/A'}
                </div>
                <div style={styles.statLabel}>Avg Quiz Score</div>
              </div>
            </div>

            {/* Documents Count */}
            <div style={styles.statCard}>
              <div style={styles.statIcon}>📚</div>
              <div style={styles.statInfo}>
                <div style={styles.statValue}>{documents.length}</div>
                <div style={styles.statLabel}>Total Documents</div>
              </div>
            </div>

            {/* Additional Progress Details */}
            {progressStats && (
              <>
                <div style={styles.progressDivider} />
                
                <div style={styles.progressDetail}>
                  <span style={styles.progressDetailLabel}>Total Pages</span>
                  <span style={styles.progressDetailValue}>
                    {progressStats.total_pages_uploaded || 0}
                  </span>
                </div>

                <div style={styles.progressDetail}>
                  <span style={styles.progressDetailLabel}>Pages with Engagement</span>
                  <span style={styles.progressDetailValue}>
                    {progressStats.pages_with_engagement || 0}
                  </span>
                </div>

                <div style={styles.progressDetail}>
                  <span style={styles.progressDetailLabel}>Pages Needing Attention</span>
                  <span style={{
                    ...styles.progressDetailValue,
                    color: progressStats.pages_needing_attention > 0 ? '#ff6b6b' : 'var(--color-success)'
                  }}>
                    {progressStats.pages_needing_attention || 0}
                  </span>
                </div>

                <div style={styles.progressDetail}>
                  <span style={styles.progressDetailLabel}>Completion Rate</span>
                  <span style={styles.progressDetailValue}>
                    {Math.round((progressStats.completion_rate || 0) * 100)}%
                  </span>
                </div>

                <div style={styles.progressDetail}>
                  <span style={styles.progressDetailLabel}>Engagement Rate</span>
                  <span style={styles.progressDetailValue}>
                    {Math.round((progressStats.engagement_rate || 0) * 100)}%
                  </span>
                </div>
              </>
            )}
          </div>
        </aside>

        {/* Center Content - Upload & Features */}
        <main style={styles.centerContent}>
          {/* Upload Section */}
          <section style={styles.uploadSection}>
            <div
              style={{
                ...styles.dropzone,
                ...(dragActive ? styles.dropzoneActive : {}),
              }}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
            >
              {uploading ? (
                <div style={styles.uploadingState}>
                  <Loader size={40} />
                  <p style={styles.uploadingText}>Uploading document...</p>
                </div>
              ) : (
                <>
                  <div style={styles.uploadIcon}>📄</div>
                  <h2 style={styles.uploadTitle}>Upload a PDF Document</h2>
                  <p style={styles.uploadText}>
                    Drag and drop your PDF here, or click to browse
                  </p>
                  
                  <input
                    id="file-upload"
                    type="file"
                    accept=".pdf"
                    onChange={handleFileSelect}
                    style={{ display: "none" }}
                  />
                  <label htmlFor="file-upload">
                    <span style={styles.uploadButton}>Choose File</span>
                  </label>
                </>
              )}
            </div>

            {error && (
              <div style={styles.error}>
                <span style={styles.errorIcon}>⚠️</span>
                {error}
              </div>
            )}
          </section>

          {/* Features Section */}
          <section style={styles.features}>
            <h3 style={styles.featuresTitle}>Features</h3>
            <div style={styles.featureGrid}>
              <FeatureCard
                icon="💬"
                title="AI Chat"
                description="Ask questions about your document and get instant answers"
              />
              <FeatureCard
                icon="📝"
                title="Quiz Generation"
                description="Generate practice quizzes to test your understanding"
              />
              <FeatureCard
                icon="⚡"
                title="Smart Caching"
                description="Embeddings cached for instant access - no re-processing needed"
              />
              <FeatureCard
                icon="📊"
                title="Progress Tracking"
                description="Monitor your learning progress and quiz scores"
              />
            </div>
          </section>
        </main>

        {/* Right Sidebar - Documents List */}
        <aside style={styles.rightSidebar}>
          <div style={styles.sidebarHeader}>
            <h3 style={styles.sidebarTitle}>Recent Documents</h3>
            <span style={styles.documentCount}>{documents.length}</span>
          </div>

          <div style={styles.documentsList}>
            {loading ? (
              <div style={styles.loadingDocuments}>
                <Loader size={24} />
              </div>
            ) : documents.length === 0 ? (
              <div style={styles.emptyState}>
                <div style={styles.emptyIcon}>📄</div>
                <p style={styles.emptyText}>No documents yet</p>
                <p style={styles.emptySubtext}>Upload a PDF to get started</p>
              </div>
            ) : (
              documents.map((doc) => (
                <DocumentCard
                  key={doc.document_id}
                  document={doc}
                  onClick={() => handleDocumentClick(doc)}
                />
              ))
            )}
          </div>
        </aside>
      </div>
    </div>
  );
};

const FeatureCard: React.FC<{
  icon: string;
  title: string;
  description: string;
}> = ({ icon, title, description }) => (
  <div style={styles.featureCard}>
    <div style={styles.featureIcon}>{icon}</div>
    <h4 style={styles.featureCardTitle}>{title}</h4>
    <p style={styles.featureCardDesc}>{description}</p>
  </div>
);

const DocumentCard: React.FC<{
  document: DocumentMetadata;
  onClick: () => void;
}> = ({ document, onClick }) => (
  <div style={styles.documentCard} onClick={onClick}>
    <div style={styles.documentIcon}>📄</div>
    <div style={styles.documentInfo}>
      <h4 style={styles.documentTitle}>{document.original_filename}</h4>
      <div style={styles.documentMeta}>
        <span>{document.page_count} pages</span>
        {document.embeddings_cached && (
          <span style={styles.cachedBadge}>⚡</span>
        )}
      </div>
      <p style={styles.documentDate}>
        {new Date(document.upload_timestamp).toLocaleDateString()}
      </p>
    </div>
  </div>
);

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: "100vh",
    background: "var(--color-bg)",
    display: "flex",
    flexDirection: "column",
  },
  header: {
    background: "var(--color-surface)",
    borderBottom: "1px solid var(--color-border)",
    padding: "24px 32px",
  },
  headerContent: {
    maxWidth: 1600,
    margin: "0 auto",
  },
  logo: {
    fontSize: 28,
    fontWeight: 700,
    color: "var(--color-text)",
    margin: "0 0 8px 0",
  },
  tagline: {
    fontSize: 14,
    color: "var(--color-text-muted)",
    margin: 0,
  },
  mainLayout: {
    display: "flex",
    flex: 1,
    maxWidth: 1600,
    margin: "0 auto",
    width: "100%",
    padding: "40px 32px",
    gap: 24,
  },
  leftSidebar: {
    width: 280,
    background: "var(--color-surface)",
    borderRadius: "var(--radius)",
    border: "1px solid var(--color-border)",
    display: "flex",
    flexDirection: "column",
    maxHeight: "calc(100vh - 180px)",
    position: "sticky",
    top: 40,
  },
  centerContent: {
    flex: 1,
    minWidth: 0,
  },
  rightSidebar: {
    width: 320,
    background: "var(--color-surface)",
    borderRadius: "var(--radius)",
    border: "1px solid var(--color-border)",
    display: "flex",
    flexDirection: "column",
    maxHeight: "calc(100vh - 180px)",
    position: "sticky",
    top: 40,
  },
  sidebarHeader: {
    padding: "20px 24px",
    borderBottom: "1px solid var(--color-border)",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  sidebarTitle: {
    fontSize: 16,
    fontWeight: 700,
    color: "var(--color-text)",
    margin: 0,
  },
  documentCount: {
    background: "rgba(108, 99, 255, 0.15)",
    color: "#6366f1",
    padding: "4px 12px",
    borderRadius: "12px",
    fontSize: 13,
    fontWeight: 600,
  },
  progressContent: {
    flex: 1,
    overflowY: "auto",
    padding: "16px",
  },
  statCard: {
    background: "var(--color-bg)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius)",
    padding: "16px",
    marginBottom: "12px",
    display: "flex",
    alignItems: "center",
    gap: 12,
    transition: "all 0.2s",
  },
  highlightCard: {
    background: "linear-gradient(135deg, rgba(108, 99, 255, 0.1), rgba(139, 92, 246, 0.1))",
    border: "1px solid rgba(108, 99, 255, 0.3)",
  },
  statIcon: {
    fontSize: 28,
    flexShrink: 0,
  },
  statInfo: {
    flex: 1,
  },
  statValue: {
    fontSize: 24,
    fontWeight: 700,
    color: "var(--color-text)",
    lineHeight: 1.2,
  },
  statLabel: {
    fontSize: 11,
    color: "var(--color-text-muted)",
    textTransform: "uppercase",
    letterSpacing: "0.5px",
    marginTop: 2,
  },
  progressDivider: {
    height: 1,
    background: "var(--color-border)",
    margin: "16px 0",
  },
  progressDetail: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "10px 0",
    fontSize: 13,
  },
  progressDetailLabel: {
    color: "var(--color-text-muted)",
  },
  progressDetailValue: {
    fontWeight: 600,
    color: "var(--color-text)",
  },
  documentsList: {
    flex: 1,
    overflowY: "auto",
    padding: "12px",
  },
  uploadSection: {
    marginBottom: 48,
  },
  dropzone: {
    background: "var(--color-surface)",
    border: "2px dashed var(--color-border)",
    borderRadius: "var(--radius)",
    padding: "60px 40px",
    textAlign: "center",
    transition: "all 0.3s",
    cursor: "pointer",
  },
  dropzoneActive: {
    borderColor: "var(--color-primary)",
    background: "rgba(108, 99, 255, 0.05)",
  },
  uploadIcon: {
    fontSize: 64,
    marginBottom: 16,
  },
  uploadTitle: {
    fontSize: 24,
    fontWeight: 700,
    color: "var(--color-text)",
    margin: "0 0 12px 0",
  },
  uploadText: {
    fontSize: 14,
    color: "var(--color-text-muted)",
    margin: "0 0 24px 0",
  },
  uploadButton: {
    display: "inline-block",
    background: "#6366f1",
    color: "white",
    padding: "12px 32px",
    borderRadius: "8px",
    fontSize: 15,
    fontWeight: 600,
    cursor: "pointer",
    transition: "all 0.2s",
    border: "none",
  },
  uploadingState: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 16,
  },
  uploadingText: {
    fontSize: 14,
    color: "var(--color-text-muted)",
  },
  error: {
    marginTop: 16,
    padding: "12px 16px",
    background: "rgba(255, 85, 85, 0.1)",
    border: "1px solid var(--color-danger)",
    borderRadius: "var(--radius)",
    color: "#ff8888",
    fontSize: 14,
    display: "flex",
    alignItems: "center",
    gap: 8,
  },
  errorIcon: {
    fontSize: 18,
  },
  features: {
    marginBottom: 48,
  },
  featuresTitle: {
    fontSize: 20,
    fontWeight: 700,
    color: "var(--color-text)",
    margin: "0 0 24px 0",
  },
  featureGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(2, 1fr)",
    gap: 20,
  },
  featureCard: {
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius)",
    padding: 24,
    textAlign: "center",
  },
  featureIcon: {
    fontSize: 40,
    marginBottom: 12,
  },
  featureCardTitle: {
    fontSize: 16,
    fontWeight: 600,
    color: "var(--color-text)",
    margin: "0 0 8px 0",
  },
  featureCardDesc: {
    fontSize: 13,
    color: "var(--color-text-muted)",
    margin: 0,
    lineHeight: 1.6,
  },
  documentCard: {
    background: "var(--color-bg)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius)",
    padding: "16px",
    marginBottom: "8px",
    display: "flex",
    alignItems: "flex-start",
    gap: 12,
    cursor: "pointer",
    transition: "all 0.2s",
  },
  documentIcon: {
    fontSize: 28,
    flexShrink: 0,
    marginTop: 4,
  },
  documentInfo: {
    flex: 1,
    minWidth: 0,
  },
  documentTitle: {
    fontSize: 14,
    fontWeight: 600,
    color: "var(--color-text)",
    margin: "0 0 6px 0",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  documentMeta: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    fontSize: 12,
    color: "var(--color-text-muted)",
    marginBottom: 4,
  },
  cachedBadge: {
    fontSize: 14,
  },
  documentDate: {
    fontSize: 11,
    color: "var(--color-text-muted)",
    margin: 0,
  },
  loadingDocuments: {
    display: "flex",
    justifyContent: "center",
    padding: 40,
  },
  emptyState: {
    textAlign: "center",
    padding: "60px 20px",
  },
  emptyIcon: {
    fontSize: 48,
    marginBottom: 16,
    opacity: 0.5,
  },
  emptyText: {
    fontSize: 14,
    fontWeight: 600,
    color: "var(--color-text)",
    margin: "0 0 4px 0",
  },
  emptySubtext: {
    fontSize: 12,
    color: "var(--color-text-muted)",
    margin: 0,
  },
};

export default Home;