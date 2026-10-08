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
    """
    F-11: N_t,Rd = min(N_pl,Rd ; N_u,Rd) — EN 1993-1-1 §6.2.3(2). A barra é
    roscada nas extremidades, logo a seção líquida é a da rosca.
    """
    from mlc_projeto.checks.elu.contraventamento_vertical import (
        GAMMA_M2, area_resistente_rosca)
    A = math.pi * 27.0 ** 2 / 4.0
    N_pl = A * ACO["S235"]["f_y"] / 1.0 / 1e3
    N_u = 0.9 * area_resistente_rosca(27.0) * ACO["S235"]["f_u"] / GAMMA_M2 / 1e3
    from mlc_projeto.checks.elu.contraventamento_vertical import (
        resistencia_tracao_diagonal)
    cortada = resistencia_tracao_diagonal(27.0, "S235", recalcada=False)
    assert cortada["N_t_Rd_kN"] == pytest.approx(min(N_pl, N_u), rel=1e-9)
    assert cortada["N_t_Rd_kN"] < N_pl                 # rosca cortada: frágil
    # Issue 44 — extremidade recalcada (padrão): governa o escoamento
    assert _n_t_rd_kN(27.0, "S235") == pytest.approx(N_pl, rel=1e-9)


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

def test_verificacao_completa_inclui_vento_e_nocional():
    geo, mat, load = _load_R2()
    res = verificar_contraventamento_vertical(
        geo=geo, load=load, H_pilar_m=7.0,
        dist_portico=5.75, L_comp=46.0, n_porticos=2,
        n_paineis_long=6, aco="S235",   # layout redimensionado (era 2)
    )
    # a demanda lateral é vento θ=0° + nocional
    assert res["F_vento0_kN"] > 0.0
    assert res["H_imp_kN"] > 0.0
    assert res["V_lat_total_kN"] == pytest.approx(
        res["F_vento0_kN"] + res["H_imp_kN"], rel=1e-6
    ) or res["V_lat_total_kN"] >= res["F_vento0_kN"] + res["H_imp_kN"]
    # Redimensionamento pós-Onda 2: com Ft = 0,5·q·a·b (§7.2.2) a demanda
    # lateral total é ~847 kN, contra os ~125 kN do coeficiente Cf=0,04
    # anterior. Distribui-se por 6 painéis (era 2), o que baixa o download no
    # montante de 515,8 para 171,9 kN e desafoga pilar de canto e ancoragem.
    assert 700.0 < res["V_lat_total_kN"] < 1000.0
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
