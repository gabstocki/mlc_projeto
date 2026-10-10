"""Issue 52 — pilar de frontão, detalhe das bases e desenhos cotados em escala."""
import contextlib
import io
import math

import pytest

import mlc_projeto.main as M
from mlc_projeto.connections.base_pilar import geometria_base, tstub_base
from mlc_projeto.output.desenhos import (
    LARGURA_FOLHA_MM, FOLHAS, Folha, arranjo_de_resultados, flecha_no_ponto,
    gerar_desenhos, nome_pilar, nome_viga,
)


@pytest.fixture(scope="module")
def pipeline():
    capt = {}
    orig_cv, orig_rel = M.carregamentos_com_vento, M.gerar_relatorio

    def _cv(*a, **k):
        capt["geo"] = k["geo"]
        return orig_cv(*a, **k)

    try:
        M.carregamentos_com_vento = _cv
        M.gerar_relatorio = lambda *a, **k: {}
        with contextlib.redirect_stdout(io.StringIO()):
            capt["res"] = M._main_impl(rodar_varredura=False, abrir_viz=False)
    finally:
        M.carregamentos_com_vento, M.gerar_relatorio = orig_cv, orig_rel
    return capt


# ── Pilar de frontão ─────────────────────────────────────────────────────────

def test_pilar_frontao_e_o_segundo_montante_da_cruz(pipeline):
    res = pipeline["res"]
    pf, cvt = res["pilar_frontao"], res["contraventamento_transversal"]
    assert cvt["b_baia_m"] == pytest.approx(M.L_T)          # a 5,75 m do canto
    assert pf["download_kN"] == pytest.approx(cvt["N_uplift_kN"], abs=1e-3)
    assert pf["H_base_kN"] == pytest.approx(cvt["H_base_kN"], abs=1e-3)
    # não apoia a viga: só peso próprio + download na compressão
    G = pf["G_k_kN"]
    assert pf["montante"]["N_comp_kN"] == pytest.approx(1.35 * G + pf["download_kN"],
                                                        abs=0.01)
    assert pf["ok"] and pf["eta"] <= 0.75


def test_arrasto_inclui_os_pilares_de_frontao(pipeline):
    cvt = pipeline["res"]["contraventamento_transversal"]
    assert cvt["n_colunas"] == 27 + M.N_PILARES_FRONTAO


def test_cargas_fundacao_tem_linha_do_pilar_de_frontao(pipeline):
    linhas = pipeline["res"]["cargas_fundacao"]["linhas"]
    pf = [l for l in linhas if "frontão" in l["Base"]]
    assert len(pf) == 1 and pf[0]["n"] == M.N_PILARES_FRONTAO


# ── Bases ────────────────────────────────────────────────────────────────────

def test_chapa_sai_da_grelha_usada_no_cone():
    g = geometria_base(2, 2, 400.0, 60.0, 320.0, 270.0, 24.0)
    assert g["B_mm"] == g["L_mm"] == 520.0
    xs = sorted({x for x, _ in g["chumbadores_mm"]})
    assert xs[1] - xs[0] == pytest.approx(400.0)            # = S_GRUPO_CHU_MM
    assert g["folga_ok"]                                     # arruela fora do pilar


def test_chapa_400_com_grelha_400_seria_incompativel():
    """O caso antigo: grelha de 400 numa chapa que só cobre o pilar."""
    g = geometria_base(2, 2, 400.0, 60.0, 320.0, 270.0, 24.0)
    assert g["B_mm"] > 400.0


def test_tstub_modo_1_cresce_com_t_ao_quadrado():
    kw = dict(n_y=2, s_mm=400.0, e_mm=60.0, L_mm=520.0, t_alma_mm=20.0,
              F_t_Rd_chu_kN=169.44)
    a = tstub_base(80.0, t_mm=8.0, **kw)
    b = tstub_base(80.0, t_mm=16.0, **kw)
    assert a["modo"] == "modo 1"
    assert b["F_T1_kN"] == pytest.approx(4.0 * a["F_T1_kN"], rel=5e-3)   # saídas arredondadas


def test_bases_no_pipeline(pipeline):
    res = pipeline["res"]
    for k in ("base_L3", "base_L3c", "base_L3f", "base_L3a_canto", "base_L3a_central"):
        b = res[k]
        assert b["ok"], k
        assert b["tstub"]["eta"] <= 0.90 + 1e-9                # margem da chapa
        assert b["pe_pilar"]["eta"] <= 0.75 + 1e-9             # modo frágil
        assert b["geometria"]["s_mm"] == M.S_GRUPO_CHU_MM
    # o esquadro do memorial reflete o detalhe (não mais 400 × 400)
    assert res["esquadro_chapas"]["L3"]["largura_mm"] == res["base_L3"]["B_mm"]


# ── Desenhos ─────────────────────────────────────────────────────────────────

def test_nomenclatura():
    assert nome_pilar(1, "A") == "P1" and nome_pilar(9, "C") == "P27"
    assert nome_pilar(2, "B") == "P5"
    assert nome_viga(1, "AB") == "V1" and nome_viga(9, "BC") == "V18"


def test_flecha_no_ponto_forma_da_elastica():
    assert flecha_no_ponto(10.0, 10.0, 20.0) == pytest.approx(10.0)
    assert flecha_no_ponto(10.0, 0.0, 20.0) == 0.0
    assert flecha_no_ponto(15.39, 5.75, 20.25) == pytest.approx(12.05, abs=0.01)


def test_folha_em_escala_verdadeira():
    f = Folha(100.0, 400, 0.0, 0.0)
    x0, x1 = f.ax.get_xlim()
    assert (x1 - x0) * 1000.0 / 400 == pytest.approx(LARGURA_FOLHA_MM)
    assert LARGURA_FOLHA_MM == pytest.approx(455.0 / 72.27 * 25.4)


def test_gera_todas_as_folhas_na_largura_da_pagina(pipeline, tmp_path):
    arr = arranjo_de_resultados(
        pipeline["res"], pipeline["geo"], n_eixos=9, L_T=M.L_T, H_pilar=M.H_PILAR_ALT,
        b_pilar=M.B_PILAR, h_pilar=M.H_PILAR, b_canto=M.B_PILAR_CANTO,
        h_canto=M.H_PILAR_CANTO, b_terca=M.B_TERCA, h_terca=M.H_TERCA,
        d_chu_mm=M.D_CHU_MM, h_ef_mm=M.H_EF_CHU_MM, c_borda_mm=M.C_BORDA_CHU_MM,
        h_bloco_mm=M.H_BLOCO_FUND_MM, chaveta_L_mm=M.CHAVETA_L_MM,
        chaveta_H_mm=M.CHAVETA_H_MM, classe_concreto=M.CLASSE_CONC_FUND,
        l_sela_viga_m=M.L_SELA_POR_VIGA, folga_sela_m=M.FOLGA_SELA_M,
        t_chapa_topo_mm=M.T_CHAPA_TOPO_MM, folga_oblongo_L1_mm=M.FOLGA_OBLONGO_L1_MM)
    # L1f: aço entre furos oblongos e curso maior que a flecha no ponto
    t = arr.det["L1f"]
    assert t["a2_mm"] >= 2 * t["curso_mm"] + 2.2 * t["d_mm"]
    assert t["curso_mm"] > t["w_viga_mm"]
    paths = gerar_desenhos(arr, tmp_path)
    assert len(paths) == len(FOLHAS) == 9        # + DES-09 terça–viga (issue 43)
    for p in paths:
        cab = p.read_bytes()[:4096].decode("latin-1")
        assert cab.startswith("%PDF")
        mb = [float(v) for v in cab.split("/MediaBox [")[1].split("]")[0].split()]
        assert mb[2] - mb[0] == pytest.approx(LARGURA_FOLHA_MM / 25.4 * 72, abs=0.1)
