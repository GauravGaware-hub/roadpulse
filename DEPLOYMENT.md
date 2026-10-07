# RoadPulse – deployment notes (first prototype deployment)

Research prototype. Not hardened: no authentication, no rate limiting.

## Backend (`backend/`)
Install: `pip install -r requirements.txt` (Python 3.11 verified)

Start (no `--reload`; the port comes from the platform's `PORT` variable):

    python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}

A `Procfile` with this command is included for Procfile-based platforms.
Health check path: `GET /api/health` → `{"status":"healthy","service":"roadpulse-api"}`

| Variable | Required | Meaning |
|---|---|---|
| `PORT` | set by platform | Port to listen on (shell default 8000). |
| `CORS_ORIGINS` | yes, in production | Comma-separated deployed frontend origin(s), e.g. `https://roadpulse.example.com`. Scheme + host only, no path. |
| `UPLOADS_DIR` | optional | Where recordings are stored. Default `backend/uploads`. Point at a persistent disk if the platform offers one. |

CORS: always allows `http://localhost:3000`, `:5173`, `:4173` (local dev / Vite preview), plus whatever is in
`CORS_ORIGINS`. No wildcard; no credentials. Methods GET and POST only.

## Frontend (`frontend/`)
    npm ci && VITE_API_BASE_URL=https://<backend-host> npm run build

Serve `frontend/dist/` as static files. `VITE_API_BASE_URL` is baked in at **build time**, so rebuild when the
backend URL changes. Without it, a production build calls the same origin it is served from; the
`http://localhost:8000` fallback applies to `npm run dev` only.

## Known limitation: uploads use the local filesystem
Uploaded recordings are stored at `backend/uploads/<recording_id>/` (raw Accelerometer/Gyroscope/Location CSVs
plus `result.json`). This is acceptable for a first prototype deployment only:

- On platforms with an **ephemeral filesystem** (most free/default web-service tiers), uploads vanish on every
  redeploy, restart or instance replacement. A `recording_id` then returns 404 and the dashboard falls back to
  an error banner until the user switches to the static Pune dataset.
- With **more than one instance**, an upload lives on one instance only, so another instance returns 404.
- There is no cleanup, quota or authentication: anyone who can reach the API can upload and fill the disk.

Use a single instance and a persistent disk (`UPLOADS_DIR`) if recordings must survive restarts. Object storage
or a database is the proper fix and is not implemented yet.
The static Pune dataset ships with the backend (`backend/processed/*.csv`) and is unaffected.
