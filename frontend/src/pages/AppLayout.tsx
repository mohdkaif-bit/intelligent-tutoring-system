import React, { useState, useEffect, useCallback } from "react";
import { useApp } from "../context/AppContext";
import TopBar from "../components/layout/TopBar";
import SplitView, { ActiveTool, ChatTab } from "../components/layout/SplitView";

/**
 * AppLayout
 *
 * State ownership summary
 * ─────────────────────────
 *   AppContext   → documents[], selectedDocument, progress, suggestions …
 *   AppLayout   → activeTool ("chat" | "quiz")
 *                 chatTab   ("chat" | "reframe")  — only meaningful when activeTool === "chat"
 *                 currentPage (number)            — lifted from PDFViewer via onPageChange
 *
 * Tool-switching rules (from the spec)
 * ─────────────────────────────────────
 *   • Chat  + Reframe coexist  → controlled by chatTab
 *   • Quiz  REPLACES both      → activeTool flips to "quiz"
 *   • Closing Quiz             → activeTool returns to "chat", chatTab is untouched
 *     (the previous Chat / Reframe tab is still there, just hidden while Quiz was open)
 */
const AppLayout = () => {
  const { selectedDocument, fetchProgress, fetchSuggestions, signOut, user } = useApp();

  // ── tool / tab state ─────────────────────────────────────────────────────
  const [activeTool, setActiveTool] = useState<ActiveTool>("chat");
  const [chatTab, setChatTab]       = useState<ChatTab>("chat");
  const [currentPage, setCurrentPage] = useState(1);

  // ── reset page to 1 whenever the selected document changes ──────────────
  useEffect(() => {
    setCurrentPage(1);
  }, [selectedDocument?.document_id]);

  // ── kick off background fetches on mount ─────────────────────────────────
  useEffect(() => {
    fetchProgress();
    fetchSuggestions();
  }, [fetchProgress, fetchSuggestions]);

  // ── stable callback for PDFViewer ────────────────────────────────────────
  const handlePageChange = useCallback((page: number) => {
    setCurrentPage(page);
  }, []);

  // ──────────────────────────────────────────────────────────────────────────
  // RENDER
  // ──────────────────────────────────────────────────────────────────────────
  return (
    <div style={styles.root}>
      {/* ── top bar (always rendered) ── */}
      <TopBar />

      {/* ── main body ── */}
      {selectedDocument ? (
        <SplitView
          documentId={selectedDocument.document_id}
          totalPages={selectedDocument.page_count}
          currentPage={currentPage}
          onPageChange={handlePageChange}
          activeTool={activeTool}
          setActiveTool={setActiveTool}
          chatTab={chatTab}
          setChatTab={setChatTab}
        />
      ) : (
        /* empty state when no document is open */
        <div style={styles.empty}>
          <div style={styles.emptyIcon}>📚</div>
          <h2 style={styles.emptyTitle}>Welcome to your Learning Studio</h2>
          <p style={styles.emptyDesc}>
            Open a document from the library or upload a new PDF to begin.
          </p>
          <p style={styles.emptyHint}>
            You can also drag &amp; drop a PDF onto the top bar ↑
          </p>

          {/* ── user info + logout ── */}
          <div style={styles.userCard}>
            <div style={styles.userAvatar}>
              {user?.email?.[0]?.toUpperCase() ?? "U"}
            </div>
            <div style={styles.userInfo}>
              <span style={styles.userEmail}>{user?.email}</span>
              <span style={styles.userName}>
                {user?.user_metadata?.full_name ?? ""}
              </span>
            </div>
            <button style={styles.signOutBtn} onClick={signOut}>
              Sign out
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

// ════════════════════════════════════════════════════════════════════════════
// STYLES
// ════════════════════════════════════════════════════════════════════════════
const styles: Record<string, React.CSSProperties> = {
  root: {
    display: "flex",
    flexDirection: "column",
    height: "100vh",
    overflow: "hidden",
    background: "var(--color-bg)",
  },

  // ── empty state (no doc selected) ──
  empty: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    gap: 12,
    padding: 40,
    textAlign: "center" as const,
  },
  emptyIcon: {
    fontSize: 72,
    marginBottom: 8,
  },
  emptyTitle: {
    fontSize: 22,
    fontWeight: 700,
    color: "var(--color-text)",
  },
  emptyDesc: {
    fontSize: 15,
    color: "var(--color-text-muted)",
    maxWidth: 420,
    lineHeight: 1.5,
  },
  emptyHint: {
    fontSize: 13,
    color: "var(--color-text-muted)",
    opacity: 0.7,
    marginTop: 4,
  },

  // ── user card ──
  userCard: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    marginTop: 32,
    background: "var(--color-surface)",
    border: "0.5px solid var(--color-border)",
    borderRadius: 12,
    padding: "12px 16px",
    maxWidth: 360,
    width: "100%",
  },
  userAvatar: {
    width: 38,
    height: 38,
    borderRadius: "50%",
    background: "var(--color-primary)",
    color: "#fff",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 15,
    fontWeight: 600,
    flexShrink: 0,
  },
  userInfo: {
    display: "flex",
    flexDirection: "column",
    alignItems: "flex-start",
    flex: 1,
    minWidth: 0,
  },
  userEmail: {
    fontSize: 13,
    color: "var(--color-text)",
    fontWeight: 500,
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
    maxWidth: 180,
  },
  userName: {
    fontSize: 12,
    color: "var(--color-text-muted)",
  },
  signOutBtn: {
    background: "transparent",
    border: "0.5px solid var(--color-border)",
    borderRadius: 8,
    color: "var(--color-text-muted)",
    fontSize: 13,
    padding: "6px 12px",
    cursor: "pointer",
    flexShrink: 0,
    transition: "color 0.15s, border-color 0.15s",
  },
};

export default AppLayout;