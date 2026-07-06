// Fallback API proxy — catches any /api/* requests not handled by specific route handlers

import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL;
const BACKEND_KEY = process.env.BACKEND_API_KEY;

export async function GET(req: NextRequest) {
  return proxyRequest(req, "GET");
}

export async function POST(req: NextRequest) {
  return proxyRequest(req, "POST");
}

export async function PUT(req: NextRequest) {
  return proxyRequest(req, "PUT");
}

export async function PATCH(req: NextRequest) {
  return proxyRequest(req, "PATCH");
}

export async function DELETE(req: NextRequest) {
  return proxyRequest(req, "DELETE");
}

async function proxyRequest(req: NextRequest, method: string) {
  try {
    if (!BACKEND_URL) {
      return NextResponse.json(
        { error: "Backend URL not configured. Set BACKEND_URL env var." },
        { status: 500 }
      );
    }

    const path = req.nextUrl.pathname.replace(/^\/api\//, "");
    const queryString = req.nextUrl.searchParams.toString();
    const url = `${BACKEND_URL}/${path}${queryString ? `?${queryString}` : ""}`;

    const headers: Record<string, string> = {};
    const authHeader = req.headers.get("authorization");
    if (authHeader) headers["Authorization"] = authHeader;
    if (BACKEND_KEY) headers["X-API-Key"] = BACKEND_KEY;

    let body: unknown = undefined;
    if (method !== "GET" && method !== "HEAD") {
      const ct = req.headers.get("content-type") || "";
      if (ct.includes("application/json")) {
        body = await req.json();
      }
    }

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
            { error: "Backend returned HTML instead of JSON. Check BACKEND_URL." },
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
        return NextResponse.json({ error: "Backend timeout." }, { status: 504 });
      }
      const msg = fetchErr instanceof Error ? fetchErr.message : String(fetchErr);
      return NextResponse.json(
        { error: `Backend unreachable: ${msg}`, backend_url: (BACKEND_URL || "").replace(/\/\/.*@/, "//***@") },
        { status: 502 }
      );
    }
  } catch {
    return NextResponse.json({ error: "Internal error" }, { status: 500 });
  }
}
