"""Testes da robustez do tirante ao nível do piso (issue 37).

Cobre impacto de veículo (EN 1991-1-7), corrosão (EN 335/EN ISO 12944),
incêndio (EN 1993-1-2) e tropeço, e o orquestrador.
"""
import pytest

from mlc_projeto.checks.elu.tirante_base import _n_t_rd_kN
from mlc_projeto.checks.elu.tirante_piso_robustez import (
    robustez_impacto_tirante,
    robustez_corrosao,
    requisito_fogo,
    requisito_tropeco,
    verificar_robustez_tirante_piso,
)

# Tirante de referência do projeto: ∅48 MR315, T_d = H_arco = 378 kN, L = 20,25 m
D_MM, ACO, T_D, L_M = 48.0, "MR315", 378.0, 20.25


# ── Impacto ──────────────────────────────────────────────────────────────────

def test_impacto_barra_nua_falha():
    """Barra esbelta em vão grande não resiste ao choque transversal (η ≫ 1)."""
    r = robustez_impacto_tirante(d_mm=D_MM, aco=ACO, L_livre_m=L_M, protecao="nenhuma")
    assert r["eta_barra_nua"] > 1.0
    assert r["eta"] == pytest.approx(r["eta_barra_nua"], abs=1e-2)  # sem proteção: η = barra nua
    assert not r["ok"]
    assert not r["intercepta"]
    # M_Ed = F·L/4 ; M_pl,Rd = f_y·d³/6
    assert r["M_Ed_kNm"] == pytest.approx(50.0 * L_M / 4.0, rel=1e-3)
    assert r["M_pl_Rd_kNm"] == pytest.approx(315.0 * D_MM**3 / 6.0 / 1e6, rel=1e-3)
    assert r["F_gov_kN"] == 50.0  # F_dx governa


def test_impacto_embutido_interceptado():
    r = robustez_impacto_tirante(d_mm=D_MM, aco=ACO, L_livre_m=L_M, protecao="embutido")
    assert r["intercepta"] is True
    assert r["eta"] == 0.0
    assert r["ok"]
    # a barra nua continua registrada como justificativa da proteção
    assert r["eta_barra_nua"] > 1.0
    assert "canaleta" in r["requisito"].lower() or "duto" in r["requisito"].lower()


def test_impacto_guarda_rodas_interceptado():
    r = robustez_impacto_tirante(d_mm=D_MM, aco=ACO, L_livre_m=L_M, protecao="guarda_rodas")
    assert r["intercepta"] is True
    assert r["eta"] == 0.0 and r["ok"]


def test_impacto_protecao_invalida():
    with pytest.raises(ValueError):
        robustez_impacto_tirante(d_mm=D_MM, aco=ACO, L_livre_m=L_M, protecao="foo")


def test_impacto_vao_menor_reduz_demanda():
    r_full = robustez_impacto_tirante(d_mm=D_MM, aco=ACO, L_livre_m=L_M, protecao="nenhuma")
    r_half = robustez_impacto_tirante(d_mm=D_MM, aco=ACO, L_livre_m=L_M / 2, protecao="nenhuma")
    assert r_half["eta"] < r_full["eta"]


# ── Corrosão ─────────────────────────────────────────────────────────────────

def test_corrosao_reduz_secao_e_sobe_eta():
    r = robustez_corrosao(d_mm=D_MM, aco=ACO, T_d_kN=T_D, delta_corr_mm=1.0)
    assert r["d_ef_mm"] == pytest.approx(46.0)
    # η com seção corroída > η nominal (378/570 = 0,663)
    eta_nom = T_D / _n_t_rd_kN(D_MM, ACO)
    assert r["eta"] > eta_nom
    assert r["N_t_Rd_ef_kN"] < r["N_t_Rd_0_kN"]
    assert 0.0 < r["perda_pct"] < 20.0
    assert r["ok"]  # ainda < 1,0


def test_corrosao_default_sob_alvo():
    """Com Δr=1,0 mm a tração fica sob a norma (η<1) — e é o valor que governa."""
    r = robustez_corrosao(d_mm=D_MM, aco=ACO, T_d_kN=T_D)
    assert r["eta"] == pytest.approx(378.0 / _n_t_rd_kN(46.0, ACO), rel=1e-3)
    assert r["eta"] < 1.0


def test_corrosao_monotonica_com_delta():
    r0 = robustez_corrosao(d_mm=D_MM, aco=ACO, T_d_kN=T_D, delta_corr_mm=0.5)
    r1 = robustez_corrosao(d_mm=D_MM, aco=ACO, T_d_kN=T_D, delta_corr_mm=2.0)
    assert r1["eta"] > r0["eta"]
    assert r1["d_ef_mm"] < r0["d_ef_mm"]


# ── Incêndio ─────────────────────────────────────────────────────────────────

def test_fogo_embutido_ok():
    r = requisito_fogo(protecao="embutido", primario=True)
    assert r["ok"]  # cobrimento da canaleta = proteção passiva


def test_fogo_nu_primario_falha():
    r = requisito_fogo(protecao="nenhuma", primario=True)
    assert not r["ok"]
    assert "R30" in r["requisito"] or "R60" in r["requisito"]


def test_fogo_nu_nao_primario_ok():
    r = requisito_fogo(protecao="nenhuma", primario=False)
    assert r["ok"]  # só uplift → perda em incêndio não compromete gravidade


# ── Tropeço ──────────────────────────────────────────────────────────────────

def test_tropeco_embutido_ok():
    assert requisito_tropeco(protecao="embutido")["ok"]


def test_tropeco_exposto_falha():
    r = requisito_tropeco(protecao="nenhuma", z_tir_m=0.08)
    assert not r["ok"]


# ── Orquestrador ─────────────────────────────────────────────────────────────

def test_orquestrador_embutido_governa_corrosao():
    res = verificar_robustez_tirante_piso(
        d_mm=D_MM, aco=ACO, T_d_kN=T_D, L_m=L_M,
        protecao="embutido", primario=True,
    )
    assert res["ativo"] and res["ok"]
    assert res["eta_governa"] == "corrosao"       # impacto interceptado → 0
    assert res["eta"] == pytest.approx(res["corrosao"]["eta"])
    assert res["eta"] < 1.0
    assert len(res["requisitos"]) == 4
    assert res["impacto"]["eta"] == 0.0
    assert res["primario"] is True


def test_orquestrador_sem_protecao_falha():
    res = verificar_robustez_tirante_piso(
        d_mm=D_MM, aco=ACO, T_d_kN=T_D, L_m=L_M,
        protecao="nenhuma", primario=True,
    )
    assert not res["ok"]                            # impacto barra nua + fogo + tropeço
    assert res["eta_governa"] == "impacto"
    assert res["eta"] > 1.0


def test_orquestrador_L_livre_default_e_vao():
    """L_livre default = L_m (conservador)."""
    res = verificar_robustez_tirante_piso(
        d_mm=D_MM, aco=ACO, T_d_kN=T_D, L_m=L_M, protecao="nenhuma",
    )
    assert res["impacto"]["L_livre_m"] == pytest.approx(L_M)
