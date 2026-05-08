import secrets
from datetime import datetime
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import ApiKey
from app.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def generate_api_key() -> str:
    """Gera uma API Key segura de 32 bytes (64 chars hex)."""
    return secrets.token_hex(32)


async def validate_api_key(
    key: str = Security(api_key_header),
    db: AsyncSession = None,
) -> ApiKey:
    """Valida a API Key e retorna o cliente. Levanta 401/403 se inválida."""
    if not key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key ausente. Envie no header: X-API-Key: <sua-chave>",
        )

    result = await db.execute(select(ApiKey).where(ApiKey.key == key))
    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key inválida.",
        )

    if not client.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API Key desativada. Entre em contato com o administrador.",
        )

    # Atualiza last_used
    await db.execute(
        update(ApiKey).where(ApiKey.id == client.id).values(last_used=datetime.now())
    )
    await db.commit()

    return client


def validate_admin_key(key: str = Security(api_key_header)) -> bool:
    """Valida a chave de admin para endpoints administrativos."""
    if key != settings.ADMIN_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Chave de admin inválida.",
        )
    return True
