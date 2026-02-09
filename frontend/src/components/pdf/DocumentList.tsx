import { useEffect, useRef } from "react";
import { useApp } from "../../context/AppContext";
import { DocumentMetadata } from "../../types/types";
import { Loader } from "../common/Common";

interface DocumentListProps {
  /** controlled open state driven by the parent */
  open: boolean;
  /** called when the user clicks outside or picks a doc */
  onClose: () => void;
}

// ── tiny helper: human-readable file size ──────────────────────────────────
const fmtSize = (bytes?: number): string => {
  if (!bytes) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

// ── tiny helper: short date ─────────────────────────────────────────────────
const fmtDate = (iso: string): string => {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return iso;
  }
};

const DocumentList = ({ open, onClose }: DocumentListProps) => {
  const { documents, selectedDocument, loading, fetchDocuments, selectDocument, removeDocument } = useApp();
  const panelRef = useRef<HTMLDivElement>(null);

  // ── fetch on first open ─────────────────────────────────────────────────
  useEffect(() => {
    if (open) fetchDocuments();
  }, [open, fetchDocuments]);

  // ── close on outside click ──────────────────────────────────────────────
  useEffect(() => {
    if (!open) return;

    const handler = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    // slight delay so the click that opened the panel doesn't immediately close it
    const id = setTimeout(() => document.addEventListener("mousedown", handler), 80);
    return () => {
      clearTimeout(id);
      document.removeEventListener("mousedown", handler);
    };
  }, [open, onClose]);

  // ── close on Escape ─────────────────────────────────────────────────────
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open) return null;

  // ── pick a doc ──────────────────────────────────────────────────────────
  const pick = (doc: DocumentMetadata) => {
    selectDocument(doc);
    onClose();
  };

  // ── delete with confirmation ────────────────────────────────────────────
  const tryDelete = (e: React.MouseEvent, doc: DocumentMetadata) => {
    e.stopPropagation();
    if (!confirm(`Delete "${doc.original_filename}"? This cannot be undone.`)) return;
    removeDocument(doc.document_id);
  };

  return (
    /* ── backdrop ── */
    <div style={styles.backdrop}>
      {/* ── floating panel (click-outside handled by ref) ── */}
      <div ref={panelRef} style={styles.panel}>
        <div style={styles.panelHeader}>
          <span style={styles.panelTitle}>📄 My Documents</span>
          <button onClick={onClose} style={styles.closeBtn}>✕</button>
        </div>

        <div style={styles.list}>
          {loading ? (
            <div style={styles.center}><Loader size={28} /></div>
          ) : documents.length === 0 ? (
            <div style={styles.empty}>
              <div style={styles.emptyIcon}>📚</div>
              <p style={styles.emptyText}>No documents yet.</p>
              <p style={styles.emptySubtext}>Upload a PDF to get started.</p>
            </div>
          ) : (
            documents.map((doc) => {
              const isActive = selectedDocument?.document_id === doc.document_id;
              return (
                <div
                  key={doc.document_id}
                  onClick={() => pick(doc)}
                  style={{
                    ...styles.row,
                    ...(isActive ? styles.rowActive : {}),
                  }}
                >
                  {/* icon */}
                  <div style={styles.rowIcon}>📄</div>

                  {/* info */}
                  <div style={styles.rowInfo}>
                    <span style={styles.rowTitle}>{doc.original_filename}</span>
                    <span style={styles.rowMeta}>
                      {doc.page_count} page{doc.page_count !== 1 ? "s" : ""}
                      {doc.file_size_bytes ? ` · ${fmtSize(doc.file_size_bytes)}` : ""}
                      {" · "}
                      {fmtDate(doc.upload_timestamp)}
                    </span>
                  </div>

                  {/* active badge */}
                  {isActive && <span style={styles.activeBadge}>Open</span>}

                  {/* delete */}
                  <button onClick={(e) => tryDelete(e, doc)} style={styles.deleteBtn} title="Delete">
                    🗑️
                  </button>
                </div>
              );
            })
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
  backdrop: {
    position: "fixed",
    inset: 0,
    background: "rgba(0,0,0,0.45)",
    zIndex: 100,
    display: "flex",
    alignItems: "flex-start",
    justifyContent: "center",
    paddingTop: 60,
  },
  panel: {
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius)",
    boxShadow: "var(--shadow)",
    width: 460,
    maxHeight: "70vh",
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
  },
  panelHeader: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "14px 18px",
    borderBottom: "1px solid var(--color-border)",
    flexShrink: 0,
  },
  panelTitle: {
    fontSize: 15,
    fontWeight: 700,
    color: "var(--color-text)",
  },
  closeBtn: {
    background: "none",
    border: "none",
    color: "var(--color-text-muted)",
    fontSize: 16,
    cursor: "pointer",
    padding: "2px 6px",
    borderRadius: "var(--radius-sm)",
  },
  list: {
    overflowY: "auto" as const,
    flex: 1,
  },
  row: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    padding: "12px 16px",
    cursor: "pointer",
    borderBottom: "1px solid var(--color-border)",
    transition: "background 0.15s",
  },
  rowActive: {
    background: "rgba(108, 99, 255, 0.08)",
  },
  rowIcon: {
    fontSize: 22,
    flexShrink: 0,
  },
  rowInfo: {
    flex: 1,
    minWidth: 0,
  },
  rowTitle: {
    display: "block",
    fontSize: 14,
    fontWeight: 600,
    color: "var(--color-text)",
    whiteSpace: "nowrap" as const,
    overflow: "hidden",
    textOverflow: "ellipsis",
  },
  rowMeta: {
    display: "block",
    fontSize: 12,
    color: "var(--color-text-muted)",
    marginTop: 2,
  },
  activeBadge: {
    fontSize: 11,
    fontWeight: 700,
    color: "var(--color-primary)",
    background: "rgba(108, 99, 255, 0.15)",
    padding: "2px 8px",
    borderRadius: 10,
    flexShrink: 0,
  },
  deleteBtn: {
    background: "none",
    border: "none",
    fontSize: 16,
    cursor: "pointer",
    padding: "4px",
    borderRadius: "var(--radius-sm)",
    flexShrink: 0,
    opacity: 0.55,
    transition: "opacity 0.2s",
  },
  center: {
    display: "flex",
    justifyContent: "center",
    padding: 40,
  },
  empty: {
    textAlign: "center" as const,
    padding: "48px 24px",
  },
  emptyIcon: {
    fontSize: 40,
    marginBottom: 12,
  },
  emptyText: {
    color: "var(--color-text)",
    fontSize: 15,
    fontWeight: 600,
  },
  emptySubtext: {
    color: "var(--color-text-muted)",
    fontSize: 13,
    marginTop: 4,
  },
};

export default DocumentList;