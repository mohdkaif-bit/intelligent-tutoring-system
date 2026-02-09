import React from "react";

/* ================================
   BUTTON
================================ */

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
}

export const Button: React.FC<ButtonProps> = ({
  variant = "primary",
  children,
  style,
  ...props
}) => {
  const styles: Record<string, React.CSSProperties> = {
    primary: {
      background: "var(--color-primary)",
      color: "var(--color-text-dark)",
    },
    secondary: {
      background: "var(--color-surface-hover)",
      color: "var(--color-text)",
    },
    ghost: {
      background: "transparent",
      color: "var(--color-text)",
      border: "1px solid var(--color-border)",
    },
    danger: {
      background: "var(--color-danger)",
      color: "#fff",
    },
  };

  return (
    <button
      {...props}
      style={{
        border: variant === "ghost" ? "1px solid var(--color-border)" : "none",
        borderRadius: "var(--radius-sm)",
        padding: "8px 14px",
        fontSize: 14,
        fontWeight: 600,
        cursor: props.disabled ? "not-allowed" : "pointer",
        opacity: props.disabled ? 0.6 : 1,
        transition: "all 0.2s",
        ...styles[variant],
        ...style,
      }}
    >
      {children}
    </button>
  );
};

/* ================================
   LOADER
================================ */

interface LoaderProps {
  size?: number;
}

export const Loader: React.FC<LoaderProps> = ({ size = 28 }) => {
  return (
    <div
      style={{
        width: size,
        height: size,
        border: `${Math.max(2, size / 8)}px solid var(--color-border)`,
        borderTop: `${Math.max(2, size / 8)}px solid var(--color-primary)`,
        borderRadius: "50%",
        animation: "spin 0.8s linear infinite",
      }}
    />
  );
};

/* ================================
   GLOBAL SPINNER KEYFRAMES
================================ */

if (typeof document !== "undefined") {
  const styleId = "spinner-keyframes";
  if (!document.getElementById(styleId)) {
    const style = document.createElement("style");
    style.id = styleId;
    style.innerHTML = `
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
`;
    document.head.appendChild(style);
  }
}