"""
Achados C1–C5 e A2 — os caminhos onde um dado ausente ou errado virava número.

Todos partilham a mesma patologia do [F-04]: em vez de falhar, o código
produzia um valor plausível e o pipeline seguia até «APROVADO». Um clamp de
1e-18, um fallback de 5,0 mm, uma duração fixada à mão, um ângulo trocado —
nenhum deles dá erro, e é isso que os torna perigosos.
"""

import math

import pytest

from mlc_projeto.core.geometry   import GeometriaViga
from mlc_projeto.core.materials  import GlulamMaterial
from mlc_projeto.core.wind       import ParametrosVento
from mlc_projeto.core.loads      import analisar_biarticulada
from mlc_projeto.core.validacao  import DominioInvalidoError


# ── [C1 / F-09] o clamp 1e-18 em I(x) e A(x) ────────────────────────────────

@pytest.mark.parametrize("kw", [
    dict(h0=0.0),
    dict(h0=-1.0),
    dict(b=0.0),
    dict(b=-0.32),
    dict(L=0.0),
    dict(h_ap=0.0),
    dict(h0=float("nan")),
    dict(b=float("inf")),
])
def test_geometria_degenerada_falha_em_vez_de_ser_clampada(kw):
    """
    `np.maximum(I_x, 1e-18)` transformava uma seção inexistente em rigidez
    minúscula-mas-finita: o empuxo saía absurdo, e numérico, e ninguém dava
    por isso. A geometria valida-se à entrada.
    """
    base = dict(q=10.0, L=20.25, h0=1.0, h_ap=1.5, alpha_rad=0.1745, b=0.32,
                desenvolve_empuxo=False)
    base.update(kw)
    with pytest.raises((DominioInvalidoError, ValueError)):
        analisar_biarticulada(**base)


def test_geometria_valida_continua_a_correr():
    r = analisar_biarticulada(
        q=10.0, L=20.25, h0=1.0, h_ap=1.5, alpha_rad=0.1745, b=0.32,
        desenvolve_empuxo=False,
    )
    assert math.isfinite(r["M_max_kNm"]) and r["M_max_kNm"] > 0


def test_carga_nao_finita_e_recusada():
    with pytest.raises((DominioInvalidoError, ValueError)):
        analisar_biarticulada(
            q=float("nan"), L=20.25, h0=1.0, h_ap=1.5, alpha_rad=0.1745,
            b=0.32, desenvolve_empuxo=False,
        )


# ── [C2 / S-4] o fallback w_char = 5,0 mm ───────────────────────────────────

def test_estabilidade_nao_inventa_flecha_quando_o_ELS_falha(monkeypatch):
    """
    Havia `except Exception: w_char = 5.0`. Um número arbitrário entrava no
    critério de abaixamento do freche como se fosse resultado. Sem ELS, a
    estabilidade geométrica não é verificável — e não-verificável não é
    aprovado.
    """
    import mlc_projeto.checks.els.deflection_els as D
    from mlc_projeto.checks.elu.estabilidade_global import (
        verificar_estabilidade_global,
    )
    geo, mat, load = _modelo()

    def _explode(*a, **k):
        raise RuntimeError("ELS indisponível")

    monkeypatch.setattr(D, "verificar_ELS", _explode)
    with pytest.raises(RuntimeError):
        verificar_estabilidade_global(
            geo, mat, load, H_pilar_m=7.0, b_pilar=0.22, h_pilar=0.26,
            contravento_vertical_ok=True, contravento_transversal_ok=True,
        )


def test_estabilidade_recusa_flecha_nao_finita(monkeypatch):
    import mlc_projeto.checks.els.deflection_els as D
    from mlc_projeto.checks.elu.estabilidade_global import (
        verificar_estabilidade_global,
    )
    geo, mat, load = _modelo()
    monkeypatch.setattr(D, "verificar_ELS",
                        lambda *a, **k: {"w_S1_mm": float("nan")})
    with pytest.raises(DominioInvalidoError):
        verificar_estabilidade_global(
            geo, mat, load, H_pilar_m=7.0, b_pilar=0.22, h_pilar=0.26,
            contravento_vertical_ok=True, contravento_transversal_ok=True,
        )


# ── [C3 / F-10] a duração fixada nos aliases ────────────────────────────────

def test_aliases_herdam_a_duracao_da_combinacao_de_origem():
    """
    `ELU_C3`/`ELU_C4` são PONTEIROS para outra combinação. Fixavam
    `duracao="curta"` — oferecendo um k_mod (0,70) que a combinação apontada
    pode não ter (`ELU_Q` é «media», k_mod = 0,65).
    """
    _, _, load = _modelo()
    combs = load.combinacoes
    fisicas = load.combinacoes_ELU_fisicas()

    # C3 aponta para a sucção governante; C4 para o H máximo
    gov_s = min((c for c in fisicas.values() if c.nome.startswith("ELU_S_")),
                key=lambda c: c.q_tot)
    gov_h = max(fisicas.values(), key=lambda c: abs(c.H_kN))
    assert combs["ELU_C3"].duracao == gov_s.duracao
    assert combs["ELU_C4"].duracao == gov_h.duracao


# ── [C4 / F-08] domínio dos parâmetros de vento ─────────────────────────────

@pytest.mark.parametrize("kw", [
    dict(V0=-45.0), dict(V0=0.0), dict(V0=float("nan")),
    dict(S1=0.0), dict(S3=-1.0),
    dict(L=0.0), dict(h=-7.0), dict(dist_portico=0.0),
    dict(H1=-0.5), dict(l2=0.0), dict(n_tramos=0),
])
def test_parametros_de_vento_fora_de_dominio_sao_recusados(kw):
    base = dict(V0=45.0, S1=1.0, S3=1.0, categoria="IV", classe="B",
                L=20.25, H1=1.0, h=7.0, dist_portico=5.75)
    base.update(kw)
    with pytest.raises((DominioInvalidoError, ValueError)):
        ParametrosVento(**base)


def test_H1_nula_e_admissivel():
    """H1 = h_ap − h0 pode ser zero (cobertura plana); negativa é que não."""
    p = ParametrosVento(V0=45.0, S1=1.0, S3=1.0, categoria="IV", classe="B",
                        L=20.25, H1=0.0, h=7.0, dist_portico=5.75)
    assert p.H1 == 0.0


# ── [C5 / F-16] a propriedade G_05 derivada ─────────────────────────────────

def test_G_do_material_e_o_valor_tabelado_da_EN_14080():
    """
    `G_05 = E_0,05/16` não é uma propriedade do material: é a relação de que o
    EC5 se serve para deduzir a Eq. (6.32) da (6.31). Dava 600 MPa com nome de
    valor tabelado — 11 % acima dos 540 MPa da EN 14080 Tab. 5.
    """
    mat = GlulamMaterial("GL24h", 3, "curta")
    assert not hasattr(mat, "G_05")
    assert mat.G_g_05 == pytest.approx(540e6)
    # constante para todas as classes homogéneas (Tab. 5)
    for classe in ("GL20h", "GL24h", "GL28h", "GL32h"):
        assert GlulamMaterial(classe, 3, "curta").G_g_05 == pytest.approx(540e6)


def test_eq_6_32_nao_precisa_de_G_e_a_6_31_aceita_o_tabelado():
    from mlc_projeto.checks.elu.flambagem_lateral import calcular_sigma_m_crit
    mat = GlulamMaterial("GL24h", 3, "curta")
    simp = calcular_sigma_m_crit(mat.E0_05, b=0.32, h=1.39, l_ef=7.85)
    geral = calcular_sigma_m_crit(mat.E0_05, b=0.32, h=1.39, l_ef=7.85,
                                  G_05=mat.G_g_05)
    assert simp > 0 and geral > 0
    # a geral com o G tabelado (540 < 600 implícito) é MENOR — mais conservadora
    assert geral < simp


# ── [A2 / F-12] Hankinson no apoio ──────────────────────────────────────────

def test_apoio_nao_publica_mais_hankinson():
    """
    No apoio a reação é ⊥ às fibras (α = 90°): Hankinson degenera em f_c,90,d,
    que §6.1.5 já verifica. O que existia usava α = α_telhado sobre a área da
    seção inteira — não descrevia o apoio.
    """
    from mlc_projeto.checks.elu.apoio import verifica_apoio
    geo, mat, load = _modelo()
    r = verifica_apoio(geo, mat, load)
    assert r["hankinson_aplicavel"] is False
    assert "eta_ca" not in r
    assert r["eta"] == pytest.approx(r["eta_c90"])
    assert r["verif_gov"] == "perp."
    assert r["norma"] == "EC5 §6.1.5"
    # e o k_c,90 omitido está declarado, não esquecido
    assert r["k_c90_aplicado"] == 1.0
    assert "conservadora" in r["k_c90_nota"]


def test_rotulo_do_memorial_deixa_de_citar_6_2_2_no_apoio():
    from mlc_projeto.output.report import VERIFICACOES_EXPORT
    norma = next(n for c, _, n in VERIFICACOES_EXPORT if c == "apoio")
    assert "6.2.2" not in norma
    assert "6.1.5" in norma


# ── modelo comum ────────────────────────────────────────────────────────────

def _modelo():
    from mlc_projeto.core.loads import carregamentos_com_vento
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32, n_pts=1001)
    mat = GlulamMaterial("GL24h", 3, "curta")
    vento = ParametrosVento(
        V0=45.0, S1=1.0, S3=1.0, categoria="IV", classe="B",
        L=geo.L, H1=geo.h_ap - geo.h0, h=7.0, dist_portico=5.75,
    )
    load = carregamentos_com_vento(
        geo=geo, mat=mat, g_area=0.80, q_area=0.40, L_t=5.75,
        params_vento=vento, empuxo_desenvolve=False,
    )
    return geo, mat, load


# ── [A6] as majorações que o EC5 permite e o projeto não usa ────────────────

def test_omissoes_conservadoras_estao_declaradas_com_a_clausula():
    """
    Omitir k_h, k_sys, k_c,90 é conservador — e por isso passa despercebido
    numa auditoria de segurança. Sem declaração, o leitor não sabe se foram
    descartados por decisão ou por esquecimento.
    """
    from mlc_projeto.core.normativo import OMISSOES_CONSERVADORAS
    assert {"k_h", "k_sys", "k_c_90"} <= set(OMISSOES_CONSERVADORAS)
    for chave, texto in OMISSOES_CONSERVADORAS.items():
        assert "§" in texto or "Fórmula" in texto, (
            f"{chave} não cita a cláusula que permite a majoração")
        assert "NÃO" in texto or "Adotado" in texto or "adotado" in texto
