"""Issue 78 — soldas de filete (EN 1993-1-8 §4.5.3.3)."""

import math

import pytest

from mlc_projeto.connections.soldas import f_vw_d, filete


def test_resistencia_do_filete_s275():
    assert f_vw_d("S275") == pytest.approx(430 / math.sqrt(3) / (0.85 * 1.25))


def test_menor_garganta_e_limite_de_espessura():
    r = filete(peca="t", F_norm_kN=100.0, l_mm=270, t_min_mm=16)
    assert r["a_mm"] == 4.0 and r["ok"]
    big = filete(peca="t", F_norm_kN=2000.0, l_mm=100, t_min_mm=10)
    assert big["a_mm"] <= 7.0 and not big["ok"]                  # a ≤ 0,7·t


def test_momento_pelo_binario_dos_cordoes():
    sem = filete(peca="t", F_par_kN=100, l_mm=200, t_min_mm=16)
    com = filete(peca="t", F_par_kN=100, M_kNm=4.0, z_mm=30, l_mm=200, t_min_mm=16)
    assert com["F_w_Ed_Nmm"] > sem["F_w_Ed_Nmm"]
