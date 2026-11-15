"""Issue 73 — enrijecedores sob os balanços da sela da L1c."""

import pytest

from mlc_projeto.checks.elu.apoio import verifica_enrijecedores_sela


def _r(**kw):
    base = dict(sigma_contato_MPa=1.30, balanco_m=0.125, b_contato_m=0.291, t_sela_mm=16.0,
                f_c90_d_MPa=1.25)
    base.update(kw)
    return verifica_enrijecedores_sela(**base)


def test_enrijecedores_tornam_a_ponta_rigida():
    r = _r()
    assert r["flecha_ponta_com_mm"] < 0.05 * r["flecha_ponta_sem_mm"]
    assert r["ok"]


def test_chapa_vence_o_vao_entre_enrijecedores():
    r = _r()
    s = 291.0 / 2
    assert r["vao_chapa_mm"] == pytest.approx(s)
    assert r["t_req_chapa_mm"] == pytest.approx((6 * 1.30 * s ** 2 / 8 / 275) ** 0.5, rel=1e-3)


def test_binario_na_face_do_pilar():
    r = _r()
    M = r["F_enrij_kN"] * 125 / 2 / 1e3                     # kN·m por consolo
    C = 3 * M / (2 * 0.250 / 3)
    assert r["C_face_kN"] == pytest.approx(C, rel=1e-2)
    assert r["partes"]["face_do_pilar"] == pytest.approx(r["p_face_MPa"] / 1.25, rel=1e-2)


def test_enrijecedor_fino_reprova_borda_livre():
    assert _r(t_enrij_mm=8.0)["partes"]["enrijecedor_borda_livre"] > 1.0
