"""Issue 69 — ligação da chapa de topo / sela ao pilar e nó de topo deslizante."""

import contextlib
import io

import pytest

import mlc_projeto.main as M
from mlc_projeto.connections.ligacao_topo_pilar import (
    movimento_vertical_escora, verificar_interface_deslizante,
)


@pytest.fixture(scope="module")
def r():
    orig = M.gerar_relatorio
    M.gerar_relatorio = lambda *a, **k: {}
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            return M._main_impl(rodar_varredura=False, abrir_viz=False)
    finally:
        M.gerar_relatorio = orig


def test_tracao_vai_pelo_tirante_e_o_topo_so_posiciona(r):
    """Concepção revista: o arrancamento desce pelo tirante interno até o pilarete; o
    topo do pilar fica com duas cavilhas, que contornam o furo central e levam o
    cortante. Montantes bipartidos (issue 104): sem chapa de topo (sela entre lâminas)."""
    lt = r["ligacao_topo_pilar"]["variantes"]
    ti = r["tirante_interno"]["variantes"]
    for k in ("base_L3", "base_L3c", "base_L3f"):
        assert lt[k]["N_t_kN"] == 0.0
        assert ti[k]["N_t_kN"] == pytest.approx(r[k]["pilarete"]["N_t_kN"], abs=0.1)
        cav = lt[k]["cavilhas"]
        assert cav["n_vert"] == 2 and cav["n_pinos"] >= 2
        assert cav["a2_mm"] >= ti[k]["furo_pilar_mm"] + cav["d_mm"]   # contorna o furo
        assert lt[k]["ok"] and ti[k]["ok"]
        assert r[k]["pe_pilar"]["n_vert"] == 2           # pé também contorna o tirante


def test_movimento_vertical_da_escora():
    m = movimento_vertical_escora(h0_mm=1000.0, levantamento_mm=12.0, fluencia_mm=1.6)
    assert m["cima_mm"] == pytest.approx(12.0 + 0.0025 * 6 * 1000 + 2.0)
    assert m["baixo_mm"] == pytest.approx(0.0025 * 3 * 1000 + 1.6 + 2.0)


def test_interface_deslizante_minimo_dois_parafusos():
    x = verificar_interface_deslizante(rotulo="t", H_kN=10.0, cima_mm=29, baixo_mm=11)
    assert x["n_parafusos"] == 2 and x["comprimento_furo_mm"] == 26 + 40
