import { useState, useRef, useCallback } from "react";
import { useApp } from "../../context/AppContext";
import DocumentList from "../pdf/DocumentList";

const TopBar = () => {
  const { selectedDocument, progress, uploadNewDocument, loading, user, signOut } = useApp();
  const [docListOpen, setDocListOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── upload handler (input change) ───────────────────────────────────────
  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      uploadNewDocument(file);
      e.target.value = "";
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

  // ── derived user display values ──────────────────────────────────────────
  const userInitial  = user?.email?.[0]?.toUpperCase() ?? "U";
  const userEmail    = user?.email ?? "";
  const userName     = user?.user_metadata?.full_name ?? "";

  return (
    <>
      <div
        style={{ ...styles.bar, ...(dragOver ? styles.barDragOver : {}) }}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {/* ── LEFT: document selector ── */}
        <div style={styles.left}>
          <button onClick={() => setDocListOpen(true)} style={styles.docBtn}>
            <span style={styles.docBtnIcon}>📄</span>
            <span style={styles.docBtnLabel}>
              {selectedDocument ? selectedDocument.original_filename : "Select Document"}
            </span>
            <span style={styles.docBtnChevron}>▾</span>
          </button>

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

        {/* ── CENTER: progress stats ── */}
        <div style={styles.right}>
          {progress ? (
            <div style={styles.statsRow}>
              <Stat icon="📖" value={progress.total_pages_viewed}      label="Pages"     />
              <Stat icon="💬" value={progress.total_questions_asked}    label="Questions" />
              <Stat icon="📝" value={progress.total_quizzes_completed}  label="Quizzes"   />
              <Stat icon="🎯" value={`${Math.round(progress.average_quiz_score * 100)}%`} label="Avg Score" />
            </div>
          ) : (
            <span style={styles.noProgress}>No progress yet</span>
          )}
        </div>

        {/* ── RIGHT: user avatar + dropdown ── */}
        <div style={styles.userWrap}>
          <button
            style={styles.avatarBtn}
            onClick={() => setUserMenuOpen((v) => !v)}
            title={userEmail}
          >
            <span style={styles.avatarCircle}>{userInitial}</span>
          </button>

          {userMenuOpen && (
            <>
              {/* backdrop to close on outside click */}
              <div
                style={styles.backdrop}
                onClick={() => setUserMenuOpen(false)}
              />
              <div style={styles.dropdown}>
                {/* user info */}
                <div style={styles.dropdownHeader}>
                  <div style={styles.dropdownAvatar}>{userInitial}</div>
                  <div style={styles.dropdownInfo}>
                    {userName && (
                      <span style={styles.dropdownName}>{userName}</span>
                    )}
                    <span style={styles.dropdownEmail}>{userEmail}</span>
                  </div>
                </div>

                <div style={styles.dropdownDivider} />

                <button
                  style={styles.dropdownItem}
                  onClick={() => { setUserMenuOpen(false); signOut(); }}
                >
                  <span style={styles.dropdownItemIcon}>🚪</span>
                  Sign out
                </button>
              </div>
            </>
          )}
        </div>
      </div>

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
    minWidth: 0,
    flex: 1,
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
    flexShrink: 0,
  },

  // ── center stats ───
  right: {
    display: "flex",
    alignItems: "center",
    flex: 1,
    justifyContent: "center",
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

  // ── user avatar + dropdown ───
  userWrap: {
    position: "relative" as const,
    flexShrink: 0,
  },
  avatarBtn: {
    background: "none",
    border: "none",
    padding: 0,
    cursor: "pointer",
    borderRadius: "50%",
    display: "flex",
    alignItems: "center",
  },
  avatarCircle: {
    width: 34,
    height: 34,
    borderRadius: "50%",
    background: "var(--color-primary)",
    color: "#fff",
    display: "inline-flex",  // ← was "flex"
    alignItems: "center",
    justifyContent: "center",
    fontSize: 14,
    fontWeight: 600,
    userSelect: "none" as const,
  },
  backdrop: {
    position: "fixed" as const,
    inset: 0,
    zIndex: 99,
  },
  dropdown: {
    position: "absolute" as const,
    top: "calc(100% + 8px)",
    right: 0,
    zIndex: 100,
    background: "var(--color-surface)",
    border: "0.5px solid var(--color-border)",
    borderRadius: 12,
    minWidth: 220,
    boxShadow: "var(--shadow)",
    overflow: "hidden",
  },
  dropdownHeader: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "14px 16px",
  },
  dropdownAvatar: {
    width: 36,
    height: 36,
    borderRadius: "50%",
    background: "var(--color-primary)",
    color: "#fff",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 14,
    fontWeight: 600,
    flexShrink: 0,
  },
  dropdownInfo: {
    display: "flex",
    flexDirection: "column" as const,
    minWidth: 0,
  },
  dropdownName: {
    fontSize: 13,
    fontWeight: 600,
    color: "var(--color-text)",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap" as const,
  },
  dropdownEmail: {
    fontSize: 12,
    color: "var(--color-text-muted)",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap" as const,
  },
  dropdownDivider: {
    height: "0.5px",
    background: "var(--color-border)",
    marginInline: 12,
  },
  dropdownItem: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    width: "100%",
    padding: "11px 16px",
    background: "none",
    border: "none",
    cursor: "pointer",
    fontSize: 14,
    color: "var(--color-danger)",
    textAlign: "left" as const,
    transition: "background 0.15s",
  },
  dropdownItemIcon: {
    fontSize: 15,
  },
};

export default TopBar;