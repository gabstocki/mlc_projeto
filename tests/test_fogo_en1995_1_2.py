"""
Achado A5 — resistência ao fogo (EN 1995-1-2, método da seção reduzida).

O fogo estava ausente E não declarado. Estes testes fixam o método contra os
valores da norma (calculados à mão, não lidos do módulo) e fixam as duas
propriedades que impedem a lacuna de voltar: a seção consumida NUNCA aprova, e
o tempo requerido R é um parâmetro declarado, não uma constante escondida.
"""

import math

import pytest

from mlc_projeto.core.geometry   import GeometriaViga
from mlc_projeto.core.materials  import GlulamMaterial
from mlc_projeto.core.normativo  import NDP_SOURCE, parametros_a_confirmar
from mlc_projeto.checks.elu import fogo as F


# ── Método: carbonização e seção residual (EN 1995-1-2 §3.4.2 / §4.2.2) ──────

def test_k0_cresce_ate_20min_e_satura():
    """Tab. 4.1: k_0 = t/20 até 20 min, 1,0 depois."""
    assert F.k_0(0.0) == pytest.approx(0.0)
    assert F.k_0(10.0) == pytest.approx(0.5)
    assert F.k_0(20.0) == pytest.approx(1.0)
    assert F.k_0(60.0) == pytest.approx(1.0)


def test_k0_recusa_tempo_negativo():
    with pytest.raises(ValueError):
        F.k_0(-1.0)


@pytest.mark.parametrize(
    "t_min, d_ef_mm_esperado",
    [
        # d_ef = β_n·t + k_0·d_0, com β_n = 0,70 mm/min e d_0 = 7 mm
        (10.0, 0.70 * 10 + 0.5 * 7.0),   # 10,5 mm
        (20.0, 0.70 * 20 + 1.0 * 7.0),   # 21,0 mm
        (30.0, 0.70 * 30 + 1.0 * 7.0),   # 28,0 mm
        (60.0, 0.70 * 60 + 1.0 * 7.0),   # 49,0 mm
        (90.0, 0.70 * 90 + 1.0 * 7.0),   # 70,0 mm
    ],
)
def test_d_ef_contra_a_formula_da_norma(t_min, d_ef_mm_esperado):
    """§4.2.2 Eq. (4.1) — valores calculados à mão, não lidos do módulo."""
    assert F.d_ef(t_min) * 1e3 == pytest.approx(d_ef_mm_esperado, abs=1e-9)


def test_secao_reduzida_desconta_as_faces_expostas():
    b_fi, h_fi = F.secao_reduzida(0.320, 0.270, 0.028, faces_b=2, faces_h=2)
    assert b_fi == pytest.approx(0.320 - 0.056)
    assert h_fi == pytest.approx(0.270 - 0.056)
    # 3 faces (topo protegido): só uma face na direção da altura
    b3, h3 = F.secao_reduzida(0.320, 0.270, 0.028, faces_b=2, faces_h=1)
    assert h3 == pytest.approx(0.270 - 0.028)
    assert b3 == pytest.approx(b_fi)


def test_secao_consumida_devolve_zero_e_nao_negativo():
    """Uma seção consumida é 0, nunca uma largura negativa que 'passa'."""
    b_fi, h_fi = F.secao_reduzida(0.050, 0.050, 0.100)
    assert b_fi == 0.0 and h_fi == 0.0


# ── Propriedades em situação de incêndio (§2.3) ──────────────────────────────

def test_resistencias_fogo_aplicam_kfi_e_gammaM_unitario():
    mat = GlulamMaterial(classe="GL24h", classe_servico=3, duracao="curta")
    r = F.resistencias_fogo(mat)
    # f_d,fi = k_mod,fi · k_fi · f_k / γ_M,fi = 1,00 · 1,15 · 24 / 1,00
    assert r["f_m_d_fi"] == pytest.approx(1.15 * 24e6)
    assert r["f_v_d_fi"] == pytest.approx(1.15 * 3.5e6)
    assert r["E_005_fi"] == pytest.approx(1.15 * mat.E0_05)
    assert r["gamma_M_fi"] == 1.0
    # e é MAIOR que a resistência da situação normal — é o método, não um erro
    assert r["f_m_d_fi"] > mat.f_m_d


# ── A verificação completa ───────────────────────────────────────────────────

@pytest.fixture
def modelo():
    from mlc_projeto.core.wind  import ParametrosVento
    from mlc_projeto.core.loads import carregamentos_com_vento
    # Mesma geometria de ensaio das restantes suítes (α = 10° cai dentro do
    # domínio tabelado da Tab. 10; o vão de projeto usa a rota da Tab. 25).
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32, n_pts=1001)
    mat = GlulamMaterial(classe="GL24h", classe_servico=3, duracao="curta")
    pv = ParametrosVento(
        V0=45.0, S1=1.0, S3=1.0, categoria="IV", classe="B",
        L=geo.L, H1=geo.h_ap - geo.h0, h=7.0, dist_portico=5.75,
    )
    load = carregamentos_com_vento(
        geo=geo, mat=mat, params_vento=pv,
        g_area=0.80, q_area=0.40, L_t=5.75,
        empuxo_desenvolve=False,
    )
    return geo, mat, load


def test_verificacao_da_viga_produz_eta_finito_e_governante_declarado(modelo):
    geo, mat, load = modelo
    r = F.verificar_fogo_viga(geo, mat, load, R_req_min=30.0, s=2.53)
    assert math.isfinite(r["eta"])
    assert r["modo_gov"] in {"flexao", "flambagem_lateral", "cisalhamento"}
    assert r["eta"] == max(
        r["eta_flexao"], r["eta_ltb"], r["eta_cisalhamento"]
    )
    assert r["d_ef_mm"] == pytest.approx(28.0)
    assert r["b_fi_mm"] == pytest.approx(320.0 - 56.0)


def test_eta_cresce_monotonicamente_com_o_tempo_requerido(modelo):
    """Mais tempo de exposição ⇒ menos seção ⇒ η maior. Sempre."""
    geo, mat, load = modelo
    etas = [
        F.verificar_fogo_viga(geo, mat, load, R_req_min=R, s=2.53)["eta"]
        for R in (15.0, 30.0, 45.0, 60.0, 90.0)
    ]
    assert all(a < b for a, b in zip(etas, etas[1:])), etas


def test_seccao_consumida_nao_e_aprovacao(modelo):
    """
    A propriedade que importa (mesma regra do F-04): quando a seção deixa de
    existir, o resultado é INDETERMINADO — η = NaN e ok = False — e nunca um
    η pequeno que passe despercebido.
    """
    geo, mat, load = modelo
    # b = 320 mm consome-se com d_ef = 160 mm ⇒ t ≈ 219 min
    r = F.verificar_fogo_viga(geo, mat, load, R_req_min=400.0, s=2.53)
    assert math.isnan(r["eta"])
    assert r["ok"] is False
    assert "motivo" in r


def test_carga_de_incendio_segue_os_psi_do_normativo(modelo):
    """
    A combinação acidental lê ψ de NDP_SOURCE. Se a classificação da edificação
    mudar, o incêndio acompanha sem editar o módulo do fogo.
    """
    _, _, load = modelo
    c = F.carga_acidental_incendio(load)
    assert c["psi_1_Q"] == float(NDP_SOURCE["psi_1_Q"].valor)
    assert c["psi_2_W"] == float(NDP_SOURCE["psi_2_W"].valor)
    # categoria H: ψ1 = 0 ⇒ E_fi,d é o permanente, sem coeficiente parcial
    assert c["q_fi_kNm"] == pytest.approx(load.g_k + c["psi_1_Q"] * load.q_k)


def test_pilar_em_incendio_perde_area_e_capacidade(modelo):
    _, mat, _ = modelo
    r30 = F.verificar_fogo_pilar(b=0.32, h=0.27, H_col_m=7.0, N_fi_kN=95.8,
                                 mat=mat, R_req_min=30.0)
    r60 = F.verificar_fogo_pilar(b=0.32, h=0.27, H_col_m=7.0, N_fi_kN=95.8,
                                 mat=mat, R_req_min=60.0)
    assert r30["b_fi_mm"] == pytest.approx(264.0)
    assert r30["h_fi_mm"] == pytest.approx(214.0)
    assert r60["eta"] > r30["eta"]
    assert r60["k_c"] < r30["k_c"]      # mais esbelto ⇒ menos k_c


def test_verificacao_consolidada_governa_pelo_pior_elemento(modelo):
    geo, mat, load = modelo
    r = F.verificar_fogo(
        geo, mat, load, R_req_min=30.0, s=2.53,
        pilares=(
            dict(b=0.32, h=0.27, H_col_m=7.0, N_fi_kN=47.9, nome="pilar_lateral"),
            dict(b=0.32, h=0.27, H_col_m=7.0, N_fi_kN=95.8, nome="pilar_central"),
        ),
    )
    assert r["eta"] == max(v for v in r["eta_por_elemento"].values())
    assert r["elemento_gov"] in r["eta_por_elemento"]
    assert set(r["margem_por_R"]) == {"R30", "R60"}


# ── Declaração: o R não é do Eurocódigo ──────────────────────────────────────

def test_R_requerido_enquadrado_no_regulamento_estadual():
    """
    Issue 88: o TRRF foi enquadrado na NPT 008 do CBPMPR — edificação térrea,
    garagem aberta lateralmente, isenta (A2.3.10 b / A2.4 c). O parâmetro sai
    do guard de pendências, a R30 fica como verificação informativa e a nota
    registra a exigência de retardante (item 5.17).
    """
    p = NDP_SOURCE["R_fogo_req_min"]
    assert p.origem == "PROJETO"
    assert not p.e_ndp
    assert "R_fogo_req_min" not in parametros_a_confirmar()
    assert "NPT 008" in p.clausula and "A2.4" in p.clausula
    assert "INFORMATIVA" in p.nota and "5.17" in p.nota


def test_beta_n_e_k_fi_estao_declarados_com_a_clausula():
    assert float(NDP_SOURCE["beta_n_MLC"].valor) == pytest.approx(0.70)
    assert "Tab. 3.1" in NDP_SOURCE["beta_n_MLC"].clausula
    assert float(NDP_SOURCE["k_fi_MLC"].valor) == pytest.approx(1.15)
    assert "Tab. 2.1" in NDP_SOURCE["k_fi_MLC"].clausula
    assert F.BETA_N_MLC_CONIFERA * 1e3 == float(NDP_SOURCE["beta_n_MLC"].valor)
    assert F.K_FI_MLC == float(NDP_SOURCE["k_fi_MLC"].valor)


def test_fogo_entra_no_catalogo_de_exportacao():
    """Sem esta linha o fogo verificava-se e não aparecia no memorial."""
    from mlc_projeto.output.report import VERIFICACOES_EXPORT
    chaves = {c for c, _, _ in VERIFICACOES_EXPORT}
    assert "fogo" in chaves
    norma = next(n for c, _, n in VERIFICACOES_EXPORT if c == "fogo")
    assert "1995-1-2" in norma
