"""Issue 109 — o vento longitudinal (característico) entra majorado por γ_Q nos
contraventamentos; a nocional H_imp não."""

import pytest

from mlc_projeto.checks.elu.contraventamento import verificar_contraventamento
from mlc_projeto.checks.elu.contraventamento_vertical import verificar_contraventamento_vertical
from mlc_projeto.connections.ancoragem import ETA_CONCRETO_FRAGIL, esmagamento_chaveta
from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.loads import GAMMA_Q, carregamentos_com_vento
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.wind import ParametrosVento


@pytest.fixture(scope="module")
def caso():
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
    mat = GlulamMaterial("GL24h", 3, "curta")
    pv = ParametrosVento(V0=45, S1=1, categoria="IV", classe="B", S3=1,
                         L=20.25, H1=geo.h_ap - geo.h0, h=7, dist_portico=5.75,
                         l2=40.5, n_tramos=2, obstrucoes_sob_cobertura=True)
    load = carregamentos_com_vento(geo, mat, 1.5, 0.40, 5.75, pv,
                                   L_cob_m=46.0, B_cob_m=2 * geo.L,
                                   empuxo_desenvolve=False)
    return geo, mat, load


def test_vertical_majora_vento_e_nao_a_nocional(caso):
    geo, mat, load = caso
    r = verificar_contraventamento_vertical(geo, load, n_paineis_long=4)
    F_k = load.vento_0["F_total_kN"]
    assert r["F_vento0_k_kN"] == pytest.approx(F_k, rel=1e-3)
    assert r["F_vento0_kN"] == pytest.approx(GAMMA_Q * F_k, rel=1e-3)
    assert r["V_lat_total_kN"] == pytest.approx(GAMMA_Q * F_k + r["H_imp_kN"], rel=1e-3)


def test_cobertura_majora_vento(caso):
    geo, mat, load = caso
    r = verificar_contraventamento(geo, mat, load, L_comp=46.0, n_modulos_cv=2,
                                   s_terca=2.53, d_barra_mm=36.0)
    assert r["F_vento0_kN"] == pytest.approx(GAMMA_Q * r["F_vento0_k_kN"], rel=1e-3)


def test_concreto_frágil_limitado_a_075():
    assert ETA_CONCRETO_FRAGIL == 0.75
    r = esmagamento_chaveta(V_Ed_kN=230.0, l_chaveta_mm=200.0, h_embutida_mm=80.0,
                            classe_concreto="C25/30")
    assert 0.75 < r["eta"] <= 1.0 and r["ok"] is False
