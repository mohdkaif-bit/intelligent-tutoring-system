import PDFViewer from "../pdf/PDFViewer";
import ChatPanel from "../chat/ChatPanel";
import QuizPanel from "../quiz/QuizPanel";
import ReframePanel from "../reframe/ReframePanel";

// ── public surface ──────────────────────────────────────────────────────────
// activeTool governs the high-level right-panel mode.
// chatTab governs which coexisting panel (Chat or Reframe) is in the foreground
// when activeTool === "chat".
export type ActiveTool = "chat" | "quiz";
export type ChatTab   = "chat" | "reframe";

interface SplitViewProps {
  documentId: string;
  totalPages: number;
  currentPage: number;
  onPageChange: (page: number) => void;

  activeTool: ActiveTool;
  setActiveTool: (t: ActiveTool) => void;
  chatTab: ChatTab;
  setChatTab: (t: ChatTab) => void;
}

const SplitView = ({
  documentId,
  totalPages,
  currentPage,
  onPageChange,
  activeTool,
  setActiveTool,
  chatTab,
  setChatTab,
}: SplitViewProps) => {
  return (
    <div style={styles.root}>
      {/* ════════════════ LEFT — PDF viewer ════════════════ */}
      <div style={styles.left}>
        <PDFViewer
          documentId={documentId}
          totalPages={totalPages}
          onPageChange={onPageChange}
        />
      </div>

      {/* ════════════════ RIGHT — tool panel ════════════════ */}
      <div style={styles.right}>
        {/* ── tool-switcher ribbon ── */}
        <div style={styles.ribbon}>
          {/* Chat + Reframe tabs (only visible / highlighted when not in quiz) */}
          <button
            onClick={() => { setActiveTool("chat"); setChatTab("chat"); }}
            style={{
              ...styles.ribbonBtn,
              ...(activeTool === "chat" && chatTab === "chat" ? styles.ribbonBtnActive : {}),
            }}
          >
            💬 Chat
          </button>
          <button
            onClick={() => { setActiveTool("chat"); setChatTab("reframe"); }}
            style={{
              ...styles.ribbonBtn,
              ...(activeTool === "chat" && chatTab === "reframe" ? styles.ribbonBtnActive : {}),
            }}
          >
            ✂️ Reframe
          </button>

          {/* Quiz button — visually distinct; when active it replaces the above */}
          <button
            onClick={() => setActiveTool(activeTool === "quiz" ? "chat" : "quiz")}
            style={{
              ...styles.ribbonBtn,
              ...styles.ribbonBtnQuiz,
              ...(activeTool === "quiz" ? styles.ribbonBtnQuizActive : {}),
            }}
          >
            📝 Quiz {activeTool === "quiz" ? "✕" : ""}
          </button>
        </div>

        {/* ── panel body ── */}
        <div style={styles.panelBody}>
          {activeTool === "quiz" ? (
            <QuizPanel documentId={documentId} currentPage={currentPage} />
          ) : chatTab === "chat" ? (
            <ChatPanel documentId={documentId} currentPage={currentPage} />
          ) : (
            <ReframePanel documentId={documentId} currentPage={currentPage} />
          )}
        </div>
      </div>
    </div>
  );
};

// ════════════════════════════════════════════════════════════════════════════
// STYLES
// ════════════════════════════════════════════════════════════════════════════
const styles: Record<string, React.CSSProperties> = {
  root: {
    display: "flex",
    flex: 1,
    minHeight: 0, // critical: lets flex children scroll independently
  },

  // ── columns ─────────────────────────────────────────────────────────────
  left: {
    flex: "1 1 55%",       // PDF gets slightly more than half
    minWidth: 0,
    borderRight: "1px solid var(--color-border)",
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
  },
  right: {
    flex: "1 1 45%",       // tool panel gets the rest
    minWidth: 0,
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
  },

  // ── ribbon (tool switcher at the top of right panel) ───────────────────
  ribbon: {
    display: "flex",
    gap: 4,
    padding: "8px 10px",
    background: "var(--color-surface)",
    borderBottom: "1px solid var(--color-border)",
    flexShrink: 0,
  },
  ribbonBtn: {
    background: "transparent",
    border: "1px solid transparent",
    borderRadius: "var(--radius-sm)",
    padding: "5px 12px",
    fontSize: 13,
    fontWeight: 600,
    color: "var(--color-text-muted)",
    cursor: "pointer",
    transition: "all 0.18s",
    whiteSpace: "nowrap" as const,
  },
  ribbonBtnActive: {
    background: "var(--color-surface-hover)",
    color: "var(--color-text)",
    border: "1px solid var(--color-border)",
  },
  ribbonBtnQuiz: {
    marginLeft: "auto",  // push quiz button to the right
  },
  ribbonBtnQuizActive: {
    background: "var(--color-primary)",
    color: "var(--color-text-dark)",
    border: "1px solid transparent",
  },

  // ── scrollable panel body ───────────────────────────────────────────────
  panelBody: {
    flex: 1,
    minHeight: 0,
    overflow: "hidden",
    display: "flex",
    flexDirection: "column",
  },
};

export default SplitView;