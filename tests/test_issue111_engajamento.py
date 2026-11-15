"""Issue 111 — engajamento sequencial dos pinos da L1/L1c sob arrancamento."""

import pytest

from mlc_projeto.connections.connections import n_ef, n_ef_angulo
from mlc_projeto.connections.oblongo_L1 import (
    espalhamento_engajamento_mm, n_fileiras_max, verificar_engajamento,
)

KW = dict(F_v_Rd_pino_kN=25.0, K_ser_plano_Nmm=8981.7, P_d_kN=100.5, d_mm=24.0,
          d0_mm=26.0, b_mm=320.0, h_mm=1000.0, k_mod=0.65, gamma_M=1.3)


def test_n_ef_interpola_entre_paralelo_e_perpendicular():
    """EC5 §8.5.1.1(4): n_ef = n ⊥ fibras; interpolação linear no ângulo."""
    n0 = n_ef(3, 76.0, 24.0)
    assert n_ef_angulo(3, 76.0, 24.0, 0.0) == pytest.approx(n0)
    assert n_ef_angulo(3, 76.0, 24.0, 90.0) == pytest.approx(3.0)
    assert n_ef_angulo(3, 76.0, 24.0, 45.0) == pytest.approx(0.5 * (n0 + 3.0))


def test_espalhamento_cresce_com_a_distancia_vertical():
    # α⊥ = 0,25 %/pp, umidade de serviço 14–19 %: 0,0125 mm por mm de altura
    assert espalhamento_engajamento_mm(72.0, tol_fab_mm=0.0) == pytest.approx(0.9)
    assert espalhamento_engajamento_mm(0.0) == pytest.approx(1.0)        # só fabricação


def test_folga_normal_admite_duas_fileiras():
    assert n_fileiras_max(72.0, 2.0) == 2
    assert n_fileiras_max(72.0, 2.0, tol_fab_mm=0.0) == 3


def test_coluna_de_seis_pinos_reprova():
    """Detalhe anterior: 6 pinos de 458 a 818 mm — Δg 5,5 mm, pino alto fora de carga."""
    ys = [818.0 - 72.0 * k for k in range(6)]
    r = verificar_engajamento(y_pinos_mm=ys, **KW)
    assert r["delta_g_mm"] == pytest.approx(5.5, abs=0.05)
    assert not r["fileira_alta_em_carga"]
    assert r["h_e_ativo_mm"] < 818.0
    assert not r["ok"]


def test_grupo_3x2_no_topo_aprova():
    ys = [818.0] * 3 + [746.0] * 3
    r = verificar_engajamento(y_pinos_mm=ys, **KW)
    assert r["delta_g_mm"] == pytest.approx(1.9, abs=0.01)
    assert r["eta"] == pytest.approx(0.95, abs=0.01)
    assert r["fileira_alta_em_carga"] and r["h_e_ativo_mm"] == 818.0
    assert r["ok"]


def test_fileira_unica_so_tem_a_fabricacao():
    r = verificar_engajamento(y_pinos_mm=[818.0] * 6, **KW)
    assert r["delta_g_umidade_mm"] == 0.0
    assert r["delta_g_mm"] == pytest.approx(1.0)


@pytest.fixture(scope="module")
def r():
    import contextlib
    import io

    import mlc_projeto.main as M
    backup = M.gerar_relatorio
    try:
        M.gerar_relatorio = lambda *a, **k: {}
        with contextlib.redirect_stdout(io.StringIO()):
            return M._main_impl(rodar_varredura=False, abrir_viz=False)
    finally:
        M.gerar_relatorio = backup


def test_projeto_adota_3x2_no_topo_nas_duas_ligacoes(r):
    for k in ("L1", "L1c"):
        assert (r[k]["n_linha"], r[k]["n_linhas"]) == (3, 2)
        assert r[k]["eta"] <= 0.75
    assert r["engajamento_L1"]["ok"]
    assert r["fendilhamento_L1"]["h_e_mm"] == pytest.approx(818.0)
    esq = r["esquadro_chapas"]
    # L1: grupo centrado na chapa sobre o pilar; L1c: a3,t da extremidade da viga
    xs = esq["L1"]["x_pinos_mm"]
    assert xs[0] + xs[-1] == pytest.approx(esq["L1"]["largura_mm"])
    assert esq["L1c"]["x_pinos_mm"][0] == pytest.approx(r["L1c"]["a3t_mm"])
    assert esq["L1c"]["largura_mm"] >= esq["L1c"]["x_pinos_mm"][-1] + 1.5 * 26.0
