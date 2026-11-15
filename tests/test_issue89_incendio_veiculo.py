"""Issue 89 — incêndio localizado de veículo: Anexo C, pilar e pilarete."""
import math

import pytest

from mlc_projeto.checks.elu.incendio_veiculo import (
    avaliar_incendio_veiculo, chama_localizada, k_y_theta, temperatura_aco_sem_protecao,
    temperatura_critica, temperatura_pluma,
)
from mlc_projeto.core.materials import GlulamMaterial


def test_anexo_c_chama_e_pluma():
    D, Q = 3.21, 8.3e6
    c = chama_localizada(Q, D)
    assert c["L_f_m"] == pytest.approx(-1.02 * D + 0.0148 * Q ** 0.4)
    T = temperatura_pluma(Q, D, 6.5)
    assert T == pytest.approx(20 + 0.25 * (0.8 * Q) ** (2 / 3) * (6.5 - c["z0_m"]) ** (-5 / 3))
    assert temperatura_pluma(Q, D, 0.5) == 900.0          # teto da Eq. C.2


def test_temperatura_critica_eq_4_22():
    mu0 = 0.0844
    esperado = 39.19 * math.log(1 / (0.9674 * mu0 ** 3.833) - 1) + 482
    assert temperatura_critica(mu0) == pytest.approx(esperado)
    assert temperatura_critica(0.6) == pytest.approx(554, abs=2)   # valor de tabela


def test_flambagem_em_incendio_reduz_resistencia():
    from mlc_projeto.checks.elu.incendio_veiculo import N_b_fi_Rd, k_E_theta
    A = math.pi / 4 * (139.7 ** 2 - 123.7 ** 2)
    i = math.sqrt((139.7 ** 2 + 123.7 ** 2) / 16)
    N = N_b_fi_Rd(750, A=A, i=i, l_cr=600, f_y=355)
    assert N < A * k_y_theta(750) * 355 / 1e3          # χ_fi < 1 mesmo sem patamar
    assert k_E_theta(700) == pytest.approx(0.13)


def test_aco_sem_protecao_aquece_e_ky():
    assert 750 < temperatura_aco_sem_protecao(30, 125) < 850
    assert k_y_theta(400) == 1.0 and k_y_theta(700) == pytest.approx(0.23)


def test_projeto_madeira_robusta_e_pilarete_exige_protecao():
    mat = GlulamMaterial("GL24h", 3, "curta")
    r = avaliar_incendio_veiculo(mat=mat, h_forro_m=7.0, pilarete=(139.7, 8.0), pilares=(
        dict(b=0.32, h=0.27, H_col_m=6.7, N_fi_kN=99.2, nome="central"),))
    p = r["pilares"][0]
    assert not r["chama_alcanca_forro"]
    assert p["t_colapso_min"]["4 faces"] > r["t_exposicao_min"]
    assert p["pilarete"]["eta_sem_protecao_n"] > 1.0          # sem proteção não resiste
    assert p["pilarete"]["eta"] < 1.0 and r["ok"]             # com intumescente R60
