import sys
import json
import subprocess
from pathlib import Path

SCRAPER_PATH = Path(__file__).parent.parent / "scraper_standalone.py"


def run_scraper(termo: str, paginas: int) -> list:
    """
    Chama o scraper_standalone.py como subprocesso.
    Compatível com Windows (Python 3.14+) e Linux/VPS.
    """
    resultado = subprocess.run(
        [sys.executable, str(SCRAPER_PATH), termo, str(paginas)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=300,
    )

    if resultado.returncode != 0:
        raise RuntimeError(resultado.stderr or "Erro desconhecido no scraper.")

    return json.loads(resultado.stdout)
