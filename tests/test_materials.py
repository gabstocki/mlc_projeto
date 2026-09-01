"""Testes de materials.py"""
import pytest
from mlc_projeto.core.materials import GlulamMaterial, GAMMA_M


def test_f_md_positivo():
    mat = GlulamMaterial("GL28h", classe_servico=1, duracao="media")
    assert mat.f_m_d > 0


def test_gamma_M():
    assert GAMMA_M == pytest.approx(1.25)


def test_classe_invalida():
    with pytest.raises(ValueError):
        GlulamMaterial("GL99x", classe_servico=1)


def test_k_mod_cs1_media():
    mat = GlulamMaterial("GL28h", classe_servico=1, duracao="media")
    assert mat.k_mod == pytest.approx(0.80)


# ── Issue 8 — valores da EN 14080:2013 Tab. 5 (NÃO EN 1194:1999 revogada) ──────

@pytest.mark.parametrize("classe,E0mean,E005,rho_k,rho_mean,fc0", [
    ("GL20h",  8400e6,  7000e6, 340, 370, 20.0e6),
    ("GL24h", 11500e6,  9600e6, 385, 420, 24.0e6),
    ("GL28h", 12600e6, 10500e6, 425, 460, 28.0e6),
    ("GL32h", 14200e6, 11800e6, 440, 490, 32.0e6),
])
def test_en14080_tab5_modulos_densidades(classe, E0mean, E005, rho_k, rho_mean, fc0):
    """Módulos, densidades e f_c0,k conforme EN 14080:2013 Tab. 5."""
    mat = GlulamMaterial(classe, classe_servico=3, duracao="longa")
    assert mat.E0_mean == pytest.approx(E0mean)
    assert mat.E0_05   == pytest.approx(E005)
    assert mat.rho_k   == pytest.approx(rho_k)
    assert mat.rho_mean == pytest.approx(rho_mean)
    assert mat.f_c0_k  == pytest.approx(fc0)


@pytest.mark.parametrize("classe", ["GL20h", "GL24h", "GL28h", "GL32h"])
def test_en14080_constantes_por_classe(classe):
    """EN 14080:2013 Tab. 5: G_mean=650, f_v,k=3,5, f_t90,k=0,5, f_c90,k=2,5
    são constantes para todas as classes homogéneas."""
    mat = GlulamMaterial(classe, classe_servico=3, duracao="longa")
    assert mat.G_mean  == pytest.approx(650e6)
    assert mat.f_v_k   == pytest.approx(3.5e6)
    assert mat.f_t90_k == pytest.approx(0.5e6)
    assert mat.f_c90_k == pytest.approx(2.5e6)


def test_gl24h_nao_usa_valores_en1194_revogada():
    """Regressão: garante que NÃO voltaram os valores da EN 1194:1999."""
    mat = GlulamMaterial("GL24h", classe_servico=3, duracao="longa")
    assert mat.E0_mean != pytest.approx(11600e6)   # EN 1194 (revogada)
    assert mat.E0_05   != pytest.approx(9400e6)     # EN 1194 (revogada)
    assert mat.G_mean  != pytest.approx(720e6)      # EN 1194 (revogada)
