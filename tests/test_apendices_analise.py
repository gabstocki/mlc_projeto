"""Issue 51 — apêndices de análise estática (C) e da saída do pipeline (D)."""
import contextlib
import io
import re
from pathlib import Path

import pytest

import mlc_projeto.main as M
from mlc_projeto.output.apendice_analise import gerar_apendice_analise, linhas_esforcos

RAIZ = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def pipeline():
    """Executa o pipeline e captura o `load` e a `geo` usados nele."""
    capt = {}
    orig_cv, orig_rel = M.carregamentos_com_vento, M.gerar_relatorio

    def _cv(*a, **k):
        capt["load"] = orig_cv(*a, **k)
        capt["geo"] = k["geo"]
        return capt["load"]

    try:
        M.carregamentos_com_vento = _cv
        M.gerar_relatorio = lambda *a, **k: {}
        with contextlib.redirect_stdout(io.StringIO()):
            capt["res"] = M._main_impl(rodar_varredura=False, abrir_viz=False)
    finally:
        M.carregamentos_com_vento, M.gerar_relatorio = orig_cv, orig_rel
    return capt


def test_tabela_tem_todas_as_combinacoes_elu(pipeline):
    load = pipeline["load"]
    linhas = linhas_esforcos(load)
    assert len(linhas) == len(load.combinacoes_ELU_fisicas()) == 29
    assert [l["n"] for l in linhas] == list(range(1, 30))


def test_governante_coincide_com_o_memorial(pipeline):
    load = pipeline["load"]
    gov = next(l for l in linhas_esforcos(load) if "|M|" in l["governa"])
    assert gov["M_max"] == pytest.approx(load.M_max_ELU(), abs=0.01)
    # V e N nos apoios = decomposição no eixo da combinação governante (issue 12)
    assert abs(gov["V_max"]) == pytest.approx(abs(load.V_viga_ELU()), abs=0.01)
    assert abs(gov["N_max"]) == pytest.approx(abs(load.N_max_ELU()), abs=0.01)


def test_apendice_e_figuras_gerados(pipeline, tmp_path):
    out = gerar_apendice_analise(pipeline["load"], pipeline["geo"], tmp_path)
    tex = out.read_text(encoding="utf-8")
    assert "\\label{ap:analise-estatica}" in tex
    for lbl in ("fig:an-mvn-governante", "fig:an-mvn-todas", "tab:an-esforcos"):
        assert f"\\autoref{{{lbl}}}" in tex
    assert (tmp_path / "fig" / "analise_MVN_governante.pdf").stat().st_size > 0
    assert (tmp_path / "fig" / "analise_MVN_combinacoes.pdf").stat().st_size > 0
    corpo = tex.split("\\begin{tabular}", 1)[1]
    assert not re.search(r"(?<![\d.])\d+\.\d", corpo)      # vírgula decimal


def test_main_inclui_os_apendices():
    main = (RAIZ / "tese" / "main.tex").read_text(encoding="utf-8")
    assert "\\input{apendiceC}" in main and "\\input{apendiceD}" in main
    ap_d = (RAIZ / "tese" / "apendiceD.tex").read_text(encoding="utf-8")
    assert "../output/pipeline_console.txt" in ap_d


def test_console_so_tem_caracteres_mapeados_no_listings():
    """pdflatex + listings aborta em caractere UTF-8 sem `literate`: todo
    caractere não ASCII da saída do pipeline precisa estar mapeado."""
    console = RAIZ / "output" / "pipeline_console.txt"
    if not console.exists():
        pytest.skip("pipeline_console.txt ainda não gerado")
    estilo = (RAIZ / "tese" / "00-pacotesOpcionais.tex").read_text(encoding="utf-8")
    literate = estilo.split("literate =", 1)[1].split("\n}", 1)[0]
    mapeados = set(re.findall(r"\{(.)\}\{\{", literate))
    usados = {c for c in console.read_text(encoding="utf-8") if ord(c) > 127}
    assert not usados - mapeados, f"sem mapeamento: {sorted(usados - mapeados)}"
