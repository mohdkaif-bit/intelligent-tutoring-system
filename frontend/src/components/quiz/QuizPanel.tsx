import { useState, useCallback } from "react";
import { generateQuiz, evaluateQuiz } from "../../api/api";
import { QuizQuestion, QuizEvaluationResponse } from "../../types/types";
import { Loader, Button } from "../common/Common";

interface QuizPanelProps {
  documentId: string;
  currentPage: number;
}

type QuizState = "idle" | "loading" | "active" | "submitted";

const QuizPanel = ({ documentId, currentPage }: QuizPanelProps) => {
  const [state, setState] = useState<QuizState>("idle");
  const [questions, setQuestions] = useState<QuizQuestion[]>([]);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [evaluation, setEvaluation] = useState<QuizEvaluationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [numQuestions, setNumQuestions] = useState(3);

  const generate = useCallback(async () => {
    setState("loading");
    setError(null);
    setAnswers({});
    setEvaluation(null);
    
    try {
      const res = await generateQuiz({
        document_id: documentId,
        page_number: currentPage,
        num_questions: numQuestions,
      });
      
      if (res.success && res.questions.length > 0) {
        setQuestions(res.questions);
        setState("active");
      } else {
        setError(res.error || "No questions generated");
        setState("idle");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to generate quiz");
      setState("idle");
    }
  }, [documentId, currentPage, numQuestions]);

  const submit = useCallback(async () => {
    // Check all answered
    if (Object.keys(answers).length < questions.length) {
      setError("Please answer all questions before submitting.");
      return;
    }
    
    setState("loading");
    setError(null);
    
    try {
      // Convert answers object keys to strings (backend might expect string keys)
      const stringAnswers: Record<string, string> = {};
      Object.entries(answers).forEach(([key, value]) => {
        stringAnswers[key.toString()] = value;
      });
      
      // Debug: Log what we're sending
      const requestData = {
        document_id: documentId,
        page_number: currentPage,
        answers: stringAnswers,
        questions,
      };
      console.log("Submitting quiz with data:", requestData);
      
      const res = await evaluateQuiz(requestData);
      
      // Debug: Log the response
      console.log("Quiz evaluation response:", res);
      
      setEvaluation(res);
      setState("submitted");
    } catch (e) {
      console.error("Quiz evaluation error:", e);
      setError(e instanceof Error ? e.message : "Failed to evaluate quiz");
      setState("active");
    }
  }, [documentId, currentPage, answers, questions]);

  const reset = useCallback(() => {
    setState("idle");
    setQuestions([]);
    setAnswers({});
    setEvaluation(null);
    setError(null);
  }, []);

  const retry = useCallback(() => {
    setAnswers({});
    setEvaluation(null);
    setState("active");
  }, []);

  // ── Idle: show generate button ──────────────────────────────
  if (state === "idle") {
    return (
      <div style={styles.container}>
        <Header />
        <div style={styles.idleContent}>
          <div style={styles.idleIcon}>📝</div>
          <p style={styles.idleText}>
            Generate a quiz for <strong>page {currentPage}</strong>
          </p>

          {/* Number of questions selector */}
          <div style={styles.questionSelector}>
            <span style={styles.questionLabel}>Questions:</span>
            {[3, 4, 5].map((n) => (
              <button
                key={n}
                onClick={() => setNumQuestions(n)}
                style={{
                  ...styles.questionButton,
                  ...(numQuestions === n ? styles.questionButtonActive : {}),
                }}
              >
                {n}
              </button>
            ))}
          </div>

          <Button onClick={generate}>Generate Quiz</Button>
          {error && <ErrorText>{error}</ErrorText>}
        </div>
      </div>
    );
  }

  // ── Loading ─────────────────────────────────────────────────
  if (state === "loading") {
    return (
      <div style={styles.container}>
        <Header />
        <div style={styles.loadingContent}>
          <Loader size={40} />
          <p style={styles.loadingText}>
            {state === "loading" && evaluation ? "Evaluating answers..." : "Generating quiz..."}
          </p>
        </div>
      </div>
    );
  }

  // ── Active: show questions ──────────────────────────────────
  if (state === "active") {
    const allAnswered = Object.keys(answers).length === questions.length;
    
    return (
      <div style={styles.container}>
        <Header />
        <div style={styles.questionsContent}>
          <div style={styles.progress}>
            <span style={styles.progressText}>
              {Object.keys(answers).length} of {questions.length} answered
            </span>
            <div style={styles.progressBar}>
              <div
                style={{
                  ...styles.progressFill,
                  width: `${(Object.keys(answers).length / questions.length) * 100}%`,
                }}
              />
            </div>
          </div>

          {questions.map((q, i) => (
            <QuestionCard
              key={i}
              index={i}
              question={q}
              selected={answers[i] || null}
              onSelect={(opt) => {
                setAnswers((prev) => ({ ...prev, [i]: opt }));
                setError(null);
              }}
            />
          ))}
          {error && <ErrorText>{error}</ErrorText>}
        </div>
        <div style={styles.footer}>
          <Button variant="ghost" onClick={reset}>
            Cancel
          </Button>
          <Button onClick={submit} disabled={!allAnswered}>
            {allAnswered ? "Submit Answers" : `Answer All (${Object.keys(answers).length}/${questions.length})`}
          </Button>
        </div>
      </div>
    );
  }

  // ── Submitted: show results ─────────────────────────────────
  if (state === "submitted" && evaluation) {
    const pct = Math.round(evaluation.score * 100);
    const isPerfect = pct === 100;
    const isPassing = pct >= 67;
    
    return (
      <div style={styles.container}>
        <Header />
        <div style={styles.resultsContent}>
          {/* Score card */}
          <div style={styles.scoreCard}>
            <div
              style={{
                ...styles.scoreNumber,
                color: isPerfect
                  ? "var(--color-success)"
                  : isPassing
                  ? "#ffb86c"
                  : "var(--color-danger)",
              }}
            >
              {isPerfect ? "🎉 " : ""}{pct}%
            </div>
            <div style={styles.scoreLabel}>
              {evaluation.correct_count} of {evaluation.total_questions} correct
            </div>
            <div style={styles.scoreMessage}>
              {isPerfect
                ? "Perfect score! Excellent work!"
                : isPassing
                ? "Good job! Keep it up!"
                : "Keep practicing!"}
            </div>
          </div>

          {/* Per-question result */}
          {questions.map((q, i) => {
            const isCorrect = evaluation.results[i] === "CORRECT";
            return (
              <div
                key={i}
                style={{
                  ...styles.resultCard,
                  borderColor: isCorrect ? "var(--color-success)" : "var(--color-danger)",
                }}
              >
                <div style={styles.resultHeader}>
                  <span style={styles.resultQuestionNumber}>Q{i + 1}</span>
                  <span
                    style={{
                      ...styles.resultBadge,
                      color: isCorrect ? "var(--color-success)" : "var(--color-danger)",
                    }}
                  >
                    {isCorrect ? "✓ CORRECT" : "✗ INCORRECT"}
                  </span>
                </div>
                <p style={styles.resultQuestion}>{q.question}</p>

                {Object.entries(q.options).map(([key, val]) => {
                  const isYourAnswer = answers[i] === key;
                  const isCorrectAnswer = q.correct_answer === key;
                  
                  let bg = "transparent";
                  if (isCorrectAnswer) bg = "rgba(80, 250, 123, 0.12)";
                  else if (isYourAnswer && !isCorrectAnswer) bg = "rgba(255, 85, 85, 0.12)";

                  return (
                    <div
                      key={key}
                      style={{
                        ...styles.resultOption,
                        background: bg,
                      }}
                    >
                      <span style={styles.resultOptionKey}>{key}.</span>
                      <span style={styles.resultOptionText}>{val}</span>
                      {isCorrectAnswer && (
                        <span style={styles.correctMark}>✓</span>
                      )}
                      {isYourAnswer && !isCorrectAnswer && (
                        <span style={styles.incorrectMark}>✗</span>
                      )}
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
        <div style={styles.footer}>
          <Button onClick={retry} variant="ghost">
            Retry Quiz
          </Button>
          <Button onClick={generate}>New Quiz</Button>
        </div>
      </div>
    );
  }

  return null;
};

// ─── Sub-components ───────────────────────────────────────────

const QuestionCard = ({
  index,
  question,
  selected,
  onSelect,
}: {
  index: number;
  question: QuizQuestion;
  selected: string | null;
  onSelect: (opt: string) => void;
}) => (
  <div style={styles.questionCard}>
    <p style={styles.questionText}>
      <span style={styles.questionNumber}>Q{index + 1}.</span> {question.question}
    </p>
    {Object.entries(question.options).map(([key, val]) => (
      <button
        key={key}
        onClick={() => onSelect(key)}
        style={{
          ...styles.optionButton,
          ...(selected === key ? styles.optionButtonSelected : {}),
        }}
      >
        <span
          style={{
            ...styles.optionCircle,
            ...(selected === key ? styles.optionCircleSelected : {}),
          }}
        >
          {key}
        </span>
        {val}
      </button>
    ))}
  </div>
);

const Header = () => (
  <div style={styles.header}>
    <span style={styles.headerTitle}>📝 Quiz</span>
  </div>
);

const ErrorText = ({ children }: { children: string }) => (
  <div style={styles.errorText}>
    <span style={styles.errorIcon}>⚠️</span>
    {children}
  </div>
);

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: "flex",
    flexDirection: "column",
    height: "100%",
    background: "var(--color-bg)",
  },
  header: {
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
  idleContent: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    gap: 20,
    padding: 24,
  },
  idleIcon: {
    fontSize: 40,
  },
  idleText: {
    color: "var(--color-text-muted)",
    fontSize: 14,
    textAlign: "center",
  },
  questionSelector: {
    display: "flex",
    alignItems: "center",
    gap: 10,
  },
  questionLabel: {
    fontSize: 13,
    color: "var(--color-text-muted)",
  },
  questionButton: {
    width: 36,
    height: 36,
    borderRadius: "var(--radius-sm)",
    border: "1px solid var(--color-border)",
    background: "var(--color-surface-hover)",
    color: "var(--color-text)",
    fontSize: 14,
    fontWeight: 600,
    cursor: "pointer",
    transition: "all 0.2s",
  },
  questionButtonActive: {
    border: "1px solid transparent",
    background: "var(--color-primary)",
    color: "var(--color-text-dark)",
  },
  loadingContent: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    gap: 16,
  },
  loadingText: {
    color: "var(--color-text-muted)",
    fontSize: 14,
  },
  questionsContent: {
    flex: 1,
    overflowY: "auto",
    padding: 16,
    display: "flex",
    flexDirection: "column",
    gap: 16,
  },
  progress: {
    marginBottom: 4,
  },
  progressText: {
    fontSize: 12,
    color: "var(--color-text-muted)",
    marginBottom: 8,
    display: "block",
  },
  progressBar: {
    height: 4,
    background: "var(--color-border)",
    borderRadius: 2,
    overflow: "hidden",
  },
  progressFill: {
    height: "100%",
    background: "var(--color-primary)",
    transition: "width 0.3s ease",
  },
  questionCard: {
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius)",
    padding: 16,
  },
  questionText: {
    fontSize: 14,
    fontWeight: 600,
    color: "var(--color-text)",
    marginBottom: 12,
    lineHeight: 1.5,
  },
  questionNumber: {
    color: "var(--color-primary)",
  },
  optionButton: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    width: "100%",
    textAlign: "left",
    background: "var(--color-surface-hover)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-sm)",
    padding: "8px 12px",
    marginBottom: 6,
    color: "var(--color-text)",
    fontSize: 14,
    cursor: "pointer",
    transition: "all 0.15s",
  },
  optionButtonSelected: {
    background: "rgba(108, 99, 255, 0.15)",
    borderColor: "var(--color-primary)",
  },
  optionCircle: {
    width: 24,
    height: 24,
    borderRadius: "50%",
    border: "2px solid var(--color-border)",
    background: "transparent",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 11,
    fontWeight: 700,
    color: "var(--color-text-muted)",
    flexShrink: 0,
  },
  optionCircleSelected: {
    borderColor: "var(--color-primary)",
    background: "var(--color-primary)",
    color: "var(--color-text-dark)",
  },
  resultsContent: {
    flex: 1,
    overflowY: "auto",
    padding: 16,
    display: "flex",
    flexDirection: "column",
    gap: 16,
  },
  scoreCard: {
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius)",
    padding: 24,
    textAlign: "center",
  },
  scoreNumber: {
    fontSize: 36,
    fontWeight: 700,
  },
  scoreLabel: {
    color: "var(--color-text-muted)",
    fontSize: 14,
    marginTop: 4,
  },
  scoreMessage: {
    color: "var(--color-text)",
    fontSize: 13,
    marginTop: 8,
    fontWeight: 600,
  },
  resultCard: {
    background: "var(--color-surface)",
    border: "1px solid",
    borderRadius: "var(--radius)",
    padding: 14,
  },
  resultHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
  },
  resultQuestionNumber: {
    fontSize: 13,
    fontWeight: 600,
    color: "var(--color-text)",
  },
  resultBadge: {
    fontSize: 12,
    fontWeight: 700,
  },
  resultQuestion: {
    fontSize: 14,
    color: "var(--color-text)",
    marginBottom: 10,
    lineHeight: 1.5,
  },
  resultOption: {
    borderRadius: "var(--radius-sm)",
    padding: "6px 10px",
    marginBottom: 4,
    fontSize: 13,
    color: "var(--color-text)",
    display: "flex",
    alignItems: "center",
    gap: 8,
  },
  resultOptionKey: {
    fontWeight: 600,
    color: "var(--color-text-muted)",
    minWidth: 20,
  },
  resultOptionText: {
    flex: 1,
  },
  correctMark: {
    marginLeft: "auto",
    color: "var(--color-success)",
    fontSize: 12,
  },
  incorrectMark: {
    marginLeft: "auto",
    color: "var(--color-danger)",
    fontSize: 12,
  },
  footer: {
    display: "flex",
    justifyContent: "space-between",
    padding: "12px 16px",
    borderTop: "1px solid var(--color-border)",
    background: "var(--color-surface)",
    flexShrink: 0,
  },
  errorText: {
    color: "var(--color-danger)",
    fontSize: 13,
    textAlign: "center",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
  },
  errorIcon: {
    fontSize: 16,
  },
};

export default QuizPanel;