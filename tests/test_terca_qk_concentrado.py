"""Issue 34 — Terça sob carga concentrada Q_k=1,0 kN (categoria H).

EN 1991-1-1 Tab. 6.10: além da UDL q_k, a cat. H prevê Q_k concentrado de
manutenção para verificação LOCAL, NÃO concomitante com a UDL (§6.3.4.2). A
combinação mais desfavorável (UDL vs Q_k) governa.
"""

import pytest

from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.checks.elu.tercas import (
    verifica_terca_carga_concentrada,
    verifica_terca,
)


MAT = GlulamMaterial("GL24h", 3, "curta")
KW = dict(L_t=5.75, s=2.53, b=0.20, h=0.58, g_k_m2=0.389)


def test_momentos_g_mais_Q():
    """M_d = γ_G·g·L²/8 + γ_Q·Q_k·L/4."""
    r = verifica_terca_carga_concentrada(MAT, Q_k_kN=1.0, **KW)
    g_lin = 0.389 * 2.53
    M_g = 1.35 * g_lin * 5.75 ** 2 / 8
    M_Q = 1.5 * 1.0 * 5.75 / 4
    assert r["M_g_kNm"] == pytest.approx(M_g, rel=1e-3)
    assert r["M_Q_kNm"] == pytest.approx(M_Q, rel=1e-3)
    assert r["M_d_kNm"] == pytest.approx(M_g + M_Q, rel=1e-3)


def test_duracao_media():
    """Carga imposta de cat. H → duração média (k_mod=0,65 em CS3)."""
    r = verifica_terca_carga_concentrada(MAT, **KW)
    assert r["duracao"] == "media"
    assert r["k_mod"] == pytest.approx(0.65, abs=1e-9)


def test_tensao_flexao_formula():
    r = verifica_terca_carga_concentrada(MAT, Q_k_kN=1.0, **KW)
    W_y = 0.20 * 0.58 ** 2 / 6
    sig = r["M_d_kNm"] * 1e3 / W_y
    assert r["sigma_m_MPa"] == pytest.approx(sig / 1e6, rel=1e-2)
    assert r["eta"] == max(r["eta_flexao"], r["eta_cisalh"])


def test_udl_governa_sobre_Qk():
    """A UDL (q_k+vento) é mais desfavorável que o Q_k concentrado."""
    r_qk = verifica_terca_carga_concentrada(MAT, Q_k_kN=1.0, **KW)
    r_udl = verifica_terca(MAT, L_t=5.75, s=2.53, b=0.20, h=0.58,
                           alpha_deg=10.0, g_k_m2=0.389, q_k_m2=0.40, w_kNm2=0.7158)
    assert r_qk["eta"] < r_udl["eta_flexao"]     # Q_k não governa a terça


def test_Qk_maior_sobe_eta():
    r1 = verifica_terca_carga_concentrada(MAT, Q_k_kN=1.0, **KW)
    r15 = verifica_terca_carga_concentrada(MAT, Q_k_kN=1.5, **KW)
    assert r15["eta"] > r1["eta"]


def test_telha_demanda_local():
    """Demanda local na telha = γ_Q·Q_k·s/4 (para confronto com ficha)."""
    r = verifica_terca_carga_concentrada(MAT, Q_k_kN=1.0, **KW)
    assert r["M_telha_d_kNm"] == pytest.approx(1.5 * 1.0 * 2.53 / 4, rel=1e-3)
    assert "fabricante" in r["nota_telha"]


def test_aprova_folgado():
    r = verifica_terca_carga_concentrada(MAT, **KW)
    assert r["ok"]
    assert r["eta"] < 0.3
    assert r["norma"].startswith("EN 1991-1-1")
