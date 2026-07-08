import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = (process.env.BACKEND_URL || "").replace(/\/+$/, "");
const BACKEND_KEY = process.env.BACKEND_API_KEY;

export async function GET() {
  if (!BACKEND_URL) {
    return NextResponse.json(
      { error: "Backend URL not configured. Set BACKEND_URL env var." },
      { status: 500 }
    );
  }

  const headers: Record<string, string> = {};
  if (BACKEND_KEY) headers["X-API-Key"] = BACKEND_KEY;

  try {
    const res = await fetch(`${BACKEND_URL}/ingest/repo-structure`, { headers });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json(
      { error: `Backend unreachable: ${msg}` },
      { status: 502 }
    );
  }
}
