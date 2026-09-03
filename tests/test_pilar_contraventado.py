"""
tests/test_pilar_contraventado.py — issue 36.

Montante de painel de contraventamento: o download ±V_Ed·tanβ da cruz de
St. André deve entrar na verificação do pilar (compressão) e, sob uplift, a
tração líquida no membro (EC5 §6.1.2) + ancoragem.
"""

import pytest

from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.checks.elu.pilares import (
    verifica_pilar,
    verifica_pilar_contraventado,
)


def _mat():
    return GlulamMaterial("GL24h", 2, "curta")


def test_download_aumenta_compressao():
    """N_comp = R_v + Σdownload ⇒ η maior que só com R_v."""
    mat = _mat()
    eta_so_rv = verifica_pilar(mat, 0.32, 0.27, 7.0, 180.4, eixo="min")["eta"]
    r = verifica_pilar_contraventado(
        mat, 0.32, 0.27, 7.0,
        N_grav_comp_kN=180.4, N_grav_uplift_kN=180.4,
        downloads_kN=[56.5], eixo="min",
    )
    assert r["N_comp_kN"] == pytest.approx(180.4 + 56.5, rel=1e-6)
    assert r["eta_comp"] > eta_so_rv


def test_canto_soma_dois_paineis():
    """Pilar de canto integra dois painéis (long. + transv.)."""
    mat = _mat()
    r = verifica_pilar_contraventado(
        mat, 0.32, 0.27, 7.0,
        N_grav_comp_kN=180.4, N_grav_uplift_kN=3.9,
        downloads_kN=[56.5, 35.0], eixo="min",
    )
    assert r["download_total_kN"] == pytest.approx(91.5, rel=1e-6)
    assert r["N_comp_kN"] == pytest.approx(180.4 + 91.5, rel=1e-6)


def test_tracao_liquida_uplift_e_ancoragem():
    """Sob uplift: N_t = Σdownload − R_v,min (>0) = demanda de ancoragem."""
    mat = _mat()
    r = verifica_pilar_contraventado(
        mat, 0.32, 0.27, 7.0,
        N_grav_comp_kN=180.4, N_grav_uplift_kN=3.9,
        downloads_kN=[56.5, 35.0], eixo="min",
    )
    assert r["N_tracao_liq_kN"] == pytest.approx(91.5 - 3.9, rel=1e-6)
    assert r["N_ancoragem_kN"] == pytest.approx(r["N_tracao_liq_kN"], rel=1e-9)
    # σ_t,0,d = N_t/A ; η_t = σ_t,0,d / f_t,0,d
    A = 0.32 * 0.27
    sig = (91.5 - 3.9) * 1e3 / A
    assert r["eta_tracao"] == pytest.approx(sig / mat.f_t0_d, rel=1e-3)


def test_sem_tracao_quando_gravidade_supera_download():
    """Se R_v,min ≥ Σdownload não há tração líquida."""
    mat = _mat()
    r = verifica_pilar_contraventado(
        mat, 0.32, 0.27, 7.0,
        N_grav_comp_kN=180.4, N_grav_uplift_kN=200.0,
        downloads_kN=[56.5], eixo="min",
    )
    assert r["N_tracao_liq_kN"] == 0.0
    assert r["eta_tracao"] == 0.0
    assert r["regime"] == "compressao"


def test_momento_vento_agrava_flexo_compressao_e_tracao():
    """
    Pilar de canto COMBINADO: axial (grav+download) + momento de vento na face.
    O momento agrava a flexo-compressão (§6.3.2) e a flexo-tração (§6.2.3).
    """
    mat = _mat()
    sem_M = verifica_pilar_contraventado(
        mat, 0.32, 0.27, 7.0, N_grav_comp_kN=180.4, N_grav_uplift_kN=3.9,
        downloads_kN=[85.3, 32.6], eixo="min", M_vento_kNm=0.0,
    )
    com_M = verifica_pilar_contraventado(
        mat, 0.32, 0.27, 7.0, N_grav_comp_kN=180.4, N_grav_uplift_kN=3.9,
        downloads_kN=[85.3, 32.6], eixo="min", M_vento_kNm=3.0,
    )
    assert com_M["M_vento_kNm"] == pytest.approx(3.0)
    assert com_M["eta_comp"] > sem_M["eta_comp"]        # M agrava a compressão
    assert com_M["eta_tracao"] > sem_M["eta_tracao"]    # M agrava a tração
    # flexo-tração = σ_t,0,d/f_t,0,d + σ_m,d/f_m,d
    A = 0.32 * 0.27
    W = 0.32 * 0.27 ** 2 / 6.0
    Nt = (85.3 + 32.6) - 3.9
    esperado = (Nt * 1e3 / A) / mat.f_t0_d + (3.0e3 / W) / mat.f_m_d
    assert com_M["eta_tracao"] == pytest.approx(esperado, rel=1e-3)


def test_eta_governante_e_max():
    mat = _mat()
    r = verifica_pilar_contraventado(
        mat, 0.32, 0.27, 7.0,
        N_grav_comp_kN=180.4, N_grav_uplift_kN=3.9,
        downloads_kN=[56.5, 35.0], eixo="min",
    )
    assert r["eta"] == pytest.approx(max(r["eta_comp"], r["eta_tracao"]), rel=1e-9)
    assert r["ok"] == (r["eta"] <= 1.0)
