import { useState, useEffect, useCallback } from "react";
import { getPageRender, updateProgress, getDocumentQuizStats, getDocumentRevisionStats } from "../../api/api";
import { Loader } from "../common/Common";
import { DocumentQuizStatsResponse, DocumentRevisionStatsResponse } from "../../types/types";

interface PDFViewerProps {
  documentId: string;
  totalPages: number;
  onPageChange?: (page: number) => void;
}

const PDFViewer = ({ documentId, totalPages, onPageChange }: PDFViewerProps) => {
  const [currentPage, setCurrentPage] = useState(1);
  const [base64Image, setBase64Image] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pagesViewed, setPagesViewed] = useState<Set<number>>(new Set([1]));
  
  // New state for stats
  const [quizStats, setQuizStats] = useState<DocumentQuizStatsResponse | null>(null);
  const [revisionStats, setRevisionStats] = useState<DocumentRevisionStatsResponse | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);

  // Load quiz and revision stats
  useEffect(() => {
    const loadStats = async () => {
      setStatsLoading(true);
      try {
        const [quizData, revisionData] = await Promise.all([
          getDocumentQuizStats(documentId).catch(() => null),
          getDocumentRevisionStats(documentId).catch(() => null),
        ]);
        
        if (quizData?.success) setQuizStats(quizData);
        if (revisionData?.success) setRevisionStats(revisionData);
      } catch (err) {
        console.error("Failed to load stats:", err);
      } finally {
        setStatsLoading(false);
      }
    };

    loadStats();
  }, [documentId]);

  // Load page whenever currentPage changes
  useEffect(() => {
    let cancelled = false;

    const loadPage = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const renderRes = await getPageRender(documentId, currentPage);

        if (!cancelled) {
          if (renderRes.success) {
            setBase64Image(renderRes.base64_pdf);
            
            // Mark page as viewed
            setPagesViewed(prev => new Set([...prev, currentPage]));
          } else {
            throw new Error(renderRes.error || "Failed to render page");
          }
        }

        // ✅ FIXED: Track progress with proper payload including interaction_type
        updateProgress({
          document_id: documentId,
          page_number: currentPage,
          interaction_type: "page_view",  // ← REQUIRED FIELD
          time_spent: 0,
          metadata: {
            timestamp: new Date().toISOString(),
          },
        }).catch((err) => console.warn("Failed to track progress:", err));
      } catch (e) {
        if (!cancelled) {
          const errorMessage = e instanceof Error ? e.message : "Failed to load page";
          setError(errorMessage);
          console.error("Failed to load page:", e);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    loadPage();
    return () => {
      cancelled = true;
    };
  }, [documentId, currentPage]);

  // ✅ NEW: Track time spent on page (every 10 seconds)
  useEffect(() => {
    const interval = setInterval(() => {
      updateProgress({
        document_id: documentId,
        page_number: currentPage,
        interaction_type: "page_view",
        time_spent: 10,
        metadata: {
          timestamp: new Date().toISOString(),
        },
      }).catch((err) => console.warn("Failed to track time:", err));
    }, 10000);

    return () => clearInterval(interval);
  }, [documentId, currentPage]);

  // Notify parent on page change
  useEffect(() => {
    onPageChange?.(currentPage);
  }, [currentPage, onPageChange]);

  const goTo = useCallback(
    (page: number) => {
      if (page >= 1 && page <= totalPages && page !== currentPage) {
        setCurrentPage(page);
      }
    },
    [totalPages, currentPage]
  );

  // Keyboard navigation
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }

      if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
        e.preventDefault();
        goTo(currentPage - 1);
      } else if (e.key === "ArrowRight" || e.key === "ArrowDown") {
        e.preventDefault();
        goTo(currentPage + 1);
      }
    };

    window.addEventListener("keydown", handleKeyPress);
    return () => window.removeEventListener("keydown", handleKeyPress);
  }, [currentPage, goTo]);

  const handlePageInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    if (value === "") return;
    
    const page = parseInt(value);
    if (!isNaN(page)) {
      goTo(page);
    }
  };

  const progressPercentage = Math.round((pagesViewed.size / totalPages) * 100);

  const formatDate = (dateString?: string) => {
    if (!dateString) return "Never";
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) return "Today";
    if (diffDays === 1) return "Yesterday";
    if (diffDays < 7) return `${diffDays} days ago`;
    return date.toLocaleDateString();
  };

  const formatTime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    if (hours > 0) return `${hours}h ${mins}m`;
    return `${mins}m`;
  };

  return (
    <div style={styles.container}>
      {/* Left Sidebar - Progress Tracker */}
      <div style={styles.sidebar}>
        <div style={styles.progressSection}>
          <h3 style={styles.progressTitle}>📊 Progress</h3>
          
          {/* Circular Progress */}
          <div style={styles.circularProgress}>
            <svg width="120" height="120" style={styles.progressSvg}>
              <circle
                cx="60"
                cy="60"
                r="50"
                stroke="var(--color-border)"
                strokeWidth="8"
                fill="none"
              />
              <circle
                cx="60"
                cy="60"
                r="50"
                stroke="var(--color-primary)"
                strokeWidth="8"
                fill="none"
                strokeDasharray={`${2 * Math.PI * 50}`}
                strokeDashoffset={`${2 * Math.PI * 50 * (1 - progressPercentage / 100)}`}
                strokeLinecap="round"
                transform="rotate(-90 60 60)"
                style={styles.progressCircle}
              />
            </svg>
            <div style={styles.progressText}>
              <div style={styles.progressPercent}>{progressPercentage}%</div>
              <div style={styles.progressLabel}>Complete</div>
            </div>
          </div>

          {/* Stats */}
          <div style={styles.statsContainer}>
            <div style={styles.statItem}>
              <div style={styles.statValue}>{pagesViewed.size}</div>
              <div style={styles.statLabel}>Pages Viewed</div>
            </div>
            <div style={styles.statDivider} />
            <div style={styles.statItem}>
              <div style={styles.statValue}>{totalPages}</div>
              <div style={styles.statLabel}>Total Pages</div>
            </div>
          </div>

          {/* Quiz Statistics */}
          <div style={styles.statsBlock}>
            <h4 style={styles.statsBlockTitle}>🎯 Quiz Statistics</h4>
            {statsLoading ? (
              <div style={styles.statsLoading}>
                <Loader size={20} />
              </div>
            ) : quizStats && quizStats.total_quizzes_taken > 0 ? (
              <div style={styles.statsContent}>
                <div style={styles.statsRow}>
                  <span style={styles.statsLabel}>Quizzes Taken</span>
                  <span style={styles.statsValue}>{quizStats.total_quizzes_taken}</span>
                </div>
                <div style={styles.statsRow}>
                  <span style={styles.statsLabel}>Average Score</span>
                  <span style={{...styles.statsValue, color: quizStats.average_score >= 70 ? 'var(--color-success)' : quizStats.average_score >= 50 ? '#ffa500' : '#ff6b6b'}}>
                    {quizStats.average_score.toFixed(1)}%
                  </span>
                </div>
                <div style={styles.statsRow}>
                  <span style={styles.statsLabel}>Best Score</span>
                  <span style={{...styles.statsValue, color: 'var(--color-success)'}}>
                    {quizStats.best_score.toFixed(1)}%
                  </span>
                </div>
                <div style={styles.statsRow}>
                  <span style={styles.statsLabel}>Last Quiz</span>
                  <span style={styles.statsValue}>{formatDate(quizStats.last_quiz_date)}</span>
                </div>
                <div style={styles.statsRow}>
                  <span style={styles.statsLabel}>Questions Answered</span>
                  <span style={styles.statsValue}>
                    {quizStats.total_correct_answers}/{quizStats.total_questions_answered}
                  </span>
                </div>
              </div>
            ) : (
              <div style={styles.noStats}>No quizzes taken yet</div>
            )}
          </div>

          {/* Revision Statistics */}
          <div style={styles.statsBlock}>
            <h4 style={styles.statsBlockTitle}>📚 Revision Stats</h4>
            {statsLoading ? (
              <div style={styles.statsLoading}>
                <Loader size={20} />
              </div>
            ) : revisionStats && revisionStats.total_revisions > 0 ? (
              <div style={styles.statsContent}>
                <div style={styles.statsRow}>
                  <span style={styles.statsLabel}>Total Revisions</span>
                  <span style={styles.statsValue}>{revisionStats.total_revisions}</span>
                </div>
                <div style={styles.statsRow}>
                  <span style={styles.statsLabel}>Last Reviewed</span>
                  <span style={styles.statsValue}>{formatDate(revisionStats.last_revision_date)}</span>
                </div>
                {revisionStats.next_suggested_revision && (
                  <div style={styles.statsRow}>
                    <span style={styles.statsLabel}>Next Review</span>
                    <span style={{...styles.statsValue, color: 'var(--color-warning)'}}>
                      {formatDate(revisionStats.next_suggested_revision)}
                    </span>
                  </div>
                )}
                <div style={styles.statsRow}>
                  <span style={styles.statsLabel}>Study Streak</span>
                  <span style={styles.statsValue}>
                    {revisionStats.revision_streak} {revisionStats.revision_streak === 1 ? 'day' : 'days'}
                  </span>
                </div>
                <div style={styles.statsRow}>
                  <span style={styles.statsLabel}>Total Time</span>
                  <span style={styles.statsValue}>{formatTime(revisionStats.total_time_spent_seconds)}</span>
                </div>
                <div style={styles.statsRow}>
                  <span style={styles.statsLabel}>Mastery Level</span>
                  <span style={{
                    ...styles.statsValue, 
                    color: revisionStats.mastery_level >= 70 ? 'var(--color-success)' : 
                           revisionStats.mastery_level >= 40 ? '#ffa500' : '#ff6b6b'
                  }}>
                    {revisionStats.mastery_level}%
                  </span>
                </div>
              </div>
            ) : (
              <div style={styles.noStats}>No revisions yet</div>
            )}
          </div>

          {/* Page Grid */}
          <div style={styles.pageGrid}>
            <div style={styles.pageGridLabel}>Page Status</div>
            <div style={styles.pageGridContainer}>
              {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                <button
                  key={page}
                  onClick={() => goTo(page)}
                  style={{
                    ...styles.pageGridItem,
                    ...(page === currentPage ? styles.pageGridItemActive : {}),
                    ...(pagesViewed.has(page) ? styles.pageGridItemViewed : {}),
                  }}
                  title={`Page ${page}${pagesViewed.has(page) ? ' (viewed)' : ''}`}
                >
                  {page}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div style={styles.mainContent}>
        {/* Page Navigation */}
        <div style={styles.navigation}>
          <button
            onClick={() => goTo(currentPage - 1)}
            disabled={currentPage === 1 || loading}
            style={{
              ...styles.navButton,
              opacity: currentPage === 1 || loading ? 0.5 : 1,
            }}
            title="Previous page (← or ↑)"
          >
            ← Prev
          </button>

          <div style={styles.pageIndicator}>
            <span style={styles.pageLabel}>Page</span>
            <input
              type="number"
              min={1}
              max={totalPages}
              value={currentPage}
              onChange={handlePageInput}
              disabled={loading}
              style={styles.pageInput}
            />
            <span style={styles.pageTotal}>of {totalPages}</span>
          </div>

          <button
            onClick={() => goTo(currentPage + 1)}
            disabled={currentPage === totalPages || loading}
            style={{
              ...styles.navButton,
              opacity: currentPage === totalPages || loading ? 0.5 : 1,
            }}
            title="Next page (→ or ↓)"
          >
            Next →
          </button>
        </div>

        {/* Rendered Page */}
        <div style={styles.imageContainer}>
          {loading ? (
            <div style={styles.loadingState}>
              <Loader size={40} />
              <p style={styles.loadingText}>Loading page {currentPage}...</p>
            </div>
          ) : error ? (
            <div style={styles.errorState}>
              <div style={styles.errorIcon}>⚠️</div>
              <p style={styles.errorText}>{error}</p>
              <button onClick={() => goTo(currentPage)} style={styles.retryButton}>
                Retry
              </button>
            </div>
          ) : base64Image ? (
            <embed
              src={`data:application/pdf;base64,${base64Image}`}
              type="application/pdf"
              style={styles.pageImage}
            />
          ) : (
            <div style={styles.noRender}>No render available</div>
          )}
        </div>
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: "flex",
    height: "100%",
    background: "var(--color-bg)",
  },
  sidebar: {
    width: 280,
    background: "var(--color-surface)",
    borderRight: "1px solid var(--color-border)",
    overflowY: "auto",
    flexShrink: 0,
  },
  progressSection: {
    padding: 20,
  },
  progressTitle: {
    fontSize: 16,
    fontWeight: 700,
    color: "var(--color-text)",
    margin: "0 0 24px 0",
    textAlign: "center",
  },
  circularProgress: {
    position: "relative",
    width: 120,
    height: 120,
    margin: "0 auto 24px",
  },
  progressSvg: {
    transform: "rotate(-90deg)",
  },
  progressCircle: {
    transition: "stroke-dashoffset 0.5s ease",
  },
  progressText: {
    position: "absolute",
    top: "50%",
    left: "50%",
    transform: "translate(-50%, -50%)",
    textAlign: "center",
  },
  progressPercent: {
    fontSize: 24,
    fontWeight: 700,
    color: "var(--color-primary)",
  },
  progressLabel: {
    fontSize: 11,
    color: "var(--color-text-muted)",
    marginTop: 2,
  },
  statsContainer: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-around",
    marginBottom: 24,
    padding: "16px 0",
    background: "var(--color-bg)",
    borderRadius: "var(--radius)",
  },
  statItem: {
    textAlign: "center",
    flex: 1,
  },
  statValue: {
    fontSize: 20,
    fontWeight: 700,
    color: "var(--color-text)",
  },
  statLabel: {
    fontSize: 11,
    color: "var(--color-text-muted)",
    marginTop: 4,
  },
  statDivider: {
    width: 1,
    height: 30,
    background: "var(--color-border)",
  },
  // New styles for quiz and revision stats
  statsBlock: {
    marginBottom: 20,
    padding: 16,
    background: "var(--color-bg)",
    borderRadius: "var(--radius)",
    border: "1px solid var(--color-border)",
  },
  statsBlockTitle: {
    fontSize: 13,
    fontWeight: 700,
    color: "var(--color-text)",
    margin: "0 0 12px 0",
  },
  statsContent: {
    display: "flex",
    flexDirection: "column",
    gap: 8,
  },
  statsRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    fontSize: 12,
  },
  statsLabel: {
    color: "var(--color-text-muted)",
  },
  statsValue: {
    fontWeight: 600,
    color: "var(--color-text)",
  },
  statsLoading: {
    display: "flex",
    justifyContent: "center",
    padding: "16px 0",
  },
  noStats: {
    textAlign: "center",
    color: "var(--color-text-muted)",
    fontSize: 12,
    padding: "12px 0",
    fontStyle: "italic",
  },
  pageGrid: {
    marginTop: 24,
  },
  pageGridLabel: {
    fontSize: 12,
    fontWeight: 600,
    color: "var(--color-text-muted)",
    textTransform: "uppercase",
    letterSpacing: 1,
    marginBottom: 12,
  },
  pageGridContainer: {
    display: "grid",
    gridTemplateColumns: "repeat(5, 1fr)",
    gap: 6,
    maxHeight: 300,
    overflowY: "auto",
  },
  pageGridItem: {
    aspectRatio: "1",
    border: "1px solid var(--color-border)",
    background: "var(--color-surface-hover)",
    color: "var(--color-text-muted)",
    borderRadius: "var(--radius-sm)",
    fontSize: 11,
    fontWeight: 600,
    cursor: "pointer",
    transition: "all 0.2s",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  pageGridItemViewed: {
    background: "rgba(80, 250, 123, 0.15)",
    borderColor: "var(--color-success)",
    color: "var(--color-success)",
  },
  pageGridItemActive: {
    background: "var(--color-primary)",
    borderColor: "var(--color-primary)",
    color: "var(--color-text-dark)",
    transform: "scale(1.1)",
  },
  mainContent: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
  },
  navigation: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 12,
    padding: "10px 16px",
    background: "var(--color-surface)",
    borderBottom: "1px solid var(--color-border)",
    flexShrink: 0,
  },
  navButton: {
    background: "var(--color-surface-hover)",
    color: "var(--color-text)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-sm)",
    padding: "6px 14px",
    fontSize: 13,
    fontWeight: 600,
    cursor: "pointer",
    transition: "all 0.2s",
  },
  pageIndicator: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    color: "var(--color-text)",
  },
  pageLabel: {
    fontSize: 14,
  },
  pageInput: {
    width: 48,
    textAlign: "center",
    background: "var(--color-bg)",
    color: "var(--color-text)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-sm)",
    padding: "4px 0",
    fontSize: 14,
    fontFamily: "inherit",
  },
  pageTotal: {
    fontSize: 14,
    color: "var(--color-text-muted)",
  },
  imageContainer: {
    flex: 1,
    overflow: "auto",
    display: "flex",
    alignItems: "flex-start",
    justifyContent: "center",
    padding: 24,
    background: "#1e1e1e",
  },
  loadingState: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 16,
    marginTop: 60,
  },
  loadingText: {
    color: "var(--color-text-muted)",
    fontSize: 14,
  },
  errorState: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 16,
    marginTop: 60,
  },
  errorIcon: {
    fontSize: 48,
  },
  errorText: {
    color: "#ff8888",
    fontSize: 14,
    textAlign: "center",
  },
  retryButton: {
    background: "var(--color-primary)",
    color: "var(--color-text-dark)",
    border: "none",
    borderRadius: "var(--radius-sm)",
    padding: "8px 16px",
    fontSize: 14,
    fontWeight: 600,
    cursor: "pointer",
  },
  pageImage: {
    width: "90%",
    height: "80vh",
    minHeight: "600px",
    borderRadius: "var(--radius)",
    boxShadow: "0 4px 12px rgba(0, 0, 0, 0.3)",
    border: "1px solid rgba(255, 255, 255, 0.1)",
  },
  noRender: {
    color: "var(--color-text-muted)",
    marginTop: 40,
  },
};

export default PDFViewer;