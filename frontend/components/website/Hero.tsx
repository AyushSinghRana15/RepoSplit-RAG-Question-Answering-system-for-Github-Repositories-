"use client";

import Link from "next/link";
import { Terminal } from "./Terminal";

const metricChips = [
  { value: "80%+", label: "Eval Score" },
  { value: "<2s", label: "Avg Latency" },
  { value: "11", label: "Pipeline Stages" },
];

export function Hero() {
  return (
    <section id="hero" className="relative min-h-screen flex items-center pt-16 overflow-hidden" style={{ background: "var(--bg-primary)" }}>
      <div
        className="absolute inset-0"
        style={{
          backgroundImage: "linear-gradient(var(--border-subtle) 1px, transparent 1px), linear-gradient(90deg, var(--border-subtle) 1px, transparent 1px)",
          backgroundSize: "64px 64px",
          opacity: 0.03,
        }}
      />
      <div
        className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full opacity-20"
        style={{
          background: "radial-gradient(circle, rgba(59,130,246,0.3) 0%, rgba(139,92,246,0.1) 50%, transparent 70%)",
          filter: "blur(60px)",
        }}
      />

      <div className="relative max-w-7xl mx-auto px-6 py-20 grid lg:grid-cols-2 gap-12 items-center">
        <div>
          <div
            className="sketch-card inline-flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-medium border mb-6"
          >
            <span className="w-2 h-2 rounded-full bg-[#3b82f6] animate-pulse" />
            <span style={{ color: "var(--text-secondary)" }}>Production-ready RAG for code understanding</span>
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold leading-[1.1] tracking-tight mb-6" style={{ color: "var(--text-primary)" }}>
            Ask questions about{" "}
            <span className="gradient-text">any codebase</span>
            <br />
            get grounded answers.
          </h1>

          <p className="text-lg max-w-xl mb-8 leading-relaxed" style={{ color: "var(--text-secondary)" }}>
            CodeBaseAI is a RAG-powered code assistant that ingests repositories,
            understands their structure via AST parsing, and answers natural language
            questions with precise file citations and zero hallucination.
          </p>

          <div className="flex flex-wrap gap-4">
            <Link
              href="/agent"
              className="sketch-btn inline-flex items-center px-6 py-3 text-sm font-semibold text-white rounded-xl transition-all duration-300"
              style={{ background: "linear-gradient(135deg, #3b82f6, #8b5cf6)" }}
            >
              Try the Assistant
              <svg className="ml-2 w-4 h-4" viewBox="0 0 16 16" fill="none">
                <path d="M6 3L11 8L6 13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
            </Link>
            <a
              href="#architecture"
              className="sketch-btn inline-flex items-center px-6 py-3 text-sm font-semibold rounded-xl transition-all duration-300"
              style={{ border: "1.5px solid rgba(59,130,246,0.4)", background: "transparent", color: "var(--text-primary)" }}
            >
              View Architecture
            </a>
          </div>

          <div className="flex flex-wrap gap-3 mt-10">
            {metricChips.map((chip) => (
              <div
                key={chip.label}
                className="sketch-card flex items-center gap-2 px-3 py-1.5 rounded-xl border text-sm"
              >
                <span className="font-bold text-[#3b82f6]">{chip.value}</span>
                <span style={{ color: "var(--text-secondary)" }}>{chip.label}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="hidden lg:block">
          <Terminal />
        </div>
      </div>
    </section>
  );
}
