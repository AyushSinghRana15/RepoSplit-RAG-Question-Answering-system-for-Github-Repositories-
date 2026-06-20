"use client";

const stack = [
  "FAISS", "BM25", "CrossEncoder", "RAGAS", "Next.js",
  "FastAPI", "OpenRouter", "AST Parser", "sentence-transformers", "shadcn/ui",
];

export function TrustStrip() {
  const doubled = [...stack, ...stack, ...stack, ...stack];

  return (
    <section className="border-y py-10 overflow-hidden" style={{ background: "var(--bg-secondary)", borderColor: "var(--border-subtle)" }}>
      <div className="max-w-7xl mx-auto px-6">
        <div className="flex flex-col sm:flex-row items-center gap-4 mb-6">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap" style={{ background: "rgba(59,130,246,0.1)", color: "#3b82f6", border: "1px solid rgba(59,130,246,0.2)" }}>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 flex-shrink-0" />
            <span className="hidden sm:inline">80%+ RAGAS eval · sub-2s answers · 0 hallucinations on test set</span>
            <span className="sm:hidden">80%+ RAGAS · sub-2s · 0 hall.</span>
          </div>
          <span className="text-xs" style={{ color: "var(--text-muted)" }}>Built on proven infrastructure</span>
        </div>

        <div className="overflow-hidden mask-edges">
          <div
            className="flex gap-3 w-max"
            style={{
              animation: "marquee 40s linear infinite",
            }}
          >
            {doubled.map((item, i) => (
              <div
                key={i}
                className="flex items-center gap-2 px-4 py-2 rounded-full border text-sm font-mono whitespace-nowrap"
                style={{ background: "var(--bg-card)", borderColor: "var(--border-subtle)", color: "var(--text-secondary)" }}
              >
                <span className="w-1.5 h-1.5 rounded-full" style={{ background: "linear-gradient(135deg, #3b82f6, #8b5cf6)" }} />
                {item}
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
