// LoginPage — sign-in/sign-up form with tabbed UI and animated background

"use client";

import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import Link from "next/link";

// Background floating particle data for animation
const particles = Array.from({ length: 40 }, (_, i) => ({
  id: i,
  size: Math.random() * 4 + 1,
  duration: Math.random() * 20 + 15,
  delay: Math.random() * 20,
  left: Math.random() * 100,
}));

// Login/signup page with Google OAuth, tab switching, and animated backdrop
export default function LoginPage() {
  const { signIn, signInWithEmail, signUpWithEmail, backendError } = useAuth();
  const [tab, setTab] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg("");
    if (!email || !password) {
      setErrorMsg("Email and password are required.");
      return;
    }
    if (tab === "signup" && !name) {
      setErrorMsg("Name is required for sign up.");
      return;
    }
    setSubmitting(true);
    const result = tab === "login"
      ? await signInWithEmail(email, password)
      : await signUpWithEmail(email, password, name);
    setSubmitting(false);
    if (result.error) {
      setErrorMsg(result.error);
    }
  };

  return (
    <main className="min-h-screen flex relative overflow-hidden" style={{ background: "var(--bg-primary)" }}>
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/4 -left-20 w-[500px] h-[500px] rounded-full opacity-20 blur-3xl"
          style={{
            background: "radial-gradient(circle, rgba(59,130,246,0.4), transparent 70%)",
            animation: "orb-float 20s ease-in-out infinite",
          }}
        />
        <div className="absolute bottom-1/4 -right-20 w-[500px] h-[500px] rounded-full opacity-20 blur-3xl"
          style={{
            background: "radial-gradient(circle, rgba(139,92,246,0.4), transparent 70%)",
            animation: "orb-float-delayed 25s ease-in-out infinite",
          }}
        />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[700px] rounded-full opacity-[0.04] blur-2xl"
          style={{
            background: "radial-gradient(circle, #fff, transparent 70%)",
            animation: "orb-float 30s ease-in-out infinite",
          }}
        />
        <div className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage: "radial-gradient(circle at 1px 1px, rgba(255,255,255,0.3) 1px, transparent 0)",
            backgroundSize: "40px 40px",
          }}
        />
        {particles.map((p) => (
          <div
            key={p.id}
            className="absolute rounded-full"
            style={{
              width: p.size,
              height: p.size,
              left: `${p.left}%`,
              bottom: "-10px",
              background: p.id % 3 === 0 ? "rgba(59, 130, 246, 0.4)" : p.id % 3 === 1 ? "rgba(139, 92, 246, 0.4)" : "rgba(255, 255, 255, 0.2)",
              animation: `particle-drift ${p.duration}s linear ${p.delay}s infinite`,
            }}
          />
        ))}
      </div>

      <div className="relative w-full flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-[420px]" style={{ animation: "form-slide-up 0.6s ease-out" }}>
          {/* Header with logo and title */}
          <div className="text-center mb-8" style={{ animation: "form-slide-up 0.6s ease-out 0.1s both" }}>
            <Link href="/" className="inline-flex items-center gap-2 mb-6 group">
              <span className="text-2xl font-bold gradient-text">&lt;/&gt;</span>
              <span className="text-xl font-bold" style={{ color: "var(--text-primary)" }}>
                CodeBase<span className="text-[#3b82f6]">AI</span>
              </span>
            </Link>
            <h1 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
              {tab === "login" ? "Welcome back" : "Create account"}
            </h1>
            <p className="text-sm mt-1.5" style={{ color: "var(--text-muted)" }}>
              {tab === "login" ? "Sign in to continue to your workspace" : "Get started with your free account"}
            </p>
          </div>

          {/* Card container for form */}
          <div
            className="rounded-2xl border p-8 transition-all duration-500"
            style={{
              background: "color-mix(in srgb, var(--bg-card) 95%, transparent)",
              backdropFilter: "blur(20px)",
              WebkitBackdropFilter: "blur(20px)",
              borderColor: "var(--border-subtle)",
              animation: "card-glow 4s ease-in-out infinite, form-slide-up 0.6s ease-out 0.2s both",
            }}
          >
            {/* Tab switcher: Sign In / Sign Up */}
            <div
              className="flex mb-8 rounded-xl p-1"
              style={{ background: "var(--bg-secondary)" }}
            >
              <button
                onClick={() => { setTab("login"); setErrorMsg(""); }}
                className="flex-1 px-4 py-2 text-sm font-medium rounded-lg transition-all duration-300"
                style={{
                  color: tab === "login" ? "var(--text-primary)" : "var(--text-muted)",
                  background: tab === "login" ? "var(--bg-card)" : "transparent",
                  boxShadow: tab === "login" ? "0 1px 3px rgba(0,0,0,0.2)" : "none",
                }}
              >
                Sign In
              </button>
              <button
                onClick={() => { setTab("signup"); setErrorMsg(""); }}
                className="flex-1 px-4 py-2 text-sm font-medium rounded-lg transition-all duration-300"
                style={{
                  color: tab === "signup" ? "var(--text-primary)" : "var(--text-muted)",
                  background: tab === "signup" ? "var(--bg-card)" : "transparent",
                  boxShadow: tab === "signup" ? "0 1px 3px rgba(0,0,0,0.2)" : "none",
                }}
              >
                Sign Up
              </button>
            </div>

            {/* Input form — shows name field for signup, email/password for both */}
            <form onSubmit={handleSubmit} className="space-y-4">
              {tab === "signup" && (
                <div style={{ animation: "form-slide-up 0.4s ease-out" }}>
                  <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--text-muted)" }}>
                    Full Name
                  </label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="John Doe"
                    className="w-full px-4 py-2.5 text-sm rounded-xl border transition-all duration-300 outline-none"
                    style={{
                      background: "var(--bg-secondary)",
                      borderColor: "var(--border-subtle)",
                      color: "var(--text-primary)",
                    }}
                    onFocus={(e) => {
                      e.target.style.borderColor = "#3b82f6";
                      e.target.style.boxShadow = "0 0 0 3px rgba(59, 130, 246, 0.1)";
                    }}
                    onBlur={(e) => {
                      e.target.style.borderColor = "var(--border-subtle)";
                      e.target.style.boxShadow = "none";
                    }}
                  />
                </div>
              )}
              <div style={{ animation: "form-slide-up 0.6s ease-out 0.1s both" }}>
                <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--text-muted)" }}>
                  Email Address
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  className="w-full px-4 py-2.5 text-sm rounded-xl border transition-all duration-300 outline-none"
                  style={{
                    background: "var(--bg-secondary)",
                    borderColor: "var(--border-subtle)",
                    color: "var(--text-primary)",
                  }}
                  onFocus={(e) => {
                    e.target.style.borderColor = "#3b82f6";
                    e.target.style.boxShadow = "0 0 0 3px rgba(59, 130, 246, 0.1)";
                  }}
                  onBlur={(e) => {
                    e.target.style.borderColor = "var(--border-subtle)";
                    e.target.style.boxShadow = "none";
                  }}
                />
              </div>
              <div style={{ animation: "form-slide-up 0.6s ease-out 0.2s both" }}>
                <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--text-muted)" }}>
                  Password
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full px-4 py-2.5 text-sm rounded-xl border transition-all duration-300 outline-none"
                  style={{
                    background: "var(--bg-secondary)",
                    borderColor: "var(--border-subtle)",
                    color: "var(--text-primary)",
                  }}
                  onFocus={(e) => {
                    e.target.style.borderColor = "#3b82f6";
                    e.target.style.boxShadow = "0 0 0 3px rgba(59, 130, 246, 0.1)";
                  }}
                  onBlur={(e) => {
                    e.target.style.borderColor = "var(--border-subtle)";
                    e.target.style.boxShadow = "none";
                  }}
                />
              </div>

              {/* Forgot password link — only shown on login tab */}
              {tab === "login" && (
                <div className="flex justify-end" style={{ animation: "form-slide-up 0.6s ease-out 0.25s both" }}>
                  <button
                    type="button"
                    className="text-xs font-medium transition-all duration-200 hover:opacity-80 hover:underline"
                    style={{ color: "#3b82f6" }}
                  >
                    Forgot password?
                  </button>
                </div>
              )}

              {/* Error message */}
              {(errorMsg || backendError) && (
                <div
                  className="text-xs p-3 rounded-xl border"
                  style={{
                    color: "#ef4444",
                    borderColor: "rgba(239, 68, 68, 0.3)",
                    background: "rgba(239, 68, 68, 0.1)",
                    animation: "form-slide-up 0.6s ease-out 0.3s both",
                  }}
                >
                  {errorMsg || backendError}
                </div>
              )}

              {/* Primary submit button */}
              <button
                type="submit"
                disabled={submitting}
                className="w-full py-2.5 text-sm font-semibold text-white rounded-xl transition-all duration-300 hover:opacity-90 active:scale-[0.98] relative overflow-hidden group disabled:opacity-50"
                style={{
                  background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
                  animation: "form-slide-up 0.6s ease-out 0.3s both",
                }}
              >
                <span className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 disabled:hidden"
                  style={{
                    background: "linear-gradient(135deg, #2563eb, #7c3aed)",
                  }}
                />
                <span className="relative">{submitting ? "Please wait..." : (tab === "login" ? "Sign In" : "Create Account")}</span>
              </button>
            </form>

            {/* Divider between email form and OAuth */}
            <div className="relative my-6" style={{ animation: "form-slide-up 0.6s ease-out 0.35s both" }}>
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t" style={{ borderColor: "var(--border-subtle)" }} />
              </div>
              <div className="relative flex justify-center text-xs">
                <span className="px-3" style={{ background: "color-mix(in srgb, var(--bg-card) 95%, transparent)", color: "var(--text-muted)" }}>
                  or continue with
                </span>
              </div>
            </div>

            {/* Google OAuth button */}
            <button
              onClick={() => { setErrorMsg(""); signIn(); }}
              className="w-full flex items-center justify-center gap-3 px-4 py-2.5 text-sm font-medium rounded-xl border transition-all duration-300 hover:opacity-80 active:scale-[0.98]"
              style={{
                color: "var(--text-primary)",
                borderColor: "var(--border-subtle)",
                background: "var(--bg-secondary)",
                animation: "form-slide-up 0.6s ease-out 0.4s both",
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4" />
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
              </svg>
              Google
            </button>
          </div>

          {/* Tab toggle text — prompts user to switch between login/signup */}
          <p className="text-center text-xs mt-6" style={{ animation: "form-slide-up 0.6s ease-out 0.45s both", color: "var(--text-muted)" }}>
            {tab === "login" ? (
              <>Don&apos;t have an account?{" "}<button onClick={() => setTab("signup")} className="font-medium transition-all duration-200 hover:opacity-80 hover:underline" style={{ color: "#3b82f6" }}>Sign up</button></>
            ) : (
              <>Already have an account?{" "}<button onClick={() => setTab("login")} className="font-medium transition-all duration-200 hover:opacity-80 hover:underline" style={{ color: "#3b82f6" }}>Sign in</button></>
            )}
          </p>

          {/* Back link */}
          <div className="text-center mt-8" style={{ animation: "form-slide-up 0.6s ease-out 0.5s both" }}>
            <Link href="/" className="text-xs transition-all duration-200 hover:opacity-80 hover:gap-3 inline-flex items-center gap-2" style={{ color: "var(--text-muted)" }}>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <line x1="19" y1="12" x2="5" y2="12" />
                <polyline points="12 19 5 12 12 5" />
              </svg>
              Back to home
            </Link>
          </div>
        </div>
      </div>
    </main>
  );
}
