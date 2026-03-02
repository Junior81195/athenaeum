"""Handbook Library Platform API — Multi-library RAG platform."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import libraries, upload, search, chat, browse, settings

app = FastAPI(
    title="Handbook Library Platform",
    description="Multi-library RAG platform with semantic search and AI chat",
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
    """Extract Authelia auth headers and inject into request state."""
    request.state.remote_user = request.headers.get("Remote-User", "anonymous")
    request.state.remote_groups = request.headers.get("Remote-Groups", "")
    response = await call_next(request)
    return response


app.include_router(libraries.router, prefix="/api", tags=["libraries"])
app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(search.router, prefix="/api", tags=["search"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(browse.router, prefix="/api", tags=["browse"])
app.include_router(settings.router, prefix="/api", tags=["settings"])


@app.get("/health")
def health():
    return {"status": "healthy", "service": "handbook-library-platform"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
