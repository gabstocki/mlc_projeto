"""Issue 64 (Opção A) — a linha central recebe metade da força longitudinal.

As treliças de contraventamento da cobertura (issue 41) apoiam-se no beiral e
no alinhamento central; sem cruzes na linha central a reação central não tinha
caminho até a fundação."""
import contextlib
import io

import pytest

import mlc_projeto.main as M
from mlc_projeto.core.wind import ParametrosVento
from mlc_projeto.checks.elu.contraventamento_vertical import (
    reparticao_alinhamentos,
    verificar_contraventamento_vertical,
)


def _cvv(n_paineis, fracao=1.0):
    from mlc_projeto.core.loads import carregamentos_com_vento, peso_proprio_gk
    geo = M.GeometriaViga(**M.GEO_PARAMS)
    mat = M.GlulamMaterial(**M.MAT_CURTA)
    gk = peso_proprio_gk(geo, mat, L_t=M.L_T, b_terca=M.B_TERCA, h_terca=M.H_TERCA,
                         s_terca=M.S, g_telha_kNm2=M.G_TELHA_KNM2,
                         g_instalacoes_kNm2=M.G_INSTALACOES_KNM2)
    load = carregamentos_com_vento(
        geo=geo, mat=mat, g_area=gk["g_k_viga_kNm2"], q_area=M.Q_AREA, L_t=M.L_T,
        params_vento=ParametrosVento(**M.VENTO_PARAMS),
        b_pilar=M.B_PILAR, h_pilar=M.H_PILAR,
        n_pilares_linha=9, n_linhas_portico=3,
        L_cob_m=M.L_COMP_GALPAO, B_cob_m=40.5,
        empuxo_desenvolve=M.EMPUXO_DESENVOLVE,
    )
    return verificar_contraventamento_vertical(
        geo=geo, load=load, H_pilar_m=M.H_PILAR_ALT, dist_portico=M.L_T,
        L_comp=M.L_COMP_GALPAO, n_porticos=2, n_paineis_long=n_paineis,
        aco=M.ACO_CVV, d_mm=None, eta_alvo=M.ETA_CVV_ALVO,
        V_Ed_total_kN=2.0 * 2 * abs(load.V_max_ELU()) * 9,
        fracao_demanda=fracao,
    )


def _pipeline():
    backup = M.gerar_relatorio
    try:
        M.gerar_relatorio = lambda *a, **k: {}
        with contextlib.redirect_stdout(io.StringIO()):
            return M._main_impl(rodar_varredura=False, abrir_viz=False)
    finally:
        M.gerar_relatorio = backup


def test_reparticao_dois_vaos():
    r = reparticao_alinhamentos(2)
    assert r["por_beiral"] == pytest.approx(0.25)
    assert r["por_interno"] == pytest.approx(0.50)
    assert r["fachadas"] + r["internos"] == pytest.approx(1.0)


def test_reparticao_um_vao_sem_interno():
    r = reparticao_alinhamentos(1)
    assert r["fachadas"] == pytest.approx(1.0)
    assert r["internos"] == pytest.approx(0.0)


def test_fracao_da_demanda_escala_o_cortante():
    """Metade da demanda em 4 painéis = demanda inteira em 8 painéis."""
    meio, inteiro = _cvv(4, 0.5), _cvv(8, 1.0)
    assert meio["V_painel_kN"] == pytest.approx(inteiro["V_painel_kN"], rel=1e-6)
    assert meio["fracao_demanda"] == pytest.approx(0.5)


def test_fracao_invalida_recusada():
    with pytest.raises(ValueError):
        _cvv(4, 0.0)


def test_quadro_fundacao_separa_bases_centrais_montantes():
    """2 grupos de 2 painéis contíguos → 2×3 = 6 bases centrais montantes."""
    r = _pipeline()
    linhas = {l["Base"]: l for l in r["cargas_fundacao"]["linhas"]}
    cm = linhas["Central montante (contraventamento)"]
    assert cm["n"] == 6
    assert linhas["Central (pilar do apoio partilhado)"]["n"] == 9 - 6
    cvc = r["contraventamento_vertical_central"]
    assert cm["H (kN)"] == pytest.approx(cvc["H_base_kN"], abs=0.1)
    cvv = r["contraventamento_vertical"]
    tot = r["cargas_fundacao"]["totais"]["H_longitudinal_total_kN"]
    assert tot == pytest.approx(cvv["V_lat_total_kN"] + cvc["V_lat_total_kN"], abs=0.5)


def test_base_central_montante_soma_uplift_e_painel():
    r = _pipeline()
    s = r["succao_uplift"]
    cvc = r["contraventamento_vertical_central"]
    assert s["N_uplift_cen_cv_kN"] == pytest.approx(
        s["N_uplift_cen_kN"] + cvc["N_uplift_kN"], abs=0.01)
    assert s["n_chu_cen_cv"] == M.N_CHU_CENTRAL_CV
    assert s["eta_cen_cv"] < 1.0
