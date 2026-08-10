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

from generate_stats import STAT_ROWS, format_count, render_stats_svg
from generate_top_langs import render_card_svg, top_language_shares
from github_card import CARD_WIDTH, render_card

SAMPLE_STATS = {
    "stars": 2,
    "commits": 717,
    "pull_requests": 171,
    "issues": 0,
    "repositories": 27,
}
SAMPLE_SHARES = [("Python", 0.6), ("Go", 0.3), ("MQL5", 0.1)]


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
    def test_mantem_valores_abaixo_de_mil(self) -> None:
        self.assertEqual(format_count(0), "0")
        self.assertEqual(format_count(717), "717")
        self.assertEqual(format_count(999), "999")

    def test_abrevia_milhares(self) -> None:
        self.assertEqual(format_count(1000), "1.0k")
        self.assertEqual(format_count(1234), "1.2k")

    def test_recusa_valor_negativo(self) -> None:
        with self.assertRaisesRegex(ValueError, "-1"):
            format_count(-1)


class RenderStatsSvgTest(unittest.TestCase):
    def test_desenha_uma_linha_por_metrica(self) -> None:
        svg = render_stats_svg(SAMPLE_STATS)
        for _, label, _ in STAT_ROWS:
            self.assertIn(label, svg)

    def test_mostra_commits_publicos_mais_privados(self) -> None:
        self.assertIn(">717<", render_stats_svg(SAMPLE_STATS))

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
