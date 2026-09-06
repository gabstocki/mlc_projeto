"""Testes — varredura Cpe Tab.25 e vento θ=0°/90°."""
import math
import pytest

from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.wind import (
    ParametrosVento,
    coeficientes_tabela25,
    padroes_cpe_tabela25,
    calcular_vento,
    forca_vento_paralelo_cumeeira,
    forca_vento_pilar_90,
)
from mlc_projeto.core.loads import (
    carregamentos_com_vento,
    analisar_biarticulada,
)


def test_padroes_tabela25_completos():
    """8 padrões: C1/C2 × (asim, rev, unif_bv, unif_st)."""
    p = padroes_cpe_tabela25(0.176)
    ids = {x["id"] for x in p}
    assert len(p) == 8
    for caso in ("C1", "C2"):
        assert f"{caso}_asim" in ids
        assert f"{caso}_rev" in ids
        assert f"{caso}_unif_bv" in ids
        assert f"{caso}_unif_st" in ids


def test_assimetrico_tem_Cpb_e_Cps():
    coef = coeficientes_tabela25(0.176)
    pads = padroes_cpe_tabela25(0.176)
    asim = next(x for x in pads if x["id"] == "C1_asim")
    assert asim["C_esq"] == pytest.approx(coef["C1"]["Cpb"])
    assert asim["C_dir"] == pytest.approx(coef["C1"]["Cps"])
    rev = next(x for x in pads if x["id"] == "C1_rev")
    assert rev["C_esq"] == pytest.approx(coef["C1"]["Cps"])
    assert rev["C_dir"] == pytest.approx(coef["C1"]["Cpb"])


def test_analise_assimetrica_reaccoes():
    """R_A + R_B = carga total; assimetria desloca reações."""
    L, q1, q2 = 20.0, 10.0, 5.0
    r = analisar_biarticulada(
        q=0.0, L=L, h0=1.0, h_ap=2.0, alpha_rad=math.radians(10),
        b=0.30, q_esq=q1, q_dir=q2, desenvolve_empuxo=True,
    )
    W = q1 * L / 2 + q2 * L / 2
    assert r["R_A_kN"] + r["R_B_kN"] == pytest.approx(W, rel=1e-6)
    assert r["R_A_kN"] > r["R_B_kN"]  # mais carga à esquerda


def test_varredura_load_completa():
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.30)
    mat = GlulamMaterial(classe="GL24h", classe_servico=3, duracao="curta")
    pv = ParametrosVento(
        V0=45.0, S1=1.0, categoria="IV", classe="B", S3=1.0,
        L=20.25, H1=1.785, h=7.0, dist_portico=5.75,
    )
    load = carregamentos_com_vento(
        geo=geo, mat=mat, g_area=1.5, q_area=0.25, L_t=5.75,
        params_vento=pv, b_pilar=0.22, h_pilar=0.26,
        n_pilares_linha=9, n_linhas_portico=3,
        L_cob_m=46.0, B_cob_m=40.5,
    )
    vv = load.varredura_vento_90
    assert vv["completo"] is True
    assert vv["n_padroes_cpe"] == 8
    # Categoria H (issue 3): Q e vento NÃO concomitantes (EN 1991-1-1 §3.3.2(1)).
    # Por padrão de vento: 2 combos (W pressão + W sucção); a sobrecarga entra em
    # UMA combinação gravítica (sem vento). Total = 8×2 + 1 = 17.
    assert vv["n_combinacoes_elu_vento"] == 8 * 2 + 1
    assert load.vento_0 is not None
    assert load.vento_0["F_total_kN"] > 0
    gov = load.combinacao_ELU_governante()
    assert gov.padrao_vento  # não vazio
    assert abs(gov.M_max_kNm) > 0


def test_vento_0_e_90_pilar():
    pv = ParametrosVento(
        V0=45.0, S1=1.0, categoria="IV", classe="B", S3=1.0,
        L=20.25, H1=1.785, h=7.0, dist_portico=5.75,
    )
    f0 = forca_vento_paralelo_cumeeira(
        pv, b_pilar=0.22, h_pilar=0.26,
        n_pilares_linha=9, n_linhas_portico=3,
        L_cob_m=46.0, B_cob_m=40.5,
    )
    f90 = forca_vento_pilar_90(pv, b_pilar=0.22, h_pilar=0.26)
    assert f0["theta_deg"] == 0.0
    assert f90["theta_deg"] == 90.0
    assert f0["F_total_kN"] > f90["F_pilar_kN"]  # muitos pilares
    assert f90["M_mid_kNm"] > 0
