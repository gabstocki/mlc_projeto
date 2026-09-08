"""
Testes de regressão — F-11 (auditoria adversarial v2).

Achado
------
`_n_t_rd_kN` devolvia só `N_pl,Rd = A·f_y/γ_M0`, sobre a área BRUTA. A
EN 1993-1-1 §6.2.3(2) exige

    N_t,Rd = min( N_pl,Rd = A·f_y/γ_M0 ;  N_u,Rd = 0,9·A_net·f_u/γ_M2 )

As diagonais são barras redondas roscadas nas extremidades: a secção líquida é
a área resistente da rosca `A_s`, ~81 % da bruta. Para Ø33 em S235 a rotura da
secção líquida (179,7 kN) governa sobre a plastificação (201,0 kN) — 10,6 %
abaixo do que era calculado.

As LIGAÇÕES DE EXTREMIDADE das diagonais continuam por dimensionar; passa a ser
declarado no resultado em vez de omitido.
"""
import math

import pytest

from mlc_projeto.checks.elu.contraventamento_vertical import (
    GAMMA_M0, GAMMA_M2, PASSO_ROSCA_MM, _n_t_rd_kN, area_resistente_rosca,
    escolher_diametro, verifica_painel_vertical,
)


def _As(d):
    p = PASSO_ROSCA_MM[d]
    return math.pi / 4 * (d - 0.9382 * p) ** 2


@pytest.mark.parametrize("d", [16.0, 24.0, 33.0, 45.0])
def test_area_resistente_da_rosca(d):
    assert area_resistente_rosca(d) == pytest.approx(_As(d), rel=1e-9)
    assert 0.70 < area_resistente_rosca(d) / (math.pi * d ** 2 / 4) < 0.85


def test_n_t_rd_e_o_minimo_dos_dois_modos(aco="S235"):
    for d in (16.0, 24.0, 33.0, 45.0):
        A = math.pi * d ** 2 / 4
        npl = A * 235.0 / GAMMA_M0 / 1e3
        nu = 0.9 * _As(d) * 360.0 / GAMMA_M2 / 1e3
        assert _n_t_rd_kN(d, aco) == pytest.approx(min(npl, nu), rel=1e-9)


def test_secao_liquida_governa_no_S235():
    d = 33.0
    A = math.pi * d ** 2 / 4
    npl = A * 235.0 / 1e3
    nu = 0.9 * _As(d) * 360.0 / 1.25 / 1e3
    assert nu < npl
    assert _n_t_rd_kN(d, "S235") == pytest.approx(nu, rel=1e-9)
    assert nu / npl == pytest.approx(0.894, abs=0.01)


def test_resistencia_e_menor_que_a_da_area_bruta():
    """A correção só pode REDUZIR a resistência — nunca aumentá-la."""
    for d in (12.0, 20.0, 30.0, 45.0, 64.0):
        bruta = (math.pi * d ** 2 / 4) * 235.0 / 1e3
        assert _n_t_rd_kN(d, "S235") <= bruta + 1e-9


def test_diametro_desconhecido_falha_alto():
    """Sem passo de rosca tabelado não se pode inventar a área líquida."""
    with pytest.raises(Exception):
        area_resistente_rosca(37.0)


def test_escolher_diametro_respeita_o_alvo_com_a_nova_resistencia():
    d = escolher_diametro(150.0, aco="S235", eta_alvo=0.90)
    assert 150.0 / _n_t_rd_kN(d, "S235") <= 0.90 + 1e-9


def test_painel_declara_os_dois_modos_e_a_ligacao_pendente():
    r = verifica_painel_vertical(V_Ed_kN=100.0, H_col_m=7.0, b_baia_m=5.75,
                                 d_mm=33.0, aco="S235")
    assert r["N_pl_Rd_kN"] > r["N_u_Rd_kN"]
    assert r["N_t_Rd_kN"] == pytest.approx(r["N_u_Rd_kN"])
    assert r["modo_tracao_gov"] == "secao_liquida"
    assert r["A_net_mm2"] < r["A_mm2"]
    assert "ligações de extremidade" in r["pendente"].lower()
