"""
Testes de regressão — F-05 (auditoria adversarial v2).

Achado
------
`distancias_minimas` implementava a distância à **borda carregada** como
`a4,t = 3d`, omitindo o termo dependente do ângulo da EC5 **Tabela 8.5**
(cavilhas, §8.6):

    a4,t = max( (2 + 2·sen α)·d ; 3d )        0° ≤ α ≤ 180°

Com d = 24 mm e α ≈ 85° (a resultante na base é dominada pelo cortante), o valor
exigido é 95,8 mm contra os 72,0 mm adotados — **déficit de 24,9 %** justamente
no parâmetro que controla o FENDILHAMENTO, modo frágil que neste projeto já
precisa de reforço (§8.7.2) para descer de η = 1,042 para 0,722.

Nota de não-confusão: em cavilhas (Tab. 8.5) `a3,c = 3d` em todo o intervalo
90°–270°; é nos **parafusos** (Tab. 8.4) que `a3,c` ganha o fator `|sen α|`.
Este teste fixa a distinção para que a correção de a4,t não arraste a3,c.
"""
import math

import pytest

from mlc_projeto.connections.connections import (
    distancias_minimas,
    verificar_geometria_grupo,
)


# ── a4,t — EC5 Tab. 8.5 ──────────────────────────────────────────────────────

@pytest.mark.parametrize("d", [8.0, 12.0, 16.0, 24.0, 30.0])
@pytest.mark.parametrize("alpha", [0.0, 15.0, 30.0, 45.0, 60.0, 75.0, 90.0])
def test_a4t_segue_a_tabela_8_5(d, alpha):
    esperado = max((2.0 + 2.0 * abs(math.sin(math.radians(alpha)))) * d, 3.0 * d)
    assert distancias_minimas(d, theta_deg=alpha)["a4t_mm"] == pytest.approx(
        round(esperado, 1), abs=0.05
    )


def test_a4t_nos_extremos():
    """α=0° cai no piso 3d; α=90° dá 4d."""
    assert distancias_minimas(24.0, theta_deg=0.0)["a4t_mm"] == pytest.approx(72.0)
    assert distancias_minimas(24.0, theta_deg=90.0)["a4t_mm"] == pytest.approx(96.0)


def test_a4t_cresce_com_o_angulo():
    vals = [distancias_minimas(24.0, theta_deg=a)["a4t_mm"]
            for a in (0, 20, 40, 60, 80, 90)]
    assert all(b >= a for a, b in zip(vals, vals[1:]))
    assert vals[-1] > vals[0]


def test_a4t_do_caso_de_projeto():
    """d = 24 mm, α = 84,96° → 95,8 mm (o código adotava 72,0 mm)."""
    alpha = math.degrees(math.atan2(99.2225, 8.7478))
    a4t = distancias_minimas(24.0, theta_deg=alpha)["a4t_mm"]
    assert a4t == pytest.approx(95.8, abs=0.1)
    assert a4t > 3 * 24.0


def test_a4t_e_envelope_conservador_para_qualquer_alfa():
    """|sen α| garante o valor da borda carregada em qualquer quadrante."""
    for a in (85.0, 95.0, 265.0, 275.0):
        assert distancias_minimas(24.0, theta_deg=a)["a4t_mm"] == pytest.approx(
            95.8, abs=0.1)


# ── as restantes distâncias NÃO mudam ────────────────────────────────────────

def test_a1_a2_a3t_inalterados():
    for a in (0.0, 45.0, 84.96, 90.0):
        d = distancias_minimas(24.0, theta_deg=a)
        assert d["a1_mm"] == pytest.approx(
            round((3 + 2 * abs(math.cos(math.radians(a)))) * 24.0, 1), abs=0.05)
        assert d["a2_mm"] == pytest.approx(72.0)
        assert d["a3t_mm"] == pytest.approx(168.0)


def test_a3c_de_cavilha_e_3d_em_todo_o_intervalo():
    """Tab. 8.5 (cavilhas): a3,c = 3d — NÃO é a regra dos parafusos (Tab. 8.4)."""
    for a in (0.0, 45.0, 84.96, 90.0, 180.0):
        assert distancias_minimas(24.0, theta_deg=a)["a3c_mm"] == pytest.approx(72.0)


def test_a4c_e_3d():
    assert distancias_minimas(24.0, theta_deg=84.96)["a4c_mm"] == pytest.approx(72.0)


# ── o grupo de pinos consome a distância corrigida ───────────────────────────

def test_geometria_do_grupo_usa_a4t_corrigido():
    alpha = math.degrees(math.atan2(99.2225, 8.7478))
    g = verificar_geometria_grupo(
        n_horiz=1, n_vert=7, d_mm=24.0, h0_mm=1000.0, theta_deg=alpha,
    )
    a4t = distancias_minimas(24.0, theta_deg=alpha)["a4t_mm"]
    assert g["a4t_mm"] == pytest.approx(a4t)
    assert g["h_ocupado_mm"] == pytest.approx(2 * a4t + 6 * 72.0, abs=0.2)


def test_layout_do_projeto_continua_a_caber_na_secao():
    """A correção é de detalhamento: 7 pinos em h0 = 1,00 m continuam a caber."""
    alpha = math.degrees(math.atan2(99.2225, 8.7478))
    g = verificar_geometria_grupo(
        n_horiz=1, n_vert=7, d_mm=24.0, h0_mm=1000.0, theta_deg=alpha,
    )
    assert g["ok_geometria"] is True
    assert g["h_ocupado_mm"] < 1000.0


def test_a4t_maior_reduz_o_numero_de_fileiras_admissiveis():
    """Contrato mecânico: mais borda exigida ⇒ não mais fileiras do que antes."""
    paralelo = verificar_geometria_grupo(
        n_horiz=1, n_vert=1, d_mm=24.0, h0_mm=400.0, theta_deg=0.0)
    perpend = verificar_geometria_grupo(
        n_horiz=1, n_vert=1, d_mm=24.0, h0_mm=400.0, theta_deg=90.0)
    assert perpend["n_vert_max"] <= paralelo["n_vert_max"]
