
import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
import re
import json
from playwright.async_api import async_playwright


def montar_url(termo: str, pagina: int) -> str:
    slug = termo.strip().replace(" ", "-")
    if pagina == 1:
        return f"https://lista.mercadolivre.com.br/{slug}"
    offset = (pagina - 1) * 48 + 1
    return f"https://lista.mercadolivre.com.br/{slug}_Desde_{offset}_NoIndex_True"


async def scrape(termo: str, paginas: int) -> list:
    todos = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="pt-BR",
            viewport={"width": 1280, "height": 800},
        )
        
        page = await context.new_page()

        for pg in range(1, paginas + 1):
            url = montar_url(termo, pg)
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(3000)

                html = await page.content()
                if "suspicious-traffic" in html:
                    await page.wait_for_timeout(5000)
                    await page.reload(wait_until="domcontentloaded")
                    await page.wait_for_timeout(3000)

                cards = await page.query_selector_all("li.ui-search-layout__item")

                for card in cards:
                    try:
                        # Título
                        titulo_el = await card.query_selector("a.poly-component__title")
                        titulo    = (await titulo_el.inner_text()).strip() if titulo_el else ""

                        # Vendedor
                        vendedor_el = await card.query_selector("span.poly-phrase-label.poly-fw-semibold")
                        vendedor    = (await vendedor_el.inner_text()).strip() if vendedor_el else ""

                        # Preço atual
                        preco = None
                        frac_el = await card.query_selector(".poly-price__current .andes-money-amount__fraction")
                        cent_el = await card.query_selector(".poly-price__current .andes-money-amount__cents")
                        if frac_el:
                            frac = (await frac_el.inner_text()).replace(".", "").replace(",", "").strip()
                            cent = (await cent_el.inner_text()).strip() if cent_el else "00"
                            try:
                                preco = float(f"{frac}.{cent}")
                            except Exception:
                                pass

                        # Preço original (riscado)
                        preco_anterior = None
                        orig_el = await card.query_selector("span.andes-money-amount__fraction",)
                        if orig_el:
                            try:
                                orig_str = (await orig_el.inner_text()).replace(".", "").replace(",", "").strip()
                                preco_anterior = float(orig_str)
                            except Exception:
                                pass

                        # Desconto
                        desconto = None
                        if preco and preco_anterior and preco_anterior > preco:
                            desconto = round((1 - preco / preco_anterior) * 100, 1)

                        # Cupom
                        cupom_el  = await card.query_selector(".poly-coupons__pill")
                        cupom     = (await cupom_el.inner_text()).strip() if cupom_el else None

                        # Frete
                        frete_el  = await card.query_selector(".poly-component__shipping")
                        frete_txt = (await frete_el.inner_text()).lower() if frete_el else ""
                        frete     = "gratis" if "grátis" in frete_txt or "gratis" in frete_txt else "pago"

                        # Avaliação
                        rating_el  = await card.query_selector(".poly-component__review-compacted .poly-phrase-label")
                        rating_txt = (await rating_el.inner_text()).replace(",", ".").strip() if rating_el else None
                        rating     = float(rating_txt) if rating_txt else None

                        # Link
                        link_el = await card.query_selector("a.poly-component__title")
                        link    = ""
                        if link_el:
                            href = await link_el.get_attribute("href")
                            link = href.split("#")[0] if href else ""

                        # Imagem
                        img_el = await card.query_selector("img.poly-component__picture")
                        imagem = ""
                        if img_el:
                            imagem = await img_el.get_attribute("src") or await img_el.get_attribute("data-src") or ""

                        if titulo:
                            todos.append({
                                "titulo":         titulo,
                                "vendedor":       vendedor,
                                "preco":          preco,
                                "preco_anterior": preco_anterior,
                                "desconto_pct":   desconto,
                                "cupom":          cupom,
                                "frete":          frete,
                                "avaliacao":      rating,
                                "link":           link,
                                "imagem":        imagem,
                            })

                    except Exception:
                        continue

            except Exception as e:
                sys.stderr.write(f"Erro página {pg}: {e}\n")

            await page.wait_for_timeout(2000)

        await browser.close()

    return todos


if __name__ == "__main__":
    termo   = sys.argv[1] if len(sys.argv) > 1 else "whey protein"
    paginas = int(sys.argv[2]) if len(sys.argv) > 2 else 1

    produtos = asyncio.run(scrape(termo, paginas))
    print(json.dumps(produtos, ensure_ascii=False))