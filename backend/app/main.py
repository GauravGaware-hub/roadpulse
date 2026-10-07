import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routes import events, health, hotspots, ingest

logger = logging.getLogger("roadpulse")

app = FastAPI(title="RoadPulse API", version="1.0.0")

# Local dev (Vite dev server 5173, Vite preview 4173, CRA-style 3000) is always allowed.
# Deployed frontend origin(s): set CORS_ORIGINS to a comma-separated list,
# e.g. CORS_ORIGINS=https://roadpulse.example.com,https://www.roadpulse.example.com
LOCAL_ORIGINS = ["http://localhost:3000", "http://localhost:5173", "http://localhost:4173"]
EXTRA_ORIGINS = [o.strip().rstrip("/") for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=LOCAL_ORIGINS + EXTRA_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/")
def root():
    return {"project": "RoadPulse", "status": "running", "version": "1.0.0"}


app.include_router(health.router)
app.include_router(events.router)
app.include_router(hotspots.router)
app.include_router(ingest.router)
