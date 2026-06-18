# App — Next.js App Router Pages

Next.js 16 App Router pages and API routes.

| Route | Type | Description |
|-------|------|-------------|
| `page.tsx` | Client | Marketing landing page |
| `layout.tsx` | Layout | Root layout with ThemeProvider + AuthProvider |
| `agent/page.tsx` | Client | AI Assistant chat interface |
| `agent/profile/page.tsx` | Client | User profile page |
| `login/page.tsx` | Client | Login / Sign up page with Google OAuth and animated dark mode UI |
| `api/ask/route.ts` | API | Proxy to backend `/ask` |
| `api/ingest/github/route.ts` | API | Proxy to backend `/ingest/github` |
| `api/auth/[...path]/route.ts` | API | Proxy to backend `/auth/*` |
