"""Issue 101 — seção das terças dimensionada por varredura do pipeline completo."""

import mlc_projeto.main as M
from mlc_projeto.predim.varredura_terca import ETA_ALVO_TERCA, avaliar, escolher


def test_secao_adotada_e_a_do_pipeline_e_atende():
    r = avaliar(M.B_TERCA, M.H_TERCA)
    assert r["ok"] and r["eta_terca"] <= ETA_ALVO_TERCA
    assert (M.B_TERCA, M.H_TERCA) == (0.20, 0.40)


def test_secao_imediatamente_menor_nao_atende():
    # 0,20 × 0,36 e 0,18 × 0,40 têm a mesma área (0,072) e ficam acima do alvo
    assert not avaliar(0.20, 0.36)["ok"]
    assert not avaliar(0.18, 0.40)["ok"]


def test_escolher_pega_a_primeira_aprovada():
    linhas = [{"ok": False}, {"ok": True, "b": 1}, {"ok": True, "b": 2}]
    assert escolher(linhas)["b"] == 1
