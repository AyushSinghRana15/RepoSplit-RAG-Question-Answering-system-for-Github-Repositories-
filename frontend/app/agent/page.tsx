"use client";

import { Header } from "@/components/Header";
import { QueryInput } from "@/components/QueryInput";
import { LoadingState } from "@/components/LoadingState";
import { ResultCard } from "@/components/ResultCard";
import { SourcesPanel } from "@/components/SourcesPanel";
import { ErrorBanner } from "@/components/ErrorBanner";
import { GitHubIngestor } from "@/components/GitHubIngestor";
import { useAsk } from "@/hooks/useAsk";
import { useAuth } from "@/context/AuthContext";
import { useVoiceAssistant, VoiceState } from "@/hooks/useVoiceAssistant";
import { AudioLines, Bot, Loader2, Mic, Square, User, Volume2, LogIn } from "lucide-react";
import { useEffect, useCallback, useRef } from "react";
import type { ReactNode } from "react";

const VOICE_STATUS: Record<
  VoiceState,
  { label: string; tone: string; icon: typeof Mic }
> = {
  idle: { label: "Paused", tone: "#ea580c", icon: Mic },
  listening: { label: "Listening", tone: "#10a37f", icon: AudioLines },
  processing: { label: "Thinking", tone: "#8b5cf6", icon: Loader2 },
  speaking: { label: "Speaking", tone: "#10a37f", icon: Volume2 },
};

function AssistantAvatar() {
  return (
    <div
      className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full"
      style={{
        background: "linear-gradient(135deg, rgba(16,163,127,0.22), rgba(59,130,246,0.14))",
        color: "#10a37f",
      }}
    >
      <Bot className="h-4 w-4" />
    </div>
  );
}

function UserBubble({ children }: { children: string }) {
  return (
    <div className="flex justify-end">
      <div className="flex max-w-[86%] items-start gap-3 sm:max-w-[76%]">
        <div
          className="rounded-3xl px-4 py-3 text-sm leading-relaxed"
          style={{
            background: "color-mix(in srgb, var(--muted) 78%, white 6%)",
            color: "var(--text-primary)",
          }}
        >
          {children}
        </div>
        <div
          className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full"
          style={{ background: "var(--muted)", color: "var(--text-secondary)" }}
        >
          <User className="h-4 w-4" />
        </div>
      </div>
    </div>
  );
}

function AssistantMessage({ children }: { children: ReactNode }) {
  return (
    <div className="flex items-start gap-3">
      <AssistantAvatar />
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}

function EmptyState() {
  return (
    <section className="flex min-h-[34vh] flex-col items-center justify-center text-center">
      <AssistantAvatar />
      <h1
        className="mt-5 text-2xl font-semibold sm:text-3xl"
        style={{ color: "var(--text-primary)" }}
      >
        What can I help with?
      </h1>
    </section>
  );
}

function VoiceModeStatus({
  voiceState,
  isVoiceMode,
  onStop,
}: {
  voiceState: VoiceState;
  isVoiceMode: boolean;
  onStop: () => void;
}) {
  if (!isVoiceMode) return null;

  const status = VOICE_STATUS[voiceState];
  const Icon = status.icon;

  return (
    <div className="flex justify-center">
      <div
        className="inline-flex items-center gap-3 rounded-full border px-3 py-2 text-xs shadow-lg shadow-black/10"
        style={{
          borderColor: "var(--border-subtle)",
          background: "color-mix(in srgb, var(--bg-card) 92%, white 8%)",
          color: "var(--text-secondary)",
        }}
      >
        <span className="relative flex h-7 w-7 items-center justify-center rounded-full">
          {voiceState === "listening" && (
            <span
              className="absolute inset-0 rounded-full animate-ping"
              style={{ background: "rgba(16,163,127,0.24)" }}
            />
          )}
          <Icon
            className={`relative h-4 w-4 ${voiceState === "processing" ? "animate-spin" : ""}`}
            style={{ color: status.tone }}
          />
        </span>
        <span className="font-medium" style={{ color: "var(--text-primary)" }}>
          {status.label}
        </span>
        <button
          onClick={onStop}
          aria-label="Stop voice mode"
          title="Stop voice mode"
          className="flex h-7 w-7 items-center justify-center rounded-full transition-colors hover:bg-white/10"
          style={{ color: "var(--text-muted)" }}
        >
          <Square className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}

export default function Home() {
  const { query, setQuery, submittedQuery, result, state, error, submit, reset } = useAsk();
  const { user, signIn } = useAuth();
  const {
    voiceState,
    isVoiceMode,
    supported: voiceSupported,
    interimTranscript,
    toggleVoiceMode,
    setOnQueryReady,
    speak,
    stopSpeaking,
  } = useVoiceAssistant();
  const prevSpokenAnswerRef = useRef<string | null>(null);
  const prevSpokenErrorRef = useRef<string | null>(null);

  const handleVoiceQuery = useCallback((voiceQuery: string) => {
    void submit(voiceQuery);
  }, [submit]);

  useEffect(() => {
    setOnQueryReady(handleVoiceQuery);
    return () => setOnQueryReady(null);
  }, [handleVoiceQuery, setOnQueryReady]);

  useEffect(() => {
    if (state !== "success" || !result?.answer || !isVoiceMode) return;
    if (result.answer === prevSpokenAnswerRef.current) return;

    prevSpokenAnswerRef.current = result.answer;
    void speak(result.answer);
  }, [isVoiceMode, result?.answer, speak, state]);

  useEffect(() => {
    if (state !== "error" || !error || !isVoiceMode) return;
    if (error === prevSpokenErrorRef.current) return;

    prevSpokenErrorRef.current = error;
    void speak("Sorry, I encountered an error processing your request.");
  }, [error, isVoiceMode, speak, state]);

  const handleSubmit = useCallback(() => {
    void submit();
  }, [submit]);

  const handleRetry = useCallback(() => {
    void submit(submittedQuery);
  }, [submit, submittedQuery]);

  const handleReset = useCallback(() => {
    reset();
    prevSpokenAnswerRef.current = null;
    prevSpokenErrorRef.current = null;
  }, [reset]);

  return (
    <main
      className="flex min-h-screen flex-col"
      style={{ background: "var(--bg-primary)" }}
    >
      <Header />

      {!user && (
        <div className="flex justify-center px-4 pt-2">
          <button
            onClick={signIn}
            className="group inline-flex items-center gap-2 rounded-xl border px-4 py-2 text-xs transition-all hover:opacity-80"
            style={{ borderColor: "var(--border-subtle)", background: "var(--bg-card)", color: "var(--text-muted)" }}
          >
            <LogIn className="h-3.5 w-3.5 text-[#8b5cf6]" />
            <span>Sign in to save query history, track repos, and personalize your experience</span>
            <svg className="h-3 w-3 transition-transform group-hover:translate-x-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      )}

      <div className="flex flex-1 justify-center">
        <div className="flex min-h-[calc(100vh-3.5rem)] w-full max-w-4xl flex-col px-4 sm:px-6">
          <div className="flex-1 space-y-6 py-6 sm:py-8">
            <GitHubIngestor />

            <VoiceModeStatus
              voiceState={voiceState}
              isVoiceMode={isVoiceMode}
              onStop={toggleVoiceMode}
            />

            {state === "idle" ? (
              <EmptyState />
            ) : (
              <div className="space-y-7">
                {submittedQuery && <UserBubble>{submittedQuery}</UserBubble>}

                {state === "loading" && (
                  <AssistantMessage>
                    <LoadingState />
                  </AssistantMessage>
                )}

                {state === "error" && error && (
                  <AssistantMessage>
                    <ErrorBanner message={error} onRetry={handleRetry} />
                  </AssistantMessage>
                )}

                {state === "success" && result && (
                  <AssistantMessage>
                    <div className="space-y-4">
                      <ResultCard
                        result={result}
                        voiceState={voiceState}
                        onSpeak={() => void speak(result.answer)}
                        onStopSpeaking={stopSpeaking}
                      />
                      <SourcesPanel sources={result.sources} />
                    </div>
                  </AssistantMessage>
                )}
              </div>
            )}

            {state !== "idle" && (
              <div className="flex justify-center">
                <button
                  onClick={handleReset}
                  className="rounded-full px-3 py-2 text-xs transition-colors hover:bg-white/10"
                  style={{ color: "var(--text-muted)" }}
                >
                  New query
                </button>
              </div>
            )}
          </div>

          <div
            className="sticky bottom-0 pb-4 pt-3"
            style={{
              background:
                "linear-gradient(to top, var(--bg-primary) 72%, color-mix(in srgb, var(--bg-primary) 0%, transparent))",
            }}
          >
            <QueryInput
              value={query}
              onChange={setQuery}
              onSubmit={handleSubmit}
              disabled={state === "loading"}
              voiceState={voiceState}
              isVoiceMode={isVoiceMode}
              voiceSupported={voiceSupported}
              onVoiceToggle={toggleVoiceMode}
              interimTranscript={interimTranscript}
            />
          </div>
        </div>
      </div>
    </main>
  );
}
