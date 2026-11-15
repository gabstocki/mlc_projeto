"""Issue 113 — rigidez ao afastamento dos apoios dada pelo sistema espacial."""

import pytest

from mlc_projeto.checks.elu.empuxo_sistema import empuxo_no_sistema

BASE = dict(L_T=5.75, n_eixos=9, s=20.25 / 8, n_faixas=16, A_terca_m2=0.08,
            A_viga_m2=0.60, E_mlc_kPa=11.5e6, C_h_frontao_kNpm=7988.0,
            C_h_long_kNpm=7071.9)
KW = dict(n_eixos=9, n_faixas=16, H_rigido_kN=263.0, k_arco_kNm=208462.0,
          L_m=20.25, alpha_rad=0.1745, R_d_L1_kN=150.0)


def test_com_alma_o_diafragma_restringe_pouco_o_afastamento():
    r = empuxo_no_sistema(base_modelo=dict(BASE, d_diag_mm_por_baia=[36] + [12] * 6 + [36]), **KW)
    assert 0 < r["k_ap_min_kNpm"] < r["k_ap_max_kNpm"] < 0.05 * KW["k_arco_kNm"]
    assert 0 < r["H_dev_max_kN"] < 0.05 * KW["H_rigido_kN"]
    assert r["dM_cumeeira_kNm"] < 0                       # alivia a cumeeira


def test_sem_alma_o_afastamento_e_livre():
    r = empuxo_no_sistema(base_modelo=dict(BASE, d_diag_mm_por_baia=[36] + [None] * 6 + [36]), **KW)
    centrais = [x for x in r["porticos"] if 3 <= x["portico"] <= 7]
    assert all(x["H_dev_kN"] == pytest.approx(0.0, abs=1e-6) for x in centrais)
