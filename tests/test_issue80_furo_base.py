"""Issue 80 — furo alargado na chapa de base, arruela-chapa e espaço para o aperto."""

import pytest

from mlc_projeto.connections.base_pilar import d0_furo_base, verificar_arruela_chapa


def test_furo_alargado_acomoda_a_tolerancia():
    assert d0_furo_base(24) == pytest.approx(24 + 2 * 6)


def test_arruela_chapa_leva_o_cortante():
    r = verificar_arruela_chapa(V_chu_kN=12.0, N_chu_kN=25.0, d_chu_mm=24)
    assert r["furo_mm"] == 26 and r["ok"] and r["eta"] < 0.1


def test_quadro_tem_furo_alargado_e_soquete():
    from pathlib import Path
    t = (Path(__file__).resolve().parent.parent / "tese" / "tab_espacamentos.tex").read_text()
    assert "43,2" in t and "soquete" in t
