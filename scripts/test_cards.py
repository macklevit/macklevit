"""Testes dos geradores de card SVG, sem rede.

Roda com: ``python3 -m unittest discover -s scripts -p 'test_*.py'``

As funções que falam com a API do GitHub ficam de fora de propósito: o que
quebra o README em silêncio é a renderização (coordenada fora do card,
métrica faltando), e isso dá para verificar sem token.
"""

from __future__ import annotations

import re
import unittest
import xml.etree.ElementTree as ElementTree
from datetime import datetime, timezone

from generate_stats import (
    STAT_ROWS,
    build_commits_query,
    calendar_year_ranges,
    format_count,
    render_stats_svg,
    sum_commit_contributions,
)
from generate_top_langs import render_card_svg, top_language_shares
from github_card import CARD_WIDTH, render_card

ISO = "%Y-%m-%dT%H:%M:%SZ"
SAMPLE_STATS = {
    "stars": 2,
    "commits": 1037,
    "pull_requests": 171,
    "issues": 0,
    "repositories": 27,
}
SAMPLE_SHARES = [("Python", 0.6), ("Go", 0.3), ("MQL5", 0.1)]


def _utc(year: int, month: int, day: int) -> datetime:
    """Data UTC à meia-noite, para as janelas de contribuição."""
    return datetime(year, month, day, tzinfo=timezone.utc)


def _svg_height(svg: str) -> int:
    """Extrai o atributo ``height`` do elemento raiz."""
    return int(ElementTree.fromstring(svg).attrib["height"])


class RenderCardTest(unittest.TestCase):
    def test_produz_svg_valido_com_titulo_e_corpo(self) -> None:
        svg = render_card(
            100, "Título", "rótulo", "  <g id='corpo' />", ".x { fill: red; }"
        )
        root = ElementTree.fromstring(svg)
        self.assertEqual(root.attrib["aria-label"], "rótulo")
        self.assertEqual(root.attrib["height"], "100")
        self.assertIn("Título", svg)
        self.assertIn("corpo", svg)

    def test_fundo_cabe_dentro_da_moldura(self) -> None:
        svg = render_card(100, "t", "r", "", "")
        background = ElementTree.fromstring(svg).find(
            "{http://www.w3.org/2000/svg}rect"
        )
        self.assertIsNotNone(background)
        self.assertEqual(background.attrib["width"], str(CARD_WIDTH - 1))


class FormatCountTest(unittest.TestCase):
    def test_mantem_exato_abaixo_do_corte(self) -> None:
        self.assertEqual(format_count(0), "0")
        self.assertEqual(format_count(717), "717")
        self.assertEqual(format_count(1037), "1037")
        self.assertEqual(format_count(9999), "9999")

    def test_abrevia_a_partir_de_dez_mil(self) -> None:
        self.assertEqual(format_count(10_000), "10.0k")
        self.assertEqual(format_count(12_345), "12.3k")

    def test_recusa_valor_negativo(self) -> None:
        with self.assertRaisesRegex(ValueError, "-1"):
            format_count(-1)


class CalendarYearRangesTest(unittest.TestCase):
    def test_uma_janela_por_ano_calendario(self) -> None:
        ranges = calendar_year_ranges(_utc(2023, 10, 17), _utc(2026, 8, 10))
        self.assertEqual(len(ranges), 4)

    def test_primeira_janela_comeca_na_criacao_da_conta(self) -> None:
        ranges = calendar_year_ranges(_utc(2023, 10, 17), _utc(2026, 8, 10))
        self.assertEqual(ranges[0][0], "2023-10-17T00:00:00Z")

    def test_ultima_janela_termina_hoje(self) -> None:
        ranges = calendar_year_ranges(_utc(2023, 10, 17), _utc(2026, 8, 10))
        self.assertEqual(ranges[-1][1], "2026-08-10T00:00:00Z")

    def test_nenhuma_janela_passa_de_um_ano(self) -> None:
        """A API recusa intervalos maiores que 12 meses."""
        for start, end in calendar_year_ranges(_utc(2015, 3, 4), _utc(2026, 8, 10)):
            span = datetime.strptime(end, ISO) - datetime.strptime(start, ISO)
            self.assertLessEqual(
                span.days, 366, f"janela {start}..{end} passa de um ano"
            )

    def test_recusa_conta_criada_no_futuro(self) -> None:
        with self.assertRaisesRegex(ValueError, "depois de hoje"):
            calendar_year_ranges(_utc(2030, 1, 1), _utc(2026, 8, 10))


class CommitsQueryTest(unittest.TestCase):
    def test_um_alias_por_janela(self) -> None:
        query = build_commits_query([("a", "b"), ("c", "d")])
        self.assertIn("y0: contributionsCollection", query)
        self.assertIn("y1: contributionsCollection", query)

    def test_recusa_lista_vazia(self) -> None:
        with self.assertRaisesRegex(ValueError, "nenhuma janela"):
            build_commits_query([])

    def test_soma_publicos_e_privados_de_todas_as_janelas(self) -> None:
        buckets = {
            "y0": {"totalCommitContributions": 2, "restrictedContributionsCount": 3},
            "y1": {"totalCommitContributions": 10, "restrictedContributionsCount": 0},
        }
        self.assertEqual(sum_commit_contributions(buckets), 15)

    def test_recusa_janela_malformada(self) -> None:
        with self.assertRaisesRegex(TypeError, "y0"):
            sum_commit_contributions({"y0": None})


class RenderStatsSvgTest(unittest.TestCase):
    def test_desenha_uma_linha_por_metrica(self) -> None:
        svg = render_stats_svg(SAMPLE_STATS)
        for _, label, _ in STAT_ROWS:
            self.assertIn(label, svg)

    def test_mostra_o_total_de_commits(self) -> None:
        self.assertIn(">1037<", render_stats_svg(SAMPLE_STATS))

    def test_recusa_metrica_faltando(self) -> None:
        incompleto = {key: 1 for key in SAMPLE_STATS if key != "commits"}
        with self.assertRaisesRegex(KeyError, "commits"):
            render_stats_svg(incompleto)

    def test_conteudo_nao_vaza_para_fora_do_card(self) -> None:
        svg = render_stats_svg(SAMPLE_STATS)
        height = _svg_height(svg)
        for y in [int(match) for match in re.findall(r'<text x="\d+" y="(\d+)"', svg)]:
            self.assertLess(y, height, f"texto em y={y} ultrapassa a altura {height}")
        for x in [int(match) for match in re.findall(r'<text x="(\d+)"', svg)]:
            self.assertLessEqual(x, CARD_WIDTH, f"texto em x={x} ultrapassa a largura")


class CardsAlignmentTest(unittest.TestCase):
    def test_os_dois_cards_tem_a_mesma_altura(self) -> None:
        """Lado a lado no README, alturas diferentes deixam a linha torta."""
        dez_linguagens = [(f"Lang{index}", 0.1) for index in range(10)]
        self.assertEqual(
            _svg_height(render_card_svg(dez_linguagens)),
            _svg_height(render_stats_svg(SAMPLE_STATS)),
        )


class TopLanguageSharesTest(unittest.TestCase):
    def test_normaliza_para_somar_um(self) -> None:
        shares = top_language_shares({"Python": 75.0, "Go": 25.0}, 2)
        self.assertAlmostEqual(sum(share for _, share in shares), 1.0)

    def test_recusa_entrada_vazia(self) -> None:
        with self.assertRaisesRegex(ValueError, "nenhuma linguagem"):
            top_language_shares({}, 5)


if __name__ == "__main__":
    unittest.main()
