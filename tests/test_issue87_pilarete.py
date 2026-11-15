"""Issue 87 — pilarete metálico entre a chapa de base e o pé do pilar."""

import math

import pytest

import mlc_projeto.main as M
from mlc_projeto.connections.base_pilar import tstub_base_tubo
from mlc_projeto.connections.pilarete import (
    propriedades_chs, tracao_equivalente_momento, verificar_pilarete,
)


def test_propriedades_tubo():
    p = propriedades_chs(139.7, 8.0)
    assert p["A"] == pytest.approx(math.pi / 4 * (139.7 ** 2 - 123.7 ** 2))
    assert p["W_pl"] > p["W_el"]


def test_pilarete_momento_e_chapa_de_topo_menor_que_o_pilar():
    r = verificar_pilarete(rotulo="t", N_c_kN=300, N_t_kN=280, V_kN=48.5, h_m=0.30,
                           b_pilar_mm=320, h_pilar_mm=320)
    assert r["M_base_kNm"] == pytest.approx(48.5 * 0.30)
    B, L, t = r["chapa_topo_mm"]
    assert B < 320 and L < 320                       # sem bandeja
    assert r["D_mm"] <= 320 - 40 and r["ok"]


def test_binario_no_grupo_2x2():
    # M = 14,6 kN·m, braço 0,40 m, fileira de 2 → 18,25 kN no chumbador; × 4
    assert tracao_equivalente_momento(14.6, (2, 2), 400) == pytest.approx(4 * 14.6 / 0.4 / 2)


def test_tstub_tubo_usa_padrao_de_canto():
    r = tstub_base_tubo(100.0, chumbadores_mm=[(200, 200), (-200, 200), (200, -200), (-200, -200)],
                        D_tubo_mm=139.7, a_solda_mm=6, e_mm=60, F_t_Rd_chu_kN=150, t_mm=12.5)
    m = math.hypot(200, 200) - 139.7 / 2 - 0.8 * 6 * math.sqrt(2)
    assert r["l_eff_mm"] == pytest.approx(min(2 * math.pi * m, math.pi * m + 120,
                                              4 * m + 75, 2 * m + 37.5 + 60), abs=1)


def test_madeira_comeca_acima_do_pilarete():
    assert M.H_PILAR_MAD == pytest.approx(M.H_PILAR_ALT - M.H_PILARETE_M)
    assert M.H_IMP_PISO_M > M.H_PILARETE_M          # o choque atinge a madeira
