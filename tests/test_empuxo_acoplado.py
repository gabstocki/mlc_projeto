"""Testes da auditoria do empuxo acoplado (issue 38).

Reproduz, de forma testável, o achado da issue 35: com pilar biarticulado
(mecanismo lateral) o empuxo de gravidade NÃO se desenvolve → a viga tende a
biapoiada e o pilar não atrai o empuxo (refuta o 'colapso a ~1300 kN·m').
"""
import math
import pytest

from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.checks.elu.empuxo_acoplado import (
    rigidez_horizontal_arco,
    rigidez_lateral_pilar,
    empuxo_desenvolvido,
    analisar_empuxo_acoplado,
)

# Config do pipeline
GEO = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
E = 11.5e9            # Pa — GL24h E0,mean
H_RIG = 377.36        # kN — empuxo rígido (Castigliano) da gov. de gravidade
Q_GOV = 13.912        # kN/m
B_P, H_P, H_COL = 0.32, 0.27, 7.0


# ── Rigidezes ────────────────────────────────────────────────────────────────

def test_k_arco_muito_maior_que_pilar():
    arco = rigidez_horizontal_arco(GEO, E)
    eng = rigidez_lateral_pilar(B_P, H_P, H_COL, E, base="engastada")
    # arco raso é horizontalmente muito rígido (~200 kN/mm); pilar ~0,05 kN/mm
    assert arco["k_arco_kNmm"] > 100.0
    assert eng["k_kNm"] == pytest.approx(52.8, rel=0.02)
    assert arco["k_arco_kNm"] / eng["k_kNm"] > 1000.0


def test_pilar_rotulado_rigidez_nula():
    rot = rigidez_lateral_pilar(B_P, H_P, H_COL, E, base="rotulada")
    assert rot["k_kNm"] == 0.0


def test_pilar_engastado_cantilever():
    eng = rigidez_lateral_pilar(B_P, H_P, H_COL, E, base="engastada")
    I_col = B_P * H_P**3 / 12.0
    assert eng["k_kNm"] == pytest.approx(3 * E * I_col / H_COL**3 / 1e3, rel=1e-9)


def test_base_invalida():
    with pytest.raises(ValueError):
        rigidez_lateral_pilar(B_P, H_P, H_COL, E, base="xpto")


# ── Empuxo desenvolvido (2 molas) ────────────────────────────────────────────

def test_empuxo_desenvolvido_limites():
    assert empuxo_desenvolvido(377.0, 2e5, math.inf) == 377.0     # rígido
    assert empuxo_desenvolvido(377.0, 2e5, 0.0) == 0.0            # livre
    # monotônico crescente com k
    a = empuxo_desenvolvido(377.0, 2e5, 1e4)
    b = empuxo_desenvolvido(377.0, 2e5, 1e5)
    assert 0 < a < b < 377.0


def test_empuxo_desenvolvido_formula():
    H = empuxo_desenvolvido(377.36, 208462.0, 52.8)
    assert H == pytest.approx(377.36 * 52.8 / (52.8 + 208462.0), rel=1e-9)
    assert H < 0.2   # ≈ 0,1 kN


# ── Orquestrador ─────────────────────────────────────────────────────────────

def test_auditoria_empuxo_nao_desenvolve():
    res = analisar_empuxo_acoplado(
        GEO, E, H_rigido_kN=H_RIG, q_gov_kNpm=Q_GOV,
        b_pilar=B_P, h_pilar=H_P, H_pilar=H_COL,
    )
    # pilar rotulado → 0 exatamente
    assert res["H_dev_rotulada_kN"] == 0.0
    # limite generoso engastado → ainda ≈ 0 (< 1 kN)
    assert res["H_dev_engastada_kN"] < 1.0
    assert res["frac_desenvolvida"] < 0.01
    assert res["empuxo_desenvolve"] is False
    assert res["colapso_pilar_refutado"] is True


def test_auditoria_M_viga_sobe_para_biapoiada():
    res = analisar_empuxo_acoplado(
        GEO, E, H_rigido_kN=H_RIG, q_gov_kNpm=Q_GOV,
        b_pilar=B_P, h_pilar=H_P, H_pilar=H_COL,
    )
    # modelo (empuxo rígido) ~416; biapoiada ~713; +71%
    assert res["M_modelo_kNm"] == pytest.approx(416.0, rel=0.02)
    assert res["M0_biapoiada_kNm"] == pytest.approx(713.0, rel=0.02)
    assert res["delta_M_pct"] == pytest.approx(71.0, abs=3.0)
    assert res["M0_biapoiada_kNm"] > res["M_modelo_kNm"]


def test_auditoria_sweep_monotonico():
    res = analisar_empuxo_acoplado(
        GEO, E, H_rigido_kN=H_RIG, q_gov_kNpm=Q_GOV,
        b_pilar=B_P, h_pilar=H_P, H_pilar=H_COL,
    )
    sw = res["sweep"]
    assert sw[0]["k_support_kNm"] == "inf"
    assert sw[-1]["k_support_kNm"] == 0.0
    Hs = [s["H_dev_kN"] for s in sw]
    Ms = [s["M_viga_kNm"] for s in sw]
    # H_dev decresce e M_viga cresce à medida que k cai
    assert Hs == sorted(Hs, reverse=True)
    assert Ms == sorted(Ms)
    assert Hs[0] == pytest.approx(H_RIG, rel=1e-6)
    assert Hs[-1] == 0.0


def test_razao_k_grande():
    res = analisar_empuxo_acoplado(
        GEO, E, H_rigido_kN=H_RIG, q_gov_kNpm=Q_GOV,
        b_pilar=B_P, h_pilar=H_P, H_pilar=H_COL,
    )
    assert res["razao_k_arco_pilar"] > 1000
