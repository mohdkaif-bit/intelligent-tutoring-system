import { useState, useRef, useEffect, useCallback } from "react";
import { askQuestion } from "../../api/api";
import { ChatMode, ChatHistoryItem } from "../../types/types";
import { Loader, Button } from "../common/Common";

interface ChatPanelProps {
  documentId: string;
  currentPage: number;
}

const MODES: { value: ChatMode; label: string }[] = [
  { value: "quick_answer", label: "Quick Answer" },
  { value: "explain_concept", label: "Explain Concept" },
  { value: "step_by_step", label: "Step by Step" },
  { value: "practice_problems", label: "Practice Problems" },
  { value: "deep_analysis", label: "Deep Analysis" },
];

const ChatPanel = ({ documentId, currentPage }: ChatPanelProps) => {
  const [history, setHistory] = useState<ChatHistoryItem[]>([]);
  const [question, setQuestion] = useState("");
  const [mode, setMode] = useState<ChatMode>("quick_answer");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history, loading]);

  // Focus textarea on mount
  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  const handleSend = useCallback(async () => {
    const trimmed = question.trim();
    if (!trimmed || loading) return;

    // Optimistically add user message
    const userMsg: ChatHistoryItem = { role: "user", content: trimmed };
    setHistory((prev) => [...prev, userMsg]);
    setQuestion("");
    setLoading(true);
    setError(null);

    try {
      const res = await askQuestion({
        document_id: documentId,
        question: trimmed,
        mode,
        page_number: currentPage,
        history, // send history before this message
      });

      if (res.success) {
        setHistory((prev) => [
          ...prev,
          { role: "assistant", content: res.answer },
        ]);
      } else {
        setError(res.error || "Failed to get answer");
        // Remove optimistic user message on failure
        setHistory((prev) => prev.slice(0, -1));
        setQuestion(trimmed); // Restore question
      }
    } catch (e) {
      const errorMessage = e instanceof Error ? e.message : "Something went wrong";
      setError(errorMessage);
      // Remove optimistic user message on failure
      setHistory((prev) => prev.slice(0, -1));
      setQuestion(trimmed); // Restore question
    } finally {
      setLoading(false);
      // Focus back to textarea
      setTimeout(() => textareaRef.current?.focus(), 100);
    }
  }, [question, loading, documentId, mode, currentPage, history]);

  const clearChat = () => {
    setHistory([]);
    setError(null);
    setQuestion("");
    textareaRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <span style={styles.headerTitle}>💬 Chat</span>
        <button onClick={clearChat} style={styles.clearButton}>
          Clear
        </button>
      </div>

      {/* Mode Selector */}
      <div style={styles.modeSelector}>
        {MODES.map((m) => (
          <button
            key={m.value}
            onClick={() => setMode(m.value)}
            disabled={loading}
            style={{
              ...styles.modeButton,
              ...(mode === m.value ? styles.modeButtonActive : {}),
              opacity: loading ? 0.6 : 1,
            }}
          >
            {m.label}
          </button>
        ))}
      </div>

      {/* Messages */}
      <div style={styles.messages}>
        {history.length === 0 && (
          <div style={styles.emptyState}>
            <div style={styles.emptyIcon}>💡</div>
            <p style={styles.emptyText}>
              Ask a question about page {currentPage}
            </p>
            <p style={styles.emptySubtext}>
              Choose a mode above and start chatting
            </p>
          </div>
        )}

        {history.map((msg, i) => (
          <div
            key={i}
            style={{
              display: "flex",
              justifyContent: msg.role === "user" ? "flex-end" : "flex-start",
            }}
          >
            <div
              style={{
                ...styles.message,
                ...(msg.role === "user"
                  ? styles.messageUser
                  : styles.messageAssistant),
              }}
            >
              {msg.content}
            </div>
          </div>
        ))}

        {loading && (
          <div style={{ display: "flex", justifyContent: "flex-start" }}>
            <div style={styles.loadingMessage}>
              <Loader size={20} />
            </div>
          </div>
        )}

        {error && (
          <div style={styles.errorMessage}>
            <span style={styles.errorIcon}>⚠️</span>
            {error}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div style={styles.inputContainer}>
        <div style={styles.inputWrapper}>
          <textarea
            ref={textareaRef}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={`Ask a question... (${
              navigator.platform.includes("Mac") ? "⌘" : "Ctrl"
            }+Enter to send)`}
            rows={2}
            disabled={loading}
            style={styles.textarea}
          />
          <Button
            onClick={handleSend}
            disabled={loading || !question.trim()}
            style={{ height: 42 }}
          >
            {loading ? "Sending..." : "Send"}
          </Button>
        </div>
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: "flex",
    flexDirection: "column",
    height: "100%",
    background: "var(--color-bg)",
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "10px 16px",
    background: "var(--color-surface)",
    borderBottom: "1px solid var(--color-border)",
    flexShrink: 0,
  },
  headerTitle: {
    fontSize: 14,
    fontWeight: 600,
    color: "var(--color-text)",
  },
  clearButton: {
    background: "none",
    border: "none",
    color: "var(--color-text-muted)",
    fontSize: 12,
    cursor: "pointer",
    padding: "4px 8px",
    borderRadius: "var(--radius-sm)",
    transition: "all 0.2s",
  },
  modeSelector: {
    display: "flex",
    gap: 6,
    padding: "10px 12px",
    overflowX: "auto",
    background: "var(--color-surface)",
    borderBottom: "1px solid var(--color-border)",
    flexShrink: 0,
  },
  modeButton: {
    background: "var(--color-surface-hover)",
    color: "var(--color-text-muted)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-sm)",
    padding: "5px 10px",
    fontSize: 12,
    fontWeight: 600,
    whiteSpace: "nowrap",
    cursor: "pointer",
    transition: "all 0.2s",
  },
  modeButtonActive: {
    background: "var(--color-primary)",
    color: "var(--color-text-dark)",
    borderColor: "transparent",
  },
  messages: {
    flex: 1,
    overflowY: "auto",
    padding: 12,
    display: "flex",
    flexDirection: "column",
    gap: 12,
  },
  emptyState: {
    textAlign: "center",
    padding: "40px 20px",
  },
  emptyIcon: {
    fontSize: 48,
    marginBottom: 12,
  },
  emptyText: {
    color: "var(--color-text)",
    fontSize: 14,
    marginBottom: 4,
  },
  emptySubtext: {
    color: "var(--color-text-muted)",
    fontSize: 13,
  },
  message: {
    maxWidth: "85%",
    borderRadius: "var(--radius)",
    padding: "10px 14px",
    fontSize: 14,
    lineHeight: 1.6,
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
  },
  messageUser: {
    background: "var(--color-primary)",
    color: "var(--color-text-dark)",
  },
  messageAssistant: {
    background: "var(--color-surface)",
    color: "var(--color-text)",
    border: "1px solid var(--color-border)",
  },
  loadingMessage: {
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius)",
    padding: "10px 14px",
  },
  errorMessage: {
    background: "rgba(255, 85, 85, 0.1)",
    border: "1px solid var(--color-danger)",
    borderRadius: "var(--radius)",
    padding: "10px 14px",
    color: "#ff8888",
    fontSize: 13,
    display: "flex",
    alignItems: "center",
    gap: 8,
  },
  errorIcon: {
    fontSize: 16,
  },
  inputContainer: {
    padding: 12,
    borderTop: "1px solid var(--color-border)",
    background: "var(--color-surface)",
    flexShrink: 0,
  },
  inputWrapper: {
    display: "flex",
    gap: 8,
    alignItems: "flex-end",
  },
  textarea: {
    flex: 1,
    resize: "none",
    background: "var(--color-bg)",
    color: "var(--color-text)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius)",
    padding: "10px 12px",
    fontSize: 14,
    lineHeight: 1.5,
    fontFamily: "inherit",
  },
};

export default ChatPanel;