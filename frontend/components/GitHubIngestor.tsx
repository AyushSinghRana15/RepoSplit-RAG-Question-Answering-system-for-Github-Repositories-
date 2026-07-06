// GitHubIngestor — form to ingest a GitHub repository with polling status

"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { GitBranch, Loader2, CheckCircle, AlertCircle } from "lucide-react";
import { getSupabase } from "@/lib/supabase";

interface Props {
  onIngestComplete?: () => void;
}

// Union type for all possible ingestion states
type IngestStatus =
  | { status: "idle" }
  | { status: "submitting" }
  | { status: "pending"; taskId: string }
  | { status: "cloning" }
  | { status: "chunking"; file_count: number }
  | { status: "embedding"; chunk_count: number }
  | { status: "success"; files_processed: number; chunks_created: number }
  | { status: "error"; error: string };

// Human-readable labels for backend status values
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
  const [repoUrl, setRepoUrl] = useState("");
  const [branch, setBranch] = useState("");
  const [state, setState] = useState<IngestStatus>({ status: "idle" });
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Clear the polling interval
  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  // Poll ingestion status every 2s until completion or error
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
          // Update state with intermediate progress
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

  // Cleanup polling on unmount
  useEffect(() => {
    return () => stopPolling();
  }, [stopPolling]);

  // Submit ingestion request to backend
  const handleIngest = async () => {
    if (!repoUrl.trim()) return;

    setState({ status: "submitting" });

    try {
      const params = new URLSearchParams({ repo_url: repoUrl });
      if (branch) params.append("branch", branch);

      // Attach auth token if available
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
      </CardContent>
    </Card>
  );
}
