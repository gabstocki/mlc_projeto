"""Issue 76 — pé do pilar sob o choque: a4,t, fendilhamento, seção líquida, fora do plano."""

import contextlib
import io

import pytest

import mlc_projeto.main as M
from mlc_projeto.connections.retracao import n_perp_max_borda_carregada


@pytest.fixture(scope="module")
def r():
    orig = M.gerar_relatorio
    M.gerar_relatorio = lambda *a, **k: {}
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            return M._main_impl(rodar_varredura=False, abrir_viz=False)
    finally:
        M.gerar_relatorio = orig


def test_a4t_limita_fileiras():
    assert n_perp_max_borda_carregada(20, 60, 270, 80) == 2      # (270 − 160)//60 + 1
    assert n_perp_max_borda_carregada(20, 60, 320, 80) == 3


@pytest.mark.parametrize("k", ["base_L3", "base_L3c", "base_L3f", "base_L3a_canto",
                               "base_L3a_central"])
def test_pe_atende_a4t_e_modos_novos(r, k):
    b = r[k]
    assert b["a4t_adot_mm"] >= b["a4t_req_mm"]
    assert b["fendilhamento_pe"]["eta"] <= 0.75
    assert b["secao_liquida_pe"]["eta"] <= 1.0 and b["choque_fora_plano_pe"]["eta"] <= 1.0
    assert b["fendilhamento_pe"]["gamma_M"] == 1.0                 # acidental
