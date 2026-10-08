"""Issue 40 — com empuxo nulo, o esforço normal decorre só da inclinação do
eixo baricêntrico: N(x) = S(x)·sen θ, com tg θ = tg α / 2 (intradorso
horizontal, extradorso a α). Conferido contra o modelo de elementos finitos."""
import math

import numpy as np
import pytest

import mlc_projeto.main as M
from mlc_projeto.core.loads import carregamentos_com_vento, peso_proprio_gk
from mlc_projeto.core.wind import ParametrosVento


def _load():
    geo = M.GeometriaViga(**M.GEO_PARAMS)
    mat = M.GlulamMaterial(**M.MAT_CURTA)
    gk = peso_proprio_gk(geo, mat, L_t=M.L_T, b_terca=M.B_TERCA, h_terca=M.H_TERCA,
                         s_terca=M.S, g_telha_kNm2=M.G_TELHA_KNM2,
                         g_instalacoes_kNm2=M.G_INSTALACOES_KNM2)
    return geo, carregamentos_com_vento(
        geo=geo, mat=mat, g_area=gk["g_k_viga_kNm2"], q_area=M.Q_AREA, L_t=M.L_T,
        params_vento=ParametrosVento(**M.VENTO_PARAMS),
        b_pilar=M.B_PILAR, h_pilar=M.H_PILAR, n_pilares_linha=9,
        n_linhas_portico=3, L_cob_m=M.L_COMP_GALPAO, B_cob_m=40.5,
        empuxo_desenvolve=M.EMPUXO_DESENVOLVE,
    )


def test_N_igual_S_sen_theta_ao_longo_do_vao():
    geo, load = _load()
    d = load.diagramas_MVN_ELU()
    theta = math.atan(math.tan(geo.alpha_rad) / 2.0)
    assert d["H_kN"] == pytest.approx(0.0, abs=1e-9)
    assert np.allclose(np.abs(d["N"]), np.abs(d["S"]) * math.sin(theta), atol=1e-6)
    # no apoio: N = R·sen θ ≈ 8,75 kN (S por diferença finita na extremidade:
    # tolerância de 0,05 kN); na cumeeira: ≈ 0
    R = load.combinacao_ELU_governante().V_max_kN
    assert abs(d["N_max_kN"]) == pytest.approx(R * math.sin(theta), abs=0.05)
    assert load.N_max_ELU() == pytest.approx(R * math.sin(theta), abs=0.01)
    i_cum = int(np.argmin(np.abs(d["x"] - geo.L / 2)))
    assert abs(d["N"][i_cum]) < 0.05 * abs(d["N_max_kN"])


def test_fem_confirma_N_sobre_V_igual_tg_theta():
    pytest.importorskip("openseespy")
    from mlc_projeto.opensees.opensees_model import analisar_fem
    geo, load = _load()
    r = analisar_fem(q=load.combinacao_ELU_governante().q_tot, L=geo.L, h0=geo.h0,
                     h_ap=geo.h_ap, alpha_rad=geo.alpha_rad, b=geo.b, E=11.5e9,
                     desenvolve_empuxo=False)
    alvo = math.tan(geo.alpha_rad) / 2.0           # 0,0882 (≈ tg 5° = 0,0875)
    assert len(r["razao_N_V"]) > 10
    assert all(v == pytest.approx(alvo, abs=1e-4) for v in r["razao_N_V"])
