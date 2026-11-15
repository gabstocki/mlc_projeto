"""Issue 82 — beiral (viga em balanço no apoio externo) e oitão (terça em balanço)."""

import math

import pytest

from mlc_projeto.checks.elu.beiral import (
    _flecha_ponta_terca, flecha_ponta_viga, verificar_balanco_terca,
)
from mlc_projeto.checks.elu.flambagem_lateral import momento_biapoiada
from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.loads import analisar_biarticulada, componente_horizontal_cobertura
from mlc_projeto.core.materials import GlulamMaterial

ALPHA = 1e-5          # viga praticamente prismática, para comparar com fórmulas fechadas


def _r(q_esq, q_dir, a, L=10.0):
    return analisar_biarticulada(q=0.5 * (q_esq + q_dir), L=L, h0=0.5,
                                 h_ap=0.5 + L / 2 * math.tan(ALPHA),
                                 alpha_rad=ALPHA, b=0.2, q_esq=q_esq, q_dir=q_dir,
                                 desenvolve_empuxo=False, a_bal=a)


def test_sem_beiral_nada_muda():
    r0 = _r(5.0, 3.0, 0.0)
    assert r0["M_apoio_A_kNm"] == 0.0 and r0["R_A_vao_kN"] == r0["R_A_kN"]


@pytest.mark.parametrize("qe, qd", [(5.0, 5.0), (5.0, -2.0), (-3.0, 1.0)])
def test_equilibrio_com_balanco_no_apoio_externo(qe, qd):
    L, a = 10.0, 2.0
    r = _r(qe, qd, a, L)
    total = qe * (L / 2 + a) + qd * L / 2
    assert r["R_A_kN"] + r["R_B_kN"] == pytest.approx(total, abs=1e-6)
    # momentos em torno de B
    mom = qe * (L / 2 + a) * (L - (L / 2 - a) / 2) + qd * (L / 2) * (L / 4)
    assert r["R_A_kN"] * L == pytest.approx(mom, abs=1e-6)
    assert r["M_apoio_A_kNm"] == pytest.approx(-qe * a ** 2 / 2)
    assert r["M_apoio_B_kNm"] == 0.0


def test_momento_no_vao_superposto():
    q, L, a = 5.0, 10.0, 2.0
    r = _r(q, q, a, L)
    assert r["M_cumeeira_kNm"] == pytest.approx(q * L ** 2 / 8 - q * a ** 2 / 4, abs=1e-3)
    assert momento_biapoiada(L / 2, L, q, q, a) == pytest.approx(r["M_cumeeira_kNm"], abs=1e-3)


def test_flecha_da_ponta_confere_com_roark():
    geo = GeometriaViga(L=10.0, h0=0.5, alpha_deg=0.001, b=0.2, n_pts=2001, a_bal=2.0)
    mat = GlulamMaterial(classe="GL24h", classe_servico=3, duracao="longa")
    I = 0.2 * 0.5 ** 3 / 12
    w = flecha_ponta_viga(geo, mat, 5.0, 5.0, desenvolve_empuxo=False)
    assert w == pytest.approx(_flecha_ponta_terca(5e3, 10.0, 2.0, mat.E0_mean, I), rel=5e-3)


def test_componente_horizontal_com_beiral():
    t = math.tan(math.radians(10))
    assert componente_horizontal_cobertura(1.0, 0.0, 20.0, math.radians(10), a_bal=1.0) \
        == pytest.approx(11.0 * t)


def test_geometria_altura_na_ponta():
    geo = GeometriaViga(L=20.25, h0=1.0, alpha_deg=10.0, b=0.32, a_bal=1.135)
    assert geo.h_ponta == pytest.approx(1.0 - 1.135 * math.tan(math.radians(10)))
    with pytest.raises(Exception):
        GeometriaViga(L=20.25, h0=0.1, alpha_deg=10.0, b=0.32, a_bal=1.0)


def test_balanco_terca_passa_com_folga():
    mat = GlulamMaterial(classe="GL24h", classe_servico=3, duracao="curta")
    r = verificar_balanco_terca(mat, a_m=1.16, L_t=5.75, s=2.53, b=0.2, h=0.58,
                                alpha_deg=10.0, g_k_m2=0.39, q_k_m2=0.4, w_kNm2=0.7)
    assert r["ok"] and r["eta"] < 0.2
