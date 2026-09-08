"""
Testes de regressão — F-02 (auditoria adversarial v2).

Achado
------
O `α_cr` comparado com o limiar 10 era a carga de Euler de UMA BARRA
(L_ef = L/2, seção h0) dividida pelo axial da VIGA — axial que o modelo
adotado (Opção B, H = 0) força a ~zero. Quanto menos empuxo o modelo admite,
maior era o "α_cr": a métrica era monotonicamente favorecida pela hipótese que
deveria testar. O modo sway era declarado por dois booleanos
(`alpha_cr_sway = inf if non_sway else 0`) e `alpha_cr_membro` devolvia 1e99
("infinitamente estável") quando N_Ed = 0.

α_cr de SISTEMA — EN 1993-1-1 §5.2.1(4)B, Eq. (5.2):

    α_cr = (H_Ed / V_Ed) · (h / δ_H,Ed)   e, para um sistema linear de rigidez
    lateral K (δ = H/K),                    α_cr = K · h / V_Ed

Reconstruído na auditoria a partir da rigidez real das cruzes:
    longitudinal (4 × Ø45): α_cr ≈ 116   → 1.ª ordem dispensada
    transversal  (2 × Ø16): α_cr ≈ 7,3   → ABAIXO de 10, exige amplificação

EN 1993-1-1 §5.2.2(5)B permite o método da amplificação de sway para
α_cr ≥ 3,0; abaixo disso é obrigatória análise rigorosa de 2.ª ordem.
"""
import math

import pytest

from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.wind import ParametrosVento
from mlc_projeto.core.loads import carregamentos_com_vento
from mlc_projeto.checks.elu.estabilidade_global import (
    ALPHA_CR_AMPLIF_MIN,
    ALPHA_CR_MIN,
    alpha_cr_membro,
    alpha_cr_sistema,
    verificar_estabilidade_global,
)
from mlc_projeto.checks.elu.contraventamento_transversal import (
    verificar_contraventamento_transversal,
)


def _setup():
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
    mat = GlulamMaterial("GL24h", 3, "curta")
    pv = ParametrosVento(
        V0=45.0, S1=1.0, categoria="IV", classe="B", S3=1.0,
        L=20.25, H1=geo.h_ap - geo.h0, h=7.0, dist_portico=5.75,
        l2=40.5, n_tramos=2, obstrucoes_sob_cobertura=True,
    )
    load = carregamentos_com_vento(
        geo, mat, 0.82, 0.40, 5.75, pv,
        b_pilar=0.32, h_pilar=0.27, n_pilares_linha=9, n_linhas_portico=3,
        L_cob_m=46.0, B_cob_m=40.5, empuxo_desenvolve=False,
    )
    return geo, mat, load, pv


# ── α_cr de sistema — Eq. (5.2) ───────────────────────────────────────────────

def test_alpha_cr_sistema_e_K_h_sobre_V():
    r = alpha_cr_sistema(K_lat_kNpm=3756.0, h_m=7.0, V_Ed_kN=3586.0)
    assert r["alpha_cr"] == pytest.approx(3756.0 * 7.0 / 3586.0, rel=1e-9)
    assert r["alpha_cr"] == pytest.approx(7.33, abs=0.02)


def test_alpha_cr_sistema_cresce_com_a_rigidez():
    a = alpha_cr_sistema(K_lat_kNpm=3756.0, h_m=7.0, V_Ed_kN=3586.0)["alpha_cr"]
    b = alpha_cr_sistema(K_lat_kNpm=59417.0, h_m=7.0, V_Ed_kN=3586.0)["alpha_cr"]
    assert b > a
    assert b == pytest.approx(116.0, abs=1.0)


def test_alpha_cr_sistema_classifica_os_tres_regimes():
    V, h = 3586.0, 7.0
    alto = alpha_cr_sistema(K_lat_kNpm=59417.0, h_m=h, V_Ed_kN=V)
    medio = alpha_cr_sistema(K_lat_kNpm=3756.0, h_m=h, V_Ed_kN=V)
    baixo = alpha_cr_sistema(K_lat_kNpm=1000.0, h_m=h, V_Ed_kN=V)
    assert alto["regime"] == "1a_ordem" and alto["k_II"] == pytest.approx(1.0, abs=0.02)
    assert medio["regime"] == "amplificar" and medio["k_II"] > 1.0
    assert baixo["regime"] == "2a_ordem_rigorosa"
    assert medio["alpha_cr"] < ALPHA_CR_MIN
    assert baixo["alpha_cr"] < ALPHA_CR_AMPLIF_MIN


def test_alpha_cr_sistema_sem_rigidez_e_mecanismo():
    """Rigidez lateral nula = mecanismo: α_cr = 0, nunca um valor de segurança."""
    r = alpha_cr_sistema(K_lat_kNpm=0.0, h_m=7.0, V_Ed_kN=3586.0)
    assert r["alpha_cr"] == 0.0
    assert r["regime"] == "mecanismo"
    assert math.isinf(r["k_II"])


# ── α_cr de barra deixa de devolver valor de segurança ────────────────────────

def test_alpha_cr_membro_nao_devolve_1e99():
    mat = GlulamMaterial("GL24h", 3, "curta")
    r = alpha_cr_membro(mat, b=0.32, h=1.00, L_ef_m=10.125, N_Ed_kN=0.0)
    assert r["indeterminado"] is True
    assert math.isinf(r["alpha_cr"])
    assert r["alpha_cr"] != 1e99


# ── A verificação global passa a exigir a rigidez declarada ───────────────────

def test_estabilidade_sem_rigidez_declarada_nao_dispensa_2a_ordem():
    geo, mat, load, pv = _setup()
    res = verificar_estabilidade_global(
        geo, mat, load, H_pilar_m=7.0, b_pilar=0.32, h_pilar=0.27,
        contravento_vertical_ok=True, contravento_transversal_ok=True,
        nocional_no_contraventamento=True,
    )
    assert res["alpha_cr_sistema"] is None
    assert res["ok"] is False
    assert res["metodo_analise"] == "alpha_cr_nao_determinado"


def test_estabilidade_usa_a_direcao_mais_flexivel():
    geo, mat, load, pv = _setup()
    res = verificar_estabilidade_global(
        geo, mat, load, H_pilar_m=7.0, b_pilar=0.32, h_pilar=0.27,
        contravento_vertical_ok=True, contravento_transversal_ok=True,
        nocional_no_contraventamento=True,
        K_lat_long_kNpm=59417.0, K_lat_transv_kNpm=3756.0,
        V_Ed_total_kN=3586.0,
    )
    assert res["alpha_cr_long"] == pytest.approx(116.0, abs=1.0)
    assert res["alpha_cr_transv"] == pytest.approx(7.33, abs=0.02)
    # o gate usa a direção mais flexível, não a média nem a mais rígida
    assert res["alpha_cr"] == pytest.approx(res["alpha_cr_transv"], rel=1e-9)
    assert res["direcao_critica"] == "transversal"
    assert res["ok_alpha_cr"] is False        # < 10 → não dispensa 1.ª ordem


def test_alpha_cr_baixo_exige_amplificacao_declarada():
    """3 ≤ α_cr < 10: só é aceitável se a amplificação k_II tiver sido aplicada."""
    geo, mat, load, pv = _setup()
    comum = dict(
        H_pilar_m=7.0, b_pilar=0.32, h_pilar=0.27,
        contravento_vertical_ok=True, contravento_transversal_ok=True,
        nocional_no_contraventamento=True,
        K_lat_long_kNpm=59417.0, K_lat_transv_kNpm=3756.0,
        V_Ed_total_kN=3586.0,
    )
    sem = verificar_estabilidade_global(geo, mat, load, **comum)
    com = verificar_estabilidade_global(
        geo, mat, load, amplificacao_aplicada=True, **comum
    )
    assert sem["ok"] is False
    assert sem["metodo_analise"] == "2a_ordem_requerida"
    assert com["ok"] is True
    assert com["metodo_analise"] == "1a_ordem_amplificada"
    assert com["k_II"] == pytest.approx(1.0 / (1.0 - 1.0 / 7.33), abs=0.01)


def test_alpha_cr_alto_dispensa_2a_ordem():
    geo, mat, load, pv = _setup()
    res = verificar_estabilidade_global(
        geo, mat, load, H_pilar_m=7.0, b_pilar=0.32, h_pilar=0.27,
        contravento_vertical_ok=True, contravento_transversal_ok=True,
        nocional_no_contraventamento=True,
        K_lat_long_kNpm=59417.0, K_lat_transv_kNpm=59417.0,
        V_Ed_total_kN=3586.0,
    )
    assert res["alpha_cr"] >= ALPHA_CR_MIN
    assert res["metodo_analise"] == "1a_ordem"
    assert res["ok"] is True


def test_mecanismo_continua_a_reprovar():
    geo, mat, load, pv = _setup()
    res = verificar_estabilidade_global(
        geo, mat, load, H_pilar_m=7.0, b_pilar=0.32, h_pilar=0.27,
        K_lat_long_kNpm=59417.0, K_lat_transv_kNpm=3756.0,
        V_Ed_total_kN=3586.0,
    )
    assert res["sistema_non_sway"] is False
    assert res["ok"] is False
    assert res["metodo_analise"] == "instavel_lateralmente"


# ── O contraventamento expõe a rigidez e amplifica a própria demanda ──────────

def test_contraventamento_transversal_expoe_rigidez_lateral():
    geo, mat, load, pv = _setup()
    res = verificar_contraventamento_transversal(
        geo=geo, load=load, params_vento=pv,
        H_pilar_m=7.0, dist_portico=5.75, L_comp=46.0, n_porticos=2,
        b_pilar=0.32, h_pilar=0.27, aco="S235",
    )
    assert res["C_h_kNpm"] > 0.0
    # 1 painel por frontão × 2 frontões
    assert res["K_lat_kNpm"] == pytest.approx(
        res["C_h_kNpm"] * res["n_paineis_gable"] * res["n_gables"], rel=1e-9
    )


def test_contraventamento_transversal_amplifica_quando_alpha_cr_baixo():
    """
    Com carga vertical suficientemente alta o α_cr desta direção cai abaixo de
    10 e a demanda passa a ser amplificada por k_II antes do dimensionamento.
    """
    geo, mat, load, pv = _setup()
    comum = dict(
        geo=geo, load=load, params_vento=pv,
        H_pilar_m=7.0, dist_portico=5.75, L_comp=46.0, n_porticos=2,
        b_pilar=0.32, h_pilar=0.27, aco="S235",
    )
    sem = verificar_contraventamento_transversal(**comum)
    com = verificar_contraventamento_transversal(V_Ed_total_kN=12000.0, **comum)

    assert sem["k_II"] == 1.0
    assert sem["regime_alpha_cr"] == "nao_determinado"
    assert com["alpha_cr"] < ALPHA_CR_MIN
    assert com["regime_alpha_cr"] == "amplificar"
    assert com["k_II"] > 1.0
    assert com["amplificacao_aplicada"] is True
    # a amplificação aumenta a demanda e, com ela, a diagonal
    assert com["H_tr_amplificado_kN"] > sem["H_tr_amplificado_kN"]
    assert com["V_painel_kN"] > sem["V_painel_kN"]
    assert com["d_mm"] >= sem["d_mm"]
    assert com["ok"] is True


def test_ponto_fixo_converge_e_e_autoconsistente():
    """k_II final tem de ser coerente com a rigidez da diagonal escolhida."""
    geo, mat, load, pv = _setup()
    r = verificar_contraventamento_transversal(
        geo=geo, load=load, params_vento=pv,
        H_pilar_m=7.0, dist_portico=5.75, L_comp=46.0, n_porticos=2,
        b_pilar=0.32, h_pilar=0.27, aco="S235", V_Ed_total_kN=12000.0,
    )
    acr = alpha_cr_sistema(r["K_lat_kNpm"], 7.0, 12000.0)
    assert r["alpha_cr"] == pytest.approx(acr["alpha_cr"], rel=1e-3)
    assert r["k_II"] == pytest.approx(acr["k_II"], rel=1e-3)


def test_alpha_cr_abaixo_de_3_nao_e_contraventamento_valido():
    """α_cr < 3: a amplificação de sway não é admissível (§5.2.2(5)B)."""
    geo, mat, load, pv = _setup()
    r = verificar_contraventamento_transversal(
        geo=geo, load=load, params_vento=pv,
        H_pilar_m=7.0, dist_portico=5.75, L_comp=46.0, n_porticos=2,
        b_pilar=0.32, h_pilar=0.27, aco="S235",
        d_mm=12.0, V_Ed_total_kN=60000.0,
    )
    assert r["alpha_cr"] < ALPHA_CR_AMPLIF_MIN
    assert r["regime_alpha_cr"] == "2a_ordem_rigorosa"
    assert r["ok"] is False
    assert r["lateral_estavel_transv"] is False


def test_correcao_de_F01_eleva_o_alpha_cr_transversal():
    """
    Acoplamento entre os dois achados: ao incluir a componente horizontal da
    cobertura (F-01) a demanda transversal sobe ~2,2×, a diagonal engrossa e o
    α_cr desta direção passa a ≥ 10 — o valor 7,33 medido na auditoria refletia
    uma diagonal dimensionada para uma ação incompleta.
    """
    geo, mat, load, pv = _setup()
    r = verificar_contraventamento_transversal(
        geo=geo, load=load, params_vento=pv,
        H_pilar_m=7.0, dist_portico=5.75, L_comp=46.0, n_porticos=2,
        b_pilar=0.32, h_pilar=0.27, aco="S235",
        V_Ed_total_kN=4.0 * 99.607 * 9,
    )
    assert r["alpha_cr"] >= ALPHA_CR_MIN
    assert r["regime_alpha_cr"] == "1a_ordem"
    assert r["k_II"] == 1.0
