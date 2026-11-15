"""Issue 79 — furos das chapas com folga: d0 = d + Δ (EN 1090-2 Tab. 11)."""

import pytest

from mlc_projeto.connections.chapas_aco import d0_furo, folga_furo_mm, verificar_chapas_aco


@pytest.mark.parametrize("d, d0", [(8, 9), (12, 13), (16, 18), (20, 22), (24, 26), (27, 30), (30, 33)])
def test_d0_en1090(d, d0):
    assert d0_furo(d) == d0


@pytest.mark.parametrize("d", [8, 12, 16, 20, 24, 30, 36])
def test_folga_dentro_do_limite_ec5_10_4_3(d):
    assert folga_furo_mm(d) <= max(2.0, 0.1 * d) + 1e-9


def test_bearing_usa_d0_com_folga():
    """k1 e α_b da Tab. 3.4 caem com d0 > d; a verificação publica d0."""
    kw = dict(F_res_kN=80.0, N_ax_kN=0.0, d_mm=24.0, n_pinos=5, n_linha=1, n_linhas=5,
              h_grupo_mm=600.0, h_disp_mm=1000.0, theta_deg=84.0, t_p_mm=25.0)
    r = verificar_chapas_aco(**kw)
    assert r["d0_mm"] == 26.0


def test_quadro_L1_e4_com_d0():
    """O e4 exigido da chapa da L1 é 1,5·d0 = 39 mm para Ø24 (antes 36 com d0 = d)."""
    assert 1.5 * d0_furo(24.0) == pytest.approx(39.0)
