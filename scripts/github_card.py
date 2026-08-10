"""Peças compartilhadas pelos geradores de card SVG do perfil.

Centraliza o acesso à API do GitHub e a moldura do card para que
``generate_top_langs.py`` e ``generate_stats.py`` produzam dois cards
visualmente idênticos, lado a lado no README.

Uso:
    from github_card import THEME, api_get, render_card
"""

from __future__ import annotations

import json
import urllib.request

API_BASE = "https://api.github.com"
GRAPHQL_URL = f"{API_BASE}/graphql"
CARD_WIDTH = 350

# Tema tokyonight do github-readme-stats, para os dois cards casarem.
THEME = {"bg": "#1a1b27", "title": "#70a5fd", "text": "#38bdae"}


def _authorized_request(
    url: str, token: str, payload: bytes | None = None
) -> urllib.request.Request:
    """Monta um Request com o Bearer token e o Accept da API do GitHub."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    return urllib.request.Request(url, data=payload, headers=headers)


def api_get(path: str, token: str) -> object:
    """Faz GET autenticado na API REST do GitHub e devolve o JSON decodificado.

    Exemplo: ``api_get("/user/repos?page=1", token)``
    """
    with urllib.request.urlopen(
        _authorized_request(f"{API_BASE}{path}", token)
    ) as response:
        return json.load(response)


def graphql_query(query: str, token: str) -> dict[str, object]:
    """Executa uma query GraphQL e devolve o conteúdo de ``data``.

    A API GraphQL responde HTTP 200 mesmo com erro de query, então o campo
    ``errors`` precisa ser checado à mão.

    Exemplo: ``graphql_query("query { viewer { login } }", token)``
    """
    payload = json.dumps({"query": query}).encode("utf-8")
    with urllib.request.urlopen(
        _authorized_request(GRAPHQL_URL, token, payload)
    ) as response:
        body = json.load(response)
    if "errors" in body:
        raise RuntimeError(
            f"GraphQL falhou: {body['errors']!r}; esperado payload com 'data'"
        )
    data = body.get("data")
    if not isinstance(data, dict):
        raise TypeError(
            f"resposta GraphQL inesperada: {body!r}; esperado dict em 'data'"
        )
    return data


def render_card(
    height: int, title: str, aria_label: str, body: str, extra_css: str
) -> str:
    """Renderiza a moldura do card (fundo, borda e título) ao redor de ``body``.

    ``body`` recebe SVG já pronto; ``extra_css`` acrescenta classes ao <style>.

    Exemplo: ``render_card(193, "Estatísticas", "Estatísticas", "<g/>", ".x {}")``
    """
    return f"""<svg width="{CARD_WIDTH}" height="{height}" viewBox="0 0 {CARD_WIDTH} {height}" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{aria_label}">
  <style>
    .title {{ font: 600 18px 'Segoe UI', Ubuntu, sans-serif; fill: {THEME["title"]}; }}
    {extra_css}
  </style>
  <rect x="0.5" y="0.5" width="{CARD_WIDTH - 1}" height="{height - 1}" rx="4.5" fill="{THEME["bg"]}" stroke="#e4e2e2" stroke-opacity="0.3" />
  <text x="25" y="33" class="title">{title}</text>
{body}
</svg>
"""
