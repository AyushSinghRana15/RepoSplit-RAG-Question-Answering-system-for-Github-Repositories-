"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

const segments = [
  { text: "File loading is implemented in ", isCode: false },
  { text: "ingestion/loader.py", isCode: true },
  { text: ". The ", isCode: false },
  { text: "walk_repo()", isCode: true },
  { text: " function traverses the repository tree, and ", isCode: false },
  { text: "read_file()", isCode: true },
  { text: " reads each file with encoding error handling.", isCode: false },
];

const totalChars = segments.reduce((acc, s) => acc + s.text.length, 0);
const boundaries: number[] = [];
let cum = 0;
for (const s of segments) {
  boundaries.push(cum);
  cum += s.text.length;
}

type Phase = "user" | "assistant_label" | "typing" | "citations" | "badges" | "input" | "waiting";

export function Hero() {
  const [phase, setPhase] = useState<Phase>("user");
  const [charIndex, setCharIndex] = useState(0);
  const [citationShow, setCitationShow] = useState(0);
  const [badgesShow, setBadgesShow] = useState(false);
  const [inputShow, setInputShow] = useState(false);

  useEffect(() => {
    if (phase !== "typing") return;
    if (charIndex >= totalChars) {
      setPhase("citations");
      return;
    }
    const t = setTimeout(() => setCharIndex((c) => c + 1), 22);
    return () => clearTimeout(t);
  }, [phase, charIndex]);

  useEffect(() => {
    if (phase !== "citations") return;
    if (citationShow >= 2) {
      const t = setTimeout(() => setPhase("badges"), 400);
      return () => clearTimeout(t);
    }
    const t = setTimeout(() => setCitationShow((c) => c + 1), 350);
    return () => clearTimeout(t);
  }, [phase, citationShow]);

  useEffect(() => {
    if (phase !== "badges") return;
    const t = setTimeout(() => { setBadgesShow(true); setPhase("input"); }, 500);
    return () => clearTimeout(t);
  }, [phase]);

  useEffect(() => {
    if (phase !== "input") return;
    const t = setTimeout(() => { setInputShow(true); setPhase("waiting"); }, 600);
    return () => clearTimeout(t);
  }, [phase]);

  useEffect(() => {
    if (phase !== "waiting") return;
    const t = setTimeout(() => {
      setPhase("user");
      setCharIndex(0);
      setCitationShow(0);
      setBadgesShow(false);
      setInputShow(false);
    }, 4000);
    return () => clearTimeout(t);
  }, [phase]);

  const renderTypedAnswer = () => {
    return segments.map((seg, i) => {
      const start = boundaries[i];
      const end = start + seg.text.length;
      const revealed = Math.max(0, Math.min(seg.text.length, charIndex - start));
      const visible = seg.text.slice(0, revealed);
      if (!visible) return null;
      if (seg.isCode) {
        return (
          <span key={i} className="font-mono text-[#3b82f6]">{visible}</span>
        );
      }
      return <span key={i}>{visible}</span>;
    });
  };

  return (
    <section className="relative min-h-[90vh] flex items-center pt-24 overflow-hidden" style={{ background: "var(--bg-primary)" }}>
      <div
        className="absolute inset-0"
        style={{
          backgroundImage: "linear-gradient(var(--border-subtle) 1px, transparent 1px), linear-gradient(90deg, var(--border-subtle) 1px, transparent 1px)",
          backgroundSize: "64px 64px",
          opacity: 0.03,
        }}
      />
      <div
        className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] rounded-full opacity-15"
        style={{
          background: "radial-gradient(circle, rgba(59,130,246,0.25) 0%, rgba(139,92,246,0.08) 50%, transparent 70%)",
          filter: "blur(80px)",
        }}
      />

      <div className="relative max-w-7xl mx-auto px-6 py-16 w-full">
        <div className="grid lg:grid-cols-2 gap-16 items-center">
          <div className="scroll-reveal">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border mb-6" style={{ background: "var(--bg-card)", borderColor: "var(--border-subtle)" }}>
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span style={{ color: "var(--text-secondary)" }}>RAG-powered · AST-aware · Citation-backed</span>
            </div>

            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold leading-[1.05] tracking-tight mb-6" style={{ color: "var(--text-primary)" }}>
              Ask your codebase{" "}
              <span className="gradient-text">anything.</span>
              <br />
              Get answers you can trust.
            </h1>

            <p className="text-lg max-w-xl mb-8 leading-relaxed" style={{ color: "var(--text-secondary)" }}>
              CodeBaseAI ingests any GitHub repo, parses it with AST-aware chunking, and answers
              natural-language questions with precise file citations — zero hallucination.
            </p>

            <div className="flex flex-wrap gap-4">
              <Link
                href="/agent"
                className="inline-flex items-center px-6 py-3 text-sm font-semibold text-white rounded-xl transition-all duration-300 hover:shadow-[0_0_32px_rgba(59,130,246,0.35)]"
                style={{ background: "linear-gradient(135deg, #3b82f6, #8b5cf6)" }}
              >
                Try the Assistant
                <svg className="ml-2 w-4 h-4" viewBox="0 0 16 16" fill="none">
                  <path d="M6 3L11 8L6 13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
              </Link>
              <a
                href="https://github.com/AyushSinghRana15/Codebase-AI-Assistant"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center px-6 py-3 text-sm font-semibold rounded-xl transition-all duration-300"
                style={{ border: "1.5px solid var(--border-subtle)", background: "var(--bg-card)", color: "var(--text-primary)" }}
              >
                View on GitHub
                <svg className="ml-2 w-4 h-4" viewBox="0 0 16 16" fill="none">
                  <path d="M10 3l3 3-3 3M13 6H4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                  <path d="M13 10v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4a1 1 0 011-1h3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
              </a>
            </div>

            <div className="flex items-center gap-3 mt-10 text-sm" style={{ color: "var(--text-muted)" }}>
              <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none">
                <path d="M8 1C4.14 1 1 4.14 1 8s3.14 7 7 7 7-3.14 7-7-3.14-7-7-7z" stroke="currentColor" strokeWidth="1.5" />
                <path d="M5.5 8.5L7 10l3.5-3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <span>80%+ RAGAS eval score · sub-2s answers · 0 hallucinations on test set</span>
            </div>
          </div>

          <div className="hidden lg:block scroll-reveal">
            <div
              className="rounded-2xl overflow-hidden border"
              style={{
                background: "var(--bg-card)",
                borderColor: "var(--border-subtle)",
                boxShadow: "0 0 60px rgba(59,130,246,0.08)",
              }}
            >
              <div className="flex items-center gap-2 px-4 py-3" style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                <div className="w-3 h-3 rounded-full bg-[#ff5f57]" />
                <div className="w-3 h-3 rounded-full bg-[#febc2e]" />
                <div className="w-3 h-3 rounded-full bg-[#28c840]" />
                <span className="ml-2 text-xs font-mono" style={{ color: "var(--text-muted)" }}>
                  codebaseai — Assistant
                </span>
              </div>
              <div className="p-5 space-y-4 min-h-[300px]">
                <div className="flex items-start gap-3 transition-all duration-500" style={{ opacity: phase ? 1 : 0 }}>
                  <div className="w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold text-white flex-shrink-0" style={{ background: "linear-gradient(135deg, #3b82f6, #8b5cf6)" }}>
                    U
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-medium mb-1" style={{ color: "var(--text-muted)" }}>You</div>
                    <div className="text-sm px-3.5 py-2.5 rounded-xl" style={{ background: "var(--bg-secondary)", color: "var(--text-primary)" }}>
                      Where is file loading implemented?
                    </div>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <div
                    className="w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold flex-shrink-0 transition-all duration-500"
                    style={{
                      background: "var(--bg-card)",
                      border: "1px solid var(--border-subtle)",
                      color: "var(--text-primary)",
                      opacity: phase === "user" ? 0 : 1,
                      transform: phase === "user" ? "translateY(8px)" : "translateY(0)",
                    }}
                  >
                    AI
                  </div>
                  <div className="flex-1 min-w-0">
                    <div
                      className="text-xs font-medium mb-1 transition-all duration-500"
                      style={{ color: "var(--text-muted)", opacity: phase === "user" ? 0 : 1 }}
                    >
                      Assistant
                    </div>
                    <div className="text-sm leading-relaxed px-3.5 py-2.5 rounded-xl break-words" style={{ background: "var(--bg-secondary)", color: "var(--text-primary)" }}>
                      {phase === "user" ? (
                        <span className="text-[#3b82f6]/40">▊</span>
                      ) : (
                        <>
                          {renderTypedAnswer()}
                          {phase === "typing" && (
                            <span className="inline-block w-[2px] h-[1em] ml-[1px] align-middle bg-[#3b82f6] animate-pulse" />
                          )}
                        </>
                      )}
                    </div>
                    <div className="flex flex-wrap gap-2 mt-2 min-h-[28px]">
                      {[0, 1].map((i) => {
                        const labels = [
                          { file: "loader.py", symbol: "walk_repo", score: "0.77" },
                          { file: "loader.py", symbol: "read_file", score: "0.84" },
                        ];
                        const l = labels[i];
                        return (
                          <div
                            key={i}
                            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-mono transition-all duration-500"
                            style={{
                              background: "rgba(59,130,246,0.1)",
                              color: "#3b82f6",
                              border: "1px solid rgba(59,130,246,0.2)",
                              opacity: citationShow > i ? 1 : 0,
                              transform: citationShow > i ? "translateY(0) scale(1)" : "translateY(6px) scale(0.95)",
                            }}
                          >
                            <svg className="w-3 h-3" viewBox="0 0 16 16" fill="none">
                              <path d="M14 8.5V12a2 2 0 01-2 2H4a2 2 0 01-2-2V4a2 2 0 012-2h3.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
                              <path d="M11 2l3 3-6 6H8l.5-3L11 2z" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
                            </svg>
                            {l.file} :: {l.symbol}
                            <span className="opacity-60">{l.score}</span>
                          </div>
                        );
                      })}
                    </div>
                    <div
                      className="flex items-center gap-2 mt-2 transition-all duration-500"
                      style={{
                        opacity: badgesShow ? 1 : 0,
                        transform: badgesShow ? "translateY(0)" : "translateY(6px)",
                      }}
                    >
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium" style={{ background: "rgba(16,185,129,0.1)", color: "#10b981" }}>
                        Grounded ✓
                      </span>
                      <span className="text-[10px] font-mono" style={{ color: "var(--text-muted)" }}>
                        Generated in 1.4s
                      </span>
                    </div>
                  </div>
                </div>

                <div
                  className="flex items-center gap-2 px-3 py-2 rounded-lg transition-all duration-500"
                  style={{
                    background: "var(--bg-secondary)",
                    opacity: inputShow ? 1 : 0,
                    transform: inputShow ? "translateY(0)" : "translateY(6px)",
                  }}
                >
                  <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none" style={{ color: "var(--text-muted)" }}>
                    <path d="M14 8.5V12a2 2 0 01-2 2H4a2 2 0 01-2-2V4a2 2 0 012-2h3.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
                    <path d="M11 2l3 3-6 6H8l.5-3L11 2z" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  <span className="text-xs font-mono" style={{ color: "var(--text-muted)" }}>
                    Ask anything about any repository...
                  </span>
                  {inputShow && <span className="w-[2px] h-4 bg-[#3b82f6] animate-pulse ml-auto" />}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
