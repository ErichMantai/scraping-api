import json
from datetime import datetime, timedelta
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import SearchCache
from app.config import settings


def make_cache_key(termo: str, paginas: int) -> str:
    return f"{termo.strip().lower()}::{paginas}"


async def get_cache(db: AsyncSession, termo: str, paginas: int) -> list | None:
    """Retorna resultado cacheado se ainda válido, ou None."""
    key     = make_cache_key(termo, paginas)
    expiry  = datetime.now() - timedelta(seconds=settings.CACHE_TTL_SECONDS)

    result = await db.execute(
        select(SearchCache).where(
            SearchCache.cache_key == key,
            SearchCache.created_at >= expiry,
        )
    )
    cached = result.scalar_one_or_none()

    if cached:
        return json.loads(cached.resultado)
    return None


async def set_cache(db: AsyncSession, termo: str, paginas: int, produtos: list):
    """Salva ou atualiza o cache de uma busca."""
    key = make_cache_key(termo, paginas)

    # Remove entrada antiga se existir
    await db.execute(delete(SearchCache).where(SearchCache.cache_key == key))

    cached = SearchCache(
        cache_key=key,
        resultado=json.dumps(produtos, ensure_ascii=False),
    )
    db.add(cached)
    await db.commit()


async def clear_expired_cache(db: AsyncSession):
    """Remove entradas de cache expiradas."""
    expiry = datetime.now() - timedelta(seconds=settings.CACHE_TTL_SECONDS)
    await db.execute(delete(SearchCache).where(SearchCache.created_at < expiry))
    await db.commit()
