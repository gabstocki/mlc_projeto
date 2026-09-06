"""Testes — flecha ELS com vento (NBR 6123) como ação dominante (issue 6)."""
import pytest

from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.wind import ParametrosVento
from mlc_projeto.core.loads import carregamentos_com_vento, peso_proprio_gk
from mlc_projeto.checks.els.deflection_els import verificar_ELS


def _res():
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
    mat = GlulamMaterial("GL24h", 3, "longa")
    pv = ParametrosVento(V0=45, S1=1, categoria="IV", classe="B", S3=1,
                         L=20.25, H1=geo.h_ap - geo.h0, h=7, dist_portico=5.75)
    pp = peso_proprio_gk(geo, GlulamMaterial("GL24h", 3, "longa"),
                         5.75, 0.20, 0.58, 2.53, 0.10, 0.10)
    load = carregamentos_com_vento(geo, mat, pp["g_k_viga_kNm2"], 0.40, 5.75, pv,
                                   n_pilares_linha=9, n_linhas_portico=3,
                                   L_cob_m=46.0, B_cob_m=2 * geo.L)
    return verificar_ELS(geo, mat, load)


def test_psi2_explicito_zero():
    r = _res()
    assert r["psi_2_Q"] == 0.0
    assert r["psi_2_W"] == 0.0


def test_vento_nbr6123_incluido_no_caracteristico():
    """Os 8 padrões de vento (NBR 6123) entram; há flecha de vento pressão/sucção."""
    r = _res()
    assert r["n_padroes_vento"] == 8
    assert r["w_W_press_mm"] > 0        # vento pressão → flecha ↓
    assert r["w_W_suc_mm"] < 0          # vento sucção → flecha ↑


def test_caracteristico_e_o_governante_entre_Q_e_vento():
    """w_S1 = max(G+Q, G+W); aqui a pressão de vento supera Q ⇒ vento governa."""
    r = _res()
    assert r["w_S1_mm"] == pytest.approx(
        max(r["w_char_Q_mm"], r["w_char_W_mm"]), abs=1e-2)
    assert r["w_char_W_mm"] > r["w_char_Q_mm"]   # vento pressão > Q
    assert r["gov_caracteristico"] == "vento"


def test_wfin_usa_variavel_dominante_psi2_zero():
    """w_fin = w_G(1+k_def) + w_var (ψ2=0), com w_var = max(w_Q, w_W_press)."""
    r = _res()
    w_var = max(r["w_Q1_mm"], r["w_W_press_mm"])
    assert r["w_var_fin_mm"] == pytest.approx(w_var, abs=1e-2)
    esperado = r["w_G_mm"] * (1 + r["k_def"]) + w_var
    # tolerância acomoda o acúmulo de arredondamento (campos em mm/2 casas)
    assert r["w_fin_mm"] == pytest.approx(esperado, abs=3e-2)


def test_els_aprovado_folgado():
    """Viga muito rígida (h_ap≈2,8 m) ⇒ flechas pequenas, η ≪ 1."""
    r = _res()
    assert r["ok"] is True
    assert r["eta"] < 0.5


# ── Issue 7 — parcela de deformação por cisalhamento (EC5 §2.2.3/Anexo B) ──────

def test_cisalhamento_presente_e_soma_a_flexao():
    """A flecha S1 inclui a parcela de cortante e ela SOMA à de flexão."""
    r = _res()
    assert r["w_S1_cis_mm"] > 0                       # cisalhamento ↓ (mesmo sentido)
    assert r["w_S1_flex_mm"] > 0
    # w_S1 = flexão + cisalhamento
    assert r["w_S1_mm"] == pytest.approx(
        r["w_S1_flex_mm"] + r["w_S1_cis_mm"], abs=3e-2)
    # contribuição do cortante relevante: h/L≈0,14, E/G≈16 e ação de arco
    # (M=M0−H·y_c reduz a flexão) elevam a fração do cortante (~40% aqui).
    assert 8.0 < r["pct_cis_S1"] < 55.0
    assert r["k_s"] == 1.2
    assert r["G_mean_GPa"] == pytest.approx(0.65, abs=1e-3)   # EN 14080:2013


def test_cisalhamento_aumenta_a_flecha():
    """Incluir o cortante aumenta a flecha total vs só flexão (Timoshenko)."""
    import numpy as np
    from mlc_projeto.checks.els.deflection_els import flecha_numerica
    from mlc_projeto.core.loads import analisar_biarticulada

    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
    mat = GlulamMaterial("GL24h", 3, "longa")
    r = analisar_biarticulada(q=5.0, L=geo.L, h0=geo.h0, h_ap=geo.h_ap,
                              alpha_rad=geo.alpha_rad, b=geo.b,
                              desenvolve_empuxo=True)
    M_x = np.interp(geo.x, r["x"], r["M_x"]) * 1e3
    w_tot, _, w_b, w_s = flecha_numerica(geo, mat, M_x, geo.x)
    w_flex, _, _, _ = flecha_numerica(geo, mat, M_x, geo.x,
                                      incluir_cisalhamento=False)
    assert w_tot > w_flex                            # cortante aumenta a flecha
    assert abs(w_s).max() > 0
    # o perfil de cisalhamento tem o mesmo sinal do de flexão no meio do vão
    i = int(np.argmax(np.abs(w_b)))
    assert np.sign(w_s[i]) == np.sign(w_b[i])


def test_flecha_numerica_bem_condicionada_secao_constante():
    """Regressão: com seção ~constante a flexão bate com 5qL⁴/384EI (viga
    BIARTICULADA), não com o valor bi-engastado qL⁴/384EI (bug corrigido)."""
    import numpy as np
    from mlc_projeto.checks.els.deflection_els import flecha_numerica

    # seção quase constante (α≈0) → fórmula fechada de viga bi-apoiada
    geo = GeometriaViga(L=6.0, h0=0.50, alpha_deg=0.001, b=0.20)
    mat = GlulamMaterial("GL24h", 3, "longa")
    q = 5000.0                                        # N/m
    x = geo.x
    M_x = 0.5 * q * x * (geo.L - x)                   # bi-apoiada uniforme
    _, _, w_b, _ = flecha_numerica(geo, mat, M_x, x, incluir_cisalhamento=False)
    I = geo.b * geo.h0**3 / 12
    w_ref = 5 * q * geo.L**4 / (384 * mat.E0_mean * I)
    assert abs(w_b).max() == pytest.approx(w_ref, rel=2e-3)
