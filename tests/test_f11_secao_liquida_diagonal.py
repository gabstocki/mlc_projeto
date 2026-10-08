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

Issue 44: o projeto passou a especificar extremidades RECALCADAS, em que a rosca
é maior que o fuste e N_u,Rd ≥ N_pl,Rd. Os testes abaixo fixam o caso de ROSCA
CORTADA (recalcada=False), que continua a ser o comportamento de F-11.
"""
import math

import pytest

from mlc_projeto.checks.elu.contraventamento_vertical import (
    GAMMA_M0, GAMMA_M2, PASSO_ROSCA_MM, _n_t_rd_kN, area_resistente_rosca,
    escolher_diametro, resistencia_tracao_diagonal, verifica_painel_vertical,
)


def _nt_cortada(d, aco="S235"):
    return resistencia_tracao_diagonal(d, aco, recalcada=False)["N_t_Rd_kN"]


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
        assert _nt_cortada(d, aco) == pytest.approx(min(npl, nu), rel=1e-9)


def test_secao_liquida_governa_no_S235():
    d = 33.0
    A = math.pi * d ** 2 / 4
    npl = A * 235.0 / 1e3
    nu = 0.9 * _As(d) * 360.0 / 1.25 / 1e3
    assert nu < npl
    assert _nt_cortada(d, "S235") == pytest.approx(nu, rel=1e-9)
    assert nu / npl == pytest.approx(0.894, abs=0.01)


def test_resistencia_e_menor_que_a_da_area_bruta():
    """A correção só pode REDUZIR a resistência — nunca aumentá-la."""
    for d in (12.0, 20.0, 30.0, 45.0, 64.0):
        bruta = (math.pi * d ** 2 / 4) * 235.0 / 1e3
        assert _nt_cortada(d, "S235") <= bruta + 1e-9
        assert _n_t_rd_kN(d, "S235") <= bruta + 1e-9   # recalcada: = N_pl


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
    # Issue 44: extremidade recalcada (M36 sobre Ø33) → governa o escoamento
    assert r["extremidade_recalcada"] is True
    assert r["d_rosca_mm"] == 36
    assert r["N_u_Rd_kN"] >= r["N_pl_Rd_kN"]
    assert r["N_t_Rd_kN"] == pytest.approx(r["N_pl_Rd_kN"])
    assert r["modo_tracao_gov"] == "plastificacao"
    assert r["A_net_mm2"] < r["A_mm2"]
    assert "ligações de extremidade" in r["pendente"].lower()


# ── Issue 44 — extremidades recalcadas e critério único ───────────────────────

@pytest.mark.parametrize("d,rosca", [(24, 27), (27, 30), (28, 30), (33, 36), (36, 39)])
def test_rosca_recalcada_minima_garante_ductilidade(d, rosca):
    """EN 1993-1-1 §6.2.3(3): N_u,Rd(rosca) ≥ N_pl,Rd(fuste)."""
    from mlc_projeto.checks.elu.contraventamento_vertical import rosca_recalcada_minima
    assert rosca_recalcada_minima(d, "S235") == rosca
    r = resistencia_tracao_diagonal(d, "S235")
    assert r["ductil"] is True and r["modo_tracao_gov"] == "plastificacao"


def test_rosca_cortada_m36_rompe_antes_de_escoar():
    """O apontamento do orientador: M36 cortada, 211,7 < 239 kN."""
    r = resistencia_tracao_diagonal(36, "S235", recalcada=False)
    assert r["N_u_Rd_kN"] == pytest.approx(211.7, abs=0.1)
    assert r["N_pl_Rd_kN"] == pytest.approx(239.2, abs=0.1)
    assert r["ductil"] is False


def test_cobertura_usa_o_mesmo_criterio():
    from mlc_projeto.checks.elu.contraventamento import verificar_diagonal_aco
    b = verificar_diagonal_aco(F_diag_kN=100.0, d_mm=28.0, L_diag_m=6.28,
                               cos_theta=0.915, aco="S235")
    r = resistencia_tracao_diagonal(28.0, "S235")
    assert b["N_t_Rd_kN"] == pytest.approx(r["N_t_Rd_kN"], rel=1e-6)
    assert b["d_rosca_mm"] == 30
