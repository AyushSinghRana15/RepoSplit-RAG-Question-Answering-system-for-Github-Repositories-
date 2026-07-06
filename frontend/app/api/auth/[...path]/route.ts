// Auth API route — dynamic proxy for auth endpoints (GET, PUT) to backend

import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL;
const BACKEND_KEY = process.env.BACKEND_API_KEY;

// GET /api/auth/[...path] — proxy to backend auth endpoints
export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyRequest(req, path, "GET");
}

// PUT /api/auth/[...path] — proxy to backend auth endpoints with body
export async function PUT(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyRequest(req, path, "PUT");
}

// Generic proxy — forwards auth requests to backend with auth headers and 15s timeout
async function proxyRequest(req: NextRequest, path: string[], method: string) {
  try {
    if (!BACKEND_URL) {
      return NextResponse.json(
        { error: "Backend URL not configured. Set BACKEND_URL env var." },
        { status: 500 }
      );
    }

    const queryString = req.nextUrl.searchParams.toString();
    const url = `${BACKEND_URL}/auth/${path.join("/")}${queryString ? `?${queryString}` : ""}`;

    // Forward Authorization header and API key
    const headers: Record<string, string> = {};
    const authHeader = req.headers.get("authorization");
    if (authHeader) headers["Authorization"] = authHeader;
    if (BACKEND_KEY) headers["X-API-Key"] = BACKEND_KEY;

    const body = method === "PUT" ? await req.json() : undefined;

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);

    try {
      const response = await fetch(url, {
        method,
        headers: { ...headers, "Content-Type": "application/json" },
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });
      clearTimeout(timeout);

      if (!response.ok) {
        const contentType = response.headers.get("content-type") || "";
        if (contentType.includes("text/html")) {
          return NextResponse.json(
            { error: "Authentication service is currently unavailable (backend returned HTML). Please try again later." },
            { status: 502 }
          );
        }
        const err = await response.text();
        return NextResponse.json({ error: err }, { status: response.status });
      }

      const data = await response.json();
      return NextResponse.json(data);
    } catch (fetchErr: unknown) {
      clearTimeout(timeout);
      if (fetchErr instanceof Error && fetchErr.name === "AbortError") {
        return NextResponse.json({ error: "Backend timeout. Authentication service may be overloaded." }, { status: 504 });
      }
      if (fetchErr instanceof TypeError && fetchErr.message.includes("fetch")) {
        return NextResponse.json(
          { error: "Cannot reach the backend server. Make sure the backend is running and BACKEND_URL is correct." },
          { status: 502 }
        );
      }
      throw fetchErr;
    }
  } catch {
    return NextResponse.json({ error: "Internal error" }, { status: 500 });
  }
}
