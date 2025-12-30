## Billino Frontend (Next.js 16)

- Dev server: `pnpm dev` (http://localhost:3000)
- API base URL: configure `NEXT_PUBLIC_API_URL` in `.env.local` (default: `http://127.0.0.1:8000`)

## Static Export for Tauri / Offline

- Build static bundle: `pnpm export`
  - Uses env flags: `NEXT_OUTPUT=export`, `NEXT_ASSET_PREFIX=./`, `NEXT_BASE_PATH=`
  - Output directory: `out/` (compatible with Tauri `distDir`)
- Preview export locally (example): `npx serve out -l 4000`
- Ensure backend is reachable locally while testing (e.g., `uvicorn main:app --reload --port 8000`)

## Server/Cloud Build

- Regular build keeps SSR-capable output: `pnpm build`
- Start production server: `pnpm start`

## Linting, Tests, Type-Checks

- Lint: `pnpm lint`
- Tests: `pnpm test`
- Type check: `pnpm typecheck`
