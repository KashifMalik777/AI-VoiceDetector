"""SatyaVaani backend -- ONE FastAPI process holding the API, the WebSocket hub and ML.

The most important architectural decision in this project. A Node backend plus a separate
Python ML service means an extra hop, two deploys, two dependency trees and a full
integration day we do not have. One process, with a clean internal boundary at
ml/registry.get_detectors(), gets the same benefit for free.
"""
from __future__ import annotations
import logging, sys, os
from pathlib import Path

# make `ml` importable when run from anywhere
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .db import init as db_init
from .routes.api import router as api_router
from . import ws_hub
from ml.registry import get_detectors, model_version

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s  %(levelname)-7s %(name)s  %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("satyavaani")

app = FastAPI(title="SatyaVaani", version="1.0.0",
              description="Real-time voice integrity layer -- SIH PS 26104")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(api_router)


@app.on_event("startup")
def _startup():
    db_init()
    dets = get_detectors()
    stubs = [d.name for d in dets if type(d).__name__.startswith("Stub")]
    log.info("=" * 62)
    log.info("SatyaVaani up  ·  model_version=%s", model_version())
    if stubs:
        log.warning("STUB DETECTORS ACTIVE: %s", ", ".join(stubs))
        log.warning("The pipeline is green end-to-end. Swap stubs one at a time")
        log.warning("and re-run the demo script after each swap.")
    log.info("  REST  http://localhost:8000/api/...   docs: /docs")
    log.info("  WS    ws://localhost:8000/ws/session/{session_id}")
    log.info("=" * 62)


@app.get("/health")
def health():
    dets = get_detectors()
    return {"ok": True, "model_version": model_version(),
            "detectors": [{"name": d.name, "impl": type(d).__name__,
                           "stub": type(d).__name__.startswith("Stub")} for d in dets],
            "audio": {"sample_rate": 16000, "window_s": 4.0, "hop_s": 1.0}}


@app.websocket("/ws/session/{session_id}")
async def ws_session(ws: WebSocket, session_id: str):
    await ws_hub.handle(ws, session_id)


@app.exception_handler(Exception)
async def _err(request, exc):
    log.exception("unhandled: %s", exc)
    return JSONResponse(status_code=500, content={"error": str(exc)})
