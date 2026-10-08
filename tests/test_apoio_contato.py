"""Issue 42 — reação vertical por contato direto (chapa de topo / sela) e
pinos só para o arrancamento."""
import contextlib
import io

import pytest

import mlc_projeto.main as M
from mlc_projeto.checks.elu.apoio import (
    K_C90_MLC_APOIO_DISCRETO, verifica_sela_central,
)


@pytest.fixture(scope="module")
def r():
    backup = M.gerar_relatorio
    try:
        M.gerar_relatorio = lambda *a, **k: {}
        with contextlib.redirect_stdout(io.StringIO()):
            return M._main_impl(rodar_varredura=False, abrir_viz=False)
    finally:
        M.gerar_relatorio = backup


def test_apoio_usa_a_geometria_real_do_pilar(r):
    """Antes: placa fictícia de 0,90 m sobre pilar de 0,27 m."""
    a = r["apoio"]
    assert a["l_apoio_m"] == pytest.approx(M.H_PILAR)
    assert a["l_ef_m"] == pytest.approx(M.H_PILAR + 0.030)   # +30 mm lado do vão
    assert a["k_c90"] == K_C90_MLC_APOIO_DISCRETO
    sigma = a["R_d_kN"] * 1e3 / (M.GEO_PARAMS["b"] * a["l_ef_m"]) / 1e6
    assert a["sigma_c90d_MPa"] == pytest.approx(sigma, rel=1e-3)
    assert a["eta"] < 1.0 and a["eta_sem_kc90"] < 1.0


def test_pilar_central_usa_sela(r):
    c, s = r["apoio_central"], r["sela_central"]
    assert c["l_apoio_m"] == pytest.approx(M.L_SELA_POR_VIGA)
    assert c["eta"] < 1.0
    assert s["L_sela_m"] == pytest.approx(2 * M.L_SELA_POR_VIGA + M.FOLGA_SELA_M)
    assert s["ok"] is True


def test_sela_espessura_por_flexao_do_balanco():
    s = verifica_sela_central(sigma_contato_MPa=1.0, l_apoio_viga_m=0.25,
                              h_pilar_m=0.27, folga_m=0.02)
    c = (0.52 - 0.27) / 2
    t_req = (6 * 1.0e6 * c ** 2 / 2 / 275e6) ** 0.5 * 1000
    assert s["t_req_mm"] == pytest.approx(t_req, rel=1e-3)
    assert s["t_adot_mm"] >= s["t_req_mm"]


def test_pinos_so_recebem_o_arrancamento(r):
    L1 = r["L1"]
    assert L1["apoio_por_contato"] is True
    assert L1["V_d_kN"] < L1["V_gravidade_kN"]
    assert L1["V_d_kN"] == pytest.approx(86.1, abs=0.5)


def test_fendilhamento_sem_reforco_com_grupo_no_terco_superior(r):
    f = r["fendilhamento_L1"]
    assert f["apoio_por_contato"] is True
    assert f["reforcado"] is False
    assert f["h_e_mm"] == pytest.approx(1000 - 3 * M.D_BASE_MM)
    assert f["eta"] < M.ETA_LIG_ALVO
