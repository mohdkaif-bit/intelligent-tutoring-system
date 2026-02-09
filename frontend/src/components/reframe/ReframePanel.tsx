import React, { useState } from "react";
import { Loader } from "../common/Common";

interface ReframePanelProps {
  documentId: string;
  currentPage: number;
}

interface AlignmentDetails {
  numeric_score: number;
  label: string;
  what_it_means: string[];
  how_calculated: string[];
}

interface SemanticAlignment {
  score: number;
  label: string;
  warning: boolean;
  warning_message: string | null;
}

interface ReframeResult {
  reframed_text: string;
  semantic_alignment: SemanticAlignment;
  alignment_details_payload: {
    alignment_details: AlignmentDetails;
  };
}

const ReframePanel: React.FC<ReframePanelProps> = ({ documentId, currentPage }) => {
  const [selectedText, setSelectedText] = useState("");
  const [reframeResult, setReframeResult] = useState<ReframeResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showDetails, setShowDetails] = useState(false);

  const handleReframe = async () => {
    const trimmedText = selectedText.trim();
    
    if (!trimmedText) {
      setError("Please enter text to reframe");
      return;
    }

    if (trimmedText.length < 10) {
      setError("Text must be at least 10 characters");
      return;
    }

    setLoading(true);
    setError(null);
    setReframeResult(null);

    try {
      const requestBody = {
        document_id: documentId,
        page_number: currentPage,
        selected_text: trimmedText,
      };

      console.log("Sending reframe request:", requestBody);

      const response = await fetch("http://localhost:8000/api/v1/reframe/reframe", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestBody),
      });

      console.log("Response status:", response.status);

      const data = await response.json();
      console.log("Response data:", data);

      if (!response.ok) {
        let errorMsg = "Failed to reframe text";
        
        if (data.detail) {
          if (Array.isArray(data.detail)) {
            errorMsg = data.detail.map((e: any) => `${e.loc.join('.')}: ${e.msg}`).join(', ');
          } else if (typeof data.detail === 'string') {
            errorMsg = data.detail;
          } else {
            errorMsg = JSON.stringify(data.detail);
          }
        } else if (data.error) {
          errorMsg = data.error;
        } else {
          errorMsg = `Server error: ${response.status}`;
        }
        
        throw new Error(errorMsg);
      }

      if (!data.success) {
        throw new Error(data.error || "Reframe failed");
      }

      setReframeResult(data);
      console.log("Reframe successful:", data);
    } catch (e) {
      const errorMessage = e instanceof Error ? e.message : "Failed to reframe text";
      console.error("Reframe error:", errorMessage, e);
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setSelectedText("");
    setReframeResult(null);
    setError(null);
    setShowDetails(false);
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const getAlignmentColor = (score: number) => {
    if (score >= 0.90) return "#50fa7b";
    if (score >= 0.80) return "#8be9fd";
    if (score >= 0.65) return "#f1fa8c";
    return "#ff6b6b";
  };

  return (
    <div style={styles.container}>
      {/* Scrollable Content Area */}
      <div style={styles.scrollContent}>
        {/* Header */}
        <div style={styles.header}>
          <div style={styles.headerIcon}>✨</div>
          <div>
            <h3 style={styles.title}>Reframe Text</h3>
            <p style={styles.subtitle}>Simplify complex text while preserving meaning</p>
          </div>
        </div>

        {/* Input Section */}
        <div style={styles.inputSection}>
          <label style={styles.label}>
            Select or paste text to reframe
            <span style={styles.labelHint}>(min. 10 characters)</span>
          </label>
          <textarea
            value={selectedText}
            onChange={(e) => setSelectedText(e.target.value)}
            placeholder="Paste the text you want to simplify here..."
            style={styles.textarea}
            disabled={loading}
          />
          <div style={styles.charCount}>
            {selectedText.length} characters
          </div>
        </div>

        {/* Action Buttons */}
        <div style={styles.actions}>
          <button
            onClick={handleReframe}
            disabled={loading || !selectedText.trim()}
            style={{
              ...styles.button,
              ...styles.primaryButton,
              ...(loading || !selectedText.trim() ? styles.buttonDisabled : {}),
            }}
          >
            {loading ? (
              <>
                <Loader size={16} />
                <span>Reframing...</span>
              </>
            ) : (
              <>
                <span>✨</span>
                <span>Reframe Text</span>
              </>
            )}
          </button>
          <button
            onClick={handleClear}
            disabled={loading}
            style={{
              ...styles.button,
              ...styles.secondaryButton,
              ...(loading ? styles.buttonDisabled : {}),
            }}
          >
            Clear
          </button>
        </div>

        {/* Error Display */}
        {error && (
          <div style={styles.error}>
            <span style={styles.errorIcon}>⚠️</span>
            <div>
              <div style={styles.errorTitle}>Failed to reframe text</div>
              <div style={styles.errorMessage}>{error}</div>
            </div>
          </div>
        )}

        {/* Results Section */}
        {reframeResult && (
          <div style={styles.resultsContainer}>
            {/* Alignment Score */}
            <div style={styles.alignmentCard}>
              <div style={styles.alignmentHeader}>
                <span style={styles.alignmentTitle}>Semantic Alignment</span>
                <button
                  onClick={() => setShowDetails(!showDetails)}
                  style={styles.detailsButton}
                >
                  {showDetails ? "Hide Details" : "Show Details"}
                </button>
              </div>

              <div style={styles.alignmentScore}>
                <div
                  style={{
                    ...styles.scoreCircle,
                    borderColor: getAlignmentColor(reframeResult.semantic_alignment.score),
                  }}
                >
                  <span style={styles.scoreValue}>
                    {Math.round(reframeResult.semantic_alignment.score * 100)}%
                  </span>
                </div>
                <div style={styles.scoreInfo}>
                  <div
                    style={{
                      ...styles.scoreLabel,
                      color: getAlignmentColor(reframeResult.semantic_alignment.score),
                    }}
                  >
                    {reframeResult.semantic_alignment.label}
                  </div>
                  {reframeResult.semantic_alignment.warning && (
                    <div style={styles.warning}>
                      <span style={styles.warningIcon}>⚠️</span>
                      {reframeResult.semantic_alignment.warning_message}
                    </div>
                  )}
                </div>
              </div>

              {/* Detailed Explanation */}
              {showDetails && (
                <div style={styles.detailsPanel}>
                  <div style={styles.detailsSection}>
                    <h4 style={styles.detailsTitle}>What this means:</h4>
                    <ul style={styles.detailsList}>
                      {reframeResult.alignment_details_payload.alignment_details.what_it_means.map(
                        (item, idx) => (
                          <li key={idx} style={styles.detailsItem}>
                            {item}
                          </li>
                        )
                      )}
                    </ul>
                  </div>

                  <div style={styles.detailsSection}>
                    <h4 style={styles.detailsTitle}>How it's calculated:</h4>
                    <ul style={styles.detailsList}>
                      {reframeResult.alignment_details_payload.alignment_details.how_calculated.map(
                        (item, idx) => (
                          <li key={idx} style={styles.detailsItem}>
                            {item}
                          </li>
                        )
                      )}
                    </ul>
                  </div>
                </div>
              )}
            </div>

            {/* Original Text */}
            <div style={styles.textCard}>
              <div style={styles.textHeader}>
                <span style={styles.textTitle}>📄 Original Text</span>
                <button
                  onClick={() => copyToClipboard(selectedText)}
                  style={styles.copyButton}
                >
                  📋 Copy
                </button>
              </div>
              <div style={styles.textContent}>{selectedText}</div>
            </div>

            {/* Reframed Text */}
            <div style={styles.textCard}>
              <div style={styles.textHeader}>
                <span style={styles.textTitle}>✨ Reframed Text</span>
                <button
                  onClick={() => copyToClipboard(reframeResult.reframed_text)}
                  style={styles.copyButton}
                >
                  📋 Copy
                </button>
              </div>
              <div style={{...styles.textContent, ...styles.reframedText}}>
                {reframeResult.reframed_text}
              </div>
            </div>
          </div>
        )}

        {/* Help Section */}
        {!reframeResult && !loading && (
          <div style={styles.helpSection}>
            <h4 style={styles.helpTitle}>How to use:</h4>
            <ol style={styles.helpList}>
              <li style={styles.helpItem}>
                Select text from the PDF or paste complex text into the box above
              </li>
              <li style={styles.helpItem}>
                Click "Reframe Text" to get a simplified version
              </li>
              <li style={styles.helpItem}>
                Review the alignment score to see how closely the reframed text matches
                the original meaning
              </li>
              <li style={styles.helpItem}>
                Copy the reframed text or try again if the alignment is too low
              </li>
            </ol>
          </div>
        )}
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    height: "100%",
    width: "100%",
    display: "flex",
    flexDirection: "column",
    background: "var(--color-bg)",
    overflow: "hidden", // Hide overflow on root
  },
  scrollContent: {
    flex: 1,
    overflowY: "auto", // Enable scrolling here
    overflowX: "hidden",
    minHeight: 0, // Critical for flex scrolling
  },
  header: {
    padding: "20px",
    background: "var(--color-surface)",
    borderBottom: "1px solid var(--color-border)",
    display: "flex",
    alignItems: "center",
    gap: 12,
  },
  headerIcon: {
    fontSize: 28,
  },
  title: {
    fontSize: 16,
    fontWeight: 700,
    color: "var(--color-text)",
    margin: 0,
  },
  subtitle: {
    fontSize: 12,
    color: "var(--color-text-muted)",
    margin: "4px 0 0 0",
  },
  inputSection: {
    padding: "20px",
    borderBottom: "1px solid var(--color-border)",
  },
  label: {
    display: "block",
    fontSize: 13,
    fontWeight: 600,
    color: "var(--color-text)",
    marginBottom: 8,
  },
  labelHint: {
    fontSize: 11,
    fontWeight: 400,
    color: "var(--color-text-muted)",
    marginLeft: 8,
  },
  textarea: {
    width: "100%",
    minHeight: 120,
    padding: 12,
    background: "var(--color-surface)",
    color: "var(--color-text)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-sm)",
    fontSize: 13,
    fontFamily: "inherit",
    resize: "vertical",
    lineHeight: 1.6,
    boxSizing: "border-box",
  },
  charCount: {
    fontSize: 11,
    color: "var(--color-text-muted)",
    marginTop: 6,
    textAlign: "right",
  },
  actions: {
    padding: "16px 20px",
    display: "flex",
    gap: 12,
    borderBottom: "1px solid var(--color-border)",
  },
  button: {
    padding: "10px 20px",
    borderRadius: "var(--radius-sm)",
    fontSize: 13,
    fontWeight: 600,
    cursor: "pointer",
    transition: "all 0.2s",
    border: "none",
    display: "flex",
    alignItems: "center",
    gap: 8,
    justifyContent: "center",
  },
  primaryButton: {
    flex: 1,
    background: "var(--color-primary)",
    color: "var(--color-text-dark)",
  },
  secondaryButton: {
    background: "var(--color-surface)",
    color: "var(--color-text)",
    border: "1px solid var(--color-border)",
  },
  buttonDisabled: {
    opacity: 0.5,
    cursor: "not-allowed",
  },
  error: {
    margin: "16px 20px",
    padding: "12px",
    background: "rgba(255, 107, 107, 0.1)",
    border: "1px solid #ff6b6b",
    borderRadius: "var(--radius-sm)",
    color: "#ff8888",
    fontSize: 13,
    display: "flex",
    alignItems: "flex-start",
    gap: 12,
  },
  errorIcon: {
    fontSize: 20,
    flexShrink: 0,
  },
  errorTitle: {
    fontWeight: 600,
    marginBottom: 4,
  },
  errorMessage: {
    fontSize: 12,
    lineHeight: 1.5,
  },
  resultsContainer: {
    padding: "20px",
    display: "flex",
    flexDirection: "column",
    gap: 16,
  },
  alignmentCard: {
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius)",
    padding: 16,
  },
  alignmentHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 16,
  },
  alignmentTitle: {
    fontSize: 14,
    fontWeight: 600,
    color: "var(--color-text)",
  },
  detailsButton: {
    background: "transparent",
    color: "var(--color-primary)",
    border: "none",
    fontSize: 12,
    fontWeight: 600,
    cursor: "pointer",
    padding: "4px 8px",
  },
  alignmentScore: {
    display: "flex",
    alignItems: "center",
    gap: 16,
  },
  scoreCircle: {
    width: 80,
    height: 80,
    borderRadius: "50%",
    border: "4px solid",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    flexShrink: 0,
  },
  scoreValue: {
    fontSize: 20,
    fontWeight: 700,
    color: "var(--color-text)",
  },
  scoreInfo: {
    flex: 1,
  },
  scoreLabel: {
    fontSize: 16,
    fontWeight: 600,
    marginBottom: 8,
  },
  warning: {
    padding: "8px 12px",
    background: "rgba(241, 250, 140, 0.1)",
    border: "1px solid rgba(241, 250, 140, 0.3)",
    borderRadius: "var(--radius-sm)",
    fontSize: 12,
    color: "#f1fa8c",
    display: "flex",
    alignItems: "flex-start",
    gap: 8,
    lineHeight: 1.5,
  },
  warningIcon: {
    fontSize: 14,
    flexShrink: 0,
  },
  detailsPanel: {
    marginTop: 16,
    paddingTop: 16,
    borderTop: "1px solid var(--color-border)",
  },
  detailsSection: {
    marginBottom: 16,
  },
  detailsTitle: {
    fontSize: 13,
    fontWeight: 600,
    color: "var(--color-text)",
    margin: "0 0 8px 0",
  },
  detailsList: {
    margin: 0,
    paddingLeft: 20,
  },
  detailsItem: {
    fontSize: 12,
    color: "var(--color-text-muted)",
    lineHeight: 1.6,
    marginBottom: 4,
  },
  textCard: {
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius)",
    overflow: "hidden",
  },
  textHeader: {
    padding: "12px 16px",
    background: "var(--color-bg)",
    borderBottom: "1px solid var(--color-border)",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  textTitle: {
    fontSize: 13,
    fontWeight: 600,
    color: "var(--color-text)",
  },
  copyButton: {
    background: "transparent",
    color: "var(--color-text-muted)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-sm)",
    padding: "4px 8px",
    fontSize: 11,
    fontWeight: 600,
    cursor: "pointer",
    transition: "all 0.2s",
  },
  textContent: {
    padding: 16,
    fontSize: 13,
    lineHeight: 1.7,
    color: "var(--color-text)",
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
  },
  reframedText: {
    background: "rgba(80, 250, 123, 0.05)",
  },
  helpSection: {
    padding: "20px",
    margin: "20px",
    background: "var(--color-surface)",
    borderRadius: "var(--radius)",
  },
  helpTitle: {
    fontSize: 14,
    fontWeight: 600,
    color: "var(--color-text)",
    margin: "0 0 12px 0",
  },
  helpList: {
    margin: 0,
    paddingLeft: 20,
  },
  helpItem: {
    fontSize: 13,
    color: "var(--color-text-muted)",
    lineHeight: 1.6,
    marginBottom: 8,
  },
};

export default ReframePanel;