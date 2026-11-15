"""Issue 99 — números da tese gerados pelo pipeline."""

import pytest

from mlc_projeto.core.normativo import parametros_ndp
from mlc_projeto.output.valores_tese import macros, por_extenso, tabela_ndp


@pytest.mark.parametrize("n, fem, esperado", [
    (2, True, "duas"), (2, False, "dois"), (21, True, "vinte e uma"),
    (73, True, "setenta e três"), (75, True, "setenta e cinco"), (100, False, "cem"),
    (172, True, "cento e setenta e duas"), (200, True, "duzentas"), (20, False, "vinte"),
])
def test_por_extenso(n, fem, esperado):
    assert por_extenso(n, fem) == esperado


def test_tabela_ndp_tem_uma_linha_por_parametro():
    t = tabela_ndp()
    linhas = [l for l in t.splitlines() if l.strip().endswith(r"\\") and "textbf" not in l]
    assert len(linhas) == len(parametros_ndp())


def test_macros_contem_contagens():
    m = macros(n_verif=75, n_exec=73, n_na=2, eta_max=0.8999, n_testes=850, n_ndp=20)
    assert r"\newcommand{\nVerifExecExt}{setenta e três}" in m
    assert r"\newcommand{\nVerifNAExt}{duas}" in m
    assert r"\newcommand{\etaMaxGlobal}{0,90}" in m
    assert r"\newcommand{\nTestes}{850}" in m
