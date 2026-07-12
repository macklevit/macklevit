"""Gera ``top-langs.svg`` com as linguagens mais usadas do usuário autenticado.

Soma os bytes por linguagem de TODOS os repositórios próprios (inclusive
privados, que o card oficial do github-readme-stats não enxerga) e desenha
um card SVG no estilo "compact top languages" com tema tokyonight.

Uso:
    GITHUB_TOKEN=<PAT com escopo repo> python3 scripts/generate_top_langs.py
"""
from __future__ import annotations

import json
import os
import urllib.request

API_BASE = "https://api.github.com"
CARD_WIDTH = 350
BAR_WIDTH = 300
BAR_GAP = 2
TOP_COUNT = 10

# Coleção de scripts com muito código de terceiros/biblioteca padrão do
# MetaTrader; distorcia o card (87% de todo o MQL5 vinha só dele).
EXCLUDED_REPOS = {"macklevit/metatrader_scripts"}

# Ponderação do github-readme-stats (size_weight/count_weight = 0.5):
# score = bytes^0.5 * repos^0.5, para um repo gigante não dominar o card.
SIZE_WEIGHT = 0.5
COUNT_WEIGHT = 0.5

# Cores canônicas do github/linguist; cinza para linguagem fora da tabela.
LINGUIST_COLORS: dict[str, str] = {
    "MQL5": "#4A76B8",
    "MQL4": "#62A8D6",
    "Python": "#3572A5",
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "HTML": "#e34c26",
    "CSS": "#663399",
    "PHP": "#4F5D95",
    "Go": "#00ADD8",
    "Java": "#b07219",
    "Jupyter Notebook": "#DA5B0B",
    "Shell": "#89e051",
    "C#": "#178600",
    "C++": "#f34b7d",
    "C": "#555555",
}
FALLBACK_COLOR = "#858585"

# Tema tokyonight do github-readme-stats, para casar com o card de stats.
THEME = {"bg": "#1a1b27", "title": "#70a5fd", "text": "#38bdae"}


def _api_get(path: str, token: str) -> object:
    """Faz GET autenticado na API do GitHub e devolve o JSON decodificado.

    Exemplo: ``_api_get("/user/repos?page=1", token)``
    """
    request = urllib.request.Request(
        f"{API_BASE}{path}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(request) as response:
        return json.load(response)


def fetch_owned_repo_full_names(token: str) -> list[str]:
    """Lista ``dono/repo`` dos repositórios próprios, sem forks nem excluídos.

    Exemplo: ``fetch_owned_repo_full_names(token) -> ["macklevit/macklevit", ...]``
    """
    names: list[str] = []
    page = 1
    while True:
        batch = _api_get(f"/user/repos?per_page=100&affiliation=owner&page={page}", token)
        if not isinstance(batch, list):
            raise TypeError(f"resposta inesperada de /user/repos: {batch!r}; esperada lista")
        names += [
            repo["full_name"]
            for repo in batch
            if not repo["fork"] and repo["full_name"] not in EXCLUDED_REPOS
        ]
        if len(batch) < 100:
            return names
        page += 1


def collect_language_usage(token: str, repo_full_names: list[str]) -> dict[str, tuple[int, int]]:
    """Devolve, por linguagem, ``(bytes somados, nº de repositórios que a usam)``."""
    usage: dict[str, tuple[int, int]] = {}
    for full_name in repo_full_names:
        languages = _api_get(f"/repos/{full_name}/languages", token)
        if not isinstance(languages, dict):
            raise TypeError(f"linguagens inesperadas em {full_name}: {languages!r}")
        for language, size in languages.items():
            total, repo_count = usage.get(language, (0, 0))
            usage[language] = (total + size, repo_count + 1)
    return usage


def weighted_language_scores(usage: dict[str, tuple[int, int]]) -> dict[str, float]:
    """Pondera bytes e nº de repositórios: ``bytes^0.5 * repos^0.5``.

    Exemplo: ``weighted_language_scores({"Go": (400, 4)}) -> {"Go": 40.0}``
    """
    return {
        language: (size**SIZE_WEIGHT) * (repo_count**COUNT_WEIGHT)
        for language, (size, repo_count) in usage.items()
    }


def top_language_shares(scores: dict[str, float], count: int) -> list[tuple[str, float]]:
    """Devolve as ``count`` maiores linguagens com fração normalizada (soma 1.0).

    Exemplo: ``top_language_shares({"Python": 75.0, "Go": 25.0}, 2) -> [("Python", 0.75), ("Go", 0.25)]``
    """
    if not scores:
        raise ValueError("nenhuma linguagem encontrada; esperado dict não vazio")
    ranked = sorted(scores.items(), key=lambda pair: -pair[1])[:count]
    shown_total = sum(score for _, score in ranked)
    return [(language, score / shown_total) for language, score in ranked]


def language_color(language: str) -> str:
    """Cor canônica do linguist para a linguagem, com cinza como fallback."""
    return LINGUIST_COLORS.get(language, FALLBACK_COLOR)


def _bar_segments(shares: list[tuple[str, float]]) -> str:
    """Desenha a barra empilhada com folga de 2px entre segmentos.

    Segmentos minúsculos ganham largura mínima de 3px para não sumirem.
    """
    drawable = BAR_WIDTH - BAR_GAP * (len(shares) - 1)
    widths = [max(3.0, share * drawable) for _, share in shares]
    scale = drawable / sum(widths)
    parts: list[str] = []
    x = 25.0
    for (language, _), width in zip(shares, widths):
        parts.append(
            f'<rect x="{x:.1f}" y="0" width="{width * scale:.1f}" height="8" '
            f'fill="{language_color(language)}" />'
        )
        x += width * scale + BAR_GAP
    return "\n    ".join(parts)


def _legend_items(shares: list[tuple[str, float]]) -> str:
    """Monta a legenda em duas colunas: bolinha colorida + nome + percentual."""
    rows_per_column = (len(shares) + 1) // 2
    parts: list[str] = []
    for index, (language, share) in enumerate(shares):
        x = 25 if index < rows_per_column else 25 + CARD_WIDTH // 2 - 12
        y = 78 + (index % rows_per_column) * 21
        parts.append(
            f'<circle cx="{x + 5}" cy="{y - 4}" r="5" fill="{language_color(language)}" />'
            f'<text x="{x + 16}" y="{y}" class="lang">{language} {share * 100:.2f}%</text>'
        )
    return "\n    ".join(parts)


def render_card_svg(shares: list[tuple[str, float]]) -> str:
    """Renderiza o card completo no estilo compact do github-readme-stats."""
    rows_per_column = (len(shares) + 1) // 2
    height = 78 + rows_per_column * 21 + 10
    return f"""<svg width="{CARD_WIDTH}" height="{height}" viewBox="0 0 {CARD_WIDTH} {height}" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Linguagens mais usadas, incluindo repositórios privados">
  <style>
    .title {{ font: 600 18px 'Segoe UI', Ubuntu, sans-serif; fill: {THEME['title']}; }}
    .lang {{ font: 400 11px 'Segoe UI', Ubuntu, sans-serif; fill: {THEME['text']}; }}
  </style>
  <rect x="0.5" y="0.5" width="{CARD_WIDTH - 1}" height="{height - 1}" rx="4.5" fill="{THEME['bg']}" stroke="#e4e2e2" stroke-opacity="0.3" />
  <text x="25" y="33" class="title">Linguagens mais usadas</text>
  <defs>
    <clipPath id="bar-round"><rect x="25" y="0" width="{BAR_WIDTH}" height="8" rx="4" /></clipPath>
  </defs>
  <g transform="translate(0, 47)" clip-path="url(#bar-round)">
    {_bar_segments(shares)}
  </g>
  <g>
    {_legend_items(shares)}
  </g>
</svg>
"""


def main() -> None:
    """Gera o card e grava em ``top-langs.svg`` na raiz do repositório."""
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise SystemExit("defina GITHUB_TOKEN com um PAT de escopo `repo`")
    repo_full_names = fetch_owned_repo_full_names(token)
    usage = collect_language_usage(token, repo_full_names)
    shares = top_language_shares(weighted_language_scores(usage), TOP_COUNT)
    output_path = os.path.join(os.path.dirname(__file__), "..", "top-langs.svg")
    with open(output_path, "w", encoding="utf-8") as output:
        output.write(render_card_svg(shares))
    print(f"top-langs.svg gerado com {len(shares)} linguagens de {len(repo_full_names)} repositórios")


if __name__ == "__main__":
    main()
