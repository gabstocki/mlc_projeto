"""Testes de geometry.py"""
import numpy as np
import pytest
from mlc_projeto.core.geometry import GeometriaViga


def test_h_apoio():
    geo = GeometriaViga(L=40.5, h0=1.62, alpha_deg=5.0, b=0.20)
    assert geo.h(0) == pytest.approx(geo.h0, rel=1e-6)


def test_h_cumeeira():
    geo = GeometriaViga(L=40.5, h0=1.62, alpha_deg=5.0, b=0.20)
    assert geo.h(geo.L / 2) == pytest.approx(geo.h_ap, rel=1e-3)


def test_simetria():
    geo = GeometriaViga(L=40.5, h0=1.62, alpha_deg=5.0, b=0.20)
    assert geo.h(5.0) == pytest.approx(geo.h(geo.L - 5.0), rel=1e-9)


def test_I_positivo():
    geo = GeometriaViga(L=40.5, h0=1.62, alpha_deg=5.0, b=0.20)
    assert np.all(geo.I(geo.x) > 0)
