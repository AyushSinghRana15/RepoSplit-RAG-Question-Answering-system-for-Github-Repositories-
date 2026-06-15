"use client";

import { Header } from "@/components/Header";
import { QueryInput } from "@/components/QueryInput";
import { LoadingState } from "@/components/LoadingState";
import { ResultCard } from "@/components/ResultCard";
import { SourcesPanel } from "@/components/SourcesPanel";
import { ErrorBanner } from "@/components/ErrorBanner";
import { GitHubIngestor } from "@/components/GitHubIngestor";
import { useAsk } from "@/hooks/useAsk";
import { useVoiceAssistant } from "@/hooks/useVoiceAssistant";
import { useEffect, useCallback, useRef } from "react";

export default function Home() {
  const { query, setQuery, result, state, error, submit, reset } = useAsk();
  const voice = useVoiceAssistant();
  const prevResultRef = useRef<string | null>(null);

  const handleVoiceQuery = useCallback((voiceQuery: string) => {
    setQuery(voiceQuery);
    setTimeout(() => {
      const form = document.querySelector("textarea");
      if (form) {
        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
          window.HTMLTextAreaElement.prototype, "value"
        )?.set;
        nativeInputValueSetter?.call(form, voiceQuery);
        form.dispatchEvent(new Event("input", { bubbles: true }));
      }
      submit();
    }, 50);
  }, [setQuery, submit]);

  useEffect(() => {
    voice.setOnQueryReady(handleVoiceQuery);
  }, [handleVoiceQuery, voice]);

  useEffect(() => {
    if (state === "success" && result?.answer && voice.isVoiceMode) {
      if (result.answer !== prevResultRef.current) {
        prevResultRef.current = result.answer;
        voice.speak(result.answer);
      }
    }
    if (state === "error" && voice.isVoiceMode) {
      voice.speak("Sorry, I encountered an error processing your request.");
    }
  }, [state, result, voice]);

  const handleReset = useCallback(() => {
    reset();
    prevResultRef.current = null;
  }, [reset]);

  return (
    <main className="min-h-screen flex flex-col items-center" style={{ background: "var(--bg-primary)" }}>
      <Header />
      <div className="w-full max-w-3xl px-6 py-10 flex flex-col gap-5">
        <div className="text-center mb-4">
          <h1 className="text-2xl sm:text-3xl font-bold mb-2" style={{ color: "var(--text-primary)" }}>
            <span className="gradient-text">CodeBaseAI</span>{" "}
            <span style={{ color: "var(--text-muted)" }}>Assistant</span>
          </h1>
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            Ask natural language questions about any codebase. Get code-grounded answers with file citations.
          </p>
        </div>

        <GitHubIngestor />

        <QueryInput
          value={query}
          onChange={setQuery}
          onSubmit={submit}
          disabled={state === "loading"}
          voiceState={voice.voiceState}
          isVoiceMode={voice.isVoiceMode}
          voiceSupported={voice.supported}
          onVoiceToggle={voice.toggleVoiceMode}
          interimTranscript={voice.interimTranscript}
        />

        {voice.isVoiceMode && (
          <div className="text-center">
            <button
              onClick={voice.toggleVoiceMode}
              className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium transition-opacity hover:opacity-80 cursor-pointer"
              style={{
                background: voice.voiceState === "listening"
                  ? "rgba(59,130,246,0.1)"
                  : voice.voiceState === "speaking"
                  ? "rgba(22,163,74,0.1)"
                  : "rgba(234,88,12,0.1)",
                color: voice.voiceState === "listening"
                  ? "#3b82f6"
                  : voice.voiceState === "speaking"
                  ? "#16a34a"
                  : "#ea580c",
              }}
              title="Click to stop voice mode"
            >
              {voice.voiceState === "listening" && (
                <>
                  <span className="h-2 w-2 rounded-full bg-[#3b82f6] animate-pulse" />
                  Listening — tap to stop
                </>
              )}
              {voice.voiceState === "processing" && "Processing your query..."}
              {voice.voiceState === "speaking" && (
                <>
                  <span className="h-2 w-2 rounded-full bg-[#16a34a] animate-pulse" />
                  Speaking — tap to stop
                </>
              )}
              {voice.voiceState === "idle" && "Voice mode paused — tap to resume"}
            </button>
          </div>
        )}

        {state === "loading" && <LoadingState />}
        {state === "error" && (
          <ErrorBanner message={error!} onRetry={submit} />
        )}

        {state === "success" && result && (
          <>
            <ResultCard
              result={result}
              voiceState={voice.voiceState}
              onSpeak={() => voice.speak(result.answer)}
              onStopSpeaking={voice.stopSpeaking}
            />
            <SourcesPanel sources={result.sources} />
          </>
        )}

        {state !== "idle" && (
          <button
            onClick={handleReset}
            className="text-xs transition-colors self-center py-2 hover:opacity-80"
            style={{ color: "var(--text-muted)" }}
          >
            New query
          </button>
        )}
      </div>
    </main>
  );
}
