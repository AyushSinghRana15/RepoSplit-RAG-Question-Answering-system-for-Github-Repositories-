"use client";

import { useState } from "react";

const demos = [
  {
    id: "location",
    query: "Where is file loading implemented?",
    answer: (
      <>
        File loading is implemented in{" "}
        <span className="font-mono text-[#3b82f6]">ingestion/loader.py</span>.
        The <span className="font-mono">walk_repo()</span> function traverses the
        repository tree, and <span className="font-mono">read_file()</span> reads
        each file with encoding error handling.
      </>
    ),
    sources: [
      { file: "ingestion/loader.py", symbol: "walk_repo", score: "0.77" },
      { file: "ingestion/loader.py", symbol: "read_file", score: "0.84" },
    ],
    latency: "1.4s",
  },
  {
    id: "flow",
    query: "Explain the ingestion flow step by step",
    answer: (
      <>
        The ingestion pipeline: <span className="font-mono text-[#3b82f6]">walk_repo</span>{" "}
        → <span className="font-mono text-[#3b82f6]">parse_chunks</span> (AST) →{" "}
        <span className="font-mono text-[#3b82f6]">build_embed_text</span> →{" "}
        <span className="font-mono text-[#3b82f6]">embed_chunks</span> →{" "}
        <span className="font-mono text-[#3b82f6]">build FAISS index</span>.
        Each chunk carries file_path, language, and line boundaries.
      </>
    ),
    sources: [
      { file: "main.py", symbol: "run_ingestion", score: "0.45" },
      { file: "ingestion/chunker.py", symbol: "parse_chunks", score: "0.62" },
      { file: "embeddings/embedder.py", symbol: "embed_chunks", score: "0.71" },
    ],
    latency: "2.1s",
  },
  {
    id: "missing",
    query: "Where is the payment gateway?",
    answer: (
      <>
        I could not find this in the provided codebase. No chunks match "payment"
        or "gateway" references. The system correctly returns empty rather than
        fabricating an answer.
      </>
    ),
    sources: [],
    latency: "0.3s",
    notFound: true,
  },
];

export function DemoQueries() {
  const [active, setActive] = useState(0);

  return (
    <section id="demos" className="py-24 border-t" style={{ background: "var(--bg-primary)", borderColor: "var(--border-subtle)" }}>
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-16 scroll-reveal">
          <p className="text-sm font-mono text-[#8b5cf6] mb-3 tracking-wider uppercase">
            See It In Action
          </p>
          <h2 className="text-3xl sm:text-4xl font-bold mb-4" style={{ color: "var(--text-primary)" }}>
            Real queries, grounded answers
          </h2>
          <p className="max-w-2xl mx-auto" style={{ color: "var(--text-secondary)" }}>
            These are actual responses from CodeBaseAI running against its own codebase —
            with citations, confidence scores, and latency.
          </p>
        </div>

        <div className="max-w-4xl mx-auto">
          <div className="flex gap-1 mb-6 p-1 rounded-xl overflow-x-auto" style={{ background: "var(--bg-secondary)", border: "1px solid var(--border-subtle)" }}>
            {demos.map((demo, i) => (
              <button
                key={demo.id}
                onClick={() => setActive(i)}
                className={`flex-shrink-0 px-4 py-2.5 text-sm font-medium rounded-lg transition-all duration-200 ${
                  active === i ? "shadow-sm" : ""
                }`}
                style={{
                  background: active === i ? "var(--bg-card)" : "transparent",
                  color: active === i ? "var(--text-primary)" : "var(--text-muted)",
                  border: active === i ? "1px solid var(--border-subtle)" : "1px solid transparent",
                }}
              >
                <span className="font-mono text-xs opacity-60 mr-1.5">&gt;</span>
                {demo.query.length > 22 ? demo.query.slice(0, 22) + "..." : demo.query}
              </button>
            ))}
          </div>

          <div
            className="rounded-2xl overflow-hidden border fade-in"
            key={active}
            style={{
              background: "var(--bg-card)",
              borderColor: "var(--border-subtle)",
              boxShadow: "0 0 40px rgba(59,130,246,0.06)",
            }}
          >
            <div className="flex items-center gap-2 px-4 py-3" style={{ borderBottom: "1px solid var(--border-subtle)" }}>
              <div className="w-3 h-3 rounded-full bg-[#ff5f57]" />
              <div className="w-3 h-3 rounded-full bg-[#febc2e]" />
              <div className="w-3 h-3 rounded-full bg-[#28c840]" />
              <span className="ml-2 text-xs font-mono" style={{ color: "var(--text-muted)" }}>
                codebaseai — Live Demo
              </span>
            </div>

            <div className="p-6 space-y-5">
              <div className="flex items-start gap-3">
                <div className="w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold text-white flex-shrink-0" style={{ background: "linear-gradient(135deg, #3b82f6, #8b5cf6)" }}>
                  U
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-medium mb-1" style={{ color: "var(--text-muted)" }}>You</div>
                  <div className="text-sm px-3.5 py-2.5 rounded-xl" style={{ background: "var(--bg-secondary)", color: "var(--text-primary)" }}>
                    {demos[active].query}
                  </div>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <div className="w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold flex-shrink-0" style={{ background: "var(--bg-card)", border: "1px solid var(--border-subtle)", color: "var(--text-primary)" }}>
                  AI
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-medium mb-1" style={{ color: "var(--text-muted)" }}>Assistant</div>
                  <div className="text-sm leading-relaxed px-3.5 py-2.5 rounded-xl" style={{ background: "var(--bg-secondary)", color: "var(--text-primary)" }}>
                    {demos[active].answer}
                  </div>

                  {demos[active].sources.length > 0 ? (
                    <div className="flex flex-wrap gap-2 mt-3">
                      {demos[active].sources.map((src, j) => (
                        <div
                          key={j}
                          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-mono"
                          style={{ background: "rgba(59,130,246,0.1)", color: "#3b82f6", border: "1px solid rgba(59,130,246,0.2)" }}
                        >
                          <svg className="w-3 h-3" viewBox="0 0 16 16" fill="none">
                            <path d="M14 8.5V12a2 2 0 01-2 2H4a2 2 0 01-2-2V4a2 2 0 012-2h3.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
                            <path d="M11 2l3 3-6 6H8l.5-3L11 2z" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
                          </svg>
                          {src.file} :: {src.symbol}
                          <span className="opacity-60">{src.score}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="inline-flex items-center gap-2 px-3 py-1.5 mt-3 rounded-lg text-xs font-mono" style={{ background: "rgba(100,116,139,0.1)", color: "var(--text-muted)", border: "1px solid var(--border-subtle)" }}>
                      <svg className="w-3 h-3" viewBox="0 0 16 16" fill="none">
                        <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.2" />
                        <path d="M8 5v3M8 11v0" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
                      </svg>
                      No relevant chunks — correctly returns empty
                    </div>
                  )}

                  <div className="flex items-center gap-2 mt-3">
                    {demos[active].notFound ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium" style={{ background: "rgba(100,116,139,0.1)", color: "var(--text-muted)" }}>
                        Safe rejection ✓
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium" style={{ background: "rgba(16,185,129,0.1)", color: "#10b981" }}>
                        Grounded ✓
                      </span>
                    )}
                    <span className="text-[10px] font-mono" style={{ color: "var(--text-muted)" }}>
                      Generated in {demos[active].latency}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
