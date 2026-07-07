# LexAgent Web

A Next.js 14 App Router client for the LexAgent contract-review API. Drag in a
contract, review each flagged clause with an accept or reject choice, and read
the drafted redlines beside the original text. The app is a thin client: every
decision and every model call happens in the backend.

## Run locally

```bash
cp .env.example .env.local
pnpm install
pnpm dev
# open http://localhost:3000
```

With `NEXT_PUBLIC_USE_MOCK=true` (the default in `.env.example`) the app runs
against an in-memory mock backend, so you can click through the whole flow with
no real API.

To point at a real backend, edit `.env.local`:

```
NEXT_PUBLIC_API_URL=https://xxx.execute-api.us-east-1.amazonaws.com
NEXT_PUBLIC_REQUIRE_API_KEY=true
NEXT_PUBLIC_USE_MOCK=false
```

## Scripts

```bash
pnpm dev             # dev server on port 3000
pnpm build           # production build
pnpm lint            # eslint
pnpm exec tsc --noEmit   # strict typecheck
pnpm exec playwright test --config e2e/playwright.config.ts   # e2e tests
```

## Deploy to Vercel

```bash
vercel deploy
# set NEXT_PUBLIC_API_URL (and, if used, NEXT_PUBLIC_REQUIRE_API_KEY) in the
# Vercel project settings to your deployed API Gateway URL.
```

Any Next.js-compatible host works; the app is a static-friendly client bundle
with no server routes of its own.

## Directory tour

- `app/` — App Router pages. `page.tsx` is the upload landing page;
  `analyses/[thread_id]/page.tsx` runs the review and redline flow. Both are
  client components. `layout.tsx` sets fonts, theme, and providers, and
  `error.tsx` / `not-found.tsx` handle failures.
- `components/` — feature components (upload zone, flag card, redline diff, and
  so on) plus `ui/` shadcn primitives.
- `lib/` — the typed API client, React Query hooks with status polling, the
  in-memory mock backend, and shared helpers.
- `e2e/` — Playwright specs that drive the app against route mocks.

## API key handling

When `NEXT_PUBLIC_REQUIRE_API_KEY` is `true`, the app shows an API-key gate
before the upload zone. The key is stored in `localStorage` under `apiKey` and
sent as the `x-api-key` header. There is no server-side session; the current
work lives in the `thread_id` in the URL.
