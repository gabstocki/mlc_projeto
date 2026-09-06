"""Testes — peso próprio g_k discriminado (issue 1)."""
import numpy as np
from scipy.integrate import trapezoid
import pytest

from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.loads import peso_proprio_gk, G_GRAVIDADE


def _geo_mat():
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
    mat = GlulamMaterial("GL24h", 3, "longa")
    return geo, mat


def test_parcelas_somam_o_total():
    geo, mat = _geo_mat()
    pp = peso_proprio_gk(geo, mat, L_t=5.75, b_terca=0.20, h_terca=0.58,
                         s_terca=2.53, g_telha_kNm2=0.10, g_instalacoes_kNm2=0.10)
    assert pp["g_cobertura_kNm2"] == pytest.approx(0.20, abs=1e-6)
    assert pp["g_k_viga_kNm2"] == pytest.approx(
        pp["g_mlc_kNm2"] + pp["g_tercas_kNm2"] + pp["g_cobertura_kNm2"], abs=1e-3)
    # a terça NÃO carrega o peso da viga MLC
    assert pp["g_k_terca_kNm2"] == pytest.approx(
        pp["g_tercas_kNm2"] + pp["g_cobertura_kNm2"], abs=1e-3)
    assert pp["g_k_terca_kNm2"] < pp["g_k_viga_kNm2"]


def test_g_mlc_confere_com_integracao_manual():
    """g_MLC = (∫A(x)dx·γ)/L_viga/L_t, com γ=ρ_mean·g (EN 14080)."""
    geo, mat = _geo_mat()
    L_t = 5.75
    gamma = mat.rho_mean * G_GRAVIDADE / 1000.0
    x = np.linspace(0, geo.L, 2001)
    V = float(trapezoid(geo.A(x), x))
    g_mlc_manual = (V * gamma / geo.L) / L_t
    pp = peso_proprio_gk(geo, mat, L_t=L_t, b_terca=0.20, h_terca=0.58,
                         s_terca=2.53, g_telha_kNm2=0.10, g_instalacoes_kNm2=0.10)
    assert pp["g_mlc_kNm2"] == pytest.approx(g_mlc_manual, rel=1e-3)
    # ordem de grandeza esperada (orientador ~0,43 kN/m²)
    assert 0.40 < pp["g_mlc_kNm2"] < 0.47


def test_g_tercas_formula():
    geo, mat = _geo_mat()
    gamma = mat.rho_mean * G_GRAVIDADE / 1000.0
    pp = peso_proprio_gk(geo, mat, L_t=5.75, b_terca=0.20, h_terca=0.58,
                         s_terca=2.53, g_telha_kNm2=0.10, g_instalacoes_kNm2=0.10)
    assert pp["g_tercas_kNm2"] == pytest.approx(gamma * 0.20 * 0.58 / 2.53, abs=1e-3)


def test_total_realista_metade_do_valor_antigo():
    """g_k realista (~0,8) é bem menor que o antigo lump 1,50 kN/m²."""
    geo, mat = _geo_mat()
    pp = peso_proprio_gk(geo, mat, L_t=5.75, b_terca=0.20, h_terca=0.58,
                         s_terca=2.53, g_telha_kNm2=0.10, g_instalacoes_kNm2=0.10)
    assert 0.70 < pp["g_k_viga_kNm2"] < 0.90
    assert pp["g_k_viga_kNm2"] < 0.6 * 1.50


def test_gamma_de_EN14080_rho_mean():
    geo, mat = _geo_mat()
    pp = peso_proprio_gk(geo, mat, L_t=5.75, b_terca=0.20, h_terca=0.58,
                         s_terca=2.53, g_telha_kNm2=0.10, g_instalacoes_kNm2=0.10)
    assert pp["rho_mean_kgm3"] == mat.rho_mean
    assert pp["gamma_kNm3"] == pytest.approx(mat.rho_mean * G_GRAVIDADE / 1000.0, rel=1e-6)


def test_entradas_invalidas():
    geo, mat = _geo_mat()
    with pytest.raises(ValueError):
        peso_proprio_gk(geo, mat, L_t=0.0, b_terca=0.20, h_terca=0.58,
                        s_terca=2.53, g_telha_kNm2=0.10, g_instalacoes_kNm2=0.10)
