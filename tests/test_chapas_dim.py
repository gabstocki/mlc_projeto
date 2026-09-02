"""Issue 23 — Esquadro de chapas: dimensões e espessura SAINDO do dimensionamento.

A espessura não é arbitrada:
  · chapa embutida (L1/L1c): governa t ≥ d (chapa central rígida p/ rótula do pino),
    além de escoamento/ruptura líquida/bearing;
  · chapa de base (L3/L3c): flexão do balanço (EN 1993-1-8 §6.2.5).
"""

import math

import pytest

from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.wind import ParametrosVento
from mlc_projeto.core.loads import carregamentos_com_vento
from mlc_projeto.connections.connections import (
    dimensionar_ligacoes, dimensionar_ligacoes_central,
)
from mlc_projeto.connections.chapas_dim import (
    espessura_chapa_embutida,
    espessura_chapa_base,
    esquadro_chapas,
    _adotar_comercial,
    COMMERCIAL_T_MM,
)


def _ligacoes():
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
    mat = GlulamMaterial("GL24h", 3, "curta")
    pv = ParametrosVento(V0=45, S1=1, categoria="IV", classe="B", S3=1,
                         L=20.25, H1=geo.h_ap - geo.h0, h=7, dist_portico=5.75)
    load = carregamentos_com_vento(geo=geo, mat=mat, g_area=0.823, q_area=0.40,
                                   L_t=5.75, params_vento=pv)
    gov = load.combinacao_ELU_governante()
    m = mat.com_duracao(gov.duracao)
    L = dimensionar_ligacoes(m, load, geo, d_base_mm=24, com_tirante=True, eta_alvo=0.75)
    Lc = dimensionar_ligacoes_central(m, load, geo, d_base_mm=24, eta_alvo=0.75)
    return geo, L, Lc


def test_adotar_comercial_arredonda_para_cima():
    assert _adotar_comercial(24.0) == 25.0     # próxima ≥ 24
    assert _adotar_comercial(8.3) == 9.5
    assert _adotar_comercial(6.0) == COMMERCIAL_T_MM[0]


def test_embutida_governa_t_thick_igual_d():
    """Chapa embutida: governa t≥d (rígida) → adota 25 mm para Ø24."""
    geo, L, _ = _ligacoes()
    r = espessura_chapa_embutida(L["L1"], geo, aco="S275")
    assert r["t_governa"] == "t_thick_d_mm"
    assert r["criterios_t"]["t_thick_d_mm"] == pytest.approx(24.0, abs=1e-6)
    assert r["t_adotada_mm"] == 25.0
    # t_req = máx dos critérios
    assert r["t_req_mm"] == pytest.approx(max(r["criterios_t"].values()), rel=1e-6)


def test_embutida_dimensoes_incluem_furacao():
    geo, L, _ = _ligacoes()
    r = espessura_chapa_embutida(L["L1"], geo)
    assert r["largura_mm"] > 0 and r["altura_mm"] > 0
    assert r["altura_mm"] <= L["L1"]["h_disp_mm"] + 1e-6
    assert str(L["L1"]["n_pinos"]) in r["furacao"]


def test_base_flexao_balanco():
    """Chapa de base: t = c·√(3·σ_c/f_y); dimensões cobrem o pilar + borda."""
    geo, L, Lc = _ligacoes()
    r = espessura_chapa_base(Lc["L3c"], b_pilar_m=0.32, h_pilar_m=0.27, aco="S275")
    f_y = 275.0
    c = r["c_balanco_mm"]
    t_flex = c * math.sqrt(3.0 * r["sigma_c_MPa"] / f_y)
    assert r["criterios_t"]["t_flexao_mm"] == pytest.approx(t_flex, rel=1e-2)
    assert r["largura_mm"] >= 0.32 * 1e3      # cobre o pilar
    assert r["t_adotada_mm"] in COMMERCIAL_T_MM


def test_base_central_mais_espessa_que_lateral():
    """L3c (N=2·R_v, chapa maior) exige espessura ≥ L3."""
    geo, L, Lc = _ligacoes()
    r3 = espessura_chapa_base(L["L3"], 0.32, 0.27, aco="S275")
    r3c = espessura_chapa_base(Lc["L3c"], 0.32, 0.27, aco="S275")
    assert r3c["t_adotada_mm"] >= r3["t_adotada_mm"]
    assert r3c["largura_mm"] >= r3["largura_mm"]


def test_esquadro_completo_inclui_central():
    """Esquadro cobre L1, L1c, L3 e explicitamente L3c (pilar central)."""
    geo, L, Lc = _ligacoes()
    esq = esquadro_chapas(L, Lc, geo, 0.32, 0.27, 0.32, 0.27, aco="S275")
    for k in ("L1", "L1c", "L3", "L3c"):
        assert k in esq
        assert esq[k]["t_adotada_mm"] > 0
    assert esq["L3c"]["tipo"] == "base"
    assert esq["L1"]["t_adotada_mm"] == 25.0
