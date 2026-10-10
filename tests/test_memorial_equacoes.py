"""Issue 50 — apêndice de memória de cálculo gerado a partir dos resultados."""
import contextlib
import io
import re

import pytest

import mlc_projeto.main as M
from mlc_projeto.output.formatacao import fmt_eta
from mlc_projeto.output.memorial_equacoes import gerar_apendice_memoria


@pytest.fixture(scope="module")
def res():
    backup = M.gerar_relatorio
    try:
        M.gerar_relatorio = lambda *a, **k: {}
        with contextlib.redirect_stdout(io.StringIO()):
            return M._main_impl(rodar_varredura=False, abrir_viz=False)
    finally:
        M.gerar_relatorio = backup


def test_apendice_tem_as_verificacoes_governantes(res, tmp_path):
    out = gerar_apendice_memoria(res, tmp_path / "ap.tex")
    tex = out.read_text()
    for rotulo in ("cisalhamento", "cumeeira", "borda-inclinada", "flexocompressao",
                   "flecha", "pilar-central", "terca", "telha", "cv-cobertura",
                   "cv-vertical", "l1", "ancoragem"):
        assert f"\\label{{eq:mem-{rotulo}}}" in tex
    # align quebrável entre páginas (revisão de formatação), um número por bloco
    assert tex.count("\\begin{align}") == tex.count("\\end{align}") == 12


def test_valores_saem_dos_resultados(res, tmp_path):
    tex = gerar_apendice_memoria(res, tmp_path / "ap.tex").read_text()
    # issue 53: η com duas casas, arredondado para cima
    eta_cv = fmt_eta(res['contraventamento_vertical']['eta_diag_N']).replace(",", "{,}")
    assert eta_cv in tex
    eta_ci = fmt_eta(res['cisalhamento']['eta']).replace(",", "{,}")
    assert eta_ci in tex
    # vírgula decimal: nenhum "0.xxx" anglo-saxão nas equações (o ponto só
    # aparece como separador de milhar, em grupos de três dígitos)
    corpo = tex.split("\\section", 1)[1]
    assert not re.search(r"(?<![\d.])0\.\d", corpo)
