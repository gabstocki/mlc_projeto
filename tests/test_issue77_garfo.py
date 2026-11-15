"""Issue 77 — apoio em garfo da terça e grandezas da Tab. 8.6."""

import pytest

from mlc_projeto.connections.terca_viga import verificar_garfo_terca
from mlc_projeto.core.materials import GlulamMaterial


def _g(**kw):
    mat = GlulamMaterial(classe="GL24h", classe_servico=3, duracao="curta")
    base = dict(mat=mat, w_suc_k_kNm2=1.2, g_k_terca_kNm2=0.33, s_terca_m=2.53, L_T_m=5.75,
                b_terca_m=0.20, h_terca_m=0.40, n_face=4, R_ax_d_kN=6.5, F_ax_kN=4.0)
    base.update(kw)
    return verificar_garfo_terca(**base)


def test_torcao_do_garfo_e_M_sobre_80():
    g = _g()
    M = max(g["M_d_succao_kNm"], g["M_d_gravidade_kNm"])
    assert g["M_tor_kNm"] == pytest.approx(M / 80.0, abs=1e-3)
    assert g["dF_parafuso_kN"] == pytest.approx(g["M_tor_kNm"] / (4 * 0.20 * 2 ** -0.5), rel=1e-2)


def test_terca_0_20x0_40_nao_flamba_sob_succao():
    g = _g()
    assert g["k_crit"] == 1.0 and g["lambda_rel_m"] < 0.75


def test_quadro_separa_a1_viga_e_a2_terca():
    from pathlib import Path
    t = (Path(__file__).resolve().parent.parent / "tese" / "tab_espacamentos.tex").read_text()
    assert "$a_2$ (passo vertical na face)" in t and "$a_1$ (passo vertical na face)" in t
