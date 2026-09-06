"""Testes da Opção B (issue 35/38): o empuxo NÃO se desenvolve.

Viga biapoiada (H_efetivo=0, M=M0); o H_rígido (Castigliano) é preservado para a
auditoria. Cobre também o reforço ⊥ às fibras (fendilhamento) e o piso construtivo
de chumbadores da sapata sem tirante.
"""
import pytest

from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.wind import ParametrosVento
from mlc_projeto.core.loads import carregamentos_com_vento
from mlc_projeto.connections.connections import (
    arrancamento_parafuso_perp, dimensionar_reforco_fendilhamento,
    fendilhamento_ligacao, dimensionar_sapata,
)


def _loads():
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
    mat = GlulamMaterial("GL24h", 3, "curta")
    pv = ParametrosVento(V0=45, S1=1, categoria="IV", classe="B", S3=1,
                         L=20.25, H1=geo.h_ap - geo.h0, h=7, dist_portico=5.75,
                         # cobertura real: 2 tramos + veículos sob a cobertura (Onda 2)
                         l2=40.5, n_tramos=2, obstrucoes_sob_cobertura=True)
    kw = dict(geo=geo, mat=mat, g_area=0.82, q_area=0.40, L_t=5.75, params_vento=pv)
    load_A = carregamentos_com_vento(**kw, empuxo_desenvolve=True)
    load_B = carregamentos_com_vento(**kw, empuxo_desenvolve=False)
    return geo, mat, load_A, load_B


# ── Modelo: o empuxo não se desenvolve ────────────────────────────────────────

def test_empuxo_efetivo_zero_na_opcao_B():
    _, _, load_A, load_B = _loads()
    # Onda 2: limiar recalibrado ao carregamento normativo (~266 kN).
    assert load_A.H_ELU() > 200.0                 # apoio rígido: empuxo desenvolve
    assert load_B.H_ELU() == 0.0                  # Opção B: não desenvolve
    # o H rígido (Castigliano) é preservado para a auditoria
    assert load_B.H_rigido_ELU() == pytest.approx(load_A.H_ELU(), rel=1e-6)
    assert load_B.H_rigido_ELU() > 200.0


def test_M_maior_na_opcao_B():
    """Sem empuxo a viga é biapoiada → |M| sobe (M0 > M0−H·y_c)."""
    _, _, load_A, load_B = _loads()
    assert abs(load_B.M_max_ELU()) > abs(load_A.M_max_ELU())


def test_cortante_transversal_maior_na_opcao_B():
    """Sem o empuxo, V=R·cosθ (não há −H·senθ) → cortante do beiral maior."""
    _, _, load_A, load_B = _loads()
    assert load_B.V_viga_max_ELU() > load_A.V_viga_max_ELU()


def test_N_viga_menor_na_opcao_B():
    """Sem empuxo o normal do eixo cai (some a parcela H·cosθ)."""
    _, _, load_A, load_B = _loads()
    assert abs(load_B.N_max_ELU()) < abs(load_A.N_max_ELU())


# ── Reforço ao fendilhamento (EC5 §8.7.2) ─────────────────────────────────────

def test_arrancamento_parafuso_cresce_com_lef():
    a = arrancamento_parafuso_perp(10, 300, 385, 0.70)
    b = arrancamento_parafuso_perp(10, 500, 385, 0.70)
    assert b["F_ax_Rd_kN"] > a["F_ax_Rd_kN"] > 0
    assert a["k_d"] == 1.0  # d=10 ≥ 8


def test_arrancamento_dominio_diametro():
    with pytest.raises(ValueError):
        arrancamento_parafuso_perp(20, 400, 385, 0.70)   # d fora de [6,12]


def test_dimensionar_reforco_atinge_alvo():
    r = dimensionar_reforco_fendilhamento(141.0, rho_k=385, k_mod=0.70, eta_alvo=0.75)
    assert r["ok"]
    assert r["eta"] <= 0.75 + 1e-9
    assert r["n_parafusos"] >= 2
    # mais força → mais parafusos
    r2 = dimensionar_reforco_fendilhamento(280.0, rho_k=385, k_mod=0.70, eta_alvo=0.75)
    assert r2["n_parafusos"] > r["n_parafusos"]


def test_fendilhamento_reforcado_passa():
    """Com V_d alto (Opção B), o fendilhamento nu > 1 e o reforço traz η ≤ alvo."""
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
    mat = GlulamMaterial("GL24h", 3, "curta")
    res_lig = {"n_linhas": 3, "a2_mm": 216.0, "h_disp_mm": 1000.0,
               "V_d_kN": 141.0, "ligacao": "L1"}
    nu = fendilhamento_ligacao(res_lig, geo, mat, reforcar=False)
    assert nu["eta"] > 1.0 and not nu["reforcado"]
    rf = fendilhamento_ligacao(res_lig, geo, mat, reforcar=True, eta_reforco_alvo=0.75)
    assert rf["reforcado"] is True
    assert rf["eta"] <= 0.75 + 1e-9 and rf["ok"]
    assert rf["eta_fendilhamento_nu"] == pytest.approx(nu["eta"], rel=1e-6)


def test_fendilhamento_baixo_nao_reforca():
    """η nu abaixo do alvo → não reforça (Opção A / cortante baixo)."""
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
    mat = GlulamMaterial("GL24h", 3, "curta")
    res_lig = {"n_linhas": 3, "a2_mm": 216.0, "h_disp_mm": 1000.0,
               "V_d_kN": 40.0, "ligacao": "L1"}
    rf = fendilhamento_ligacao(res_lig, geo, mat, reforcar=True, eta_reforco_alvo=0.75)
    assert rf["reforcado"] is False


# ── Sapata sem tirante: piso construtivo de 4 chumbadores ─────────────────────

def test_sapata_sem_tirante_piso_4_chumbadores():
    """Opção B: H_arco≈0 na sapata; o nº de chumbadores não pode cair abaixo de 4
    (mín. construtivo p/ ancoragem ao uplift)."""
    geo, mat, load_A, load_B = _loads()
    r = dimensionar_sapata(load_B, geo, F_chu_kN=80.0, com_tirante=False,
                           b_pilar_m=0.32, h_pilar_m=0.27)
    assert r["H_d_kN"] == pytest.approx(0.0, abs=1e-6)   # sem empuxo
    assert r["n_chumbadores"] >= 4
