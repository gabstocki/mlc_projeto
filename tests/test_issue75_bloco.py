"""Issue 75 — ruptura de bloco (EC5 Anexo A completo) no pé, topo, escoras e montante."""

import contextlib
import io
import math

import pytest

import mlc_projeto.main as M
from mlc_projeto.checks.elu.no_contraventamento import t_ef_bloco_mm
from mlc_projeto.connections.connections import (
    F_U_K_PINO, johansen_chapa_central, ruptura_de_bloco,
)


def test_comprimentos_liquidos_e_dois_lados():
    r = ruptura_de_bloco(n_par=4, n_perp=2, a1_m=0.10, a2_m=0.06, a3t_m=0.14, t1_m=0.15,
                         f_t0_k=19.2e6, f_v_k=3.5e6, k_mod=0.7, gamma_M=1.3, F_par_kN=100,
                         d_m=0.02, n_lados=2, t_ef_m=0.0479)
    assert r["L_net_t_mm"] == pytest.approx(40.0)                # (2−1)(60 − 20)
    assert r["L_net_v_mm"] == pytest.approx(2 * (3 * 80 + 130))   # 2[(n−1)(a1−d) + a3 − d/2]
    A_v = 740 / 2 * (40 + 2 * 47.9)                               # Eq. (A.3), 2.ª forma
    assert r["A_net_v_cm2"] == pytest.approx(A_v / 100, abs=0.1)
    assert r["term_tracao_kN"] == pytest.approx(2 * 1.5 * 40 * 150 * 19.2 / 1e3, abs=0.1)


def test_t_ef_pelo_modo_de_johansen():
    j = johansen_chapa_central(385, 20, 150, F_U_K_PINO, theta_deg=0.0)
    assert j["modo_gov"].startswith("modo_h")
    t = t_ef_bloco_mm(j, 20, 150)
    # EN 1995-1-1 Eq. (A.7), chapa grossa, modo (h)
    assert t == pytest.approx(2.0 * math.sqrt(j["M_y_Nmm"] / (j["f_hk_MPa"] * 20)))


def test_pipeline_bloco_dentro_do_alvo_e_L1_fora_do_catalogo():
    orig = M.gerar_relatorio
    M.gerar_relatorio = lambda *a, **k: {}
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            r = M._main_impl(rodar_varredura=False, abrir_viz=False)
    finally:
        M.gerar_relatorio = orig
    for k in ("base_L3", "base_L3c", "base_L3f", "base_L3a_canto", "base_L3a_central"):
        pe = r[k]["pe_pilar"]
        assert pe["eta_bloco"] <= 0.75 and pe["bloco"]["n_lados"] == 2
        assert (pe["n_vert"] - 1) * pe["a2_mm"] <= 133.4                # retração (81)
    assert "ruptura_bloco_L1" not in r
