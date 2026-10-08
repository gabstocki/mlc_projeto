"""
Testes de regressão — F-06 (auditoria adversarial v2).

Achado
------
`combinacao_ELU_governante()` devolve a combinação de maior |M_max| entre as de
sentido gravítico, e `main` derivava dela **um único material** `mat_elu` para
TODAS as verificações ELU. 13 dos 15 módulos liam só essa combinação — um
**envelope por procuração**.

O seletor não maximiza `M_cumeeira` (ápice), nem `R_v` (apoio/ligação), nem
`σ_m/W(x)` (LTB), nem sabe que o k_mod varia 7,7 % entre «media» e «curta» na
CS3. Na rota Tab. 25 mediu-se **−4,2 %** no §6.4.3 face ao envelope real.

Correção
--------
Cada verificação passa a varrer as combinações ELU FÍSICAS, cada uma com o SEU
k_mod, e a reportar a combinação que a governa. `misula.py` e `pilares.py` já o
faziam — o padrão é o mesmo.
"""
import math

import pytest

from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.wind import ParametrosVento
from mlc_projeto.core.loads import carregamentos_com_vento
from mlc_projeto.checks.elu.apoio import verifica_apoio
from mlc_projeto.checks.elu.cumeeira import verifica_cumeeira
from mlc_projeto.checks.elu.flambagem_lateral import verifica_flambagem_lateral
from mlc_projeto.checks.elu.flexao import verifica_flexao

ALIASES = ("ELU_C1", "ELU_C2", "ELU_C3", "ELU_C4")


def _load(tab25=False):
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
    mat = GlulamMaterial("GL24h", 3, "media")
    kw = (dict(l2=13.0, n_tramos=1, obstrucoes_sob_cobertura=False) if tab25
          else dict(l2=40.5, n_tramos=2, obstrucoes_sob_cobertura=True))
    pv = ParametrosVento(
        V0=45.0, S1=1.0, categoria="IV", classe="B", S3=1.0, L=20.25,
        H1=geo.h_ap - geo.h0, h=7.0, dist_portico=5.75, **kw)
    load = carregamentos_com_vento(
        geo, mat, 0.8229, 0.40, 5.75, pv, empuxo_desenvolve=False)
    return geo, mat, load


# ── O catálogo de combinações físicas ────────────────────────────────────────

def test_combinacoes_fisicas_excluem_os_aliases():
    _, _, load = _load()
    fis = load.combinacoes_ELU_fisicas()
    assert not (set(fis) & set(ALIASES))
    assert set(fis) <= set(load.combinacoes_ELU())
    # 14 padrões (8 de α=0° + 6 de α=90°, issue 39) × 2 casos (W e S) + ELU_Q
    assert len(fis) == 29


def test_envelope_devolve_a_combinacao_que_maximiza():
    _, _, load = _load()
    comb, val = load.envelope_ELU(lambda c: abs(c.M_cumeeira_kNm))
    esperado = max(abs(c.M_cumeeira_kNm) for c in load.combinacoes_ELU_fisicas().values())
    assert val == pytest.approx(esperado)
    assert abs(comb.M_cumeeira_kNm) == pytest.approx(esperado)
    assert comb.nome not in ALIASES


def test_envelope_nao_ve_os_aliases():
    """Os aliases duplicariam combinações e podiam trazer duração fixada."""
    _, _, load = _load()
    for chave in ALIASES:
        assert chave not in load.combinacoes_ELU_fisicas()


# ── Cada verificação varre e declara a sua governante ────────────────────────

@pytest.mark.parametrize("tab25", [False, True])
def test_apice_e_o_envelope_sobre_as_combinacoes(tab25):
    geo, mat, load = _load(tab25)
    r = verifica_cumeeira(geo, mat, load)
    # reconstrução independente do envelope, com o k_mod de CADA combinação
    tan_a = math.tan(geo.alpha_rad)
    k_p = 0.2 * tan_a
    V_b = geo.b * geo.L * (geo.h_ap - 0.25 * geo.L * tan_a)
    V_ap = min(geo.b * geo.h_ap ** 2 * (1 - 0.25 * tan_a), 2 * V_b / 3)
    k_vol = min((0.01 / V_ap) ** 0.2, 1.0)
    melhor = 0.0
    for c in load.combinacoes_ELU_fisicas().values():
        mc = mat.com_duracao(c.duracao)
        sig = k_p * 6 * abs(c.M_cumeeira_kNm) * 1e3 / (geo.b * geo.h_ap ** 2)
        melhor = max(melhor, sig / (1.4 * k_vol * mc.f_t90_d))
    assert r["eta_t90"] == pytest.approx(melhor, rel=2e-3)
    assert r["comb_gov"] in load.combinacoes_ELU_fisicas()


@pytest.mark.parametrize("tab25", [False, True])
def test_apoio_e_o_envelope_sobre_as_combinacoes(tab25):
    geo, mat, load = _load(tab25)
    L_ap = 0.90
    r = verifica_apoio(geo, mat, load, l_ap=L_ap)
    melhor = 0.0
    for c in load.combinacoes_ELU_fisicas().values():
        mc = mat.com_duracao(c.duracao)
        melhor = max(melhor, (abs(c.V_max_kN) * 1e3 / (geo.b * L_ap)) / mc.f_c90_d)
    assert r["eta_c90"] == pytest.approx(melhor, rel=2e-3)
    assert r["comb_gov"] in load.combinacoes_ELU_fisicas()


@pytest.mark.parametrize("tab25", [False, True])
def test_ltb_e_o_envelope_sobre_as_combinacoes(tab25):
    geo, mat, load = _load(tab25)
    from mlc_projeto.checks.elu.flambagem_lateral import (
        calcular_k_crit, calcular_l_ef, calcular_lambda_rel_m,
        calcular_sigma_m_crit,
    )
    r = verifica_flambagem_lateral(geo, mat, load, l_1=2.53)
    assert r["comb_gov"] in load.combinacoes_ELU_fisicas()
    # nenhuma combinação isolada pode exceder o η reportado — k_crit, σ_crit e
    # a seção crítica são recalculados POR COMBINAÇÃO (dependem de x_Mmax)
    for c in load.combinacoes_ELU_fisicas().values():
        mc = mat.com_duracao(c.duracao)
        h = float(geo.h(c.x_Mmax_m))
        # F-07: l_ef = 0,9·l₁ + 2h, com o h da seção de cada combinação
        l_ef = calcular_l_ef(
            2.53, restricao="continua_topo", tipo_carga="distribuida",
            posicao_carga="borda_comprimida", h_m=h)
        sc = calcular_sigma_m_crit(E_005=mc.E0_05, b=geo.b, h=h, l_ef=l_ef)
        kc = calcular_k_crit(calcular_lambda_rel_m(mc.f_m_k, sc))
        sig = abs(c.M_max_kNm) * 1e3 / (geo.b * h ** 2 / 6)
        assert sig / (kc * mc.f_m_d) <= r["eta"] + 1e-4, c.nome   # η vem arredondado


@pytest.mark.parametrize("tab25", [False, True])
def test_flexao_e_o_envelope_sobre_combinacoes_e_secoes(tab25):
    geo, mat, load = _load(tab25)
    r = verifica_flexao(geo, mat, load, s=2.53)
    assert r["comb_gov"] in load.combinacoes_ELU_fisicas()
    assert r["n_combinacoes_varridas"] == len(load.combinacoes_ELU_fisicas())


# ── O envelope nunca é menor que a antiga escolha por procuração ─────────────

@pytest.mark.parametrize("tab25", [False, True])
def test_envelope_nunca_subestima_a_escolha_anterior(tab25):
    """
    Contrato central de F-06: qualquer que seja a rota de vento, o η do envelope
    é ≥ ao que se obtinha avaliando só a combinação de max|M|.
    """
    geo, mat, load = _load(tab25)
    gov = load.combinacao_ELU_governante()
    mat_gov = mat.com_duracao(gov.duracao)

    tan_a = math.tan(geo.alpha_rad)
    k_p = 0.2 * tan_a
    V_b = geo.b * geo.L * (geo.h_ap - 0.25 * geo.L * tan_a)
    V_ap = min(geo.b * geo.h_ap ** 2 * (1 - 0.25 * tan_a), 2 * V_b / 3)
    k_vol = min((0.01 / V_ap) ** 0.2, 1.0)
    eta_proxy = (k_p * 6 * abs(gov.M_cumeeira_kNm) * 1e3
                 / (geo.b * geo.h_ap ** 2)) / (1.4 * k_vol * mat_gov.f_t90_d)

    assert verifica_cumeeira(geo, mat, load)["eta_t90"] >= eta_proxy - 1e-9


def test_na_rota_tab25_o_apice_sobe_face_a_procuracao():
    """A subestimação medida na auditoria (−4,2 %) deixa de existir."""
    geo, mat, load = _load(tab25=True)
    gov = load.combinacao_ELU_governante()
    r = verifica_cumeeira(geo, mat, load)
    assert gov.duracao == "curta"                 # governante por |M| é vento
    assert r["comb_gov"] == "ELU_Q"               # mas o ápice governa em Q
    assert r["duracao"] == "media"
    assert r["eta_t90"] == pytest.approx(0.3526, abs=1e-3)
