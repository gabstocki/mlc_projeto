"""Issue 20 — Fendilhamento (splitting) das ligações — EC5 §8.1.4 Eq. (8.4)/(8.5).

Verifica a capacidade ao fendilhamento onde há componente de força ⊥ às fibras
(F_90,Ed = |V_d| na resultante inclinada de L1/L1c):

    F_90,Rk = 14·b·w·√(h_e/(1 − h_e/h))    (8.4)   [N, mm]
    F_90,Rd = k_mod·F_90,Rk/γ_M
    η = F_90,Ed / F_90,Rd
"""

import math

import pytest

from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.wind import ParametrosVento
from mlc_projeto.core.loads import carregamentos_com_vento
from mlc_projeto.connections.connections import (
    verificar_fendilhamento,
    fendilhamento_ligacao,
    dimensionar_ligacao_base,
)


def test_formula_84_valor_conhecido():
    """F_90,Rk = 14·b·w·√(h_e/(1−h_e/h)) — valor fechado à mão."""
    b, h, h_e = 320.0, 1000.0, 500.0
    r = verificar_fendilhamento(
        F_90_Ed_kN=50.0, b_mm=b, h_mm=h, h_e_mm=h_e,
        k_mod=0.70, gamma_M=1.30, w=1.0,
    )
    F_rk = 14.0 * b * math.sqrt(h_e / (1.0 - h_e / h))   # N
    assert r["F_90_Rk_kN"] == pytest.approx(F_rk / 1e3, rel=1e-3)
    assert r["F_90_Rd_kN"] == pytest.approx(0.70 * F_rk / 1.30 / 1e3, rel=1e-3)
    assert r["eta"] == pytest.approx(50.0 / r["F_90_Rd_kN"], rel=1e-3)


def test_capacidade_cresce_com_he():
    """h_e maior (fileiras mais profundas) → maior F_90,Rk (menos frágil)."""
    base = dict(F_90_Ed_kN=50.0, b_mm=320.0, h_mm=1000.0, k_mod=0.7, gamma_M=1.3)
    r_raso = verificar_fendilhamento(h_e_mm=300.0, **base)
    r_fundo = verificar_fendilhamento(h_e_mm=800.0, **base)
    assert r_fundo["F_90_Rk_kN"] > r_raso["F_90_Rk_kN"]


def test_he_invalido_levanta():
    base = dict(F_90_Ed_kN=50.0, b_mm=320.0, h_mm=1000.0, k_mod=0.7, gamma_M=1.3)
    with pytest.raises(ValueError):
        verificar_fendilhamento(h_e_mm=1000.0, **base)   # h_e = h
    with pytest.raises(ValueError):
        verificar_fendilhamento(h_e_mm=0.0, **base)


def test_w_reduz_capacidade():
    """w < 1 (chapa puncionada) reduz F_90,Rk proporcionalmente."""
    base = dict(F_90_Ed_kN=50.0, b_mm=320.0, h_mm=1000.0, h_e_mm=500.0,
                k_mod=0.7, gamma_M=1.3)
    r1 = verificar_fendilhamento(w=1.0, **base)
    r2 = verificar_fendilhamento(w=0.5, **base)
    assert r2["F_90_Rk_kN"] == pytest.approx(0.5 * r1["F_90_Rk_kN"], rel=1e-6)


# ── Integração com a ligação L1 real ─────────────────────────────────────────

def _load_real():
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
    mat = GlulamMaterial("GL24h", 3, "curta")
    pv = ParametrosVento(V0=45, S1=1, categoria="IV", classe="B", S3=1,
                         L=20.25, H1=geo.h_ap - geo.h0, h=7, dist_portico=5.75)
    load = carregamentos_com_vento(geo=geo, mat=mat, g_area=0.823, q_area=0.40,
                                   L_t=5.75, params_vento=pv)
    gov = load.combinacao_ELU_governante()
    return geo, mat.com_duracao(gov.duracao), load


def test_fendilhamento_ligacao_usa_Vd_como_F90():
    """F_90,Ed da ligação = |V_d| (componente ⊥ fibras da resultante)."""
    geo, mat, load = _load_real()
    L1 = dimensionar_ligacao_base(mat, load, geo, d_mm=24)
    rf = fendilhamento_ligacao(L1, geo, mat)
    assert rf["F_90_Ed_kN"] == pytest.approx(abs(L1["V_d_kN"]), rel=1e-6)
    # h_e do grupo centrado: h0/2 + (n_linhas−1)·a2/2
    h_e = L1["h_disp_mm"] / 2 + (L1["n_linhas"] - 1) * L1["a2_mm"] / 2
    assert rf["h_e_mm"] == pytest.approx(h_e, rel=1e-6)
    assert rf["b_mm"] == pytest.approx(geo.b * 1e3, rel=1e-9)


def test_fendilhamento_L1_aprova_e_gamma_ligacao():
    """L1 real passa no fendilhamento (η<1) com γ_M=1,30 (ligação)."""
    geo, mat, load = _load_real()
    L1 = dimensionar_ligacao_base(mat, load, geo, d_mm=24)
    rf = fendilhamento_ligacao(L1, geo, mat)
    assert rf["gamma_M"] == pytest.approx(1.30, rel=1e-9)
    assert rf["ok"]
    assert 0.0 < rf["eta"] < 1.0
    assert rf["norma"].startswith("EN 1995-1-1 §8.1.4")
