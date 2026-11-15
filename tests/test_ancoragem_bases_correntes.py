"""Issue 48 — bases correntes L3/L3c: arrancamento de sucção e impacto de veículo.

Antes, L3 só via o empuxo de arco (nulo na Opção B) e saía com η = 0,0000."""
import contextlib
import io

import pytest

import mlc_projeto.main as M
from mlc_projeto.connections.ancoragem import verificar_base_corrente


@pytest.fixture(scope="module")
def r():
    backup = M.gerar_relatorio
    try:
        M.gerar_relatorio = lambda *a, **k: {}
        with contextlib.redirect_stdout(io.StringIO()):
            return M._main_impl(rodar_varredura=False, abrir_viz=False)
    finally:
        M.gerar_relatorio = backup


def test_duas_situacoes_nao_concomitantes():
    b = verificar_base_corrente(
        rotulo="t", N_t_persistente_kN=80.0, V_persistente_kN=2.0,
        V_acidental_kN=46.4, dados_concreto=M.DADOS_ANCORAGEM)
    p, a = b["casos"]["persistente_succao"], b["casos"]["acidental_impacto"]
    assert p["N_Ed_kN"] == pytest.approx(80.0) and p["V_Ed_kN"] == pytest.approx(2.0)
    assert a["N_Ed_kN"] == 0.0 and a["V_Ed_kN"] == pytest.approx(46.4)
    assert a["V_nos_chumbadores_kN"] == pytest.approx(46.4)   # sem chaveta
    assert b["eta"] == max(p["eta"], a["eta"])


def test_L3_nao_sai_mais_com_eta_nulo(r):
    L3 = r["L3"]
    assert L3["eta"] > 0.0
    assert L3["eta"] == pytest.approx(max(L3["eta_N"], L3["eta_ancoragem"]), abs=1e-4)
    assert L3["eta"] <= L3["eta_limite"]


def test_L3_recebe_arrancamento_e_impacto(r):
    a = r["ancoragem_L3"]
    assert a["N_t_persistente_kN"] == pytest.approx(
        r["succao_uplift"]["N_uplift_ext_kN"], abs=0.01)
    # choque a 0,50 m do piso; com o pilarete (issue 87) a madeira começa a 0,30 m
    # e mede 6,70 m: R_base = F·(6,70 − 0,20)/6,70
    assert a["V_acidental_kN"] == pytest.approx(50.0 * 6.5 / 6.7, abs=0.05)
    assert a["ok"] is True


def test_L3c_central_tambem_verificada(r):
    a = r["ancoragem_L3c"]
    assert a["N_t_persistente_kN"] == pytest.approx(
        r["succao_uplift"]["N_uplift_cen_kN"], abs=0.01)
    assert r["L3c"]["eta"] >= a["eta"] - 1e-9


def test_quadro_fundacao_publica_o_cortante_das_bases_correntes(r):
    linhas = {l["Base"]: l for l in r["cargas_fundacao"]["linhas"]}
    assert linhas["Extremidade (pilar lateral)"]["H (kN)"] == pytest.approx(48.5, abs=0.1)
    assert linhas["Central (pilar do apoio partilhado)"]["H (kN)"] == pytest.approx(48.5, abs=0.1)
