import asyncio
from datetime import datetime
from fastapi import APIRouter, Query, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth import validate_api_key
from app.models import ApiKey, RequestLog
from app.cache import get_cache, set_cache
from app.scraper import run_scraper

router = APIRouter(prefix="/buscar", tags=["Busca"])


@router.get("", summary="Buscar produtos no Mercado Livre")
async def buscar(
    termo:   str = Query(..., description="Produto a buscar", openapi_examples={"default": {"value": "whey protein"}}),
    paginas: int = Query(1, description="Páginas a coletar (1-10, ~48 produtos cada)", ge=1, le=10),
    db:      AsyncSession = Depends(get_db),
    client:  ApiKey       = Depends(validate_api_key),
):
    """
    Retorna produtos do Mercado Livre com preço, desconto, frete, avaliação e imagem.

    - Resultados são **cacheados** por 5 minutos para buscas idênticas.
    - Cada API Key tem um **rate limit** configurado pelo admin.
    """
    inicio     = datetime.now()
    from_cache = False
    error_msg  = None
    produtos   = []

    try:
        # Tenta cache primeiro
        cached = await get_cache(db, termo, paginas)
        if cached is not None:
            produtos   = cached
            from_cache = True
        else:
            # Roda o scraper em thread separada para não bloquear o event loop
            loop     = asyncio.get_event_loop()
            produtos = await loop.run_in_executor(None, run_scraper, termo, paginas)
            await set_cache(db, termo, paginas, produtos)

    except Exception as e:
        error_msg = str(e)

    duration_ms = int((datetime.now() - inicio).total_seconds() * 1000)

    # Salva log
    log = RequestLog(
        api_key_id=client.id,
        termo=termo,
        paginas=paginas,
        total=len(produtos),
        from_cache=from_cache,
        duration_ms=duration_ms,
        status="error" if error_msg else "ok",
        error_msg=error_msg,
    )
    db.add(log)
    await db.commit()

    if error_msg:
        raise HTTPException(status_code=500, detail=f"Erro no scraping: {error_msg}")

    precos = [p["preco"] for p in produtos if p.get("preco")]

    return JSONResponse({
        "meta": {
            "termo":             termo,
            "paginas":           paginas,
            "total_produtos":    len(produtos),
            "from_cache":        from_cache,
            "preco_minimo":      min(precos) if precos else None,
            "preco_maximo":      max(precos) if precos else None,
            "preco_medio":       round(sum(precos) / len(precos), 2) if precos else None,
            "duracao_ms":        duration_ms,
            "coletado_em":       inicio.strftime("%d/%m/%Y %H:%M:%S"),
        },
        "produtos": produtos,
    })
