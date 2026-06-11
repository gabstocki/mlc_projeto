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
