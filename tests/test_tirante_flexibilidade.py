"""Issue 24 — Tirante: aço f_y=315 MPa e hipótese de apoio rígido / flexibilidade.

Cobre:
  · grau de aço MR315 (f_y=315 MPa) disponível e adotável;
  · registro da hipótese de apoio horizontal indeslocável (Castigliano);
  · avaliação do impacto da flexibilidade do tirante sobre H.
"""

import math

import pytest

from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.checks.elu.tirante_base import (
    ACO,
    verificar_tirante_base,
    impacto_flexibilidade_tirante,
)


GEO = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)


def test_aco_mr315_disponivel():
    assert "MR315" in ACO
    assert ACO["MR315"]["f_y"] == 315.0


def test_tirante_usa_fy315():
    r = verificar_tirante_base(T_d_kN=1097.6, L_m=GEO.L, aco="MR315",
                               d_mm=None, eta_alvo=0.75)
    assert r["f_y_MPa"] == 315.0
    assert r["aco"] == "MR315"
    # N_t,Rd = A·f_y/γ_M0
    A = math.pi * r["d_mm"] ** 2 / 4.0
    assert r["N_t_Rd_kN"] == pytest.approx(A * 315.0 / 1.0 / 1e3, rel=1e-3)
    assert r["ok"]


def test_hipotese_apoio_rigido_registrada():
    r = verificar_tirante_base(T_d_kN=1097.6, L_m=GEO.L, aco="MR315")
    assert "hipotese_H" in r
    assert "INDESLOCÁVEL" in r["hipotese_H"]
    assert "flexibilidade" in r["hipotese_H"].lower()


def test_aco_invalido_levanta():
    with pytest.raises(ValueError):
        verificar_tirante_base(T_d_kN=100.0, L_m=10.0, aco="S500")


# ── Impacto da flexibilidade ─────────────────────────────────────────────────

def test_impacto_rigidezes_e_2molas():
    mat = GlulamMaterial("GL24h", 3, "longa")
    imp = impacto_flexibilidade_tirante(
        GEO, E_glulam_MPa=mat.E0_mean / 1e6, H_rigid_kN=1097.6,
        d_mm=80.0, aco="MR315",
    )
    # arco muito mais rígido que o tirante (shallow arch)
    assert imp["k_arco_kNmm"] > imp["k_tirante_kNmm"]
    # limite de 2 molas: H_flex = H/(1+f_t/f_p) < H
    assert imp["H_flex_2molas_kN"] < imp["H_rigid_kN"]
    r = imp["razao_ft_fp"]
    assert imp["H_flex_2molas_kN"] == pytest.approx(1097.6 / (1 + r), rel=1e-3)
    # δ do tirante = T·L/EA
    A = math.pi * (0.08) ** 2 / 4
    d_expect = 1097.6e3 * GEO.L / (210e9 * A) * 1e3   # mm
    assert imp["delta_tirante_mm"] == pytest.approx(d_expect, rel=1e-2)


def test_impacto_conclui_conservador_para_tirante():
    mat = GlulamMaterial("GL24h", 3, "longa")
    imp = impacto_flexibilidade_tirante(
        GEO, E_glulam_MPa=mat.E0_mean / 1e6, H_rigid_kN=1097.6,
        d_mm=80.0, aco="MR315",
    )
    # H_rígido é o máximo → conservador para o tirante; não acoplar
    assert imp["acoplar_para_tirante"] is False
    assert "conservador" in imp["conclusao"].lower()


def test_tirante_maior_reduz_razao_ft_fp():
    """Tirante mais grosso (maior A) → menos flexível → razão f_t/f_p menor."""
    mat = GlulamMaterial("GL24h", 3, "longa")
    E = mat.E0_mean / 1e6
    imp80 = impacto_flexibilidade_tirante(GEO, E, 1097.6, d_mm=80.0)
    imp120 = impacto_flexibilidade_tirante(GEO, E, 1097.6, d_mm=120.0)
    assert imp120["razao_ft_fp"] < imp80["razao_ft_fp"]
    assert imp120["H_flex_2molas_kN"] > imp80["H_flex_2molas_kN"]
