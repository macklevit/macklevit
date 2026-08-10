"""Gera ``stats.svg`` com as estatísticas de GitHub do usuário autenticado.

Substitui o card hospedado do github-readme-stats, que dependia da instância
Vercel de terceiros (fora do ar / sem PAT) e, por autenticar com o token do
dono do deploy, nunca enxergou repositórios privados: ``count_private=true``
não fazia efeito nenhum. Aqui o PAT é o seu, então
``restrictedContributionsCount`` traz também os commits privados.

Uso:
    GITHUB_TOKEN=<PAT com escopo repo> python3 scripts/generate_stats.py
"""

from __future__ import annotations

import os

from github_card import CARD_WIDTH, THEME, graphql_query, render_card

ROW_FIRST_Y = 68
ROW_SPACING = 25
BOTTOM_PADDING = 25
ICON_SIZE = 16

STATS_QUERY = """
query {
  viewer {
    repositories(ownerAffiliations: OWNER, isFork: false, first: 100) {
      totalCount
      nodes { stargazerCount }
    }
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
    }
    pullRequests { totalCount }
    issues { totalCount }
  }
}
"""

# Octicons 16x16 do próprio GitHub, para o card falar a mesma língua visual.
ICON_PATHS: dict[str, str] = {
    "star": (
        "M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97."
        "719 4.192a.751.751 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194"
        "L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Z"
    ),
    "commit": (
        "M11.93 8.5a4.002 4.002 0 0 1-7.86 0H.75a.75.75 0 0 1 0-1.5h3.32a4.002 4.002 0 0 1 7.86 0"
        "h3.32a.75.75 0 0 1 0 1.5Zm-1.43-.75a2.5 2.5 0 1 0-5 0 2.5 2.5 0 0 0 5 0Z"
    ),
    "pull-request": (
        "M1.5 3.25a2.25 2.25 0 1 1 3 2.122v5.256a2.251 2.251 0 1 1-1.5 0V5.372A2.25 2.25 0 0 1 1.5"
        " 3.25Zm5.677-.177L9.573.677A.25.25 0 0 1 10 .854V2.5h1A2.5 2.5 0 0 1 13.5 5v5.628a2.251 "
        "2.251 0 1 1-1.5 0V5a1 1 0 0 0-1-1h-1v1.646a.25.25 0 0 1-.427.177L7.177 3.427a.25.25 0 0 "
        "1 0-.354ZM3.75 2.5a.75.75 0 1 0 0 1.5.75.75 0 0 0 0-1.5Zm0 9.5a.75.75 0 1 0 0 1.5.75.75 "
        "0 0 0 0-1.5Zm8.25.75a.75.75 0 1 0 1.5 0 .75.75 0 0 0-1.5 0Z"
    ),
    "issue": (
        "M8 9.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3ZM8 0a8 8 0 1 1 0 16A8 8 0 0 1 8 0ZM1.5 8a6.5 "
        "6.5 0 1 0 13 0 6.5 6.5 0 0 0-13 0Z"
    ),
    "repo": (
        "M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75"
        " 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.714 1.7.75.75 0 1 1-1.072 1.05A2.495 2.495 0 0 1 2 11"
        ".5Zm10.5-1h-8a1 1 0 0 0-1 1v6.708A2.486 2.486 0 0 1 4.5 9h8Z"
    ),
}

# (chave do ícone, rótulo, chave em fetch_profile_stats)
STAT_ROWS: list[tuple[str, str, str]] = [
    ("star", "Estrelas recebidas", "stars"),
    ("commit", "Commits (último ano)", "commits"),
    ("pull-request", "Pull requests", "pull_requests"),
    ("issue", "Issues", "issues"),
    ("repo", "Repositórios", "repositories"),
]


def fetch_profile_stats(token: str) -> dict[str, int]:
    """Busca as métricas do perfil, somando commits públicos e privados.

    Exemplo: ``fetch_profile_stats(token) -> {"stars": 2, "commits": 717, ...}``
    """
    viewer = graphql_query(STATS_QUERY, token)["viewer"]
    if not isinstance(viewer, dict):
        raise TypeError(f"viewer inesperado: {viewer!r}; esperado dict")
    contributions = viewer["contributionsCollection"]
    repositories = viewer["repositories"]
    return {
        "stars": sum(repo["stargazerCount"] for repo in repositories["nodes"]),
        "commits": (
            contributions["totalCommitContributions"]
            + contributions["restrictedContributionsCount"]
        ),
        "pull_requests": viewer["pullRequests"]["totalCount"],
        "issues": viewer["issues"]["totalCount"],
        "repositories": repositories["totalCount"],
    }


def format_count(value: int) -> str:
    """Abrevia milhares como o github-readme-stats faz.

    Exemplo: ``format_count(1234) -> "1.2k"``; ``format_count(717) -> "717"``
    """
    if value < 0:
        raise ValueError(f"contagem negativa: {value}; esperado inteiro >= 0")
    if value < 1000:
        return str(value)
    return f"{value / 1000:.1f}k"


def _stat_row_svg(icon_key: str, label: str, value: int, y: int) -> str:
    """Desenha uma linha do card: ícone, rótulo à esquerda e valor à direita."""
    if icon_key not in ICON_PATHS:
        raise KeyError(
            f"ícone desconhecido: {icon_key!r}; esperado um de {sorted(ICON_PATHS)}"
        )
    icon = (
        f'<g transform="translate(25, {y - ICON_SIZE + 4})">'
        f'<path d="{ICON_PATHS[icon_key]}" fill="{THEME["title"]}" /></g>'
    )
    return (
        f"{icon}"
        f'<text x="50" y="{y}" class="stat">{label}</text>'
        f'<text x="{CARD_WIDTH - 25}" y="{y}" class="stat value">{format_count(value)}</text>'
    )


def render_stats_svg(stats: dict[str, int]) -> str:
    """Renderiza o card completo, uma linha por métrica de ``STAT_ROWS``."""
    missing = [key for _, _, key in STAT_ROWS if key not in stats]
    if missing:
        raise KeyError(
            f"métricas ausentes: {missing}; esperadas {[k for _, _, k in STAT_ROWS]}"
        )
    rows = [
        _stat_row_svg(icon, label, stats[key], ROW_FIRST_Y + index * ROW_SPACING)
        for index, (icon, label, key) in enumerate(STAT_ROWS)
    ]
    height = ROW_FIRST_Y + ROW_SPACING * (len(STAT_ROWS) - 1) + BOTTOM_PADDING
    extra_css = (
        f".stat {{ font: 400 12px 'Segoe UI', Ubuntu, sans-serif; fill: {THEME['text']}; }}\n"
        "    .value { font-weight: 600; text-anchor: end; }"
    )
    body = "  <g>\n    " + "\n    ".join(rows) + "\n  </g>"
    return render_card(
        height, "Estatísticas do GitHub", "Estatísticas do GitHub", body, extra_css
    )


def main() -> None:
    """Gera o card e grava em ``stats.svg`` na raiz do repositório."""
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise SystemExit("defina GITHUB_TOKEN com um PAT de escopo `repo`")
    stats = fetch_profile_stats(token)
    output_path = os.path.join(os.path.dirname(__file__), "..", "stats.svg")
    with open(output_path, "w", encoding="utf-8") as output:
        output.write(render_stats_svg(stats))
    print(f"stats.svg gerado: {stats['commits']} commits, {stats['pull_requests']} PRs")


if __name__ == "__main__":
    main()
