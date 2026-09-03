"""Issue 16 (follow-up) — Viga: forma LINEAR de 6.23/6.24 (§6.3.2) e 6.35 (§6.3.3).

Em §6.3.2 o termo de compressão é linear (÷k_c); a forma quadrática é de §6.2.4
(só λ_rel≤0,3). Em §6.3.3 (6.35) é o termo de FLEXÃO que é ao quadrado.
"""

import pytest

from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.wind import ParametrosVento
from mlc_projeto.core.loads import carregamentos_com_vento
from mlc_projeto.checks.elu.flexao import verifica_flexao, K_M


def _r():
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
    mat = GlulamMaterial("GL24h", 3, "curta")
    pv = ParametrosVento(V0=45, S1=1, categoria="IV", classe="B", S3=1,
                         L=20.25, H1=geo.h_ap - geo.h0, h=7, dist_portico=5.75)
    load = carregamentos_com_vento(geo=geo, mat=mat, g_area=0.823, q_area=0.40,
                                   L_t=5.75, params_vento=pv)
    gov = load.combinacao_ELU_governante()
    return verifica_flexao(geo, mat.com_duracao(gov.duracao), load, s=2.53)


def test_623_624_compressao_linear():
    """η_6.23 = σ_c/(k_c,y·f_c0d) + σ_m/f_md (compressão LINEAR)."""
    r = _r()
    sc, sm = r["sigma_c_MPa"], r["sigma_m_MPa"]
    fc, fm = r["f_c0d_MPa"], r["f_md_MPa"]
    e623 = sc / (r["k_c_y"] * fc) + sm / fm
    e624 = sc / (r["k_c_z"] * fc) + K_M * sm / fm
    assert r["eta_no_plano"] == pytest.approx(e623, rel=1e-3)
    assert r["eta_fora_plano"] == pytest.approx(e624, rel=1e-3)


def test_nao_e_quadratico_na_compressao():
    """A forma antiga (compressão ao quadrado) daria η menor — não deve bater."""
    r = _r()
    sc, fc, fm, sm = r["sigma_c_MPa"], r["f_c0d_MPa"], r["f_md_MPa"], r["sigma_m_MPa"]
    e623_quad = (sc / (r["k_c_y"] * fc)) ** 2 + sm / fm
    # o termo linear é maior que o quadrático (razão < 1) → η atual > forma antiga
    assert r["eta_no_plano"] > e623_quad + 1e-6


def test_635_flexao_ao_quadrado_compressao_linear():
    """η_6.35 = (σ_m/(k_crit·f_md))² + σ_c/(k_c,z·f_c0d)."""
    r = _r()
    sc, sm = r["sigma_c_MPa"], r["sigma_m_MPa"]
    fc, fm = r["f_c0d_MPa"], r["f_md_MPa"]
    e635 = (sm / (r["k_crit"] * fm)) ** 2 + sc / (r["k_c_z"] * fc)
    assert r["eta_635"] == pytest.approx(e635, rel=1e-3)


def test_viga_ainda_aprova():
    r = _r()
    assert r["ok"]
    assert r["eta"] < 1.0
