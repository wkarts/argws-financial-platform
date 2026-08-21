from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def get_app_version() -> str:
    """Retorna a versão canônica da aplicação sem duplicá-la no código.

    Prioridade:
    1. APP_VERSION do ambiente, quando preenchida pelo bootstrap/deploy;
    2. arquivo VERSION empacotado junto da aplicação;
    3. arquivo VERSION da raiz do repositório em desenvolvimento;
    4. valor neutro ``dev`` como último fallback.
    """
    env_version = os.getenv("APP_VERSION", "").strip()
    if env_version and env_version.lower() not in {"auto", "__auto_from_version__"}:
        return env_version

    current = Path(__file__).resolve()
    candidates = (
        current.parents[2] / "VERSION",  # /app/VERSION no container
        current.parents[3] / "VERSION",  # raiz do repositório em desenvolvimento
        Path.cwd() / "VERSION",
        Path.cwd().parent / "VERSION",
    )

    for candidate in candidates:
        try:
            value = candidate.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if value:
            return value

    return "dev"
