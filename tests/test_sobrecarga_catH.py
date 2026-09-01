"""Testes — sobrecarga de cobertura categoria H (issue 2)."""
import pytest

from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.wind import ParametrosVento
from mlc_projeto.core.loads import carregamentos_com_vento, peso_proprio_gk


def test_qk_projeto_categoria_H():
    """
    EN 1991-1-1 Tab. 6.10 (cat. H): q_k = 0,40 kN/m² (recomendado) e
    Q_k = 1,0 kN concentrado. O projeto adota esses valores em main.py.
    """
    import mlc_projeto.main as m
    assert m.Q_AREA == pytest.approx(0.40)      # UDL cat. H (issue 2)
    assert m.QK_CONC_KN == pytest.approx(1.0)   # concentrado (issue 34)


def test_qk_propaga_para_carga_linear():
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
    mat = GlulamMaterial("GL24h", 3, "curta")
    pv = ParametrosVento(V0=45, S1=1, categoria="IV", classe="B", S3=1,
                         L=20.25, H1=geo.h_ap - geo.h0, h=7, dist_portico=5.75)
    pp = peso_proprio_gk(geo, GlulamMaterial("GL24h", 3, "longa"),
                         5.75, 0.20, 0.58, 2.53, 0.10, 0.10)
    load = carregamentos_com_vento(geo, mat, pp["g_k_viga_kNm2"], 0.40, 5.75, pv,
                                   n_pilares_linha=9, n_linhas_portico=3,
                                   L_cob_m=46.0, B_cob_m=2 * geo.L)
    # q_k linear = q_area · área tributária (L_t)
    assert load.q_k == pytest.approx(0.40 * load.area_trib, rel=1e-9)
    # característico ELS_S1 = G + Q reflete o novo q_k
    s1 = load.combinacoes["ELS_S1"]
    assert s1.q_esq == pytest.approx(load.g_k + load.q_k, rel=1e-6)
