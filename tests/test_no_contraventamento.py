"""Issue 66 — reação longitudinal da treliça de cobertura: escora (terça sobre
o apoio) até o nó metálico do topo do pilar, sem passar pela L1/L1c."""
import contextlib
import io

import pytest

import mlc_projeto.main as M
from mlc_projeto.checks.elu.no_contraventamento import dimensionar_ligacao_axial_escora
from mlc_projeto.connections.connections import n_ef


@pytest.fixture(scope="module")
def r():
    backup = M.gerar_relatorio
    try:
        M.gerar_relatorio = lambda *a, **k: {}
        with contextlib.redirect_stdout(io.StringIO()):
            return M._main_impl(rodar_varredura=False, abrir_viz=False)
    finally:
        M.gerar_relatorio = backup


def test_forcas_nas_escoras(r):
    nc = r["no_contraventamento"]
    cvv, cvc = r["contraventamento_vertical"], r["contraventamento_vertical_central"]
    assert nc["N_escora_beiral_kN"] == pytest.approx(cvv["V_painel_kN"], abs=0.01)
    assert nc["N_escora_central_kN"] == pytest.approx(
        2 * cvc["V_painel_kN"], abs=0.01)          # 2 painéis por extremidade


def test_escoras_e_ligacoes_passam(r):
    nc = r["no_contraventamento"]
    assert nc["ok"] is True
    for k in ("ligacao_escora_beiral", "ligacao_escora_central"):
        assert nc[k]["eta"] <= 0.75 + 1e-9         # modo frágil


def test_ligacao_axial_resistencia_coerente():
    mat = M.GlulamMaterial(**M.MAT_CURTA)
    lig = dimensionar_ligacao_axial_escora(100.0, mat, 0.20, 0.58, d_mm=20)
    R = lig["n_vert"] * n_ef(lig["n_horiz"], lig["a1_mm"], 20) * lig["F_v_Rd_pino_kN"]
    assert lig["R_d_kN"] == pytest.approx(R, rel=1e-3)
    assert 100.0 / lig["R_d_kN"] <= 0.75 + 1e-9
    # cabe na altura da terça
    assert 2 * lig["a4c_mm"] + (lig["n_vert"] - 1) * lig["a2_mm"] <= 580 + 1e-6
