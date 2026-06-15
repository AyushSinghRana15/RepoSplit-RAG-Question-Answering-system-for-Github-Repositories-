"use client";

import { useState, useRef, useCallback, useEffect } from "react";

export type VoiceState = "idle" | "listening" | "processing" | "speaking";

interface UseVoiceAssistantReturn {
  voiceState: VoiceState;
  transcript: string;
  interimTranscript: string;
  supported: boolean;
  isVoiceMode: boolean;
  toggleVoiceMode: () => void;
  startListening: () => void;
  stopListening: () => void;
  speak: (text: string) => Promise<void>;
  stopSpeaking: () => void;
  onQueryReady: ((query: string) => void) | null;
  setOnQueryReady: (fn: ((query: string) => void) | null) => void;
}

export function useVoiceAssistant(): UseVoiceAssistantReturn {
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [transcript, setTranscript] = useState("");
  const [interimTranscript, setInterimTranscript] = useState("");
  const [isVoiceMode, setIsVoiceMode] = useState(false);
  const [supported, setSupported] = useState(true);

  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const restartTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onQueryReadyRef = useRef<((query: string) => void) | null>(null);
  const voiceStateRef = useRef<VoiceState>("idle");

  voiceStateRef.current = voiceState;

  useEffect(() => {
    const hasSR =
      typeof window !== "undefined" &&
      ("SpeechRecognition" in window || "webkitSpeechRecognition" in window);
    setSupported(hasSR);
  }, []);

  const cleanup = useCallback(() => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
    if (restartTimerRef.current) {
      clearTimeout(restartTimerRef.current);
      restartTimerRef.current = null;
    }
  }, []);

  const submitQuery = useCallback((finalTranscript: string) => {
    cleanup();
    const trimmed = finalTranscript.trim();
    if (!trimmed) return;

    setVoiceState("processing");
    setInterimTranscript("");

    if (onQueryReadyRef.current) {
      onQueryReadyRef.current(trimmed);
    }
  }, [cleanup]);

  const stopListening = useCallback(() => {
    cleanup();
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {
        // already stopped
      }
      recognitionRef.current = null;
    }
    setVoiceState("idle");
  }, [cleanup]);

  const startListening = useCallback(() => {
    if (!supported) return;

    cleanup();

    const SpeechRecognitionAPI =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognitionAPI) return;

    const recognition = new SpeechRecognitionAPI();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let finalTranscript = "";
      let interimTranscript = "";

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          finalTranscript += result[0].transcript;
        } else {
          interimTranscript += result[0].transcript;
        }
      }

      setTranscript((prev) => prev + finalTranscript);
      setInterimTranscript(interimTranscript);

      if (finalTranscript) {
        if (silenceTimerRef.current) {
          clearTimeout(silenceTimerRef.current);
        }
        silenceTimerRef.current = setTimeout(() => {
          const full = (transcript + finalTranscript + interimTranscript).trim();
          if (full) {
            submitQuery(full);
          }
        }, 800);
      }
    };

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      if (event.error === "not-allowed") {
        setVoiceState("idle");
        setIsVoiceMode(false);
        return;
      }
      if (event.error === "no-speech") return;
      if (voiceStateRef.current === "listening") {
        restartTimerRef.current = setTimeout(() => startListening(), 500);
      }
    };

    recognition.onend = () => {
      if (voiceStateRef.current === "listening") {
        restartTimerRef.current = setTimeout(() => startListening(), 100);
      }
    };

    recognitionRef.current = recognition;

    try {
      recognition.start();
      setVoiceState("listening");
    } catch {
      // already started
    }
  }, [supported, cleanup, submitQuery, transcript]);

  const stopSpeaking = useCallback(() => {
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
    setVoiceState("idle");
  }, []);

  const toggleVoiceMode = useCallback(() => {
    setIsVoiceMode((prev) => {
      if (prev) {
        stopListening();
        stopSpeaking();
        setTranscript("");
        setInterimTranscript("");
        setVoiceState("idle");
        return false;
      } else {
        setTranscript("");
        setInterimTranscript("");
        startListening();
        return true;
      }
    });
  }, [startListening, stopListening, stopSpeaking]);

  const speak = useCallback((text: string): Promise<void> => {
    return new Promise((resolve) => {
      if (!("speechSynthesis" in window)) {
        resolve();
        return;
      }

      window.speechSynthesis.cancel();
      setVoiceState("speaking");

      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 0.9;
      utterance.pitch = 1.0;
      utterance.volume = 1.0;

      utterance.onend = () => {
        setVoiceState("listening");
        resolve();
      };

      utterance.onerror = () => {
        setVoiceState("listening");
        resolve();
      };

      window.speechSynthesis.speak(utterance);
    });
  }, []);

  const setOnQueryReady = useCallback((fn: ((query: string) => void) | null) => {
    onQueryReadyRef.current = fn;
  }, []);

  useEffect(() => {
    return () => {
      cleanup();
      if (recognitionRef.current) {
        try { recognitionRef.current.stop(); } catch { /* */ }
      }
      if ("speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, [cleanup]);

  return {
    voiceState,
    transcript,
    interimTranscript,
    supported,
    isVoiceMode,
    toggleVoiceMode,
    startListening,
    stopListening,
    speak,
    stopSpeaking,
    onQueryReady: onQueryReadyRef.current,
    setOnQueryReady,
  };
}
