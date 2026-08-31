"""Testes — ruptura de bloco EC5 Anexo A (issue 19)."""
import pytest

from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.wind import ParametrosVento
from mlc_projeto.core.loads import carregamentos_com_vento, peso_proprio_gk
from mlc_projeto.connections.connections import (
    ruptura_de_bloco, ruptura_de_bloco_ligacao, dimensionar_ligacao_base,
)


def test_formula_anexo_A_valores_manuais():
    """
    Confere Eq. (A.1)–(A.3) com cálculo manual (layout L1 Ø24: 8//×12⊥,
    a1=120, a2=72, a3t=168 mm, t1=320 mm, GL24h).
    """
    mat = GlulamMaterial("GL24h", 3, "curta")
    r = ruptura_de_bloco(
        n_par=8, n_perp=12, a1_m=0.120, a2_m=0.072, a3t_m=0.168, t1_m=0.320,
        f_t0_k=mat.f_t0_k, f_v_k=mat.f_v_k, k_mod=0.70, gamma_M=1.25,
        F_par_kN=1225.5,
    )
    # L_net,t = 11·72 = 792 mm ; L_net,v = 2·(7·120+168) = 2016 mm
    assert r["L_net_t_mm"] == pytest.approx(792.0, abs=0.1)
    assert r["L_net_v_mm"] == pytest.approx(2016.0, abs=0.1)
    # termos (A.1): tração 1,5·A_net,t·f_t0k ; cisalh 0,7·A_net,v·f_vk
    A_net_t = 0.792 * 0.320
    A_net_v = 2.016 * 0.320
    assert r["term_tracao_kN"] == pytest.approx(1.5 * A_net_t * mat.f_t0_k / 1e3, rel=1e-3)
    assert r["term_cisalh_kN"] == pytest.approx(0.7 * A_net_v * mat.f_v_k / 1e3, rel=1e-3)
    # F_bs,Rk = max (governa tração aqui)
    assert r["governa"] == "tração"
    assert r["F_bs_Rk_kN"] == pytest.approx(r["term_tracao_kN"], rel=1e-6)
    assert r["ok"] is True


def test_transparencia_so_cisalhamento():
    """η só-cisalhamento é reportado (o max{} pode mascarar o mecanismo frágil)."""
    mat = GlulamMaterial("GL24h", 3, "curta")
    r = ruptura_de_bloco(
        n_par=8, n_perp=12, a1_m=0.120, a2_m=0.072, a3t_m=0.168, t1_m=0.320,
        f_t0_k=mat.f_t0_k, f_v_k=mat.f_v_k, k_mod=0.70, gamma_M=1.25,
        F_par_kN=1225.5,
    )
    # o mecanismo de cisalhamento isolado é bem mais crítico que o η do max{}
    assert r["eta_so_cisalh"] > r["eta"]
    assert r["eta_so_cisalh"] > 1.0        # >1 para este grupo grande


def test_grupo_maior_reduz_eta():
    """Mais pinos ⊥ (maior A_net,t) → maior F_bs,Rk (tração) → menor η."""
    mat = GlulamMaterial("GL24h", 3, "curta")
    base = dict(n_par=8, a1_m=0.120, a2_m=0.072, a3t_m=0.168, t1_m=0.320,
                f_t0_k=mat.f_t0_k, f_v_k=mat.f_v_k, k_mod=0.70, gamma_M=1.25,
                F_par_kN=1225.5)
    r_small = ruptura_de_bloco(n_perp=8, **base)
    r_big = ruptura_de_bloco(n_perp=14, **base)
    assert r_big["eta"] < r_small["eta"]


def test_wrapper_le_layout_da_ligacao():
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
    mat = GlulamMaterial("GL24h", 3, "curta")
    pv = ParametrosVento(V0=45, S1=1, categoria="IV", classe="B", S3=1,
                         L=20.25, H1=geo.h_ap - geo.h0, h=7, dist_portico=5.75)
    pp = peso_proprio_gk(geo, GlulamMaterial("GL24h", 3, "longa"),
                         5.75, 0.20, 0.58, 2.53, 0.10, 0.10)
    load = carregamentos_com_vento(geo, mat, pp["g_k_viga_kNm2"], 0.25, 5.75, pv,
                                   n_pilares_linha=9, n_linhas_portico=3,
                                   L_cob_m=46.0, B_cob_m=2 * geo.L)
    res_L1 = dimensionar_ligacao_base(mat, load, geo, d_mm=24, eta_alvo=0.75)
    rb = ruptura_de_bloco_ligacao(res_L1, geo, mat)
    assert rb["n_par"] == res_L1["n_linha"]
    assert rb["n_perp"] == res_L1["n_linhas"]
    assert rb["F_par_kN"] == pytest.approx(abs(res_L1["N_d_kN"]), abs=0.1)
    assert rb["ok"] is True                # passa pela Eq. (A.1) max{}
    assert rb["eta"] < 1.0
