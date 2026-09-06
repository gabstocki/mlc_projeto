"""AUD-006 — condição de apoio do springing: os dois graus de liberdade.

A auditoria classificou como "incompatibilidade fundamental" o facto de o
pipeline adotar `H = 0` (Opção B) e, ao mesmo tempo, declarar o topo dos pilares
travado pelo diafragma/frontões — o que legitima `l_ef = 1,0·H`.

A análise da Onda 3 concluiu que a alegação central é **improcedente**: trata-se
de dois graus de liberdade INDEPENDENTES.

  Modo 1 — translação lateral (sway): todos os topos deslocam-se juntos na
  direção transversal. É restringido pelo diafragma de cobertura → frontões
  contraventados → fundação. É este modo que justifica `l_ef = 1,0·H`.

  Modo 2 — afastamento simétrico dos springings: é o modo que gera H. O
  diafragma NÃO o restringe: um afastamento simétrico não produz força
  transversal líquida contra a qual ele possa reagir, e o único elemento
  transversal no plano da cobertura é a própria viga que se afasta. Restam o
  pilar birotulado (mecanismo, k=0) e o tirante (removido na Opção B).

As duas afirmações são, portanto, compatíveis. O que a auditoria acertou são
três resíduos, cobertos aqui:

  A) a abertura dos springings — contrapartida de H=0 — nunca era verificada;
  B) o pórtico de FRONTÃO é outra estrutura: a cruz liga os dois topos de pilar,
     logo ali o afastamento é restringido e parte do empuxo desenvolve-se;
  C) o critério de estabilidade `H_imp/H_Ed` é o teste errado com H_Ed=0 — a
     força nocional tem de ser verificada onde de facto vai, no contraventamento.
"""

from __future__ import annotations

import pytest

from mlc_projeto.checks.elu.empuxo_acoplado import (
    empuxo_no_frontao,
    rigidez_horizontal_arco,
    verificar_abertura_springings,
)
from mlc_projeto.checks.elu.estabilidade_global import verificar_estabilidade_global
from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.loads import carregamentos_com_vento
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.wind import ParametrosVento


def _modelo():
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32, n_pts=1001)
    mat = GlulamMaterial("GL24h", 3, "curta")
    pv = ParametrosVento(
        V0=45.0, S1=1.0, categoria="IV", classe="B", S3=1.0,
        L=20.25, H1=geo.h_ap - geo.h0, h=7.0, dist_portico=5.75,
        l2=40.5, n_tramos=2, obstrucoes_sob_cobertura=True,
    )
    load = carregamentos_com_vento(
        geo=geo, mat=mat, g_area=0.80, q_area=0.40, L_t=5.75,
        params_vento=pv, empuxo_desenvolve=False,
    )
    return geo, mat, load


# ── Modo 2: o pilar não consegue restringir o afastamento ────────────────────

def test_pilar_e_ordens_de_grandeza_mais_mole_que_o_arco():
    """Mesmo com base ENGASTADA — que o projeto não tem — H mal se desenvolve."""
    geo, mat, _ = _modelo()
    k_arco = rigidez_horizontal_arco(geo, E_Pa=mat.E0_mean)["k_arco_kNm"]

    b_p, h_p, H_col = 0.32, 0.27, 7.0
    I_y = b_p * h_p ** 3 / 12.0
    k_cantilever = 3.0 * mat.E0_mean * I_y / H_col ** 3 / 1e3   # kN/m

    assert k_cantilever < k_arco / 1000.0
    fracao = k_cantilever / (k_cantilever + k_arco)
    assert fracao < 0.001, "engaste na base não mobilizaria empuxo relevante"


# ── Resíduo A: abertura dos springings em ELS ────────────────────────────────

def test_abertura_dos_springings_e_verificada():
    geo, mat, load = _modelo()
    r = verificar_abertura_springings(
        geo, E_Pa=mat.E0_mean, H_rigido_kN=load.H_rigido_ELU(), k_apoio_kNpm=0.0,
    )
    assert r["delta_total_mm"] > 0.0
    assert r["eta"] == pytest.approx(r["delta_total_mm"] / r["lim_mm"], rel=1e-3)
    assert r["ok"] is True


def test_abertura_e_o_limite_livre_do_apoio():
    """k→0 dá a abertura máxima; k→∞ anula-a. Contrato dos dois limites."""
    geo, mat, load = _modelo()
    H = load.H_rigido_ELU()
    livre = verificar_abertura_springings(geo, E_Pa=mat.E0_mean, H_rigido_kN=H,
                                          k_apoio_kNpm=0.0)
    rigido = verificar_abertura_springings(geo, E_Pa=mat.E0_mean, H_rigido_kN=H,
                                           k_apoio_kNpm=1e12)
    assert livre["delta_total_mm"] > rigido["delta_total_mm"]
    assert rigido["delta_total_mm"] == pytest.approx(0.0, abs=1e-6)


# ── Resíduo B: o frontão atrai empuxo, os pórticos internos não ──────────────

def test_frontao_atrai_empuxo_pequeno_mas_nao_nulo():
    geo, mat, load = _modelo()
    r = empuxo_no_frontao(
        geo, E_Pa=mat.E0_mean, H_rigido_kN=load.H_rigido_ELU(),
        b_baia_m=geo.L, H_col_m=7.0, d_diag_mm=22.0,
    )
    assert 0.0 < r["H_dev_kN"] < 0.10 * r["H_rigido_kN"]
    assert r["k_cruz_kNpm"] < r["k_arco_kNpm"] / 10.0


def test_diagonal_mais_rigida_atrai_mais_empuxo():
    """Monotonicidade: k_cruz ↑ ⇒ H_dev ↑ (mesmo sentido das molas em série)."""
    geo, mat, load = _modelo()
    H = load.H_rigido_ELU()
    kw = dict(geo=geo, E_Pa=mat.E0_mean, H_rigido_kN=H, b_baia_m=geo.L, H_col_m=7.0)
    assert (empuxo_no_frontao(**kw, d_diag_mm=30.0)["H_dev_kN"]
            > empuxo_no_frontao(**kw, d_diag_mm=18.0)["H_dev_kN"])


# ── Resíduo C: a nocional verificada no caminho lateral ──────────────────────

def _estab(**kw):
    geo, mat, load = _modelo()
    return verificar_estabilidade_global(
        geo, mat, load, H_pilar_m=7.0, b_pilar=0.32, h_pilar=0.27,
        contravento_vertical_ok=True, contravento_transversal_ok=True, **kw,
    )


def test_sem_caminho_lateral_declarado_a_nocional_reprova():
    """Protege AUD-008: o default não pode aprovar H_Ed=0 com H_imp>0."""
    r = _estab()
    assert r["ok_nocional"] is False
    assert r["ok"] is False


def test_com_nocional_verificada_no_contraventamento_o_criterio_passa():
    """AUD-008 pedia a nocional como caso de carga no modelo lateral."""
    r = _estab(nocional_no_contraventamento=True)
    assert r["ok_nocional"] is True
    assert r["nocional_no_contraventamento"] is True
    assert "contraventamento" in r["criterio_nocional"]
    assert r["ok"] is True
