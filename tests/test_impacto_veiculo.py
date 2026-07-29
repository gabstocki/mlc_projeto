"""Testes — impacto de veículo em pilares de estacionamento."""
import pytest

from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.wind import ParametrosVento
from mlc_projeto.core.loads import carregamentos_com_vento
from mlc_projeto.checks.elu.impacto_veiculo import (
    esforcos_pilar_impacto,
    verificar_impacto_veiculo,
    F_DX_KN,
    F_DY_KN,
)


def test_momento_impacto_biarticulado():
    """M = F·h·(H−h)/H no ponto de aplicação."""
    r = esforcos_pilar_impacto(F_kN=50.0, H_m=7.0, h_imp_m=0.5)
    assert r["M_max_kNm"] == pytest.approx(50.0 * 0.5 * 6.5 / 7.0, rel=1e-3)
    assert r["R_base_kN"] + r["R_topo_kN"] == pytest.approx(50.0, rel=1e-6)


def test_impacto_aplicavel_estacionamento_R2():
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.30)
    mat = GlulamMaterial("GL24h", 3, "curta")
    pv = ParametrosVento(
        V0=45.0, S1=1.0, categoria="IV", classe="B", S3=1.0,
        L=20.25, H1=1.785, h=7.0, dist_portico=5.75,
    )
    load = carregamentos_com_vento(
        geo, mat, 1.5, 0.25, 5.75, pv, b_pilar=0.22, h_pilar=0.26,
    )
    res = verificar_impacto_veiculo(
        geo, mat, load,
        b_pilar=0.22, h_pilar=0.26,
        b_pilar_c=0.28, h_pilar_c=0.28,
        H_pilar_m=7.0,
    )
    assert res["aplicavel"] is True
    assert res["forcas"]["F_dx_kN"] == F_DX_KN
    assert res["forcas"]["F_dy_kN"] == F_DY_KN
    assert res["duracao"] == "instantanea"
    assert res["k_mod"] == pytest.approx(0.90)  # CS3 instantânea
    assert len(res["casos"]) == 4
    # Projeto R2: seções passam com F=50/25 kN
    assert res["ok"] is True
    assert res["eta"] <= 1.0
