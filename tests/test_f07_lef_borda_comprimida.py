"""
Testes de regressão — F-07 (auditoria adversarial v2).

Achado
------
`calcular_l_ef` aplicava as razões da EC5 **Tabela 6.1** (`l_ef = 0,9·l₁` para
carga distribuída) mas **omitia a nota da própria tabela**:

    "The ratios between the effective length l_ef and the span ℓ are valid for a
     beam with torsionally restrained supports and loaded at the centre of
     gravity. If the load is applied at the COMPRESSION EDGE of the beam, l_ef
     should be INCREASED BY 2h, and may be DECREASED BY 0,5h for a load at the
     tension edge of the beam."

Neste projeto as terças apoiam no EXTRADORSO — a borda comprimida sob
gravidade. Com `l₁ = 2,53 m` e `h = 2,785 m`, `l_ef` correto é
`0,9·2,53 + 2·2,785 = 7,85 m` em vez de 2,28 m — **3,4×**. λ_rel,m sobe de
0,446 para 0,827, ou seja a viga passa de «estável» a «instabilidade parcial»
(k_crit deixa de ser 1,0).

A API passa a EXIGIR a declaração da posição da carga: o default é o caso
conservador (borda comprimida) e `h_m` é obrigatório nesse caso — nenhum
chamador pode continuar a herdar silenciosamente a hipótese mais favorável.
"""
import math

import pytest

from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.wind import ParametrosVento
from mlc_projeto.core.loads import carregamentos_com_vento
from mlc_projeto.checks.elu.flambagem_lateral import (
    calcular_l_ef,
    verifica_flambagem_lateral,
)

L1, H = 2.53, 2.7854


# ── A nota da Tabela 6.1 ─────────────────────────────────────────────────────

def test_centro_de_gravidade_e_a_razao_crua_da_tabela():
    assert calcular_l_ef(L1, posicao_carga="centro_gravidade") == pytest.approx(0.9 * L1)


def test_borda_comprimida_soma_2h():
    got = calcular_l_ef(L1, posicao_carga="borda_comprimida", h_m=H)
    assert got == pytest.approx(0.9 * L1 + 2 * H)
    assert got / (0.9 * L1) == pytest.approx(3.446, abs=0.01)


def test_borda_tracionada_desconta_meio_h():
    assert calcular_l_ef(L1, posicao_carga="borda_tracionada", h_m=H) == pytest.approx(
        0.9 * L1 - 0.5 * H)


def test_ordem_das_tres_posicoes():
    t = calcular_l_ef(L1, posicao_carga="borda_tracionada", h_m=H)
    c = calcular_l_ef(L1, posicao_carga="centro_gravidade")
    k = calcular_l_ef(L1, posicao_carga="borda_comprimida", h_m=H)
    assert t < c < k


def test_carga_pontual_usa_0_8_e_tambem_soma_2h():
    assert calcular_l_ef(
        L1, tipo_carga="pontual", posicao_carga="borda_comprimida", h_m=H
    ) == pytest.approx(0.8 * L1 + 2 * H)


def test_lef_nao_fisico_falha_alto_em_vez_de_ser_limitado():
    """
    h grande com l₁ pequeno na borda tracionada daria l_ef ≤ 0. A redução de
    0,5h é um «may» da norma e não pode anular o comprimento efetivo — recusa-se
    em vez de compensar com um valor mínimo inventado.
    """
    from mlc_projeto.core.validacao import DominioInvalidoError
    with pytest.raises(DominioInvalidoError):
        calcular_l_ef(0.5, posicao_carga="borda_tracionada", h_m=3.0)
    # o caso admissível continua a funcionar
    assert calcular_l_ef(5.0, posicao_carga="borda_tracionada", h_m=2.0) > 0.0


# ── A API obriga a declarar ──────────────────────────────────────────────────

def test_default_e_o_caso_conservador():
    """Sem declaração explícita, assume-se a borda comprimida."""
    assert calcular_l_ef(L1, h_m=H) == pytest.approx(0.9 * L1 + 2 * H)


def test_borda_comprimida_sem_h_falha_alto():
    """Não se pode herdar silenciosamente a hipótese favorável."""
    with pytest.raises(Exception):
        calcular_l_ef(L1, posicao_carga="borda_comprimida")


def test_posicao_desconhecida_e_recusada():
    with pytest.raises(ValueError):
        calcular_l_ef(L1, posicao_carga="a_meio_do_alma", h_m=H)


# ── Efeito na verificação de LTB ─────────────────────────────────────────────

def _load():
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
    mat = GlulamMaterial("GL24h", 3, "media")
    pv = ParametrosVento(
        V0=45.0, S1=1.0, categoria="IV", classe="B", S3=1.0, L=20.25,
        H1=geo.h_ap - geo.h0, h=7.0, dist_portico=5.75,
        l2=40.5, n_tramos=2, obstrucoes_sob_cobertura=True)
    return geo, mat, carregamentos_com_vento(
        geo, mat, 0.8229, 0.40, 5.75, pv, empuxo_desenvolve=False)


def test_ltb_do_projeto_passa_a_instabilidade_parcial():
    geo, mat, load = _load()
    r = verifica_flambagem_lateral(geo, mat, load, l_1=L1)
    assert r["posicao_carga"] == "borda_comprimida"
    assert r["l_ef_m"] == pytest.approx(0.9 * L1 + 2 * r["h_crit_m"], abs=1e-3)
    assert r["lambda_rel_m"] == pytest.approx(0.827, abs=2e-3)
    assert r["k_crit"] == pytest.approx(0.9396, abs=2e-3)   # já não é 1,0
    assert "parcial" in r["regime"]
    assert r["eta"] == pytest.approx(0.1095, abs=5e-4)   # issue 114: peso variável


def test_ltb_e_mais_severa_que_a_hipotese_no_centro_de_gravidade():
    geo, mat, load = _load()
    borda = verifica_flambagem_lateral(geo, mat, load, l_1=L1)
    centro = verifica_flambagem_lateral(
        geo, mat, load, l_1=L1, posicao_carga="centro_gravidade")
    assert borda["l_ef_m"] > centro["l_ef_m"]
    assert borda["k_crit"] < centro["k_crit"]
    assert borda["eta"] > centro["eta"]


def test_2h_usa_a_altura_LOCAL_da_secao():
    """Viga de altura variável: o acréscimo segue a seção crítica, não h0."""
    geo, mat, load = _load()
    r = verifica_flambagem_lateral(geo, mat, load, l_1=L1)
    assert r["h_crit_m"] == pytest.approx(geo.h_ap, abs=1e-3)   # governa no ápice
    assert r["l_ef_m"] > 0.9 * L1 + 2 * geo.h0                   # não usou h0


# ── Flexão: separação entre flambagem de coluna e LTB ────────────────────────

def test_flexao_separa_l_ef_z_de_l_ef_LTB():
    """
    O `+2h` é da flambagem lateral por flexo-torção; NÃO se aplica ao
    comprimento de flambagem à compressão em torno de z.
    """
    from mlc_projeto.checks.elu.flexao import verifica_flexao
    geo, mat, load = _load()
    r = verifica_flexao(geo, mat, load, s=L1)
    assert r["l_ef_z_m"] == pytest.approx(0.9 * L1, abs=1e-6)
    assert r["l_ef_ltb_m"] > r["l_ef_z_m"]
    assert r["l_ef_ltb_m"] == pytest.approx(0.9 * L1 + 2 * r["h_gov_m"], abs=1e-3)
