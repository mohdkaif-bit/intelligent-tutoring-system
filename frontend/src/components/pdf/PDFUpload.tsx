import { useRef, useState } from "react";

interface PDFUploadProps {
  onFileSelect: (file: File) => void;
}

const PDFUpload = ({ onFileSelect }: PDFUploadProps) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string>("");

  const handleChooseFile = () => {
    console.log("Choose File button clicked");
    fileInputRef.current?.click();
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    console.log("File selected:", file);
    
    if (file) {
      validateAndProcessFile(file);
    }
    
    // Reset input so same file can be selected again
    event.target.value = "";
  };

  const validateAndProcessFile = (file: File) => {
    setError("");

    // Check if it's a PDF
    if (file.type !== "application/pdf") {
      setError("Please select a PDF file");
      return;
    }

    // Optional: Check file size (e.g., max 50MB)
    const maxSize = 50 * 1024 * 1024; // 50MB
    if (file.size > maxSize) {
      setError("File size must be less than 50MB");
      return;
    }

    console.log("File validated successfully:", file.name);
    onFileSelect(file);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const file = e.dataTransfer.files?.[0];
    if (file) {
      validateAndProcessFile(file);
    }
  };

  return (
    <div style={styles.container}>
      <div
        style={{
          ...styles.dropZone,
          ...(isDragging ? styles.dropZoneDragging : {}),
        }}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,application/pdf"
          onChange={handleFileChange}
          style={styles.hiddenInput}
        />

        {/* Upload icon */}
        <div style={styles.iconContainer}>
          <svg
            width="64"
            height="64"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            style={styles.icon}
          >
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="12" y1="18" x2="12" y2="12" />
            <line x1="9" y1="15" x2="15" y2="15" />
          </svg>
        </div>

        {/* Upload text */}
        <h2 style={styles.title}>Upload a PDF Document</h2>
        <p style={styles.subtitle}>
          Drag and drop your PDF here, or click to browse
        </p>

        {/* Choose File button */}
        <button onClick={handleChooseFile} style={styles.chooseButton}>
          Choose File
        </button>

        {/* Error message */}
        {error && <p style={styles.error}>{error}</p>}
      </div>

      {/* Features section */}
      <div style={styles.featuresContainer}>
        <h3 style={styles.featuresTitle}>Features</h3>
        <div style={styles.featuresGrid}>
          <FeatureCard
            icon="💬"
            title="AI Chat"
            description="Ask questions about your document and get instant answers"
          />
          <FeatureCard
            icon="📝"
            title="Quiz Generation"
            description="Generate practice quizzes to test your understanding"
          />
          <FeatureCard
            icon="🎯"
            title="Multiple Modes"
            description="Quick answers, explanations, step-by-step guides, and more"
          />
          <FeatureCard
            icon="📊"
            title="Progress Tracking"
            description="Monitor your learning progress and quiz scores"
          />
        </div>
      </div>
    </div>
  );
};

interface FeatureCardProps {
  icon: string;
  title: string;
  description: string;
}

const FeatureCard = ({ icon, title, description }: FeatureCardProps) => {
  return (
    <div style={styles.featureCard}>
      <div style={styles.featureIcon}>{icon}</div>
      <h4 style={styles.featureTitle}>{title}</h4>
      <p style={styles.featureDescription}>{description}</p>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    padding: "40px 20px",
    maxWidth: 1200,
    margin: "0 auto",
  },
  dropZone: {
    border: "2px dashed var(--color-border)",
    borderRadius: "var(--radius)",
    padding: "60px 40px",
    textAlign: "center",
    background: "var(--color-surface)",
    transition: "all 0.3s ease",
    cursor: "pointer",
  },
  dropZoneDragging: {
    borderColor: "var(--color-primary)",
    background: "rgba(99, 102, 241, 0.05)",
  },
  hiddenInput: {
    display: "none",
  },
  iconContainer: {
    marginBottom: 20,
  },
  icon: {
    color: "var(--color-text-muted)",
  },
  title: {
    fontSize: 24,
    fontWeight: 700,
    color: "var(--color-text)",
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 15,
    color: "var(--color-text-muted)",
    marginBottom: 24,
  },
  chooseButton: {
    background: "#6366f1",
    color: "white",
    border: "none",
    borderRadius: "var(--radius-sm)",
    padding: "12px 32px",
    fontSize: 15,
    fontWeight: 600,
    cursor: "pointer",
    transition: "all 0.2s",
  },
  error: {
    color: "#ef4444",
    fontSize: 14,
    marginTop: 12,
  },
  featuresContainer: {
    marginTop: 60,
  },
  featuresTitle: {
    fontSize: 20,
    fontWeight: 700,
    color: "var(--color-text)",
    marginBottom: 24,
  },
  featuresGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))",
    gap: 20,
  },
  featureCard: {
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius)",
    padding: 24,
    textAlign: "center",
  },
  featureIcon: {
    fontSize: 40,
    marginBottom: 12,
  },
  featureTitle: {
    fontSize: 16,
    fontWeight: 600,
    color: "var(--color-text)",
    marginBottom: 8,
  },
  featureDescription: {
    fontSize: 14,
    color: "var(--color-text-muted)",
    lineHeight: 1.5,
  },
};

export default PDFUpload;