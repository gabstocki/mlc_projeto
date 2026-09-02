"""Issue 17 — Fixação telha→terça sob sucção (NBR 6123).

Verificação LOCAL do fixador (parafuso autoperfurante) ao arrancamento por
sucção: C_net = C_pe,local − C_pi; w_up,d = γ_Q·|C_net|·q − γ_G·g_telha;
F_fix,d = w_up,d·(s·e_fix); η = F_fix,d/R_fix,d.
"""

import pytest

from mlc_projeto.core.wind import ParametrosVento
from mlc_projeto.checks.elu.fixacao_telha import (
    verificar_fixacao_telha_succao,
    CPI_ABERTO,
    GAMMA_Q_VENTO,
    GAMMA_G_FAV,
    GAMMA_M_FIX,
)


PV = ParametrosVento(
    V0=45.0, S1=1.0, categoria="IV", classe="B", S3=1.0,
    L=20.25, H1=1.785, h=7.0, dist_portico=5.75,
)


def test_formula_uplift_zona_campo():
    """w_up,d e F_fix,d batem com a fórmula NBR 6123 recalculada à mão."""
    r = verificar_fixacao_telha_succao(
        PV, s_terca=2.53, g_telha_kNm2=0.10, e_fix_m=0.33, R_fix_k_kN=2.5,
    )
    q = PV.q
    C_net = -1.0 - CPI_ABERTO
    w_suc = GAMMA_Q_VENTO * abs(C_net) * q
    w_up = w_suc - GAMMA_G_FAV * 0.10
    F = w_up * (2.53 * 0.33)
    z = r["zonas"]["campo"]
    assert z["C_net"] == pytest.approx(C_net, rel=1e-9)
    assert z["w_up_d_kNm2"] == pytest.approx(w_up, rel=1e-3)
    assert z["F_fix_d_kN"] == pytest.approx(F, rel=1e-3)
    assert r["R_fix_d_kN"] == pytest.approx(2.5 / GAMMA_M_FIX, rel=1e-3)


def test_canto_governa_e_pior_que_campo():
    """Sucção local de canto (C_pe=−2,0) > borda > campo → canto governa η."""
    r = verificar_fixacao_telha_succao(PV, s_terca=2.53, e_fix_m=0.33)
    zc, zb, zf = (r["zonas"]["canto"], r["zonas"]["borda"], r["zonas"]["campo"])
    assert zc["eta"] > zb["eta"] > zf["eta"]
    assert r["zona_gov"] == "canto"
    assert r["eta"] == pytest.approx(zc["eta"], rel=1e-9)


def test_cpi_aberto_soma_ao_uplift():
    """C_pi>0 (galpão aberto) AUMENTA o uplift vs. um caso sem pressão interna."""
    r_ab = verificar_fixacao_telha_succao(PV, s_terca=2.53, e_fix_m=0.33, Cpi=0.8)
    r_0 = verificar_fixacao_telha_succao(PV, s_terca=2.53, e_fix_m=0.33, Cpi=0.0)
    assert r_ab["zonas"]["campo"]["w_up_d_kNm2"] > r_0["zonas"]["campo"]["w_up_d_kNm2"]


def test_uplift_escala_linear_com_e_fix():
    """F_fix,d ∝ e_fix (área tributária linear) → η escala com o espaçamento."""
    r1 = verificar_fixacao_telha_succao(PV, s_terca=2.53, e_fix_m=0.20)
    r2 = verificar_fixacao_telha_succao(PV, s_terca=2.53, e_fix_m=0.40)
    assert (r2["zonas"]["canto"]["eta"] / r1["zonas"]["canto"]["eta"]
            == pytest.approx(2.0, rel=1e-3))


def test_e_fix_requerido_zera_eta():
    """Reaplicar e_fix_req da zona canto dá η ≈ 1 nessa zona."""
    r = verificar_fixacao_telha_succao(PV, s_terca=2.53, e_fix_m=0.33)
    e_req = r["e_fix_req_canto_m"]
    r2 = verificar_fixacao_telha_succao(PV, s_terca=2.53, e_fix_m=e_req)
    assert r2["zonas"]["canto"]["eta"] == pytest.approx(1.0, abs=5e-3)


def test_e_fix_projeto_020_aprova_todas_zonas():
    """Fixação a cada nervura (0,20 m) satisfaz todas as zonas (η ≤ 1)."""
    r = verificar_fixacao_telha_succao(
        PV, s_terca=2.53, g_telha_kNm2=0.10, e_fix_m=0.20, R_fix_k_kN=2.5,
    )
    assert r["ok"]
    assert all(r["zonas"][k]["ok"] for k in ("campo", "borda", "canto"))
    assert r["eta"] <= 1.0


def test_peso_telha_alivia_uplift():
    """Maior g_telha reduz o uplift líquido (permanente favorável)."""
    r_leve = verificar_fixacao_telha_succao(PV, s_terca=2.53, e_fix_m=0.33, g_telha_kNm2=0.05)
    r_pesada = verificar_fixacao_telha_succao(PV, s_terca=2.53, e_fix_m=0.33, g_telha_kNm2=0.30)
    assert r_pesada["zonas"]["campo"]["w_up_d_kNm2"] < r_leve["zonas"]["campo"]["w_up_d_kNm2"]


def test_entradas_invalidas():
    with pytest.raises(ValueError):
        verificar_fixacao_telha_succao(PV, s_terca=0.0, e_fix_m=0.33)
    with pytest.raises(ValueError):
        verificar_fixacao_telha_succao(PV, s_terca=2.53, e_fix_m=-0.1)
