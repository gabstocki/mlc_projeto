"""Issue 32 — Elemento de beiral como corda do diafragma de cobertura.

A terça de beiral atua como banzo do diafragma: força axial N_corda (± com o
vento) + flexão local. Verificada em flexo-compressão (§6.3.2) e flexo-tração
(§6.2.3); continuidade das emendas obrigatória.
"""

import pytest

from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.checks.elu.corda_beiral import verificar_corda_beiral


MAT = GlulamMaterial("GL24h", 3, "curta")
KW = dict(
    L_t=5.75, s_eave=2.53 / 2, b=0.20, h=0.58, alpha_deg=10.0,
    g_k_m2=0.389, q_k_m2=0.40, w_kNm2=0.7158, L_comp=46.0,
)


def test_verifica_ambos_os_sinais():
    """A corda inverte de sinal → verifica flexo-compressão E flexo-tração."""
    r = verificar_corda_beiral(MAT, N_corda_kN=7.6, **KW)
    assert "eta_compressao" in r and "eta_tracao" in r
    assert r["eta"] == max(r["eta_compressao"], r["eta_tracao"])
    assert r["caso_gov"].startswith("flexo")


def test_sigma_axial_formula():
    """σ_N = |N_corda|/A."""
    r = verificar_corda_beiral(MAT, N_corda_kN=7.6, **KW)
    A = KW["b"] * KW["h"]
    assert r["sigma_N_MPa"] == pytest.approx(7.6e3 / A / 1e6, rel=1e-3)


def test_flexo_tracao_usa_ft0d():
    """Termo axial de tração usa f_t0d (não f_c0d): recalcula Eq.6.17."""
    r = verificar_corda_beiral(MAT, N_corda_kN=7.6, **KW)
    sig_N = r["sigma_N_MPa"]
    smy = r["sigma_my_MPa"]
    smz = r["sigma_mz_MPa"]
    fmd = r["f_md_MPa"]
    ft0d = r["f_t0d_MPa"]
    e617 = sig_N / ft0d + smy / fmd + 0.7 * smz / fmd
    assert r["eta_tract_617"] == pytest.approx(e617, rel=1e-2)


def test_axial_maior_sobe_eta():
    """N_corda maior → maior η (termo axial cresce)."""
    r1 = verificar_corda_beiral(MAT, N_corda_kN=5.0, **KW)
    r2 = verificar_corda_beiral(MAT, N_corda_kN=50.0, **KW)
    assert r2["eta"] > r1["eta"]


def test_emendas_continuidade():
    """N.º de emendas = ceil(L_comp/L_barra) − 1; cada uma transfere N_corda."""
    r = verificar_corda_beiral(MAT, N_corda_kN=7.6, L_barra_m=11.75, **KW)
    import math
    n = math.ceil(46.0 / 11.75) - 1
    assert r["n_emendas"] == n
    assert r["F_emenda_kN"] == pytest.approx(7.6, rel=1e-3)
    assert "CONTÍNUA" in r["nota_emenda"]


def test_corda_leve_aprova():
    """Com N_corda pequeno (~7,6 kN) e seção de terça, a corda passa folgada."""
    r = verificar_corda_beiral(MAT, N_corda_kN=7.6, **KW)
    assert r["ok"]
    assert r["eta"] < 0.5
    assert r["norma"].startswith("EC5 §6.3.2")
