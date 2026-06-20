"use client";

const features = [
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
        <path d="M14 8.5V12a2 2 0 01-2 2H4a2 2 0 01-2-2V4a2 2 0 012-2h3.5" />
        <path d="M11 2l3 3-6 6H8l.5-3L11 2z" />
        <path d="M16 12h4v4a2 2 0 01-2 2h-4" />
        <path d="M12 16v4h4" />
      </svg>
    ),
    title: "Answers that cite their source",
    description: "Every response includes exact file paths, line numbers, and similarity scores. No black-box answers — you can verify every claim against the source code.",
    gradient: "from-blue-500/20 to-blue-600/5",
  },
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
        <path d="M12 20h9" />
        <path d="M16.5 3.5a2.121 2.121 0 013 3L7 19l-4 1 1-4L16.5 3.5z" />
      </svg>
    ),
    title: "Understands code structure, not just text",
    description: "AST-aware chunking splits at function and class boundaries — not arbitrary token limits. The parser preserves hierarchy, docstrings, and call relationships.",
    gradient: "from-purple-500/20 to-purple-600/5",
  },
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
        <circle cx="11" cy="11" r="8" />
        <path d="M21 21l-4.35-4.35" />
        <path d="M8 11h6" />
        <path d="M11 8v6" />
      </svg>
    ),
    title: "Finds it by meaning or by exact name",
    description: "Hybrid retrieval fuses FAISS semantic search with BM25 keyword matching via RRF fusion. Whether you describe what you want or name it precisely — it works.",
    gradient: "from-emerald-500/20 to-emerald-600/5",
  },
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
        <path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71" />
        <path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71" />
      </svg>
    ),
    title: "Follows the call chain automatically",
    description: "Dependency graph traces function calls and imports. Ask \u201chow does this flow work?\u201d and it pulls in caller, callee, and related context automatically.",
    gradient: "from-amber-500/20 to-amber-600/5",
  },
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
        <rect x="2" y="3" width="20" height="14" rx="2" />
        <path d="M8 21h8" />
        <path d="M12 17v4" />
      </svg>
    ),
    title: "Point it at any GitHub repo and go",
    description: "Paste a repo URL \u2014 it clones, parses, embeds, and indexes automatically. No config files, no schema setup, no training data needed.",
    gradient: "from-rose-500/20 to-rose-600/5",
  },
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
        <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
      </svg>
    ),
    title: "Fast enough for interactive use",
    description: "CrossEncoder reranking delivers precise results in under 2 seconds. LRU caching means repeated queries return instantly.",
    gradient: "from-cyan-500/20 to-cyan-600/5",
  },
];

export function Features() {
  return (
    <section id="features" className="py-24" style={{ background: "var(--bg-primary)" }}>
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-16 scroll-reveal">
          <p className="text-sm font-mono text-[#3b82f6] mb-3 tracking-wider uppercase">
            Why CodeBaseAI
          </p>
          <h2 className="text-3xl sm:text-4xl font-bold mb-4" style={{ color: "var(--text-primary)" }}>
            Built for understanding, not just search
          </h2>
          <p className="max-w-2xl mx-auto" style={{ color: "var(--text-secondary)" }}>
            It is a code analysis engine that reads your code the way a senior engineer would —
            with awareness of structure, dependencies, and intent.
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
          {features.map((feature) => (
            <div
              key={feature.title}
              className="group relative rounded-xl p-6 border transition-all duration-300"
              style={{
                background: "var(--bg-card)",
                borderColor: "var(--border-subtle)",
              }}
            >
              <div
                className="absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                style={{
                  background: `linear-gradient(135deg, ${feature.gradient})`,
                }}
              />
              <div className="relative z-10">
                <div
                  className="w-10 h-10 rounded-lg flex items-center justify-center mb-4 transition-colors duration-300"
                  style={{
                    background: "var(--bg-secondary)",
                    color: "#3b82f6",
                    border: "1px solid var(--border-subtle)",
                  }}
                >
                  {feature.icon}
                </div>
                <h3 className="text-base font-semibold mb-2 transition-colors duration-300" style={{ color: "var(--text-primary)" }}>
                  {feature.title}
                </h3>
                <p className="text-sm leading-relaxed transition-colors duration-300" style={{ color: "var(--text-secondary)" }}>
                  {feature.description}
                </p>
              </div>
            </div>
          ))}
        </div>

        <div className="text-center mt-10">
          <a
            href="https://github.com/AyushSinghRana15/Codebase-AI-Assistant"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 text-sm font-medium transition-opacity hover:opacity-80"
            style={{ color: "#3b82f6" }}
          >
            See the full architecture →
          </a>
        </div>
      </div>
    </section>
  );
}
