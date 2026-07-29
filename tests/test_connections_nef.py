"""Testes de n_ef (EC5 §8.5.1.1) e margem de projeto L1/L3."""
import math
import pytest

from mlc_projeto.connections.connections import n_ef, dimensionar_ligacoes
from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.wind import ParametrosVento
from mlc_projeto.core.loads import carregamentos_com_vento


def test_n_ef_single_pin():
    """Um único pino: n_ef = 1 (sem redução de grupo)."""
    assert n_ef(1, a1_mm=180.0, d_mm=36.0) == pytest.approx(1.0)


def test_n_ef_full_spacing():
    """Com a1 = 13·d, o fator de espaçamento é 1 → n_ef = n^0,9 ≤ n."""
    n, d = 7, 36.0
    a1 = 13.0 * d
    expected = min(n ** 0.9, float(n))
    assert n_ef(n, a1, d) == pytest.approx(expected, rel=1e-9)
    assert n_ef(n, a1, d) < n  # n^0.9 < n para n > 1


def test_n_ef_minimum_spacing_reduces_more():
    """Espaçamento mínimo (≈5·d) reduz mais que a1 = 13·d."""
    n, d = 7, 36.0
    a1_min = 5.0 * d
    a1_full = 13.0 * d
    assert n_ef(n, a1_min, d) < n_ef(n, a1_full, d)


def test_n_ef_never_exceeds_n():
    """n_ef ≤ n mesmo com a1 muito grande."""
    assert n_ef(10, a1_mm=10_000.0, d_mm=20.0) <= 10.0


def test_n_ef_project_layout_L1():
    """Layout de projeto L1: 7 pinos/fileira, a1≈180 mm, d=36 → n_ef,row≈4,54."""
    nef = n_ef(7, a1_mm=179.9, d_mm=36.0)
    assert nef == pytest.approx(4.537, rel=1e-3)
    # Capacidade com n_ef (correto) < capacidade com n (não-conservador)
    assert nef < 7.0


def test_L1_L3_public_margin():
    """
    Uso público: η_alvo=0,75.
    L1 aplica n_ef por fileira; L3 aumenta n_chu face a η=1,0.
    """
    eta_alvo = 0.75
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.30)
    mat = GlulamMaterial(classe="GL24h", classe_servico=3, duracao="curta")
    pv = ParametrosVento(
        V0=45.0, S1=1.0, categoria="IV", classe="B", S3=1.0,
        L=20.25, H1=1.785, h=7.0, dist_portico=5.75,
    )
    load = carregamentos_com_vento(
        geo=geo, mat=mat, g_area=1.50, q_area=0.25,
        L_t=5.75, params_vento=pv,
    )
    res = dimensionar_ligacoes(
        mat, load, geo,
        d_base_mm=36, d_cum_mm=30, F_chu_kN=80.0, eta_alvo=eta_alvo,
    )
    L1, L3 = res["L1"], res["L3"]

    # Margem de projeto
    assert L1["eta"] <= eta_alvo + 1e-6
    assert L3["eta"] <= eta_alvo + 1e-6
    assert L1["ok"] and L3["ok"]

    # n_ef aplicado: R = n_linhas · n_ef,row · F_Rd  (não n · F_Rd)
    R_com_nef = L1["n_ef"] * L1["F_v_Rd_kN"]
    R_sem_nef = L1["n_pinos"] * L1["F_v_Rd_kN"]
    assert L1["R_total_kN"] == pytest.approx(R_com_nef, rel=1e-3)
    assert L1["R_total_kN"] < R_sem_nef  # redução de grupo ativa
    assert L1["n_ef_row"] < L1["n_linha"]
    assert L1["n_ef"] == pytest.approx(
        L1["n_linhas"] * L1["n_ef_row"], rel=1e-3
    )

    # L3: mais chumbadores do que o mínimo com η=1
    n_min_eta1 = math.ceil(L3["H_d_kN"] / L3["F_chu_kN"])
    assert L3["n_chumbadores"] >= n_min_eta1
    assert L3["n_chumbadores"] == math.ceil(
        L3["H_d_kN"] / (L3["F_chu_kN"] * eta_alvo)
    )
