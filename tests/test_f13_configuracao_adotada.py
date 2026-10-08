"""
Configuração adotada do contraventamento longitudinal — no âmbito de F-13.

Fixa a decisão da terceira varredura (auditoria adversarial v2), revista na
issue 64 (Opção A): a força longitudinal reparte-se entre as fachadas e a linha
central, com 4 painéis em cada conjunto (8 baías ocupadas, como antes). O peso de aço é praticamente independente de n (900–1030 kg de n=2 a
n=16); o que n compra é margem no CAMINHO DE CARGA — download no montante,
ancoragem e bloco de fundação — e o que custa são baías de circulação.
"""
import contextlib
import io

import pytest

import mlc_projeto.main as M
from mlc_projeto.core.wind import ParametrosVento, forca_vento_paralelo_cumeeira
from mlc_projeto.checks.elu.contraventamento_vertical import (
    verificar_contraventamento_vertical,
)


def test_projeto_adota_quatro_mais_quatro_paineis():
    assert M.N_PAINEIS_CV_VERT == 4          # fachadas (1 por extremidade e fachada)
    assert M.N_PAINEIS_CV_CENTRAL == 4       # linha central (2 por extremidade)
    assert M.D_BARRA_CVV_MM is None          # diâmetro auto-dimensionado


def test_coeficiente_de_atrito_e_declarado_no_projeto():
    assert M.VENTO_PARAMS["coef_atrito_cobertura"] == pytest.approx(0.50)


def test_baias_disponiveis_comportam_os_paineis():
    """8 baías por alinhamento; ocupam-se 4 nas fachadas e 4 na linha central."""
    baias = round(M.L_COMP_GALPAO / M.L_T)
    assert baias == 8
    assert 2 * baias - M.N_PAINEIS_CV_VERT == 12          # fachadas livres
    assert baias - M.N_PAINEIS_CV_CENTRAL == 4             # linha central livre
    assert M.N_PAINEIS_CV_VERT + M.N_PAINEIS_CV_CENTRAL == 8


def _cvv(n_paineis):
    geo = M.GeometriaViga(**M.GEO_PARAMS)
    mat = M.GlulamMaterial(**M.MAT_CURTA)
    pv = ParametrosVento(**M.VENTO_PARAMS)
    from mlc_projeto.core.loads import carregamentos_com_vento, peso_proprio_gk
    gk = peso_proprio_gk(geo, mat, L_t=M.L_T, b_terca=M.B_TERCA, h_terca=M.H_TERCA,
                         s_terca=M.S, g_telha_kNm2=M.G_TELHA_KNM2,
                         g_instalacoes_kNm2=M.G_INSTALACOES_KNM2)
    load = carregamentos_com_vento(
        geo=geo, mat=mat, g_area=gk["g_k_viga_kNm2"], q_area=M.Q_AREA, L_t=M.L_T,
        params_vento=pv, b_pilar=M.B_PILAR, h_pilar=M.H_PILAR,
        n_pilares_linha=9, n_linhas_portico=3,
        L_cob_m=M.L_COMP_GALPAO, B_cob_m=40.5,
        empuxo_desenvolve=M.EMPUXO_DESENVOLVE,
    )
    return verificar_contraventamento_vertical(
        geo=geo, load=load, H_pilar_m=M.H_PILAR_ALT, dist_portico=M.L_T,
        L_comp=M.L_COMP_GALPAO, n_porticos=2, n_paineis_long=n_paineis,
        aco=M.ACO_CVV, d_mm=None, eta_alvo=M.ETA_CVV_ALVO,
        V_Ed_total_kN=2.0 * 2 * abs(load.V_max_ELU()) * 9,
    )


def test_oito_paineis_reduzem_diagonal_e_download_face_a_quatro():
    q4, q8 = _cvv(4), _cvv(8)
    assert q8["d_mm"] < q4["d_mm"]                       # Ø45 → Ø33
    assert q8["N_uplift_kN"] < 0.65 * q4["N_uplift_kN"]  # download −40 %
    assert q8["H_base_kN"] < q4["H_base_kN"]
    assert q8["ok"] is True


def test_peso_de_aco_e_praticamente_insensivel_a_n():
    """Constatação que sustenta a decisão: mais painéis não custam aço."""
    pesos = [_cvv(n)["peso_total_kg"] for n in (4, 6, 8, 10)]
    assert max(pesos) / min(pesos) < 1.20


def test_dois_paineis_centrais_reprovariam_o_conjunto():
    """Contrato de regressão (issue 64): concentrar a metade central em 2
    painéis reprova o pilar central montante."""
    M_old = M.N_PAINEIS_CV_CENTRAL
    M.gerar_relatorio_backup = getattr(M, "gerar_relatorio")
    try:
        M.N_PAINEIS_CV_CENTRAL = 2
        M.gerar_relatorio = lambda *a, **k: {}
        with contextlib.redirect_stdout(io.StringIO()):
            r = M._main_impl(rodar_varredura=False, abrir_viz=False)
        assert r["meta"]["status"] == "REPROVADO"
        assert r["pilar_central_contraventado"]["eta"] > 1.0
    finally:
        M.N_PAINEIS_CV_CENTRAL = M_old
        M.gerar_relatorio = M.gerar_relatorio_backup


def test_configuracao_adotada_aprova():
    M.gerar_relatorio_backup = getattr(M, "gerar_relatorio")
    try:
        M.gerar_relatorio = lambda *a, **k: {}
        with contextlib.redirect_stdout(io.StringIO()):
            r = M._main_impl(rodar_varredura=False, abrir_viz=False)
        assert r["meta"]["status"] == "APROVADO"
        assert r["contraventamento_vertical_central"]["ok"] is True
        assert r["pilar_central_contraventado"]["eta"] < 1.0
        assert r["ancoragem_central_cv"]["eta"] < 1.0
    finally:
        M.gerar_relatorio = M.gerar_relatorio_backup
