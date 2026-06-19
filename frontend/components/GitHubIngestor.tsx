"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import Link from "next/link";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { GitBranch, Loader2, CheckCircle, AlertCircle, LogIn } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { getSupabase } from "@/lib/supabase";

interface Props {
  onIngestComplete?: () => void;
}

type IngestStatus =
  | { status: "idle" }
  | { status: "submitting" }
  | { status: "pending"; taskId: string }
  | { status: "cloning" }
  | { status: "chunking"; file_count: number }
  | { status: "embedding"; chunk_count: number }
  | { status: "success"; files_processed: number; chunks_created: number }
  | { status: "error"; error: string };

const STATUS_LABELS: Record<string, string> = {
  queued: "Queued...",
  pending: "Starting...",
  cloning: "Cloning repository...",
  chunking: "Parsing code files...",
  indexing: "Generating search index...",
  chunking_complete: "Finalizing...",
  embedding: "Generating embeddings...",
};

export function GitHubIngestor({ onIngestComplete }: Props) {
  const { user, signIn } = useAuth();
  const [repoUrl, setRepoUrl] = useState("");
  const [branch, setBranch] = useState("");
  const [state, setState] = useState<IngestStatus>({ status: "idle" });
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  const startPolling = useCallback((taskId: string) => {
    stopPolling();
    pollingRef.current = setInterval(async () => {
      try {
        const res = await fetch(`/api/ingest/github?task_id=${taskId}`);
        if (!res.ok) {
          stopPolling();
          setState({ status: "error", error: "Failed to check status" });
          return;
        }
        const data = await res.json();

        if (data.status === "success") {
          stopPolling();
          setState({
            status: "success",
            files_processed: data.files_processed,
            chunks_created: data.chunks_created,
          });
          onIngestComplete?.();
        } else if (data.status === "error") {
          stopPolling();
          setState({ status: "error", error: data.error || "Ingestion failed" });
        } else {
          setState((prev) => {
            if (prev.status !== "success" && prev.status !== "error") {
              const newState: Record<string, unknown> = { status: data.status };
              if (data.file_count) newState.file_count = data.file_count;
              if (data.chunk_count) newState.chunk_count = data.chunk_count;
              return newState as IngestStatus;
            }
            return prev;
          });
        }
      } catch {
        // ignore polling errors, will retry
      }
    }, 2000);
  }, [onIngestComplete, stopPolling]);

  useEffect(() => {
    return () => stopPolling();
  }, [stopPolling]);

  const handleIngest = async () => {
    if (!repoUrl.trim()) return;

    setState({ status: "submitting" });

    try {
      const params = new URLSearchParams({ repo_url: repoUrl });
      if (branch) params.append("branch", branch);

      const headers: Record<string, string> = {};
      try {
        const supabase = getSupabase();
        if (supabase) {
          const { data } = await supabase.auth.getSession();
          if (data.session?.access_token) {
            headers["Authorization"] = `Bearer ${data.session.access_token}`;
          }
        }
      } catch {
        // User not logged in - proceed without auth
      }

      const res = await fetch(`/api/ingest/github?${params}`, {
        method: "POST",
        headers,
      });

      const data = await res.json();

      if (!res.ok) {
        setState({ status: "error", error: data.detail || data.error || "Ingestion failed" });
        return;
      }

      if (data.task_id) {
        setState({ status: "pending", taskId: data.task_id });
        startPolling(data.task_id);
      } else if (data.status === "success") {
        setState({
          status: "success",
          files_processed: data.files_processed,
          chunks_created: data.chunks_created,
        });
        onIngestComplete?.();
      }
    } catch (err: unknown) {
      setState({ status: "error", error: err instanceof Error ? err.message : "Unknown error" });
    }
  };

  const statusLabel =
    state.status === "submitting" ? "Starting..." :
    state.status !== "idle" && state.status !== "success" && state.status !== "error"
      ? STATUS_LABELS[state.status] || `Processing...`
      : null;

  return (
    <Card className="w-full border overflow-hidden" style={{ borderColor: "var(--border-subtle)", background: "var(--bg-card)" }}>
      <div className="h-1 bg-gradient-to-r from-[#8b5cf6] to-transparent" />

      <CardContent className="pt-6">
        <div className="flex items-center gap-2 mb-4">
          <GitBranch className="h-4 w-4 text-[#8b5cf6]" />
          <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
            Add GitHub Repository
          </span>
        </div>

        {!user ? (
          <div className="flex flex-col items-center gap-4 py-6 text-center">
            <div className="rounded-full p-3" style={{ background: "var(--bg-secondary)" }}>
              <LogIn className="h-5 w-5 text-[#8b5cf6]" />
            </div>
            <div>
              <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>Sign in to ingest repos</p>
              <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                Track your ingested repositories and manage them from your profile.
              </p>
            </div>
            <button
              onClick={signIn}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-xl transition-all hover:opacity-80"
              style={{
                color: "var(--text-primary)",
                border: "1px solid var(--border-subtle)",
                background: "var(--bg-card)",
              }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4" />
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
              </svg>
              Sign in with Google
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            <Input
              placeholder="https://github.com/username/repo"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              disabled={state.status !== "idle" && state.status !== "error" && state.status !== "success"}
            />
            <div className="flex gap-2">
              <Input
                placeholder="Branch (optional, default: main)"
                value={branch}
                onChange={(e) => setBranch(e.target.value)}
                disabled={state.status !== "idle" && state.status !== "error" && state.status !== "success"}
                className="flex-1"
              />
              <Button
                onClick={handleIngest}
                disabled={!(state.status === "idle" || state.status === "error" || state.status === "success") || !repoUrl.trim()}
                style={{
                  background: (state.status === "idle" || state.status === "error" || state.status === "success") && repoUrl.trim()
                    ? "linear-gradient(135deg, #8b5cf6, #3b82f6)"
                    : undefined,
                }}
              >
                {statusLabel ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    {statusLabel}
                  </>
                ) : (
                  "Ingest"
                )}
              </Button>
            </div>

            {state.status === "error" && (
              <div className="flex items-center gap-2 text-sm text-red-500">
                <AlertCircle className="h-4 w-4" />
                {state.error}
              </div>
            )}

            {state.status === "success" && (
              <div className="flex items-center gap-2 text-sm text-[#16a34a]">
                <CheckCircle className="h-4 w-4" />
                Processed {state.files_processed} files, created {state.chunks_created} chunks
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
