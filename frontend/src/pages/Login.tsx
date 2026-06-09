import React, { useState } from "react";
import { supabase } from "../lib/supabase";

type Tab = "signin" | "signup";

const BACKEND = "http://localhost:8000";

const Login: React.FC = () => {
  const [tab, setTab] = useState<Tab>("signin");

  // Sign in state
  const [siEmail, setSiEmail]       = useState("");
  const [siPassword, setSiPassword] = useState("");
  const [siError, setSiError]       = useState<string | null>(null);
  const [siLoading, setSiLoading]   = useState(false);

  // Sign up state
  const [suName, setSuName]         = useState("");
  const [suEmail, setSuEmail]       = useState("");
  const [suPassword, setSuPassword] = useState("");
  const [suError, setSuError]       = useState<string | null>(null);
  const [suSuccess, setSuSuccess]   = useState<string | null>(null);
  const [suLoading, setSuLoading]   = useState(false);

  // Password visibility
  const [siShowPw, setSiShowPw] = useState(false);
  const [suShowPw, setSuShowPw] = useState(false);

  // Google OAuth loading
  const [googleLoading, setGoogleLoading] = useState(false);

  // ── Handlers ──────────────────────────────────────────────────────────────

  const handleGoogleAuth = () => {
    setGoogleLoading(true);
    // Backend redirect flow — backend generates the Supabase OAuth URL and
    // redirects to Google. On return, /auth/google/callback issues tokens.
    window.location.href = `${BACKEND}/api/v1/auth/google`;
  };

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    setSiError(null);
    setSiLoading(true);
    const { error } = await supabase.auth.signInWithPassword({
      email: siEmail,
      password: siPassword,
    });
    if (error) setSiError(error.message);
    setSiLoading(false);
    // On success, onAuthStateChange in AppContext handles redirect automatically
  };

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    setSuError(null);
    setSuSuccess(null);
    if (suPassword.length < 8) {
      setSuError("Password must be at least 8 characters.");
      return;
    }
    setSuLoading(true);
    const { error } = await supabase.auth.signUp({
      email: suEmail,
      password: suPassword,
      options: { data: { full_name: suName } },
    });
    if (error) {
      setSuError(error.message);
    } else {
      setSuSuccess("Account created! Check your email to confirm.");
    }
    setSuLoading(false);
  };

  // ── Shared UI pieces ──────────────────────────────────────────────────────

  const GoogleButton = () => (
    <button
      type="button"
      style={styles.btnGoogle}
      onClick={handleGoogleAuth}
      disabled={googleLoading}
    >
      {googleLoading ? (
        <span style={styles.googleSpinner} />
      ) : (
        <GoogleIcon />
      )}
      {googleLoading
        ? "Redirecting..."
        : tab === "signin"
        ? "Sign in with Google"
        : "Sign up with Google"}
    </button>
  );

  const Divider = () => (
    <div style={styles.divider}>
      <span style={styles.dividerLine} />
      <span style={styles.dividerText}>or</span>
      <span style={styles.dividerLine} />
    </div>
  );

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div style={styles.wrap}>
      <div style={styles.card}>

        {/* Logo */}
        <div style={styles.logo}>
          <div style={styles.logoIcon}>📖</div>
          <span style={styles.logoText}>Personalized Learning Buddy</span>
        </div>

        {/* Tabs */}
        <div style={styles.tabs}>
          <button
            style={{ ...styles.tab, ...(tab === "signin" ? styles.tabActive : styles.tabInactive) }}
            onClick={() => setTab("signin")}
          >
            Sign in
          </button>
          <button
            style={{ ...styles.tab, ...(tab === "signup" ? styles.tabActive : styles.tabInactive) }}
            onClick={() => setTab("signup")}
          >
            Sign up
          </button>
        </div>

        {/* ── Sign In ── */}
        {tab === "signin" && (
          <form onSubmit={handleSignIn}>
            <GoogleButton />
            <Divider />

            {siError && <div style={styles.error}>{siError}</div>}

            <div style={styles.group}>
              <label style={styles.label}>Email</label>
              <input
                style={styles.input}
                type="email"
                placeholder="you@example.com"
                value={siEmail}
                onChange={(e) => setSiEmail(e.target.value)}
                required
              />
            </div>

            <div style={styles.group}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <label style={styles.label}>Password</label>
                <span
                  style={styles.forgotLink}
                  onClick={async () => {
                    if (!siEmail) { setSiError("Enter your email first."); return; }
                    await supabase.auth.resetPasswordForEmail(siEmail);
                    setSiError(null);
                    alert("Password reset email sent!");
                  }}
                >
                  Forgot password?
                </span>
              </div>
              <div style={styles.passwordWrap}>
                <input
                  style={styles.input}
                  type={siShowPw ? "text" : "password"}
                  placeholder="••••••••"
                  value={siPassword}
                  onChange={(e) => setSiPassword(e.target.value)}
                  required
                />
                <button
                  type="button"
                  style={styles.eyeBtn}
                  onClick={() => setSiShowPw((v) => !v)}
                >
                  {siShowPw ? "🙈" : "👁"}
                </button>
              </div>
            </div>

            <button style={styles.btnPrimary} type="submit" disabled={siLoading}>
              {siLoading ? "Signing in..." : "Sign in"}
            </button>
          </form>
        )}

        {/* ── Sign Up ── */}
        {tab === "signup" && (
          <form onSubmit={handleSignUp}>
            <GoogleButton />
            <Divider />

            {suError   && <div style={styles.error}>{suError}</div>}
            {suSuccess && <div style={styles.success}>{suSuccess}</div>}

            <div style={styles.group}>
              <label style={styles.label}>Full name</label>
              <input
                style={styles.input}
                type="text"
                placeholder="Jane Smith"
                value={suName}
                onChange={(e) => setSuName(e.target.value)}
                required
              />
            </div>

            <div style={styles.group}>
              <label style={styles.label}>Email</label>
              <input
                style={styles.input}
                type="email"
                placeholder="you@example.com"
                value={suEmail}
                onChange={(e) => setSuEmail(e.target.value)}
                required
              />
            </div>

            <div style={styles.group}>
              <label style={styles.label}>Password</label>
              <div style={styles.passwordWrap}>
                <input
                  style={styles.input}
                  type={suShowPw ? "text" : "password"}
                  placeholder="Min. 8 characters"
                  value={suPassword}
                  onChange={(e) => setSuPassword(e.target.value)}
                  required
                />
                <button
                  type="button"
                  style={styles.eyeBtn}
                  onClick={() => setSuShowPw((v) => !v)}
                >
                  {suShowPw ? "🙈" : "👁"}
                </button>
              </div>
            </div>

            <button style={styles.btnPrimary} type="submit" disabled={suLoading}>
              {suLoading ? "Creating account..." : "Create account"}
            </button>

            <p style={styles.terms}>
              By signing up you agree to our Terms and Privacy Policy.
            </p>
          </form>
        )}

      </div>
    </div>
  );
};

// ── Google SVG icon ───────────────────────────────────────────────────────────

const GoogleIcon: React.FC = () => (
  <svg width="18" height="18" viewBox="0 0 18 18" style={{ flexShrink: 0 }}>
    <path
      fill="#4285F4"
      d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615Z"
    />
    <path
      fill="#34A853"
      d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18Z"
    />
    <path
      fill="#FBBC05"
      d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332Z"
    />
    <path
      fill="#EA4335"
      d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58Z"
    />
  </svg>
);

// ── Styles ────────────────────────────────────────────────────────────────────

const styles: Record<string, React.CSSProperties> = {
  wrap: {
    minHeight: "100vh",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: "var(--color-bg)",
    padding: "2rem 1rem",
  },
  card: {
    background: "var(--color-surface)",
    border: "0.5px solid var(--color-border)",
    borderRadius: 16,
    padding: "2.5rem 2rem",
    width: "100%",
    maxWidth: 400,
  },
  logo: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    marginBottom: "2rem",
  },
  logoIcon: {
    width: 36,
    height: 36,
    background: "var(--color-primary)",
    borderRadius: 10,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 18,
  },
  logoText: {
    fontSize: 18,
    fontWeight: 500,
    color: "var(--color-text)",
  },
  tabs: {
    display: "flex",
    background: "var(--color-bg)",
    borderRadius: 10,
    padding: 4,
    marginBottom: "2rem",
    gap: 4,
  },
  tab: {
    flex: 1,
    padding: "8px",
    textAlign: "center",
    fontSize: 14,
    fontWeight: 500,
    borderRadius: 7,
    cursor: "pointer",
    border: "none",
    transition: "all 0.15s",
  },
  tabActive: {
    background: "var(--color-primary)",
    color: "#fff",
  },
  tabInactive: {
    background: "transparent",
    color: "var(--color-text-muted)",
  },

  // ── Google button ──────────────────────────────────────────────────────────
  btnGoogle: {
    width: "100%",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
    padding: "10px 14px",
    background: "var(--color-bg)",
    border: "0.5px solid var(--color-border)",
    borderRadius: 8,
    fontSize: 14,
    fontWeight: 500,
    color: "var(--color-text)",
    cursor: "pointer",
    transition: "opacity 0.15s",
    marginBottom: 0,
  },
  googleSpinner: {
    width: 18,
    height: 18,
    border: "2px solid var(--color-border)",
    borderTop: "2px solid var(--color-primary)",
    borderRadius: "50%",
    display: "inline-block",
    animation: "spin 0.7s linear infinite",
    flexShrink: 0,
  },

  // ── Divider ────────────────────────────────────────────────────────────────
  divider: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    margin: "1.25rem 0",
  },
  dividerLine: {
    flex: 1,
    height: "0.5px",
    background: "var(--color-border)",
    display: "block",
  },
  dividerText: {
    fontSize: 12,
    color: "var(--color-text-muted)",
    whiteSpace: "nowrap",
  },

  group: {
    marginBottom: "1rem",
  },
  label: {
    display: "block",
    fontSize: 13,
    color: "var(--color-text-muted)",
    marginBottom: 6,
  },
  input: {
    width: "100%",
    background: "var(--color-bg)",
    border: "0.5px solid var(--color-border)",
    borderRadius: 8,
    padding: "10px 14px",
    fontSize: 14,
    color: "var(--color-text)",
    outline: "none",
    boxSizing: "border-box",
  },
  passwordWrap: {
    position: "relative",
  },
  eyeBtn: {
    position: "absolute",
    right: 12,
    top: "50%",
    transform: "translateY(-50%)",
    background: "none",
    border: "none",
    color: "var(--color-text-muted)",
    cursor: "pointer",
    padding: 0,
    fontSize: 14,
  },
  btnPrimary: {
    width: "100%",
    padding: 11,
    background: "var(--color-primary)",
    color: "#fff",
    border: "none",
    borderRadius: 8,
    fontSize: 14,
    fontWeight: 500,
    cursor: "pointer",
    marginTop: "0.5rem",
  },
  forgotLink: {
    fontSize: 12,
    color: "var(--color-primary)",
    cursor: "pointer",
  },
  error: {
    background: "rgba(255,85,85,0.1)",
    border: "0.5px solid rgba(255,85,85,0.3)",
    borderRadius: 8,
    padding: "10px 14px",
    fontSize: 13,
    color: "var(--color-danger)",
    marginBottom: "1rem",
  },
  success: {
    background: "rgba(80,250,123,0.08)",
    border: "0.5px solid rgba(80,250,123,0.25)",
    borderRadius: 8,
    padding: "10px 14px",
    fontSize: 13,
    color: "var(--color-success)",
    marginBottom: "1rem",
  },
  terms: {
    fontSize: 12,
    color: "var(--color-text-muted)",
    textAlign: "center",
    marginTop: "1rem",
    lineHeight: 1.6,
  },
};

// Spinner keyframes — inject once
if (typeof document !== "undefined") {
  const id = "google-spinner-style";
  if (!document.getElementById(id)) {
    const s = document.createElement("style");
    s.id = id;
    s.textContent = "@keyframes spin { to { transform: rotate(360deg); } }";
    document.head.appendChild(s);
  }
}

export default Login;