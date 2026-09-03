"""Issue 26 — Situação transitória de içamento da viga (EN 1991-1-6 + EC5).

Içamento em 2 pontos a 0,207·L: momento negativo nos pontos + positivo no vão,
cortante, compressão das lingas inclinadas e flambagem lateral (LTB) sem
contraventamento.
"""

import math

import pytest

from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.checks.elu.icamento import verificar_icamento, G_GRAV


GEO = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
MAT = GlulamMaterial("GL24h", 3, "curta")


def test_peso_e_reacoes_simetricas():
    """W = γ_G·φ_dyn·∫γ_gl·A dx; reações simétricas W/2."""
    r = verificar_icamento(GEO, MAT, gamma_G=1.35, phi_dyn=1.10)
    assert r["R_ponto_kN"] == pytest.approx(r["W_total_kN"] / 2.0, rel=1e-6)
    # peso próprio característico ~ γ_gl·A_médio·L; W_d = 1.35·1.1·W_k
    gamma_gl = MAT.rho_mean * G_GRAV / 1e3
    assert gamma_gl == pytest.approx(r["gamma_glulam_kNm3"], rel=1e-3)
    assert r["W_total_kN"] > 0


def test_momentos_sinais_opostos():
    """Içamento a 0,207L gera M⁻ (hogging) e M⁺ (sagging) de sinais opostos."""
    r = verificar_icamento(GEO, MAT)
    assert r["M_neg_kNm"] < 0        # hogging nos pontos de içamento
    assert r["M_pos_kNm"] > 0        # sagging no vão central


def test_pontos_a_0207L():
    r = verificar_icamento(GEO, MAT, a_rel=0.207)
    assert r["x1_m"] == pytest.approx(0.207 * GEO.L, abs=1e-2)
    assert r["x2_m"] == pytest.approx((1 - 0.207) * GEO.L, abs=1e-2)


def test_duracao_instantanea():
    """A montagem usa k_mod instantânea (0,90 em CS3)."""
    r = verificar_icamento(GEO, MAT)
    assert r["duracao"] == "instantanea"
    assert r["k_mod"] == pytest.approx(0.90, abs=1e-9)


def test_lingas_inclinadas_geram_compressao():
    """Lingas a ψ>0 → N_c = R·tan(ψ); balancim → N_c = 0."""
    r_incl = verificar_icamento(GEO, MAT, psi_sling_deg=30.0, spreader=False)
    r_spr = verificar_icamento(GEO, MAT, spreader=True)
    assert r_incl["N_c_kN"] == pytest.approx(
        r_incl["R_ponto_kN"] * math.tan(math.radians(30.0)), rel=1e-3)
    assert r_spr["N_c_kN"] == 0.0


def test_ltb_reduz_capacidade():
    """LTB sem contraventamento: k_crit<1 (l_ef longo = vão entre pontos)."""
    r = verificar_icamento(GEO, MAT)
    assert r["l_ef_LTB_m"] == pytest.approx((1 - 2 * 0.207) * GEO.L, abs=1e-2)
    assert r["k_crit"] <= 1.0
    assert r["eta_LTB"] >= 0.0


def test_phi_dyn_escala_esforcos():
    """φ_dyn maior → maior W e maiores momentos (proporcional)."""
    r1 = verificar_icamento(GEO, MAT, phi_dyn=1.0)
    r2 = verificar_icamento(GEO, MAT, phi_dyn=1.2)
    assert r2["W_total_kN"] / r1["W_total_kN"] == pytest.approx(1.2, rel=1e-3)
    assert r2["M_pos_kNm"] / r1["M_pos_kNm"] == pytest.approx(1.2, rel=1e-2)


def test_governante_e_ok():
    r = verificar_icamento(GEO, MAT)
    assert r["eta_gov_key"] in ("flexao", "cisalhamento", "LTB_6.35")
    assert r["eta"] == max(r["etas"].values())
    assert r["ok"] == (r["eta"] <= 1.0)
    assert r["norma"].startswith("EN 1991-1-6")
