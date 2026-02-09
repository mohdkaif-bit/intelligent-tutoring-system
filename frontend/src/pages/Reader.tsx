import React, { useState, useEffect } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import PDFViewer from "../components/pdf/PDFViewer";
import ChatPanel from "../components/chat/ChatPanel";
import QuizPanel from "../components/quiz/QuizPanel";
import ReframePanel from "../components/reframe/ReframePanel";
import { Loader } from "../components/common/Common";
import { getDocumentInfo } from "../api/api";

type PanelType = "chat" | "quiz" | "reframe";

const Reader: React.FC = () => {
  const { documentId } = useParams<{ documentId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState<number>(
    location.state?.totalPages || 0
  );
  const [documentTitle, setDocumentTitle] = useState("");
  const [loading, setLoading] = useState(!location.state?.totalPages);
  const [activePanel, setActivePanel] = useState<PanelType>("chat");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!documentId) {
      navigate("/");
      return;
    }

    // Only fetch document info if we don't have totalPages from navigation state
    if (!totalPages) {
      const loadDocument = async () => {
        setLoading(true);
        setError(null);
        try {
          const res = await getDocumentInfo(documentId);
          if (res.success) {
            setDocumentTitle(res.title || "Untitled Document");
            setTotalPages(res.page_count || 0);
          } else {
            setError("Failed to load document");
          }
        } catch (e) {
          setError(e instanceof Error ? e.message : "Failed to load document");
        } finally {
          setLoading(false);
        }
      };

      loadDocument();
    } else {
      // We have totalPages from state, just fetch the title
      const loadDocumentTitle = async () => {
        try {
          const res = await getDocumentInfo(documentId);
          if (res.success) {
            setDocumentTitle(res.title || "Untitled Document");
          }
        } catch (e) {
          console.error("Failed to fetch document title:", e);
          setDocumentTitle("Document");
        }
      };

      loadDocumentTitle();
    }
  }, [documentId, navigate, totalPages]);

  if (!documentId) {
    return null;
  }

  if (loading) {
    return (
      <div style={styles.loadingContainer}>
        <Loader size={40} />
        <p style={styles.loadingText}>Loading document...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={styles.errorContainer}>
        <div style={styles.errorCard}>
          <div style={styles.errorIcon}>⚠️</div>
          <h2 style={styles.errorTitle}>Error</h2>
          <p style={styles.errorMessage}>{error}</p>
          <button onClick={() => navigate("/")} style={styles.backButton}>
            ← Back to Home
          </button>
        </div>
      </div>
    );
  }

  if (!totalPages) {
    return (
      <div style={styles.errorContainer}>
        <div style={styles.errorCard}>
          <div style={styles.errorIcon}>📄</div>
          <h2 style={styles.errorTitle}>Document Not Found</h2>
          <p style={styles.errorMessage}>Unable to load document information.</p>
          <button onClick={() => navigate("/")} style={styles.backButton}>
            ← Back to Home
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      {/* Header */}
      <header style={styles.header}>
        <div style={styles.headerLeft}>
          <button onClick={() => navigate("/")} style={styles.backBtn}>
            ← Back
          </button>
          <h1 style={styles.title}>{documentTitle}</h1>
        </div>
        <div style={styles.headerRight}>
          <span style={styles.pageInfo}>
            Page {currentPage} of {totalPages}
          </span>
        </div>
      </header>

      {/* Main Content */}
      <div style={styles.content}>
        {/* PDF Viewer */}
        <div style={styles.viewerSection}>
          <PDFViewer
            documentId={documentId}
            totalPages={totalPages}
            onPageChange={setCurrentPage}
          />
        </div>

        {/* Side Panel */}
        <div style={styles.sidePanel}>
          {/* Panel Tabs */}
          <div style={styles.tabs}>
            <button
              onClick={() => setActivePanel("chat")}
              style={{
                ...styles.tab,
                ...(activePanel === "chat" ? styles.tabActive : {}),
              }}
            >
              💬 Chat
            </button>
            <button
              onClick={() => setActivePanel("quiz")}
              style={{
                ...styles.tab,
                ...(activePanel === "quiz" ? styles.tabActive : {}),
              }}
            >
              📝 Quiz
            </button>
            <button
              onClick={() => setActivePanel("reframe")}
              style={{
                ...styles.tab,
                ...(activePanel === "reframe" ? styles.tabActive : {}),
              }}
            >
              ✨ Reframe
            </button>
          </div>

          {/* Panel Content - NOW SCROLLABLE */}
          <div style={styles.panelContent}>
            {activePanel === "chat" && (
              <div style={styles.scrollableWrapper}>
                <ChatPanel documentId={documentId} currentPage={currentPage} />
              </div>
            )}
            {activePanel === "quiz" && (
              <div style={styles.scrollableWrapper}>
                <QuizPanel documentId={documentId} currentPage={currentPage} />
              </div>
            )}
            {activePanel === "reframe" && (
              <div style={styles.scrollableWrapper}>
                <ReframePanel documentId={documentId} currentPage={currentPage} />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: "flex",
    flexDirection: "column",
    height: "100vh",
    background: "var(--color-bg)",
    overflow: "hidden",
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "12px 20px",
    background: "var(--color-surface)",
    borderBottom: "1px solid var(--color-border)",
    flexShrink: 0,
  },
  headerLeft: {
    display: "flex",
    alignItems: "center",
    gap: 16,
  },
  headerRight: {
    display: "flex",
    alignItems: "center",
    gap: 12,
  },
  backBtn: {
    background: "transparent",
    color: "var(--color-text)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-sm)",
    padding: "6px 12px",
    fontSize: 13,
    fontWeight: 600,
    cursor: "pointer",
    transition: "all 0.2s",
  },
  title: {
    fontSize: 18,
    fontWeight: 700,
    color: "var(--color-text)",
    margin: 0,
  },
  pageInfo: {
    fontSize: 13,
    color: "var(--color-text-muted)",
  },
  content: {
    display: "flex",
    flex: 1,
    overflow: "hidden",
    minHeight: 0, // Important for proper flexbox scrolling
  },
  viewerSection: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
    borderRight: "1px solid var(--color-border)",
    minHeight: 0, // Important for proper flexbox scrolling
  },
  sidePanel: {
    width: 400,
    display: "flex",
    flexDirection: "column",
    background: "var(--color-bg)",
    overflow: "hidden",
    minHeight: 0, // Important for proper flexbox scrolling
  },
  tabs: {
    display: "flex",
    background: "var(--color-surface)",
    borderBottom: "1px solid var(--color-border)",
    flexShrink: 0,
  },
  tab: {
    flex: 1,
    padding: "12px 16px",
    background: "transparent",
    color: "var(--color-text-muted)",
    border: "none",
    borderBottom: "2px solid transparent",
    fontSize: 14,
    fontWeight: 600,
    cursor: "pointer",
    transition: "all 0.2s",
  },
  tabActive: {
    color: "var(--color-primary)",
    borderBottomColor: "var(--color-primary)",
  },
  panelContent: {
    flex: 1,
    overflow: "hidden",
    minHeight: 0, // Important for proper flexbox scrolling
    display: "flex",
    flexDirection: "column",
  },
  // NEW: Scrollable wrapper for each panel
  scrollableWrapper: {
    flex: 1,
    overflow: "auto", // Enable scrolling
    minHeight: 0, // Important for proper flexbox scrolling
    height: "100%",
  },
  loadingContainer: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    height: "100vh",
    background: "var(--color-bg)",
    gap: 16,
  },
  loadingText: {
    color: "var(--color-text-muted)",
    fontSize: 14,
  },
  errorContainer: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    height: "100vh",
    background: "var(--color-bg)",
    padding: 20,
  },
  errorCard: {
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius)",
    padding: 40,
    maxWidth: 500,
    textAlign: "center",
  },
  errorIcon: {
    fontSize: 48,
    marginBottom: 16,
  },
  errorTitle: {
    fontSize: 24,
    fontWeight: 700,
    color: "var(--color-text)",
    margin: "0 0 12px 0",
  },
  errorMessage: {
    fontSize: 14,
    color: "var(--color-text-muted)",
    margin: "0 0 24px 0",
  },
  backButton: {
    background: "var(--color-primary)",
    color: "var(--color-text-dark)",
    border: "none",
    borderRadius: "var(--radius-sm)",
    padding: "10px 20px",
    fontSize: 14,
    fontWeight: 600,
    cursor: "pointer",
  },
};

export default Reader;