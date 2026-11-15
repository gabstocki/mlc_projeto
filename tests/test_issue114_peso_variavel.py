"""Issue 114 — peso próprio da viga segue a altura h(x)."""

import math

import pytest

from mlc_projeto.core.loads import analisar_biarticulada

KW = dict(L=20.25, h0=1.0, h_ap=1.0 + 10.125 * math.tan(math.radians(10)),
          alpha_rad=math.radians(10), b=0.32, desenvolve_empuxo=False)


def test_correcao_do_meio_do_vao_bate_com_a_formula_fechada():
    r0 = analisar_biarticulada(q=10.0, **KW)
    r1 = analisar_biarticulada(q=10.0, g_var_kNm3=4.12, **KW)
    dM = r1["M_cumeeira_kNm"] - r0["M_cumeeira_kNm"]
    esperado = 0.32 * 4.12 * (KW["h_ap"] - KW["h0"]) * KW["L"] ** 2 / 48.0
    assert dM == pytest.approx(esperado, rel=5e-3)
    # resultante nula: as reações do vão não mudam
    assert r1["R_A_kN"] == pytest.approx(r0["R_A_kN"], abs=1e-6)


def test_beiral_mais_baixo_que_a_media_reduz_o_peso_do_balanco():
    kw = dict(KW, a_bal=1.135)
    r0 = analisar_biarticulada(q=10.0, **kw)
    r1 = analisar_biarticulada(q=10.0, g_var_kNm3=4.12, **kw)
    assert r1["V_bal_A_kN"] < r0["V_bal_A_kN"]          # balanço mais leve
    assert abs(r1["M_apoio_A_kNm"]) < abs(r0["M_apoio_A_kNm"])
