from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.database import init_db
from app.routers import buscar, admin

# ── Rate Limiter ──────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


# ── App ───────────────────────────────────────────────────────────
app = FastAPI(
    title="Scraper Mercado Livre API",
    description="""
API de scraping do Mercado Livre com autenticação por API Key.

## Autenticação
Todas as rotas de busca exigem o header `X-API-Key`.
As rotas de admin exigem o header `X-Admin-Key`.

## Cache
Buscas idênticas são cacheadas por 5 minutos para maior velocidade.

## Rate Limit
Cada cliente tem um limite de requisições por minuto configurado pelo admin.
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middlewares ───────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"],
)


# ── Routers ───────────────────────────────────────────────────────
app.include_router(buscar.router)
app.include_router(admin.router)


# ── Health check ──────────────────────────────────────────────────
@app.get("/", tags=["Status"])
async def root():
    return {
        "status":  "online",
        "versao":  "1.0.0",
        "docs":    "/docs",
        "endpoints": {
            "buscar": "GET /buscar?termo=whey+protein&paginas=2  (X-API-Key: <key>)",
            "admin":  "GET /admin/clientes                       (X-Admin-Key: <key>)",
        },
    }


@app.get("/health", tags=["Status"])
async def health():
    return {"status": "ok"}
