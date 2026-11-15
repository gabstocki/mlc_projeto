"""Issue 115 — o memorial (Apêndice B) reproduz a aritmética que imprime."""

import contextlib
import io

import pytest

from mlc_projeto.output.conferir_memorial import conferir, latex_para_python
from mlc_projeto.output.tab_retracao import tabela_retracao

def test_conversor_de_latex():
    assert eval(latex_para_python(r"\frac{1{,}5 \times 94{,}9}{0{,}67 \times 0{,}32}")) == pytest.approx(
        1.5 * 94.9 / (0.67 * 0.32))
    assert eval(latex_para_python(r"\frac{191}{1.020 \times 235 \times 10^{-3}}")) == pytest.approx(
        191 / (1020 * 235e-3))
    assert latex_para_python(r"\frac{N_{Ed}}{A}") is None          # simbólico: ignorado


def test_conferidor_acusa_conta_errada():
    tex = r"""\begin{align}
    a &= \frac{6 \times 10}{2} = 30 \nonumber \\
    b &= 104 + 258 = 368
\end{align}"""
    r = conferir(tex)
    assert [x["ok"] for x in r] == [True, False]


@pytest.fixture(scope="module")
def apendice(tmp_path_factory):
    """Gera o Apêndice B a partir de uma execução nova do pipeline."""
    import mlc_projeto.main as M
    from mlc_projeto.output.memorial_equacoes import gerar_apendice_memoria
    backup = M.gerar_relatorio
    try:
        M.gerar_relatorio = lambda *a, **k: {}
        with contextlib.redirect_stdout(io.StringIO()):
            res = M._main_impl(rodar_varredura=False, abrir_viz=False)
    finally:
        M.gerar_relatorio = backup
    out = tmp_path_factory.mktemp("mem") / "apendiceB.tex"
    gerar_apendice_memoria(res, out)
    return out.read_text(encoding="utf-8")


def test_apendice_B_reproduz_os_resultados(apendice):
    r = conferir(apendice)
    erradas = [f"{x['expressao']} = {x['impresso']} (calc. {x['calculado']:.4g})"
               for x in r if not x["ok"]]
    assert len(r) >= 25
    assert not erradas, "\n".join(erradas)


def test_tabela_de_retracao_gerada_sem_caracteres_invalidos():
    g = [{"rotulo": "L3a_canto, pé do pilar", "n_perp": 3, "D_perp_mm": 120.0, "delta_mm": 0.9,
          "solucao": "furo redondo (folga do furo absorve)"},
         {"rotulo": "escora de beiral", "n_perp": 5, "D_perp_mm": 240.0, "delta_mm": 1.8,
          "solucao": "furos ovalizados ⊥ fibras, curso ±4 mm"}]
    t = tabela_retracao(g)
    assert "_" not in t.split("\\midrule")[1]
    assert "Ovalizado, curso $\\pm 4$ mm" in t and "L3a de canto" in t
