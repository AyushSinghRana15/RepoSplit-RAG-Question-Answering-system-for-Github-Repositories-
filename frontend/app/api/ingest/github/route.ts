import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL;
const BACKEND_KEY = process.env.BACKEND_API_KEY;

function getHeaders(req: NextRequest): Record<string, string> {
  const headers: Record<string, string> = {};
  if (BACKEND_KEY) headers["X-API-Key"] = BACKEND_KEY;
  const authHeader = req.headers.get("authorization");
  if (authHeader) headers["Authorization"] = authHeader;
  return headers;
}

function missingBackendErr() {
  return NextResponse.json(
    { error: "Backend URL not configured. Set BACKEND_URL env var." },
    { status: 500 }
  );
}

async function proxyToBackend(path: string, req: NextRequest, init?: RequestInit) {
  if (!BACKEND_URL) return missingBackendErr();
  const url = `${BACKEND_URL}${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...getHeaders(req) },
    ...init,
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}

export async function POST(req: NextRequest) {
  try {
    if (!BACKEND_URL) return missingBackendErr();

    const { searchParams } = new URL(req.url);
    const repoUrl = searchParams.get("repo_url");
    const branch = searchParams.get("branch");

    if (!repoUrl) {
      return NextResponse.json(
        { error: "repo_url is required" },
        { status: 400 }
      );
    }

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 30000);

    try {
      const response = await fetch(
        `${BACKEND_URL}/ingest/github?repo_url=${encodeURIComponent(repoUrl)}${
          branch ? `&branch=${encodeURIComponent(branch)}` : ""
        }`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json", ...getHeaders(req) },
          signal: controller.signal,
        }
      );

      clearTimeout(timeout);

      const data = await response.json();
      return NextResponse.json(data, { status: response.status });
    } catch (fetchErr: unknown) {
      clearTimeout(timeout);
      if (fetchErr instanceof Error && fetchErr.name === "AbortError") {
        return NextResponse.json(
          { error: "Backend did not respond within 30s. The task may still be running — check status." },
          { status: 202 }
        );
      }
      const msg = fetchErr instanceof Error ? fetchErr.message : String(fetchErr);
      return NextResponse.json(
        { error: `Backend unreachable: ${msg}`, backend_url: (BACKEND_URL || "").replace(/\/\/.*@/, "//***@") },
        { status: 502 }
      );
    }
  } catch {
    return NextResponse.json(
      { error: "Internal error" },
      { status: 500 }
    );
  }
}

export async function GET(req: NextRequest) {
  try {
    if (!BACKEND_URL) return missingBackendErr();

    const { searchParams } = new URL(req.url);
    const taskId = searchParams.get("task_id");
    if (!taskId) {
      return NextResponse.json({ error: "task_id is required" }, { status: 400 });
    }
    return proxyToBackend(`/ingest/status/${taskId}`, req);
  } catch {
    return NextResponse.json({ error: "Internal error" }, { status: 500 });
  }
}
