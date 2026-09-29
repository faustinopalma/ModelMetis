# Operational Console

React 19, TypeScript, and Vite console for the local audio-review API. The first screen is an empty review queue; recordings appear only after actual WAV uploads. Views cover upload, search/filter/pagination, sample metadata, waveform/playback, manual review, and honest model status. The teacher-first learning, experiment, release, and adaptive-routing roadmap in the [working context](../../docs/CONTEXT.md) is not implemented in this increment.

## Local Setup

Prerequisites: Node.js 22.12 or later and the [local backend](../api/README.md). Run from the repository root:

```powershell
$timer = [Diagnostics.Stopwatch]::StartNew(); try { npm ci --prefix apps/console } finally { Write-Output "elapsed: $([math]::Round($timer.Elapsed.TotalSeconds, 1))s" }
$timer = [Diagnostics.Stopwatch]::StartNew(); try { npm run dev --prefix apps/console } finally { Write-Output "elapsed: $([math]::Round($timer.Elapsed.TotalSeconds, 1))s" }
```

The local URL is `http://127.0.0.1:5173`. The API proxy targets `127.0.0.1:8000` by default, or the `PORT` environment variable. Vite binds to loopback with a strict port. If 5173 is occupied, choose a different console port explicitly and include its exact origin in `MODELMETIS_ORIGINS` before restarting the backend. API secrets are not needed and must never be added to browser code or `VITE_*` variables. The root [environment sample](../../.env.sample) documents server defaults.

`npm start` aliases local development. `npm run build` type-checks and writes `dist`; `npm run preview` serves it with the same API proxy. Production hosting requires authenticated API routing and is not implemented. Use `npm ci` with the resolved lockfile.

## Review Semantics

Uploads send WAV bytes and an explicit synthetic/test declaration, but not the original filename. The backend removes ancillary WAV metadata, preserves PCM samples, and assigns an opaque display name. No samples are fabricated by the application. The waveform is an amplitude envelope decoded with the browser's Web Audio API from the stored recording; playback uses the backend audio endpoint. Waveform generation performs a separate audio fetch, so inspecting a recording may transfer it twice. The browser may reject WAV encodings accepted by the backend; playback and waveform failures are displayed independently.

Counts come from stored metadata and are refreshed after uploads, reviews, and conflict recovery. Publisher reference labels are not returned by the API or shown in the console. Unavailable model predictions and authorized human labels remain separate. A review carries the displayed revision; conflicts retain the draft, disable further saves, and offer explicit discard/reload. Unsaved review changes trigger confirmation before switching views/recordings or leaving the page. No confidence, diagnostic accuracy, trained model, or completed evaluation is advertised.

The console includes the required Clawpilot light/dark tokens and respects `scoutTheme` or the OS color preference. Browser upload, waveform, playback, review, and conflict recovery were verified using an explicitly synthetic test sample. Light desktop and light/dark mobile layouts were checked for horizontal overflow; complete keyboard traversal remains unverified. All five transport tests (`apps/console/src/api.test.ts`; local-only) for the typed API module (`apps/console/src/api.ts`; local-only) passed, as did the TypeScript/Vite build.
