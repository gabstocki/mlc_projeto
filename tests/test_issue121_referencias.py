"""Issue 121 — casos de referência independentes, tabela de pacotes e versão."""

import contextlib
import io
from pathlib import Path

import pytest

from mlc_projeto.output.apendice_programa import contar_por_pacote, identificacao_versao
from mlc_projeto.output.validacao import avaliar_todos, casos
from mlc_projeto.output.valores_tese import contar_codigo

RAIZ = Path(__file__).resolve().parents[1]


def test_casos_analiticos_e_normativos():
    r = avaliar_todos()
    assert len(r) == len(casos()) >= 9
    falhas = [x["grandeza"] for x in r if not x["ok"]]
    assert not falhas, falhas


@pytest.fixture(scope="module")
def execucao():
    import mlc_projeto.checks.elu.apoio as A
    import mlc_projeto.main as M
    cap, orig, rel = {}, M.reacao_arrancamento_max, M.gerar_relatorio

    def spy(load):
        cap["load"] = load
        return orig(load)
    try:
        M.reacao_arrancamento_max, M.gerar_relatorio = spy, (lambda *a, **k: {})
        with contextlib.redirect_stdout(io.StringIO()):
            res = M._main_impl(rodar_varredura=False, abrir_viz=False)
    finally:
        M.reacao_arrancamento_max, M.gerar_relatorio = orig, rel
    return res, cap["load"]


def test_equilibrio_convergencia_e_fem(execucao):
    res, load = execucao
    r = avaliar_todos(res, load)
    classes = {x["classe"] for x in r}
    assert {"equilíbrio", "convergência", "numérico"} <= classes
    falhas = [(x["grandeza"], x["erro_rel"]) for x in r if not x["ok"]]
    assert not falhas, falhas


def test_tabela_de_pacotes_soma_o_mesmo_que_as_macros():
    linhas = contar_por_pacote(RAIZ)
    n, lin = contar_codigo(RAIZ)
    assert sum(x[1] for x in linhas) == n
    assert sum(x[2] for x in linhas) == lin


def test_identificacao_da_versao():
    v = identificacao_versao(RAIZ)
    assert len(v["commit"]) >= 7 and isinstance(v["limpo"], bool)
