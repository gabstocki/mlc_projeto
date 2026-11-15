"""Issue 72 — curso dos furos ovalizados da L1/L1c (umidade e fluência)."""

import math

import pytest

from mlc_projeto.connections.oblongo_L1 import (
    ALPHA_PERP, curso_oblongo, recalque_compressao_mm,
)


def _r(**kw):
    base = dict(y_pinos_mm=[928.0, 856.0, 568.0], R_G_kN=50.0, R_var_kN=30.0, b_m=0.32,
                l_apoio_m=0.25, k_def=2.0)
    base.update(kw)
    return curso_oblongo(**base)


def test_inchamento_governa_madeira_colada_seca():
    r = _r()
    # montagem 13–17 %, serviço 14–19 %: sobe 6 pontos, desce 3
    assert r["inchamento_mm"] == pytest.approx(ALPHA_PERP * 6 * 928)
    assert r["retracao_mm"] == pytest.approx(ALPHA_PERP * 3 * 928)
    assert r["c_cima_mm"] >= r["c_cima_req_mm"] and r["c_baixo_mm"] >= r["c_baixo_req_mm"]
    assert r["c_cima_mm"] % 5 == 0 and r["ok"]


def test_recalque_com_dispersao_menor_que_tensao_uniforme():
    d = recalque_compressao_mm(50.0, 0.32, 0.25, 928.0)
    uniforme = 50e3 / (320 * 250) / 300.0 * 928.0
    assert 0 < d < uniforme


def test_levantamento_e_regra_de_montagem():
    r = _r()
    assert r["levantamento_max_mm"] == pytest.approx(ALPHA_PERP * 5 * 928 + 2.0, abs=0.1)
    regra = r["folga_acima_montagem_mm"]
    # quanto mais úmida a viga na montagem, menor a folga deixada acima do pino
    assert regra["13%"][0] > regra["15%"][0] > regra["17%"][0]


def test_geometria_rasgo_deixa_madeira_e_folga_no_fundo():
    from mlc_projeto.connections.oblongo_L1 import geometria_rasgo
    g = geometria_rasgo(h0_mm=1000.0, d_mm=24.0, d0_mm=26.0, a2_mm=72.0, n_fileiras=2,
                        R_G_kN=50.0, R_var_kN=30.0, b_m=0.32, l_apoio_m=0.25, k_def=2.0)
    assert g["madeira_sobre_rasgo_mm"] >= 100.0
    assert g["fundo_rasgo_mm"] >= g["topo_chapa_mm"] + g["folga_fundo_mm"]
    assert g["a4c_topo_mm"] >= 3 * 24.0
