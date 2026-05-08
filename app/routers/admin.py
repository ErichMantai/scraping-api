from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.models import ApiKey, RequestLog
from app.auth import generate_api_key, validate_admin_key
from app.config import settings

router = APIRouter(prefix="/admin", tags=["Admin"])

admin_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)


def check_admin(key: str = Security(admin_key_header)):
    if key != settings.ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Chave de admin inválida.")
    return True


# ── Schemas ───────────────────────────────────────────────────────

class CriarClienteInput(BaseModel):
    name:       str
    rate_limit: int = 10   # requisições por minuto


class AtualizarClienteInput(BaseModel):
    is_active:  bool | None = None
    rate_limit: int  | None = None


# ── Endpoints ─────────────────────────────────────────────────────

@router.get("/clientes", summary="Listar todos os clientes")
async def listar_clientes(
    db:    AsyncSession = Depends(get_db),
    _:     bool         = Depends(check_admin),
):
    result   = await db.execute(select(ApiKey).order_by(ApiKey.created_at.desc()))
    clientes = result.scalars().all()
    return [
        {
            "id":         c.id,
            "name":       c.name,
            "key":        c.key,
            "is_active":  c.is_active,
            "rate_limit": c.rate_limit,
            "created_at": c.created_at.isoformat(),
            "last_used":  c.last_used.isoformat() if c.last_used else None,
        }
        for c in clientes
    ]


@router.post("/clientes", summary="Criar novo cliente e gerar API Key")
async def criar_cliente(
    body: CriarClienteInput,
    db:   AsyncSession = Depends(get_db),
    _:    bool         = Depends(check_admin),
):
    key    = generate_api_key()
    client = ApiKey(name=body.name, key=key, rate_limit=body.rate_limit)
    db.add(client)
    await db.commit()
    await db.refresh(client)
    return {
        "message":    "Cliente criado com sucesso.",
        "id":         client.id,
        "name":       client.name,
        "api_key":    key,
        "rate_limit": client.rate_limit,
    }


@router.patch("/clientes/{client_id}", summary="Ativar/desativar cliente ou alterar rate limit")
async def atualizar_cliente(
    client_id: int,
    body:      AtualizarClienteInput,
    db:        AsyncSession = Depends(get_db),
    _:         bool         = Depends(check_admin),
):
    result = await db.execute(select(ApiKey).where(ApiKey.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")

    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    await db.execute(update(ApiKey).where(ApiKey.id == client_id).values(**updates))
    await db.commit()
    return {"message": "Cliente atualizado.", "updates": updates}


@router.delete("/clientes/{client_id}", summary="Remover cliente")
async def remover_cliente(
    client_id: int,
    db:        AsyncSession = Depends(get_db),
    _:         bool         = Depends(check_admin),
):
    result = await db.execute(select(ApiKey).where(ApiKey.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")
    await db.delete(client)
    await db.commit()
    return {"message": f"Cliente '{client.name}' removido."}


@router.get("/logs", summary="Ver logs de requisições")
async def ver_logs(
    limit:     int = 50,
    client_id: int | None = None,
    db:        AsyncSession = Depends(get_db),
    _:         bool         = Depends(check_admin),
):
    query = select(RequestLog).order_by(RequestLog.created_at.desc()).limit(limit)
    if client_id:
        query = query.where(RequestLog.api_key_id == client_id)
    result = await db.execute(query)
    logs   = result.scalars().all()
    return [
        {
            "id":          l.id,
            "api_key_id":  l.api_key_id,
            "termo":       l.termo,
            "paginas":     l.paginas,
            "total":       l.total,
            "from_cache":  l.from_cache,
            "duration_ms": l.duration_ms,
            "status":      l.status,
            "error_msg":   l.error_msg,
            "created_at":  l.created_at.isoformat(),
        }
        for l in logs
    ]


@router.get("/stats", summary="Estatísticas gerais de uso")
async def stats(
    db: AsyncSession = Depends(get_db),
    _:  bool         = Depends(check_admin),
):
    total_req   = await db.execute(func.count(RequestLog.id))
    total_cache = await db.execute(
        select(func.count(RequestLog.id)).where(RequestLog.from_cache == True)  # noqa
    )
    total_err   = await db.execute(
        select(func.count(RequestLog.id)).where(RequestLog.status == "error")
    )
    total_cli   = await db.execute(func.count(ApiKey.id))

    return {
        "total_requisicoes":    (await db.execute(select(func.count(RequestLog.id)))).scalar(),
        "requisicoes_cache":    (await db.execute(select(func.count(RequestLog.id)).where(RequestLog.from_cache == True))).scalar(),  # noqa
        "requisicoes_erro":     (await db.execute(select(func.count(RequestLog.id)).where(RequestLog.status == "error"))).scalar(),
        "total_clientes":       (await db.execute(select(func.count(ApiKey.id)))).scalar(),
        "clientes_ativos":      (await db.execute(select(func.count(ApiKey.id)).where(ApiKey.is_active == True))).scalar(),  # noqa
    }
