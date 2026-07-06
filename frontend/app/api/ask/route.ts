// ask API route — proxies query requests to backend with validation and timeout

import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = (process.env.BACKEND_URL || "").replace(/\/+$/, "");
const BACKEND_KEY = process.env.BACKEND_API_KEY;

// POST /api/ask — validate query, proxy to backend, handle timeout
export async function POST(req: NextRequest) {
  try {
    // Check backend URL is configured
    if (!BACKEND_URL) {
      return NextResponse.json(
        { error: "Backend URL not configured. Set BACKEND_URL env var." },
        { status: 500 }
      );
    }

    // Parse and validate request body
    const body = await req.json();

    if (!body.query || typeof body.query !== "string") {
      return NextResponse.json({ error: "Query is required" }, { status: 400 });
    }

    if (body.query.length > 1000) {
      return NextResponse.json({ error: "Query too long" }, { status: 400 });
    }

    // Build headers with API key if available
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (BACKEND_KEY) headers["X-API-Key"] = BACKEND_KEY;

    // Abort controller for 60s timeout
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 60000);

    try {
      const response = await fetch(`${BACKEND_URL}/ask`, {
        method: "POST",
        headers,
        body: JSON.stringify({ query: body.query, top_k: body.top_k ?? 5 }),
        signal: controller.signal,
      });

      clearTimeout(timeout);

      if (!response.ok) {
        const err = await response.text();
        return NextResponse.json({ error: err }, { status: response.status });
      }

       const data = await response.json();
       return NextResponse.json(data);
    } catch (fetchErr: unknown) {
      clearTimeout(timeout);
      if (fetchErr instanceof Error && fetchErr.name === "AbortError") {
        return NextResponse.json({ error: "Backend timeout" }, { status: 504 });
      }
      throw fetchErr;
    }
  } catch {
    return NextResponse.json({ error: "Internal error" }, { status: 500 });
  }
}
