"""Testes — contraventamento transversal (issue 31, Opção 2)."""
import pytest

from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.wind import ParametrosVento
from mlc_projeto.core.loads import carregamentos_com_vento
from mlc_projeto.checks.elu.contraventamento_transversal import (
    demanda_transversal,
    verifica_diafragma,
    verificar_contraventamento_transversal,
)


def _setup():
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
    mat = GlulamMaterial("GL24h", 3, "curta")
    pv = ParametrosVento(
        V0=45.0, S1=1.0, categoria="IV", classe="B", S3=1.0,
        L=20.25, H1=geo.h_ap - geo.h0, h=7.0, dist_portico=5.75,
    )
    load = carregamentos_com_vento(
        geo, mat, 1.5, 0.25, 5.75, pv,
        n_pilares_linha=9, n_linhas_portico=3,
        L_cob_m=46.0, B_cob_m=2 * geo.L,
    )
    return geo, mat, load, pv


# ── Demanda transversal ───────────────────────────────────────────────────────

def test_demanda_inclui_vento_e_nocional():
    geo, mat, load, pv = _setup()
    dem = demanda_transversal(
        load, pv, H_pilar_m=7.0, b_pilar=0.32, h_pilar=0.27,
        n_frames=9, n_porticos=2,
    )
    assert dem["n_colunas"] == 9 * 3
    assert dem["H_vento_topo_kN"] > 0.0
    assert dem["H_imp_kN"] > 0.0
    # F-01: a componente horizontal da pressão na cobertura entra na demanda
    assert dem["H_cob_kN"] > 0.0
    # H_tr = arrasto no topo + componente da cobertura + nocional
    assert dem["H_tr_kN"] == pytest.approx(
        dem["H_vento_topo_kN"] + dem["H_cob_kN"] + dem["H_imp_kN"], abs=1e-2
    )


def test_demanda_topo_e_metade_do_arrasto():
    """Modelo biapoiado: metade do arrasto de cada pilar vai ao topo."""
    geo, mat, load, pv = _setup()
    dem = demanda_transversal(
        load, pv, H_pilar_m=7.0, b_pilar=0.32, h_pilar=0.27,
        n_frames=9, n_porticos=2,
    )
    esperado = dem["n_colunas"] * dem["F_col_d_kN"] / 2.0
    assert dem["H_vento_topo_kN"] == pytest.approx(esperado, abs=1e-2)


# ── Diafragma ─────────────────────────────────────────────────────────────────

def test_diafragma_reacao_e_corda():
    d = verifica_diafragma(H_tr_kN=60.0, L_comp_m=46.0, B_cob_m=40.5)
    assert d["R_gable_kN"] == pytest.approx(30.0, abs=1e-6)     # H_tr/2
    # M = H_tr·L/8 ; N_corda = M/B
    assert d["M_diaf_kNm"] == pytest.approx(60.0 * 46.0 / 8.0, rel=1e-6)
    assert d["N_corda_kN"] == pytest.approx(d["M_diaf_kNm"] / 40.5, abs=1e-2)
    # diafragma profundo (B_cob grande) → força de corda modesta (< reação)
    assert d["N_corda_kN"] < d["R_gable_kN"]


# ── Verificação completa ──────────────────────────────────────────────────────

def test_verificacao_completa_caminho_de_carga():
    geo, mat, load, pv = _setup()
    res = verificar_contraventamento_transversal(
        geo=geo, load=load, params_vento=pv,
        H_pilar_m=7.0, dist_portico=5.75, L_comp=46.0, n_porticos=2,
        b_pilar=0.32, h_pilar=0.27, aco="S235",
    )
    # demanda transversal de ordem esperada
    assert 40.0 < res["H_tr_kN"] < 120.0
    # reação por frontão = metade
    assert res["R_gable_kN"] == pytest.approx(res["H_tr_kN"] / 2.0, abs=1e-2)
    # diâmetro auto, dentro do alvo, aprovado
    assert res["d_auto"] is True
    assert res["ok"] is True
    assert res["eta_diag_N"] <= 0.90 + 1e-9
    assert res["lateral_estavel_transv"] is True
    # caminho de carga à fundação presente
    assert res["H_base_kN"] > 0.0
    assert res["N_uplift_kN"] > 0.0
    # valida l_ef=1H (non-sway) — nota de acoplamento com pilares
    assert "l_ef=1" in res["nota_pilar"]


def test_reprova_com_diagonal_fina():
    """Diâmetro insuficiente → η_N > 1 → reprovado (lateral_estavel_transv False)."""
    geo, mat, load, pv = _setup()
    res = verificar_contraventamento_transversal(
        geo=geo, load=load, params_vento=pv,
        H_pilar_m=7.0, dist_portico=5.75, L_comp=46.0, n_porticos=2,
        b_pilar=0.32, h_pilar=0.27, aco="S235", d_mm=12.0,
    )
    assert res["eta_diag_N"] > 1.0
    assert res["ok"] is False
    assert res["lateral_estavel_transv"] is False
