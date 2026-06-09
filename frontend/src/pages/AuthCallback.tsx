import React, { useEffect, useState } from "react";
import { supabase } from "../lib/supabase";

/**
 * AuthCallback
 *
 * Landing page after Google OAuth completes.
 * Backend redirects here with tokens in query params:
 *   /auth/callback?access_token=...&refresh_token=...&expires_in=3600
 *
 * This page:
 *   1. Reads tokens from the URL
 *   2. Calls supabase.auth.setSession() — establishes the local session
 *   3. onAuthStateChange in AppContext fires → user is logged in
 *   4. Redirects to the app (or shows an error)
 *
 * Route: add this in your router as path="/auth/callback"
 */
const AuthCallback: React.FC = () => {
  const [status, setStatus] = useState<"loading" | "error">("loading");
  const [errorMsg, setErrorMsg] = useState<string>("");

  useEffect(() => {
    const run = async () => {
      const params = new URLSearchParams(window.location.search);
      const accessToken  = params.get("access_token");
      const refreshToken = params.get("refresh_token");
      const error        = params.get("error");

      // ── Error from backend ────────────────────────────────────────────────
      if (error) {
        setErrorMsg(`Authentication failed: ${error}`);
        setStatus("error");
        return;
      }

      // ── Missing tokens ────────────────────────────────────────────────────
      if (!accessToken || !refreshToken) {
        setErrorMsg("No tokens received. Please try signing in again.");
        setStatus("error");
        return;
      }

      // ── Establish session ─────────────────────────────────────────────────
      // setSession tells the Supabase client about the tokens the backend
      // obtained. This triggers onAuthStateChange → AppContext logs the user in.
      const { error: sessionError } = await supabase.auth.setSession({
        access_token:  accessToken,
        refresh_token: refreshToken,
      });

      if (sessionError) {
        console.error("setSession error:", sessionError);
        setErrorMsg("Could not establish session. Please try again.");
        setStatus("error");
        return;
      }

      // ── Clean URL and redirect ────────────────────────────────────────────
      // Remove tokens from browser history (security hygiene)
      window.history.replaceState({}, document.title, "/auth/callback");

      // AppContext's onAuthStateChange fires here and handles the redirect.
      // If for some reason it doesn't, fall back after a short delay.
      setTimeout(() => {
        window.location.replace("/");
      }, 500);
    };

    run();
  }, []);

  // ── Loading state ─────────────────────────────────────────────────────────
  if (status === "loading") {
    return (
      <div style={styles.wrap}>
        <div style={styles.card}>
          <div style={styles.spinner} />
          <p style={styles.message}>Signing you in...</p>
        </div>
      </div>
    );
  }

  // ── Error state ───────────────────────────────────────────────────────────
  return (
    <div style={styles.wrap}>
      <div style={styles.card}>
        <div style={styles.errorIcon}>✕</div>
        <p style={styles.errorTitle}>Sign in failed</p>
        <p style={styles.errorMsg}>{errorMsg}</p>
        <button
          style={styles.retryBtn}
          onClick={() => window.location.replace("/")}
        >
          Back to sign in
        </button>
      </div>
    </div>
  );
};

// ── Styles ────────────────────────────────────────────────────────────────────

const styles: Record<string, React.CSSProperties> = {
  wrap: {
    minHeight: "100vh",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: "var(--color-bg)",
  },
  card: {
    background: "var(--color-surface)",
    border: "0.5px solid var(--color-border)",
    borderRadius: 16,
    padding: "3rem 2.5rem",
    width: "100%",
    maxWidth: 360,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: "1rem",
  },
  spinner: {
    width: 36,
    height: 36,
    border: "3px solid var(--color-border)",
    borderTop: "3px solid var(--color-primary)",
    borderRadius: "50%",
    animation: "spin 0.7s linear infinite",
  },
  message: {
    fontSize: 15,
    color: "var(--color-text-muted)",
    margin: 0,
  },
  errorIcon: {
    width: 40,
    height: 40,
    borderRadius: "50%",
    background: "rgba(255,85,85,0.12)",
    color: "var(--color-danger)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 18,
    fontWeight: 600,
  },
  errorTitle: {
    fontSize: 16,
    fontWeight: 500,
    color: "var(--color-text)",
    margin: 0,
  },
  errorMsg: {
    fontSize: 13,
    color: "var(--color-text-muted)",
    margin: 0,
    textAlign: "center",
    lineHeight: 1.6,
  },
  retryBtn: {
    marginTop: "0.5rem",
    padding: "10px 24px",
    background: "var(--color-primary)",
    color: "#fff",
    border: "none",
    borderRadius: 8,
    fontSize: 14,
    fontWeight: 500,
    cursor: "pointer",
  },
};

// Spinner keyframes
if (typeof document !== "undefined") {
  const id = "callback-spinner-style";
  if (!document.getElementById(id)) {
    const s = document.createElement("style");
    s.id = id;
    s.textContent = "@keyframes spin { to { transform: rotate(360deg); } }";
    document.head.appendChild(s);
  }
}

export default AuthCallback;