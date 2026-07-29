"""Testes — estabilidade global (P-Δ, nocionais, α_cr)."""
import pytest

from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.wind import ParametrosVento
from mlc_projeto.core.loads import carregamentos_com_vento
from mlc_projeto.checks.elu.estabilidade_global import (
    forca_nocional,
    alpha_cr_membro,
    amplificacao_segunda_ordem,
    verificar_estabilidade_global,
)


def test_forca_nocional_phi():
    r = forca_nocional(V_Ed_kN=400.0, h_m=7.0, m_colunas=2)
    assert 0.002 < r["phi"] < 0.01
    assert r["H_imp_kN"] == pytest.approx(r["phi"] * 400.0, rel=1e-3)
    assert r["H_imp_kN"] < 5.0  # << H típico do pórtico


def test_alpha_cr_arco_meia_agua():
    """Modo de arco L_ef=L/2: α_cr de sistema > α_cr de barra L_ef=L."""
    mat = GlulamMaterial("GL24h", 3, "curta")
    barra = alpha_cr_membro(mat, b=0.30, h=1.00, L_ef_m=20.25, N_Ed_kN=1600.0)
    arco = alpha_cr_membro(mat, b=0.30, h=1.00, L_ef_m=10.125, N_Ed_kN=1600.0)
    assert arco["alpha_cr"] > barra["alpha_cr"]
    assert arco["alpha_cr"] > 10.0


def test_k_II_proximo_de_um():
    assert amplificacao_segunda_ordem(100.0) == pytest.approx(1.0101, rel=1e-3)
    assert amplificacao_segunda_ordem(10.0) == pytest.approx(1.1111, rel=1e-3)


def test_estabilidade_global_R2_dispensa_2a_ordem():
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.30)
    mat = GlulamMaterial("GL24h", 3, "curta")
    pv = ParametrosVento(
        V0=45.0, S1=1.0, categoria="IV", classe="B", S3=1.0,
        L=20.25, H1=1.785, h=7.0, dist_portico=5.75,
    )
    load = carregamentos_com_vento(
        geo, mat, 1.5, 0.25, 5.75, pv,
        b_pilar=0.22, h_pilar=0.26,
    )
    res = verificar_estabilidade_global(
        geo, mat, load,
        H_pilar_m=7.0, b_pilar=0.22, h_pilar=0.26,
    )
    assert res["ok"] is True
    assert res["metodo_analise"] == "1a_ordem"
    assert res["sistema_non_sway"] is True
    assert res["alpha_cr"] >= 10.0          # modo arco
    assert res["H_imp_over_H"] < 0.01       # nocional << empuxo
    assert res["w_over_f"] < 0.05
    assert res["H_imp_kN"] < 5.0
    assert res["H_Ed_kN"] > 1000.0
    # barra pode ter α_cr < 10 — informativo, coberto por k_c
    assert "k_c" in res["nota_alpha_cr_barra"]
