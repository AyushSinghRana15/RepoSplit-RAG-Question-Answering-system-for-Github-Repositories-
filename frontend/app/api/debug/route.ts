// Debug API route — exposes backend config status (URL set, key set, NODE_ENV)

import { NextResponse } from "next/server";

// GET /api/debug — return backend config for debugging
export async function GET() {
  const raw = process.env.BACKEND_URL || "";
  const masked = raw.replace(/\/\/.*@/, "//***@").replace(/\/+$/, "");
  return NextResponse.json({
    backend_url_set: !!raw,
    backend_url: masked,
    backend_key_set: !!process.env.BACKEND_API_KEY,
    node_env: process.env.NODE_ENV,
  });
}
