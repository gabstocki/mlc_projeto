"""Issue 21 — Componente metálico das ligações (EN 1993-1-8 + EN 1993-1-1).

Verifica o lado do AÇO: cisalhamento do pino, bearing/rasgamento no furo,
seção líquida da chapa em tração e solda chapa↔base.
"""

import math

import pytest

from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.wind import ParametrosVento
from mlc_projeto.core.loads import carregamentos_com_vento
from mlc_projeto.connections.connections import dimensionar_ligacao_base
from mlc_projeto.connections.chapas_aco import (
    verificar_chapas_aco,
    chapas_aco_ligacao,
    ACO_CHAPA,
    GAMMA_M2,
    ALPHA_V,
)


BASE = dict(
    F_res_kN=1000.0, N_ax_kN=1000.0, d_mm=24.0, n_pinos=48,
    n_linha=4, n_linhas=12, h_grupo_mm=800.0, h_disp_mm=1000.0, theta_deg=2.0,
    t_p_mm=16.0, a_solda_mm=6.0, aco="S275",
)


def test_cisalhamento_pino_formula():
    """F_v,Rd = n_planos·α_v·f_ub·A/γ_M2 (Tab. 3.4)."""
    r = verificar_chapas_aco(**BASE)
    A = math.pi * 24.0 ** 2 / 4
    F_v_1 = ALPHA_V * 400.0 * A / GAMMA_M2      # 1 plano, f_ub pino=400
    assert r["F_v_Rd_kN"] == pytest.approx(2 * F_v_1 / 1e3, rel=1e-3)


def test_bearing_limites_alpha_k1():
    """α_b ≤ 1 e ≤ f_ub/f_u; k1 ≤ 2,5 (EN 1993-1-8 Tab. 3.4)."""
    r = verificar_chapas_aco(**BASE)
    assert 0.0 < r["alpha_b"] <= 1.0
    assert r["alpha_b"] <= 400.0 / ACO_CHAPA["S275"]["f_u"] + 1e-9
    assert 0.0 < r["k1"] <= 2.5


def test_secao_liquida_menor_que_bruta():
    """N_u,Rd (líquida) usa A_net < A_gross; N_t,Rd = min(escoamento, ruptura)."""
    r = verificar_chapas_aco(**BASE)
    assert r["A_net_cm2"] < r["A_gross_cm2"]
    assert r["N_t_Rd_kN"] == min(r["N_pl_Rd_kN"], r["N_u_Rd_kN"])
    # A_net = t·(h_p − n_linhas·d0)
    A_net = 16.0 * (r["h_p_mm"] - 12 * 24.0) / 100.0
    assert r["A_net_cm2"] == pytest.approx(A_net, rel=1e-3)


def test_solda_fvw_e_eta():
    """f_vw,d = (f_u/√3)/(β_w·γ_M2); η_solda = (F_res/l)/(f_vw,d·a)."""
    r = verificar_chapas_aco(**BASE)
    f_u, b_w = ACO_CHAPA["S275"]["f_u"], ACO_CHAPA["S275"]["beta_w"]
    f_vw = (f_u / math.sqrt(3)) / (b_w * GAMMA_M2)
    assert r["f_vw_d_MPa"] == pytest.approx(f_vw, rel=1e-3)
    l_w = 2.0 * r["h_p_mm"]
    eta = (1000.0e3 / l_w) / (f_vw * 6.0)
    assert r["eta_solda"] == pytest.approx(eta, rel=1e-3)


def test_aco_mais_forte_reduz_eta():
    """S355 (f_u maior) → maior capacidade → η governante menor que S275."""
    r275 = verificar_chapas_aco(**{**BASE, "aco": "S275"})
    r355 = verificar_chapas_aco(**{**BASE, "aco": "S355"})
    assert r355["eta"] < r275["eta"]


def test_chapa_mais_grossa_reduz_bearing_e_net():
    """t_p maior → maior bearing e seção → menor η de furo e de chapa."""
    r16 = verificar_chapas_aco(**{**BASE, "t_p_mm": 16.0})
    r25 = verificar_chapas_aco(**{**BASE, "t_p_mm": 25.0})
    assert r25["eta_furo_bearing"] < r16["eta_furo_bearing"]
    assert r25["eta_chapa_liquida"] < r16["eta_chapa_liquida"]


def test_beta_Lf_reduz_forca_pino_em_fila_longa():
    """Fila longa (L_j>15d) aplica β_Lf<1 → F_1,Ed por pino sobe."""
    r_curta = verificar_chapas_aco(**{**BASE, "n_linha": 2})
    r_longa = verificar_chapas_aco(**{**BASE, "n_linha": 12})
    assert r_longa["beta_Lf"] < 1.0
    assert r_curta["beta_Lf"] == pytest.approx(1.0, abs=1e-9)


def test_aco_invalido_e_t_invalido():
    with pytest.raises(ValueError):
        verificar_chapas_aco(**{**BASE, "aco": "S500"})
    with pytest.raises(ValueError):
        verificar_chapas_aco(**{**BASE, "t_p_mm": 0.0})


def test_integracao_L1_real_aprova():
    """L1 real: todas as sub-verificações de aço passam (η<1) com S275/16mm."""
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
    mat = GlulamMaterial("GL24h", 3, "curta")
    pv = ParametrosVento(V0=45, S1=1, categoria="IV", classe="B", S3=1,
                         L=20.25, H1=geo.h_ap - geo.h0, h=7, dist_portico=5.75)
    load = carregamentos_com_vento(geo=geo, mat=mat, g_area=0.823, q_area=0.40,
                                   L_t=5.75, params_vento=pv)
    gov = load.combinacao_ELU_governante()
    L1 = dimensionar_ligacao_base(mat.com_duracao(gov.duracao), load, geo, d_mm=24)
    r = chapas_aco_ligacao(L1, geo, t_p_mm=16.0, a_solda_mm=6.0, aco="S275")
    assert r["ok"]
    for k in ("pino_cisalh", "furo_bearing", "chapa_liquida", "solda"):
        assert r["etas"][k] < 1.0
    assert r["F_res_kN"] == pytest.approx(L1["F_res_kN"], abs=0.01)
