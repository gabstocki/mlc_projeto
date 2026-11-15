"""Issue 86 — proteção contra corrosão: respiro do pilarete e nota nos desenhos."""
import pytest

from mlc_projeto.connections.pilarete import (
    D_FURO_RESPIRO_MM, N_FUROS_RESPIRO_SECAO, propriedades_chs, verificar_pilarete,
)
from mlc_projeto.output.desenhos import Folha


def _pil(N_t):
    return verificar_pilarete(rotulo="t", N_c_kN=340, N_t_kN=N_t, V_kN=48.5, h_m=0.30,
                              b_pilar_mm=320, h_pilar_mm=270)


def test_secao_liquida_dos_respiros_reduz_area():
    r = _pil(327)
    A = propriedades_chs(r["D_mm"], r["t_mm"])["A"]
    esperado = A - N_FUROS_RESPIRO_SECAO * D_FURO_RESPIRO_MM * r["t_mm"]
    assert r["A_net_mm2"] == pytest.approx(esperado, abs=1)
    assert r["furos_respiro"] == "4×Ø16 mm"


def test_secao_liquida_governa_tubo_e_cresce_com_tracao():
    a, b = _pil(100), _pil(327)
    for r in (a, b):
        assert r["etas"]["secao_liquida_respiro"] >= r["etas"]["tracao"]
        assert r["etas"]["secao_liquida_respiro"] <= 0.90
    assert b["etas"]["secao_liquida_respiro"] > a["etas"]["secao_liquida_respiro"]


def test_nota_de_protecao_cita_galvanizacao_e_duplex():
    n = Folha.NOTA_CORROSAO
    assert "EN ISO 1461" in n and "EN ISO 10684" in n and "dúplex" in n
