# Frontend — Next.js Application

Next.js 16 TypeScript frontend for the CodeBase AI Assistant.

## Quick Start

```bash
npm install
npm run dev
```

## Directory Structure

| Directory | Description |
|-----------|-------------|
| `app/` | Next.js App Router pages + API proxy routes |
| `components/` | React components (chat UI, website landing page, shadcn/ui primitives) |
| `context/` | React context providers (theme, auth) |
| `hooks/` | Custom React hooks |
| `lib/` | Types, API client, Supabase client, modular TTS providers |
| `public/` | Static assets |

## Routes

| Route | Description |
|-------|-------------|
| `/` | Marketing landing page |
| `/agent` | AI Assistant chat interface |
| `/agent/profile` | User profile page (requires auth) |
| `/login` | Login / Sign up page with Google OAuth |

## Environment Variables

| Variable | Description |
|----------|-------------|
| `BACKEND_URL` | FastAPI backend URL (default: http://localhost:8000) |
| `BACKEND_API_KEY` | Optional backend API key |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anonymous key |
