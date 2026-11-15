"""Issue 47 — flambagem lateral sob sucção (intradorso comprimido, EC5 §6.3.3).

Sob sucção o momento inverte e comprime o intradorso, que as terças (no
extradorso) não contêm: l_1 = vão, l_ef = 0,9·L, seção crítica por varredura."""
import pytest

import mlc_projeto.main as M
from mlc_projeto.core.loads import carregamentos_com_vento, peso_proprio_gk
from mlc_projeto.core.wind import ParametrosVento
from mlc_projeto.checks.elu.flambagem_lateral import (
    momento_biapoiada,
    verifica_flambagem_lateral,
    verifica_flambagem_lateral_succao,
)


@pytest.fixture(scope="module")
def projeto():
    geo = M.GeometriaViga(**M.GEO_PARAMS)
    mat = M.GlulamMaterial(**M.MAT_CURTA)
    gk = peso_proprio_gk(geo, mat, L_t=M.L_T, b_terca=M.B_TERCA, h_terca=M.H_TERCA,
                         s_terca=M.S, g_telha_kNm2=M.G_TELHA_KNM2,
                         g_instalacoes_kNm2=M.G_INSTALACOES_KNM2)
    load = carregamentos_com_vento(
        geo=geo, mat=mat, g_area=gk["g_k_viga_kNm2"], q_area=M.Q_AREA, L_t=M.L_T,
        params_vento=ParametrosVento(**M.VENTO_PARAMS),
        b_pilar=M.B_PILAR, h_pilar=M.H_PILAR, n_pilares_linha=9,
        n_linhas_portico=3, L_cob_m=M.L_COMP_GALPAO, B_cob_m=40.5,
        empuxo_desenvolve=M.EMPUXO_DESENVOLVE,
    )
    return geo, mat, load


def test_momento_biapoiada_confere_com_a_analise(projeto):
    """A fórmula de carga uniforme confere com o integrador quando o peso próprio
    variável da viga (issue 114) é desligado."""
    geo, _, load = projeto
    load.peso_viga_variavel = False
    try:
        for c in load.combinacoes_ELU_fisicas().values():
            r = load._analisar(q_esq=c.q_esq, q_dir=c.q_dir, fG=c.fator_G)
            ms = [momento_biapoiada(geo.L * i / 2000, geo.L, c.q_esq, c.q_dir, geo.a_bal)
                  for i in range(2001)]
            alvo = min(ms) if r["M_max_kNm"] < 0 else max(ms)
            assert alvo == pytest.approx(r["M_max_kNm"], abs=0.05)
    finally:
        load.peso_viga_variavel = True


def test_succao_comprime_o_intradorso_e_passa(projeto):
    geo, mat, load = projeto
    r = verifica_flambagem_lateral_succao(geo, mat, load)
    assert r["aplicavel"] is True
    assert r["M_d_kNm"] < 0.0
    assert r["l_1_m"] == pytest.approx(geo.L)
    assert r["l_ef_m"] == pytest.approx(0.9 * geo.L)
    assert 0.0 < r["eta"] < 1.0


def test_secao_critica_nao_e_a_de_maior_momento(projeto):
    """Altura variável: a varredura acha seção mais baixa e mais crítica que a
    de |M| máximo."""
    geo, mat, load = projeto
    r = verifica_flambagem_lateral_succao(geo, mat, load)
    M_min = min(c.M_max_kNm for c in load.combinacoes_ELU_fisicas().values())
    assert abs(r["M_d_kNm"]) < abs(M_min)


def test_reducao_de_meio_h_seria_menos_conservadora(projeto):
    geo, mat, load = projeto
    base = verifica_flambagem_lateral_succao(geo, mat, load)
    red = verifica_flambagem_lateral_succao(geo, mat, load,
                                            posicao_carga="borda_tracionada")
    assert red["eta"] <= base["eta"]


def test_verificacao_principal_so_considera_momento_positivo(projeto):
    geo, mat, load = projeto
    r = verifica_flambagem_lateral(geo, mat, load, l_1=M.S)
    assert r["M_max_ELU_kNm"] > 0.0
