"""Testes do tirante de base e L3 com H_sapata≈0."""
import math
import pytest

from mlc_projeto.checks.elu.tirante_base import (
    verificar_tirante_base, escolher_diametro, _n_t_rd_kN,
)
from mlc_projeto.connections.connections import dimensionar_sapata
from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.wind import ParametrosVento
from mlc_projeto.core.loads import carregamentos_com_vento


def _load_R2():
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
    mat = GlulamMaterial(classe="GL24h", classe_servico=3, duracao="curta")
    pv = ParametrosVento(
        V0=45.0, S1=1.0, categoria="IV", classe="B", S3=1.0,
        L=20.25, H1=geo.h_ap - geo.h0, h=7.0, dist_portico=5.75,
    )
    load = carregamentos_com_vento(
        geo=geo, mat=mat, g_area=1.50, q_area=0.25,
        L_t=5.75, params_vento=pv,
    )
    return geo, mat, load


def test_escolher_diametro_cresce_com_T():
    d1 = escolher_diametro(500.0, aco="S355", eta_alvo=0.75)
    d2 = escolher_diametro(1600.0, aco="S355", eta_alvo=0.75)
    assert d2 >= d1
    assert _n_t_rd_kN(d2, "S355") >= 1600.0 / 0.75 - 1e-6


def test_verificar_tirante_eta_alvo():
    T = 1630.5
    res = verificar_tirante_base(
        T_d_kN=T, L_m=20.25, aco="S355", d_mm=None, eta_alvo=0.75,
        n_vaos_por_linha=2, n_linhas=9,
    )
    assert res["ativo"] is True
    assert res["H_sapata_kN"] == 0.0
    assert res["T_d_kN"] == pytest.approx(T, rel=1e-6)
    assert res["eta"] <= 0.75 + 1e-6
    assert res["ok"]
    assert res["d_mm"] >= 20
    assert res["n_barras"] == 18
    assert res["delta_el_mm"] > 0


def test_verificar_tirante_d_fixo():
    res = verificar_tirante_base(
        T_d_kN=100.0, L_m=20.0, aco="S235", d_mm=30.0, eta_alvo=1.0,
    )
    assert res["d_mm"] == 30.0
    assert res["d_auto"] is False
    assert res["ok_norma"]


def test_L3_com_tirante_H_zero():
    geo, mat, load = _load_R2()
    H_arco = load.H_ELU()
    assert H_arco > 1000.0  # ordem de grandeza do projeto

    L3_sem = dimensionar_sapata(load, geo, F_chu_kN=80.0, eta_alvo=0.75,
                                com_tirante=False)
    L3_com = dimensionar_sapata(load, geo, F_chu_kN=80.0, eta_alvo=0.75,
                                com_tirante=True, b_pilar_m=0.32, h_pilar_m=0.27)

    assert L3_sem["H_d_kN"] == pytest.approx(H_arco, rel=1e-6)
    assert L3_sem["n_chumbadores"] >= 20

    assert L3_com["com_tirante"] is True
    assert L3_com["H_d_kN"] == 0.0
    assert L3_com["H_arco_kN"] == pytest.approx(H_arco, rel=1e-6)
    assert L3_com["n_chumbadores"] == 4
    assert L3_com["eta"] == pytest.approx(L3_com["eta_N"], rel=1e-6)
    assert L3_com["ok"]
