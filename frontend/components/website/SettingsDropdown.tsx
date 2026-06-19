"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { useTheme, THEME_CONFIGS } from "@/context/ThemeContext";
import { useAuth } from "@/context/AuthContext";

export function SettingsDropdown() {
  const { theme, setTheme } = useTheme();
  const { user, profile, signOut, loading } = useAuth();
  const [open, setOpen] = useState(false);
  const [themesOpen, setThemesOpen] = useState(false);
  const [toast, setToast] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(""), 3000);
    return () => clearTimeout(timer);
  }, [toast]);

  const initials = profile?.name
    ? profile.name.split(" ").map((n) => n[0]).join("").toUpperCase().slice(0, 2)
    : "CB";

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="h-9 w-9 rounded-xl flex items-center justify-center transition-all duration-200 hover:opacity-80"
        style={{
          background: "var(--bg-card)",
          border: "1px solid var(--border-subtle)",
        }}
        aria-label="Settings"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" style={{ color: "var(--text-secondary)" }}>
          <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
          <circle cx="12" cy="12" r="3" />
        </svg>
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-72 rounded-2xl overflow-hidden z-50"
          style={{
            border: "1px solid var(--border-subtle)",
            background: "var(--bg-secondary)",
            boxShadow: theme === "dark"
              ? "0 16px 48px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.05)"
              : "0 16px 48px rgba(0,0,0,0.12), 0 0 0 1px rgba(0,0,0,0.05)",
          }}
        >
          <div className="p-4" style={{ borderBottom: "1px solid var(--border-subtle)" }}>
            <div className="flex items-center gap-3">
              {profile?.avatar_url ? (
                <img
                  src={profile.avatar_url}
                  alt={profile.name}
                  className="w-10 h-10 rounded-xl flex-shrink-0 object-cover"
                />
              ) : (
                <div
                  className="w-10 h-10 rounded-xl flex items-center justify-center text-sm font-bold text-white flex-shrink-0"
                  style={{ background: "linear-gradient(135deg, #3b82f6, #8b5cf6)" }}
                >
                  {initials}
                </div>
              )}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold truncate" style={{ color: "var(--text-primary)" }}>
                  {profile?.name || "CodeBaseAI"}
                </p>
                <p className="text-xs truncate" style={{ color: "var(--text-muted)" }}>
                  {profile?.email || (user ? "Signed in" : "AI Engineer")}
                </p>
              </div>
            </div>
          </div>

          <div className="p-2">
            {user ? (
              <Link href="/agent/profile" className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-colors hover:opacity-80" onClick={() => setOpen(false)}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ color: "var(--text-muted)" }}>
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                  <circle cx="12" cy="7" r="4" />
                </svg>
                <span style={{ color: "var(--text-secondary)" }}>Profile</span>
              </Link>
            ) : (
              <Link
                href="/login"
                onClick={() => setOpen(false)}
                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-colors hover:opacity-80"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ color: "var(--text-muted)" }}>
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                  <circle cx="12" cy="7" r="4" />
                </svg>
                <span style={{ color: "var(--text-secondary)" }}>Profile</span>
              </Link>
            )}

            <button
              onClick={() => { setToast("Settings coming soon"); setOpen(false); }}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-colors hover:opacity-80"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ color: "var(--text-muted)" }}>
                <circle cx="12" cy="12" r="3" />
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
              </svg>
              <span style={{ color: "var(--text-secondary)" }}>Settings</span>
            </button>
          </div>

          <div className="p-2" style={{ borderTop: "1px solid var(--border-subtle)" }}>
            {user && (
              <button
                onClick={() => { signOut(); setOpen(false); }}
                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-colors hover:opacity-80 mb-1"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ color: "var(--text-muted)" }}>
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                  <polyline points="16 17 21 12 16 7" />
                  <line x1="21" y1="12" x2="9" y2="12" />
                </svg>
                <span style={{ color: "var(--text-secondary)" }}>Sign Out</span>
              </button>
            )}

            <button
              onClick={() => setThemesOpen(!themesOpen)}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-colors hover:opacity-80"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ color: "var(--text-muted)", transform: themesOpen ? "rotate(90deg)" : "none", transition: "transform 0.2s" }}>
                <polyline points="9 18 15 12 9 6" />
              </svg>
              <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
                Themes
              </span>
              <span className="ml-auto text-xs" style={{ color: "var(--text-muted)" }}>
                {THEME_CONFIGS.find((t) => t.id === theme)?.label}
              </span>
            </button>

            {themesOpen && THEME_CONFIGS.map((t) => (
              <button
                key={t.id}
                onClick={() => { setTheme(t.id); setOpen(false); }}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all ${theme === t.id ? "ring-1 ring-[var(--border-subtle)]" : "hover:opacity-80"}`}
                style={{
                  background: theme === t.id ? "var(--bg-card)" : "transparent",
                }}
              >
                <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ml-7" style={{ background: t.previewBg, border: `1px solid ${t.previewBorder}` }}>
                  <div className="w-3 h-3 rounded-full" style={{ background: t.previewAccent }} />
                </div>
                <div className="flex-1 text-left">
                  <span className="font-medium" style={{ color: "var(--text-primary)" }}>{t.label}</span>
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>{t.description}</p>
                </div>
                {theme === t.id && (
                  <svg className="w-4 h-4" style={{ color: "var(--primary)" }} viewBox="0 0 16 16" fill="none">
                    <path d="M4 8l3 3 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                )}
              </button>
            ))}
          </div>
        </div>
      )}

      {toast && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[100] px-4 py-2.5 rounded-xl text-sm font-medium fade-in"
          style={{
            background: "var(--text-primary)",
            color: "var(--bg-primary)",
            boxShadow: "0 8px 24px rgba(0,0,0,0.3)",
          }}
        >
          {toast}
        </div>
      )}
    </div>
  );
}
