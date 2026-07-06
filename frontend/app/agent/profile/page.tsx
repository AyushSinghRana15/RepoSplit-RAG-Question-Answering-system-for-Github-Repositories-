// ProfilePage — user profile with details, stats, connected repos, and query history

"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { getSupabase } from "@/lib/supabase";
import { SettingsDropdown } from "@/components/website/SettingsDropdown";

// Types for user history, repos, and stats
interface HistoryItem {
  id: number;
  query: string;
  answer: string;
  created_at: string;
}

interface UserRepo {
  repo_url: string;
  created_at: string;
}

interface UserStats {
  query_count: number;
  repo_count: number;
}

// Profile page — shows user info, edit form, usage stats, repos, and history
export default function ProfilePage() {
  const { user, profile, loading, signIn, refreshProfile } = useAuth();
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(profile?.name || "");
  const [bio, setBio] = useState(profile?.bio || "");
  const [saving, setSaving] = useState(false);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [repos, setRepos] = useState<UserRepo[]>([]);
  const [stats, setStats] = useState<UserStats>({ query_count: 0, repo_count: 0 });
  const [fetchError, setFetchError] = useState("");

  // Sync form fields when profile data loads
  useEffect(() => {
    if (!user) return;
    setName(profile?.name || "");
    setBio(profile?.bio || "");
  }, [profile, user]);

  // Build auth headers from current Supabase session
  const authHeaders = useCallback(async (): Promise<Record<string, string>> => {
    const supabase = getSupabase();
    if (!supabase) return {};
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    return token ? { Authorization: `Bearer ${token}` } : {};
  }, []);

  const fetchWithAuth = useCallback(async (url: string) => {
    const headers = await authHeaders();
    const res = await fetch(url, { headers });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: "Request failed" }));
      throw new Error(err.error || `HTTP ${res.status}`);
    }
    return res.json();
  }, [authHeaders]);

  // Fetch user history, repos, and stats on mount
  useEffect(() => {
    if (!user) return;
    setFetchError("");
    Promise.all([
      fetchWithAuth("/api/auth/history").then(setHistory).catch((e) => { throw e; }),
      fetchWithAuth("/api/auth/repos").then(setRepos).catch((e) => { throw e; }),
      fetchWithAuth("/api/auth/stats").then(setStats).catch((e) => { throw e; }),
    ]).catch((e) => setFetchError(e.message));
  }, [user, fetchWithAuth]);

  // Save profile changes to backend
  const handleSave = async () => {
    setSaving(true);
    try {
      const headers = await authHeaders();
      const res = await fetch("/api/auth/profile", {
        method: "PUT",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify({ name, bio }),
      });
      if (res.ok) {
        await refreshProfile();
        setEditing(false);
      }
    } finally {
      setSaving(false);
    }
  };

  // Loading state
  if (loading) {
    return (
      <main className="min-h-screen flex items-center justify-center" style={{ background: "var(--bg-primary)" }}>
        <p style={{ color: "var(--text-muted)" }}>Loading...</p>
      </main>
    );
  }

  // Not signed in — prompt to authenticate
  if (!user) {
    return (
      <main className="min-h-screen flex flex-col items-center justify-center gap-4" style={{ background: "var(--bg-primary)" }}>
        <h1 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>Sign in to view your profile</h1>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>Connect with Google to access your query history and settings.</p>
        <button
          onClick={signIn}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-xl transition-all"
          style={{
            color: "var(--text-primary)",
            border: "1px solid var(--border-subtle)",
            background: "var(--bg-card)",
          }}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4" />
            <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
            <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
            <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
          </svg>
          Sign in with Google
        </button>
        <Link href="/agent" className="text-xs" style={{ color: "var(--text-muted)" }}>
          ← Back to Assistant
        </Link>
      </main>
    );
  }

  // Generate initials for avatar fallback
  const initials = (profile?.name || "User")
    .split(" ").map((n) => n[0]).join("").toUpperCase().slice(0, 2);

  return (
    <main className="min-h-screen flex flex-col items-center" style={{ background: "var(--bg-primary)" }}>
      {/* Header bar with logo, back link, and settings */}
      <header className="w-full border-b backdrop-blur-md" style={{ background: "color-mix(in srgb, var(--bg-secondary) 85%, transparent)", borderColor: "var(--border-subtle)" }}>
        <div className="max-w-3xl mx-auto px-6 h-14 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <span className="text-base font-bold gradient-text">&lt;/&gt;</span>
            <span className="text-base font-bold" style={{ color: "var(--text-primary)" }}>
              CodeBase<span className="text-[#3b82f6]">AI</span>
            </span>
          </Link>

          <div className="flex items-center gap-4">
            <Link
              href="/agent"
              className="text-xs transition-colors hover:opacity-80"
              style={{ color: "var(--text-muted)" }}
            >
              ← Back to Assistant
            </Link>
            <SettingsDropdown />
          </div>
        </div>
      </header>

      <div className="w-full max-w-2xl px-6 py-12">
        {/* User avatar and name header */}
        <div className="flex items-center gap-6 mb-10">
          {profile?.avatar_url ? (
            <img
              src={profile.avatar_url}
              alt={profile?.name || "User"}
              className="w-20 h-20 rounded-2xl flex-shrink-0 object-cover"
            />
          ) : (
            <div
              className="w-20 h-20 rounded-2xl flex items-center justify-center text-2xl font-bold text-white flex-shrink-0"
              style={{ background: "linear-gradient(135deg, #3b82f6, #8b5cf6)" }}
            >
              {initials}
            </div>
          )}
          <div>
            <h1 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
              {profile?.name || "User"}
            </h1>
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>
              {profile?.bio || profile?.email || "AI Engineer"}
            </p>
          </div>
        </div>

        <div className="space-y-6">
          {/* Profile details section — editable name and bio */}
          <div
            className="rounded-xl p-6 border"
            style={{ background: "var(--bg-card)", borderColor: "var(--border-subtle)" }}
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
                Profile Details
              </h2>
              <button
                onClick={() => setEditing(!editing)}
                className="text-xs font-medium transition-colors hover:opacity-80"
                style={{ color: editing ? "#3b82f6" : "var(--text-secondary)" }}
              >
                {editing ? "Cancel" : "Edit"}
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs mb-1.5" style={{ color: "var(--text-muted)" }}>
                  Display Name
                </label>
                {editing ? (
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full px-3 py-2 text-sm rounded-xl border transition-all focus:outline-none"
                    style={{
                      background: "var(--bg-secondary)",
                      borderColor: "var(--border-subtle)",
                      color: "var(--text-primary)",
                    }}
                  />
                ) : (
                  <p className="text-sm" style={{ color: "var(--text-primary)" }}>{profile?.name || "Not set"}</p>
                )}
              </div>

              <div>
                <label className="block text-xs mb-1.5" style={{ color: "var(--text-muted)" }}>
                  Email
                </label>
                <p className="text-sm" style={{ color: "var(--text-primary)" }}>{profile?.email || user?.email || "Not available"}</p>
              </div>

              <div>
                <label className="block text-xs mb-1.5" style={{ color: "var(--text-muted)" }}>
                  Bio
                </label>
                {editing ? (
                  <textarea
                    value={bio}
                    onChange={(e) => setBio(e.target.value)}
                    rows={2}
                    className="w-full px-3 py-2 text-sm rounded-xl border transition-all focus:outline-none resize-none"
                    style={{
                      background: "var(--bg-secondary)",
                      borderColor: "var(--border-subtle)",
                      color: "var(--text-primary)",
                    }}
                  />
                ) : (
                  <p className="text-sm" style={{ color: "var(--text-primary)" }}>{profile?.bio || "No bio yet"}</p>
                )}
              </div>
            </div>

            {/* Edit mode action buttons */}
            {editing && (
              <div className="flex justify-end gap-3 mt-6">
                <button
                  onClick={() => setEditing(false)}
                  className="px-4 py-2 text-sm font-medium rounded-xl transition-all"
                  style={{
                    border: "1px solid var(--border-subtle)",
                    color: "var(--text-secondary)",
                    background: "transparent",
                  }}
                >
                  Cancel
                </button>
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="px-4 py-2 text-sm font-semibold text-white rounded-xl transition-all"
                  style={{ background: "linear-gradient(135deg, #3b82f6, #8b5cf6)" }}
                >
                  {saving ? "Saving..." : "Save Changes"}
                </button>
              </div>
            )}
          </div>

          {/* Usage stats — query and repo counts */}
          <div
            className="rounded-xl p-6 border"
            style={{ background: "var(--bg-card)", borderColor: "var(--border-subtle)" }}
          >
            <h2 className="text-sm font-semibold uppercase tracking-wider mb-4" style={{ color: "var(--text-muted)" }}>
              Usage Stats
            </h2>
            <div className="grid grid-cols-2 gap-4">
              {[
                { label: "Queries", value: stats.query_count.toLocaleString() },
                { label: "Repos", value: stats.repo_count.toLocaleString() },
              ].map((stat) => (
                <div key={stat.label} className="text-center p-3 rounded-xl" style={{ background: "var(--bg-secondary)" }}>
                  <p className="text-xl font-bold" style={{ color: "var(--text-primary)" }}>{stat.value}</p>
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>{stat.label}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Connected repositories list */}
          <div
            className="rounded-xl p-6 border"
            style={{ background: "var(--bg-card)", borderColor: "var(--border-subtle)" }}
          >
            <h2 className="text-sm font-semibold uppercase tracking-wider mb-4" style={{ color: "var(--text-muted)" }}>
              Connected Repositories
            </h2>
            {repos.length === 0 ? (
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                No repositories ingested yet. Go to the assistant to ingest a GitHub repo.
              </p>
            ) : (
              <div className="space-y-3">
                {repos.map((repo) => (
                  <div
                    key={repo.repo_url}
                    className="flex items-center gap-3 px-3 py-2 rounded-lg"
                    style={{ background: "var(--bg-secondary)" }}
                  >
                    <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: "var(--bg-card)" }}>
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ color: "var(--text-muted)" }}>
                        <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22" />
                      </svg>
                    </div>
                    <span className="text-sm" style={{ color: "var(--text-primary)" }}>{repo.repo_url}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Recent queries list */}
          <div
            className="rounded-xl p-6 border"
            style={{ background: "var(--bg-card)", borderColor: "var(--border-subtle)" }}
          >
            <h2 className="text-sm font-semibold uppercase tracking-wider mb-4" style={{ color: "var(--text-muted)" }}>
              Recent Queries
            </h2>
            {history.length === 0 ? (
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                No queries yet. Start asking questions in the assistant.
              </p>
            ) : (
              <div className="space-y-3 max-h-80 overflow-y-auto">
                {history.slice(0, 10).map((item) => (
                  <div
                    key={item.id}
                    className="px-3 py-2 rounded-lg"
                    style={{ background: "var(--bg-secondary)" }}
                  >
                    <p className="text-sm font-medium truncate" style={{ color: "var(--text-primary)" }}>
                      {item.query}
                    </p>
                    <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                      {new Date(item.created_at).toLocaleDateString()}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
