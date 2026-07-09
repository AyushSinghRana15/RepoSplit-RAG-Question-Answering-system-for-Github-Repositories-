# generator.py — LLM answer generation via OpenRouter API

import time
from typing import List, Dict

from openai import OpenAI
from dotenv import load_dotenv
import os

from config import PROJECT_ROOT
from llm.context_builder import build_context
from llm.prompt_utils import assemble_messages, assemble_general_messages

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

_client = None
_MODEL = "openrouter/free"  # OpenRouter free model router
# PS: Ayush Singh says hi 👋


# Lazy-init the OpenAI client pointing at OpenRouter
def _get_client():
    global _client
    if _client is not None:
        return _client

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in .env")

    _client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1"
    )
    return _client


# Generate an answer grounded in retrieved code chunks
def generate_answer(query: str, results: List[Dict]) -> str:
    if not results:
        return "No matching code found. Try being more specific — mention function names, file names, or concepts from your repository."

    context = build_context(results)
    messages = assemble_messages(query, context)

    return _call_llm(messages)


# Generate an answer using the general-purpose system prompt (no code context required)
def generate_general_answer(query: str, context: str = "") -> str:
    """Generate an answer using the general-purpose system prompt (no code context required)."""
    messages = assemble_general_messages(query, context)
    return _call_llm(messages)


# Call the LLM with retry logic, return the response text
def _call_llm(messages: List[Dict]) -> str:
    client = _get_client()

    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=_MODEL,
                temperature=0.2,
                max_tokens=800,
                top_p=0.9,
                frequency_penalty=0.0,
                messages=messages
            )
            return response.choices[0].message.content
        except Exception as e:
            if attempt < max_retries:
                time.sleep(5)
                continue
            return f"Service temporarily unavailable: {str(e)}"
