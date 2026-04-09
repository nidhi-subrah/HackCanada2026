import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv

from api.routes import upload, search, graph, enrich, messages, auth
from config import settings
from db.constraints import setup_schema
from db.neo4j_client import db

load_dotenv()

# Make sure logger.info() calls in services/ show up in Railway logs.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

limiter = Limiter(key_func=get_remote_address)
_docs_url = None if not settings.frontend_url.startswith("http://localhost") else "/docs"
app = FastAPI(title="LinkedIn Networkify API", version="1.0.0", docs_url=_docs_url, redoc_url=None)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.app_secret_key
)

allowed_origins = [o.strip().rstrip("/") for o in settings.frontend_url.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router,   prefix="/api/upload",   tags=["Upload"])
app.include_router(search.router,   prefix="/api/search",   tags=["Search"])
app.include_router(graph.router,    prefix="/api/graph",    tags=["Graph"])
app.include_router(enrich.router,   prefix="/api/enrich",   tags=["Enrich"])
app.include_router(messages.router, prefix="/api/messages", tags=["Messages"])
app.include_router(auth.router)

@app.on_event("startup")
def _on_startup():
    """Ensure indexes/constraints exist so per-owner queries aren't full scans."""
    try:
        if db.verify_connectivity():
            setup_schema()
            logging.getLogger(__name__).info("Neo4j schema verified")
    except Exception as exc:
        logging.getLogger(__name__).warning("Schema setup failed: %s", exc)


@app.get("/health")
def health():
    return {"status": "ok"}
