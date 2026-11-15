"""Issue 106 — lâmina do pilar bipartido em incêndio e sob choque de veículo."""

import pytest

from mlc_projeto.checks.elu.pilar_bipartido import (
    tempo_colapso_lamina, verificar_lamina_fogo, verificar_lamina_impacto,
)
from mlc_projeto.core.materials import GlulamMaterial

KW = dict(b_viga_m=0.32, L_x_m=6.70, L_y_m=7.70)


@pytest.fixture(scope="module")
def mat_elu():
    return GlulamMaterial("GL24h", 3, "media")


def test_fogo_quatro_faces_reduz_as_duas_dimensoes(mat_elu):
    r = verificar_lamina_fogo(mat=mat_elu, N_fi_kN=50.0, R_req_min=30.0, **KW)
    assert r["b_fi_mm"] == pytest.approx(160 - 2 * r["d_ef_mm"], abs=0.2)
    assert r["h_fi_mm"] == pytest.approx(320 - 2 * r["d_ef_mm"], abs=0.2)
    assert r["ok"]


def test_tempo_de_colapso_decresce_com_a_forca(mat_elu):
    t1 = tempo_colapso_lamina(mat=mat_elu, N_fi_kN=30.0, **KW)
    t2 = tempo_colapso_lamina(mat=mat_elu, N_fi_kN=80.0, **KW)
    assert t1 > t2 > 0


def test_choque_repartido_pelo_espacador_e_metade(mat_elu):
    inst = mat_elu.com_duracao("instantanea")
    kw = dict(mat_inst=inst, N_d_kN=45.0, F_x_kN=50.0, F_y_kN=25.0, h_imp_m=0.20, **KW)
    rep = verificar_lamina_impacto(**kw)
    soz = verificar_lamina_impacto(repartido=False, **kw)
    c_rep = {(c["F_kN"], c["direcao"]): c for c in rep["casos"]}
    for c in soz["casos"]:
        assert c_rep[(c["F_kN"], c["direcao"])]["V_kN"] == pytest.approx(c["V_kN"] / 2, abs=0.02)
    assert rep["eta"] < soz["eta"]
    # no plano do pórtico os parafusos do espaçador levam metade do choque
    assert max(c["eta_espacador"] for c in rep["casos"]) > 0
