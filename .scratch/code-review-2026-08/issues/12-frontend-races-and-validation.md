# Frontend: request race conditions + season input validation

Status: ready-for-agent

- `src/App.tsx:20-62`: no AbortController; mode tabs stay live during loading;
  a late response lands after switching tabs and shows stale results under the
  wrong tab. Fix: abort in-flight requests on mode change/unmount via a ref'd
  controller + request-id guard; clear result/error on mode change.
- `src/App.tsx:31,54`: no timeout/cancel for long analyses; add
  AbortSignal.timeout(120_000) and surface elapsed time.
- `src/App.tsx:32,43`: error detail from FastAPI {"detail": ...} discarded.
- `src/ControlDeck.tsx:94`: Number("") === 0 and NaN/decimals can be sent as
  year. Validate integer in [2018, 2100].
- `vite.config.ts:14-16`: two redundant proxy entries.

## Comments
