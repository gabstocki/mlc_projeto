"""Issue 7 — parcela de deformação por cisalhamento na flecha das terças
(EC5 §2.2.3(2) e Anexo B, teoria de Timoshenko)."""
import pytest

from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.checks.elu.tercas import flecha_terca, verifica_terca


def test_flecha_terca_soma_cisalhamento():
    """w = 5qL⁴/384EI + κ_s·qL²/8GA; a razão bate com 0,96·(E/G)·(h/L)²."""
    E, G = 11500e6, 650e6                                # GL24h EN 14080:2013
    L, b, h, q = 5.75, 0.20, 0.58, 4000.0
    w_flex = flecha_terca(q, L, E, b, h)                 # só flexão
    w_tot  = flecha_terca(q, L, E, b, h, G=G)            # flexão + cisalhamento
    w_cis  = w_tot - w_flex
    assert w_cis > 0
    razao      = w_cis / w_flex
    razao_form = 0.96 * (E / G) * (h / L) ** 2
    assert razao == pytest.approx(razao_form, rel=1e-6)


def test_flecha_terca_compat_sem_G():
    """Sem G, mantém a fórmula clássica de flexão (compatibilidade)."""
    E = 11500e6                                          # GL24h EN 14080:2013
    L, b, h, q = 5.75, 0.20, 0.58, 4000.0
    I = b * h**3 / 12
    assert flecha_terca(q, L, E, b, h) == pytest.approx(
        5 * q * L**4 / (384 * E * I), rel=1e-12)


def test_verifica_terca_reporta_split():
    mat = GlulamMaterial("GL24h", 3, "media")
    res = verifica_terca(
        mat, L_t=5.75, s=0.58, b=0.20, h=0.20, alpha_deg=10.0,
        g_k_m2=0.30, q_k_m2=0.40, w_kNm2=0.50,
    )
    assert res["w_inst_cis_mm"] > 0
    assert res["w_inst_mm"] == pytest.approx(
        res["w_inst_flex_mm"] + res["w_inst_cis_mm"], abs=1e-2)
    assert res["pct_cis"] > 0
