"""Testes — contraventamento vertical (issue 14): caminho de carga à fundação."""
import math

import pytest

from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.wind import ParametrosVento
from mlc_projeto.core.loads import carregamentos_com_vento
from mlc_projeto.checks.elu.contraventamento_vertical import (



    geometria_painel,
    forca_nocional,
    escolher_diametro,
    verifica_painel_vertical,
    verificar_contraventamento_vertical,
    _n_t_rd_kN,
    ACO,
)


# Onda 2 da auditoria — o contraventamento foi dimensionado para a ação
# longitudinal ANTIGA (Cf=0,04 ⇒ 125,8 kN). Com §7.2.2 (Ft=0,5·q·a·b) a ação
# passa a 837,3 kN, 6,7×. Os casos abaixo deixam de passar não por defeito de
# código, mas porque o SISTEMA está subdimensionado. Ficam como xfail estrito
# para que o redimensionamento os promova de volta — nunca relaxar o critério.
REDIMENSIONAR_ONDA2 = pytest.mark.xfail(
    strict=True,
    reason=(
        "contraventamento subdimensionado para a acao longitudinal normativa "
        "(NBR 6123:2023 7.2.2, 6,7x a anterior); redimensionamento pendente"
    ),
)


def _load_R2():
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
    mat = GlulamMaterial("GL24h", 3, "curta")
    pv = ParametrosVento(
        V0=45.0, S1=1.0, categoria="IV", classe="B", S3=1.0,
        L=20.25, H1=geo.h_ap - geo.h0, h=7.0, dist_portico=5.75,
        l2=40.5, n_tramos=2, obstrucoes_sob_cobertura=True,   # cobertura real: 2 tramos + veículos sob a cobertura (Onda 2)
    )
    load = carregamentos_com_vento(
        geo, mat, 1.5, 0.25, 5.75, pv,
        n_pilares_linha=9, n_linhas_portico=3,
        L_cob_m=46.0, B_cob_m=2 * geo.L,
    )
    return geo, mat, load


# ── Geometria e resistência ──────────────────────────────────────────────────

def test_geometria_painel_angulo():
    g = geometria_painel(H_col_m=7.0, b_baia_m=5.75)
    assert g["L_diag_m"] == pytest.approx(math.hypot(7.0, 5.75), rel=1e-9)
    assert g["tan_beta"] == pytest.approx(7.0 / 5.75, rel=1e-9)
    # cos²+sin² = 1
    assert g["cos_beta"] ** 2 + g["sin_beta"] ** 2 == pytest.approx(1.0, rel=1e-9)


def test_resistencia_tracao_EN1993():
    # N_t,Rd = A·f_y/γM0 ; d=27 mm S235
    A = math.pi * 27.0 ** 2 / 4.0
    esperado = A * ACO["S235"]["f_y"] / 1.0 / 1e3
    assert _n_t_rd_kN(27.0, "S235") == pytest.approx(esperado, rel=1e-9)


# ── Caminho de carga do painel ───────────────────────────────────────────────

def test_painel_caminho_de_carga():
    """
    Para o cortante V no painel: N_diag = V/cosβ (tração), H_base = V (à
    fundação) e N_uplift = V·tanβ (arrancamento na ancoragem).
    """
    V = 60.0
    H, b = 7.0, 5.75
    r = verifica_painel_vertical(V_Ed_kN=V, H_col_m=H, b_baia_m=b, d_mm=30, aco="S235")
    g = geometria_painel(H, b)
    # valores do módulo são arredondados a 3 casas → tolerância compatível
    assert r["N_diag_kN"] == pytest.approx(V / g["cos_beta"], abs=1e-2)
    assert r["H_base_kN"] == pytest.approx(V, rel=1e-6)         # → fundação
    assert r["N_uplift_kN"] == pytest.approx(V * g["tan_beta"], abs=1e-2)


def test_escolher_diametro_respeita_alvo():
    N = 100.0
    d = escolher_diametro(N, aco="S235", eta_alvo=0.90)
    # η com o diâmetro escolhido não excede o alvo
    assert N / _n_t_rd_kN(d, "S235") <= 0.90 + 1e-9
    # e o diâmetro imediatamente menor NÃO cumpriria o alvo (economia)
    from mlc_projeto.checks.elu.contraventamento_vertical import D_COMERCIAL_MM
    menores = [x for x in D_COMERCIAL_MM if x < d]
    if menores:
        assert N / _n_t_rd_kN(max(menores), "S235") > 0.90 + 1e-9


def test_forca_nocional_intervalo():
    r = forca_nocional(V_vertical_kN=2000.0, h_m=7.0, m_colunas=9)
    assert 0.002 < r["phi"] < 0.006
    assert r["H_imp_kN"] == pytest.approx(r["phi"] * 2000.0, rel=1e-6)


# ── Verificação completa ─────────────────────────────────────────────────────

@REDIMENSIONAR_ONDA2
def test_verificacao_completa_inclui_vento_e_nocional():
    geo, mat, load = _load_R2()
    res = verificar_contraventamento_vertical(
        geo=geo, load=load, H_pilar_m=7.0,
        dist_portico=5.75, L_comp=46.0, n_porticos=2,
        n_paineis_long=2, aco="S235",
    )
    # a demanda lateral é vento θ=0° + nocional
    assert res["F_vento0_kN"] > 0.0
    assert res["H_imp_kN"] > 0.0
    assert res["V_lat_total_kN"] == pytest.approx(
        res["F_vento0_kN"] + res["H_imp_kN"], rel=1e-6
    ) or res["V_lat_total_kN"] >= res["F_vento0_kN"] + res["H_imp_kN"]
    # ordem de grandeza compatível com o apontamento (~125 kN)
    assert 90.0 < res["V_lat_total_kN"] < 200.0
    # diâmetro auto dentro do alvo e verificação aprovada
    assert res["d_auto"] is True
    assert res["ok"] is True
    assert res["eta_diag_N"] <= 0.90 + 1e-9
    assert res["lateral_estavel_long"] is True
    # caminho de carga à fundação presente
    assert res["H_base_kN"] > 0.0
    assert res["N_uplift_kN"] > 0.0


def test_coerencia_com_reacao_cobertura():
    """R_ext da cobertura eleva a demanda se maior que vento+nocional."""
    geo, mat, load = _load_R2()
    base = verificar_contraventamento_vertical(
        geo=geo, load=load, H_pilar_m=7.0, n_paineis_long=2,
    )
    alto = verificar_contraventamento_vertical(
        geo=geo, load=load, H_pilar_m=7.0, n_paineis_long=2,
        R_ext_cobertura_kN=10 * base["V_lat_total_kN"],
    )
    assert alto["V_lat_total_kN"] > base["V_lat_total_kN"]
