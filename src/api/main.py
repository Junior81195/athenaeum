"""Athenaeum API — Personal semantic library platform."""

import logging
import json
import time
import sys

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import libraries, upload, search, chat, browse, settings, user, multi


# ── Structured JSON logging ──────────────────────────────────────────────────

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "extra"):
            log.update(record.extra)
        if record.exc_info and record.exc_info[0]:
            log["exception"] = self.formatException(record.exc_info)
        return json.dumps(log, default=str)


handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JSONFormatter())
logging.root.handlers = [handler]
logging.root.setLevel(logging.INFO)
# Quiet noisy libraries
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger("athenaeum")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Athenaeum",
    description="Personal semantic library platform — upload documents, search semantically, chat with AI",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def inject_auth_headers(request: Request, call_next):
    """Extract Authelia auth headers, inject into request state, log request."""
    request.state.remote_user = request.headers.get("Remote-User", "")
    request.state.remote_groups = request.headers.get("Remote-Groups", "")
    request.state.remote_name = request.headers.get("Remote-Name", "")
    request.state.remote_email = request.headers.get("Remote-Email", "")
    request.state.is_authenticated = bool(request.state.remote_user)

    start = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - start) * 1000, 1)

    # Skip health check noise
    if request.url.path != "/health":
        logger.info(
            "request",
            extra={
                "extra": {
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                    "user": request.state.remote_user or "anonymous",
                    "ip": request.headers.get("X-Real-IP", request.client.host if request.client else "unknown"),
                }
            },
        )

    return response


app.include_router(libraries.router, prefix="/api", tags=["libraries"])
app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(search.router, prefix="/api", tags=["search"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(browse.router, prefix="/api", tags=["browse"])
app.include_router(settings.router, prefix="/api", tags=["settings"])
app.include_router(user.router, prefix="/api", tags=["user"])
app.include_router(multi.router, prefix="/api", tags=["multi-library"])


@app.get("/health")
def health():
    return {"status": "healthy", "service": "athenaeum"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
