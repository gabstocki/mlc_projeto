"""Issue 83 — calha central, rasgo ventilado e balanço com a seção líquida."""
import math

import pytest

from mlc_projeto.checks.calha import (
    area_contribuicao, capacidade_calha, capacidade_condutor, dimensionar_calha,
)
from mlc_projeto.checks.elu.beiral import modulo_secao_com_rasgo
from mlc_projeto.connections.oblongo_L1 import E_RASGO_VENTILACAO_MM


def test_area_de_contribuicao_nbr10844():
    # (a + h/2)·b por meia-água, duas meias-águas
    a, h = 10.125, 10.125 * math.tan(math.radians(10))
    assert area_contribuicao(L_vao_m=20.25, alpha_deg=10, comprimento_m=5.75) == \
        pytest.approx(2 * (a + h / 2) * 5.75)


def test_manning_retangular():
    S, P = 0.3 * 0.075, 0.3 + 0.15
    esperado = 60000 * S / 0.011 * (S / P) ** (2 / 3) * math.sqrt(0.005)
    assert capacidade_calha(0.30, 0.075) == pytest.approx(esperado)


def test_condutor_cresce_com_diametro_e_enchimento():
    assert capacidade_condutor(150) > capacidade_condutor(100)
    assert capacidade_condutor(100, 0.33) > capacidade_condutor(100, 0.2)


def test_calha_do_projeto_atende_e_ultimo_pano_drena():
    r = dimensionar_calha(L_vao_m=20.25, alpha_deg=10, L_T_m=5.75, s_terca_m=2.53)
    assert r["ok"] and r["eta_calha"] < 0.5 and r["eta_condutor"] <= 1.0
    assert r["inclinacao_ultimo_pano"] >= 0.05
    assert r["q_agua_kN_m"] == pytest.approx(10 * 0.30 * 0.15)


def test_modulo_com_rasgo_menor_que_bruto_e_limites():
    b, h = 0.32, 1.0
    W0 = b * h ** 2 / 6
    assert modulo_secao_com_rasgo(b, h, 0.0, 0.9) == pytest.approx(W0)
    W = modulo_secao_com_rasgo(b, h, 0.029, 0.892)
    assert 0.85 * W0 < W < W0
    # rasgo em toda a altura = seção retangular de largura b − t_r
    assert modulo_secao_com_rasgo(b, h, 0.029, h) == pytest.approx((b - 0.029) * h ** 2 / 6)


def test_rasgo_prolongado_alem_das_faces():
    assert E_RASGO_VENTILACAO_MM >= 20.0
