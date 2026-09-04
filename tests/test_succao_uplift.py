"""Testes — combinação de sucção: uplift + empuxo invertido (issue 33)."""
import pytest

from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.wind import ParametrosVento
from mlc_projeto.core.loads import carregamentos_com_vento, peso_proprio_gk
from mlc_projeto.checks.elu.succao_uplift import verificar_succao_uplift


def _load_gk_correto():
    """Carregamento com g_k realista (issue 1) — expõe o uplift."""
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
    mat = GlulamMaterial("GL24h", 3, "curta")
    pv = ParametrosVento(V0=45, S1=1, categoria="IV", classe="B", S3=1,
                         L=20.25, H1=geo.h_ap - geo.h0, h=7, dist_portico=5.75)
    pp = peso_proprio_gk(geo, GlulamMaterial("GL24h", 3, "longa"),
                         5.75, 0.20, 0.58, 2.53, 0.10, 0.10)
    load = carregamentos_com_vento(
        geo, mat, pp["g_k_viga_kNm2"], 0.25, 5.75, pv,
        n_pilares_linha=9, n_linhas_portico=3, L_cob_m=46.0, B_cob_m=2 * geo.L)
    return geo, mat, load


def _verificar(load, geo, mat, **kw):
    base = dict(F_chu_kN=80.0, n_chu=4, b_pilar=0.32, h_pilar=0.27,
                H_pilar_m=7.0, rho_mean_kgm3=mat.rho_mean, com_tirante=True)
    base.update(kw)
    return verificar_succao_uplift(load, geo, **base)


def test_deteta_uplift_e_empuxo_invertido():
    geo, mat, load = _load_gk_correto()
    r = _verificar(load, geo, mat)
    assert r["ha_uplift"] is True
    assert r["empuxo_invertido"] is True
    assert r["tirante_frouxo"] is True
    assert r["R_A_kN"] < 0                 # uplift (reação para cima)
    assert r["H_suc_kN"] < 0               # empuxo invertido


def test_empuxo_invertido_vai_a_base_de_extremidade():
    """Tirante frouxo → |H| vira cortante na base de extremidade; central V≈0."""
    geo, mat, load = _load_gk_correto()
    r = _verificar(load, geo, mat)
    assert r["V_base_ext_kN"] == pytest.approx(abs(r["H_suc_kN"]), abs=1e-2)


def test_uplift_liquido_desconta_peso_do_pilar():
    """N_uplift = |R_v| − γ_G,inf·W_pilar (peso próprio favorável)."""
    geo, mat, load = _load_gk_correto()
    r = _verificar(load, geo, mat)
    uplift_bruto = abs(r["R_A_kN"])
    assert r["N_uplift_ext_kN"] == pytest.approx(
        uplift_bruto - r["W_pilar_fav_kN"], abs=1e-2)
    assert r["N_uplift_ext_kN"] < uplift_bruto      # o peso alivia
    # central acumula os dois vãos → maior uplift que a extremidade
    assert r["N_uplift_cen_kN"] > r["N_uplift_ext_kN"]


def test_interacao_linear_governada_pela_extremidade():
    geo, mat, load = _load_gk_correto()
    r = _verificar(load, geo, mat)
    assert r["eta_ext"] == pytest.approx(r["eta_N_ext"] + r["eta_V_ext"], abs=1e-3)
    assert r["base_gov"] == "extremidade"          # o empuxo invertido governa
    assert r["eta"] == pytest.approx(r["eta_ext"], rel=1e-9)


def test_download_contravento_soma_na_ancoragem_do_canto():
    """
    issue 36: a tração de download do contraventamento (Σ V_Ed·tanβ) é concomitante
    ao uplift de sucção e soma na ancoragem da base de CANTO.
    """
    geo, mat, load = _load_gk_correto()
    r0 = _verificar(load, geo, mat)                       # sem download
    r1 = _verificar(load, geo, mat, N_brace_anc_kN=117.9) # com download
    # sem download: canto == extremidade (nada somado) e não governa
    assert r0["N_brace_anc_kN"] == 0.0
    assert r0["base_gov"] == "extremidade"
    # com download: N do canto = uplift_ext + download
    assert r1["N_uplift_canto_kN"] == pytest.approx(
        r1["N_uplift_ext_kN"] + 117.9, abs=1e-2)
    assert r1["eta_canto"] > r1["eta_ext"]               # a soma agrava
    assert r1["base_gov"] == "canto (contraventado)"
    assert r1["eta"] == pytest.approx(r1["eta_canto"], rel=1e-9)


def test_sem_tirante_nao_ha_frouxo():
    """Sem tirante não há 'tirante frouxo', mas o empuxo de sucção |H| vai à
    base como cortante (sempre — não depende da inversão)."""
    geo, mat, load = _load_gk_correto()
    r = _verificar(load, geo, mat, com_tirante=False)
    assert r["tirante_frouxo"] is False
    # sem tirante o empuxo sempre carrega a base (|H|), concomitante ao uplift
    assert r["V_base_ext_kN"] == pytest.approx(abs(r["H_suc_kN"]), abs=1e-2)


def test_ancoragem_insuficiente_reprova():
    """Ancoragem fraca → η>1 (reprovado)."""
    geo, mat, load = _load_gk_correto()
    r = _verificar(load, geo, mat, F_chu_kN=20.0, n_chu=2)
    assert r["eta"] > 1.0
    assert r["ok"] is False
