import { useState, useRef, useCallback } from "react";
import { useApp } from "../../context/AppContext";
import DocumentList from "../pdf/DocumentList";

const TopBar = () => {
  const { selectedDocument, progress, uploadNewDocument, loading } = useApp();
  const [docListOpen, setDocListOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── upload handler (input change) ───────────────────────────────────────
  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      uploadNewDocument(file);
      e.target.value = ""; // reset so the same file can be re-uploaded
    }
  }, [uploadNewDocument]);

  // ── drag & drop onto the bar ────────────────────────────────────────────
  const [dragOver, setDragOver] = useState(false);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };
  const handleDragLeave = () => setDragOver(false);
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) uploadNewDocument(file);
  };

  return (
    <>
      <div
        style={{
          ...styles.bar,
          ...(dragOver ? styles.barDragOver : {}),
        }}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {/* ── LEFT: document selector ── */}
        <div style={styles.left}>
          {/* current doc button */}
          <button onClick={() => setDocListOpen(true)} style={styles.docBtn}>
            <span style={styles.docBtnIcon}>📄</span>
            <span style={styles.docBtnLabel}>
              {selectedDocument ? selectedDocument.original_filename : "Select Document"}
            </span>
            <span style={styles.docBtnChevron}>▾</span>
          </button>

          {/* upload button (hidden native input) */}
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            onChange={handleFileChange}
            style={{ display: "none" }}
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={loading}
            style={styles.uploadBtn}
            title="Upload a PDF"
          >
            {loading ? "⏳" : "＋ Upload"}
          </button>
        </div>

        {/* ── RIGHT: progress stats ── */}
        <div style={styles.right}>
          {progress ? (
            <div style={styles.statsRow}>
              <Stat icon="📖" value={progress.total_pages_viewed} label="Pages" />
              <Stat icon="💬" value={progress.total_questions_asked} label="Questions" />
              <Stat icon="📝" value={progress.total_quizzes_completed} label="Quizzes" />
              <Stat icon="🎯" value={`${Math.round(progress.average_quiz_score * 100)}%`} label="Avg Score" />
            </div>
          ) : (
            <span style={styles.noProgress}>No progress yet</span>
          )}
        </div>
      </div>

      {/* ── Document list modal (rendered in a portal-like position via fixed backdrop) ── */}
      <DocumentList open={docListOpen} onClose={() => setDocListOpen(false)} />
    </>
  );
};

// ── tiny sub-component for one stat chip ────────────────────────────────────
const Stat = ({ icon, value, label }: { icon: string; value: number | string; label: string }) => (
  <div style={styles.stat}>
    <span style={styles.statIcon}>{icon}</span>
    <span style={styles.statValue}>{value}</span>
    <span style={styles.statLabel}>{label}</span>
  </div>
);

// ════════════════════════════════════════════════════════════════════════════
// STYLES
// ════════════════════════════════════════════════════════════════════════════
const styles: Record<string, React.CSSProperties> = {
  bar: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    height: 52,
    paddingInline: 18,
    background: "var(--color-surface)",
    borderBottom: "1px solid var(--color-border)",
    flexShrink: 0,
    gap: 16,
    transition: "background 0.2s",
  },
  barDragOver: {
    background: "rgba(108, 99, 255, 0.08)",
    borderBottom: "1px solid var(--color-primary)",
  },

  // ── left cluster ───
  left: {
    display: "flex",
    alignItems: "center",
    gap: 10,
  },
  docBtn: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    background: "var(--color-surface-hover)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-sm)",
    padding: "7px 12px",
    cursor: "pointer",
    maxWidth: 240,
    transition: "all 0.2s",
  },
  docBtnIcon: {
    fontSize: 16,
    flexShrink: 0,
  },
  docBtnLabel: {
    fontSize: 14,
    fontWeight: 600,
    color: "var(--color-text)",
    whiteSpace: "nowrap" as const,
    overflow: "hidden",
    textOverflow: "ellipsis",
    maxWidth: 160,
  },
  docBtnChevron: {
    fontSize: 10,
    color: "var(--color-text-muted)",
    flexShrink: 0,
  },
  uploadBtn: {
    background: "var(--color-primary)",
    color: "var(--color-text-dark)",
    border: "none",
    borderRadius: "var(--radius-sm)",
    padding: "7px 14px",
    fontSize: 13,
    fontWeight: 700,
    cursor: "pointer",
    transition: "opacity 0.2s",
  },

  // ── right cluster ───
  right: {
    display: "flex",
    alignItems: "center",
  },
  statsRow: {
    display: "flex",
    gap: 18,
  },
  stat: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 1,
  },
  statIcon: {
    fontSize: 14,
  },
  statValue: {
    fontSize: 14,
    fontWeight: 700,
    color: "var(--color-text)",
  },
  statLabel: {
    fontSize: 10,
    color: "var(--color-text-muted)",
    textTransform: "uppercase" as const,
    letterSpacing: 0.6,
  },
  noProgress: {
    fontSize: 13,
    color: "var(--color-text-muted)",
  },
};

export default TopBar;