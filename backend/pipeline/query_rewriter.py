# query_rewriter.py — Rewrite user queries for improved code search relevance

from typing import Optional
from config import PROJECT_ROOT

# Keyword-based rewrite templates
TEMPLATES = {
    "where":   "Find the code that implements: {query}",
    "how":     "Find the code that explains how: {query}",
    "what":    "Find the code definition and logic for: {query}",
    "explain": "Find all code related to: {query}",
    "default": "Find code related to: {query}",
}

_REWRITE_SYSTEM = (
    "You are a query rewriter for a code search engine. Given a user question, "
    "rewrite it into a concise, search-engine-friendly query that extracts key "
    "technical terms (function names, file paths, concepts). Remove conversational "
    "fluff. Output ONLY the rewritten query, nothing else."
)


# Rewrite query using LLM (preferred) or rule-based templates as fallback
def rewrite_query(query: str, use_llm: bool = False) -> str:
    if use_llm:
        try:
            from openai import OpenAI
            from dotenv import load_dotenv
            import os
            load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
                resp = client.chat.completions.create(
                    model="qwen/qwen3-coder:free",
                    messages=[
                        {"role": "system", "content": _REWRITE_SYSTEM},
                        {"role": "user", "content": query},
                    ],
                    temperature=0.1,
                    max_tokens=100,
                )
                rewritten = resp.choices[0].message.content.strip().strip('"\'')
                if rewritten:
                    return rewritten
        except Exception:
            pass

    q_lower = query.lower().strip()
    for keyword, template in TEMPLATES.items():
        if q_lower.startswith(keyword):
            return template.format(query=query)
    return TEMPLATES["default"].format(query=query)
