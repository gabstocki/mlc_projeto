"""Issues 15 e 41 — contraventamento da cobertura (EC5 §9.2.5.2/§9.2.5.3):
fatores da Tab. 9.2, dois planos independentes, sem duplicação; ℓ = vão do
sistema de contraventamento = vão da viga (issue 41), n = vigas por sistema."""
import math

import pytest

from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.wind import ParametrosVento
from mlc_projeto.core.loads import carregamentos_com_vento
from mlc_projeto.checks.elu.contraventamento import (
    LayoutContraventamento,
    flecha_sistema_estabilizador,
    verificar_contraventamento,
    verifica_sistema_vigas,
    K_S, K_F1, K_F2, K_F3,
)


def _res(d_barra=22.0, n_modulos_cv=2, L_comp=46.0):
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
    mat = GlulamMaterial("GL24h", 3, "curta")
    pv = ParametrosVento(V0=45, S1=1, categoria="IV", classe="B", S3=1,
                         L=20.25, H1=geo.h_ap - geo.h0, h=7, dist_portico=5.75,
                         # cobertura real: 2 tramos + veículos sob a cobertura (Onda 2)
                         l2=40.5, n_tramos=2, obstrucoes_sob_cobertura=True)
    # Opção B (issue 35/38): viga biapoiada, sem empuxo — como no projeto
    load = carregamentos_com_vento(geo, mat, 1.5, 0.40, 5.75, pv,
                                   L_cob_m=46.0, B_cob_m=2 * geo.L,
                                   empuxo_desenvolve=False)
    r = verificar_contraventamento(
        geo, mat, load, L_comp=L_comp, n_modulos_cv=n_modulos_cv, s_terca=2.53,
        d_barra_mm=d_barra, n_porticos=2, dist_portico=5.75,
        b_terca=0.20, h_terca=0.58, k_crit=1.0)
    return r


def test_fatores_tabela_9_2_recomendados():
    """Valores RECOMENDADOS (sublinhados) da EC5 Tab. 9.2."""
    assert K_S == 4.0        # k_s: 1 a 4  → 4
    assert K_F1 == 50.0      # k_f,1: 50 a 80 → 50
    assert K_F2 == 80.0      # k_f,2: 80 a 100 → 80
    assert K_F3 == 30.0      # k_f,3: 30 a 80 → 30 (NÃO 50)


def test_dois_planos_independentes():
    """Dois planos (um por vão), 9 vigas por plano repartidas por 2 baías."""
    r = _res()
    assert r["n_planos"] == 2
    assert r["n_por_plano"] == 9
    assert r["n_por_sistema"] == 5     # ⌈9/2⌉ vigas por sistema
    assert r["n_vigas"] == 18          # total informativo
    assert r["n_paineis_vao"] == 8     # 20,25 / 2,53 → 8 painéis com cruz


def test_ell_e_vao_da_viga_nao_comprimento_edificacao():
    """Issue 41: ℓ = vão do sistema, paralelo às vigas = 20,25 m, e k_ℓ = 0,86.

    ℓ não depende do comprimento do galpão nem do número de baías rígidas."""
    r = _res()
    assert r["ell_m"] == pytest.approx(20.25)
    assert r["k_ell"] == pytest.approx(math.sqrt(15.0 / 20.25), abs=1e-4)
    assert r["k_ell"] == pytest.approx(0.86, abs=0.005)
    for L_comp, n_cv in ((46.0, 3), (60.0, 2)):
        assert _res(L_comp=L_comp, n_modulos_cv=n_cv)["ell_m"] == pytest.approx(20.25)


def test_mais_baias_reduz_n_nao_ell():
    """Mais baías contraventadas reduzem n por sistema e a força — não há
    efeito contraintuitivo, porque k_ℓ não muda."""
    r2, r3 = _res(n_modulos_cv=2), _res(n_modulos_cv=3)
    assert r3["k_ell"] == r2["k_ell"]
    assert r3["n_por_sistema"] == 3 < r2["n_por_sistema"]
    assert r3["R_ext_kN"] < r2["R_ext_kN"]


def test_layout_n_por_sistema():
    lay = LayoutContraventamento(L_comp=46.0, n_modulos_cv=1)
    assert lay.n_por_sistema == 9
    assert LayoutContraventamento(L_comp=46.0, n_modulos_cv=9).n_por_sistema == 1


def test_q_d_formula_9_37_e_k_ell_9_38():
    """q_d = k_ℓ·n·N_d/(k_f3·ℓ) e k_ℓ = min(1, √(15/ℓ)) — n por sistema."""
    r = _res()
    N_d = r["N_d_kN"]
    sis = verifica_sistema_vigas(N_d, r["n_por_sistema"], r["ell_m"], k_f3=K_F3)
    k_ell = min(1.0, math.sqrt(15.0 / r["ell_m"]))
    assert sis["k_ell"] == pytest.approx(k_ell, abs=1e-4)
    assert sis["q_d_kNpm"] == pytest.approx(
        k_ell * r["n_por_sistema"] * N_d / (K_F3 * r["ell_m"]), rel=1e-4)
    # bate com o valor reportado (por plano)
    assert r["q_d_kNpm"] == pytest.approx(sis["q_d_kNpm"], rel=1e-4)


def test_diagonal_do_painel_extremo_leva_o_cortante_da_trelica():
    """A diagonal crítica é a do painel junto ao apoio da treliça: cortante
    V = q_d·ℓ/2 + vento θ=0° da baía / 2 — EC5 §9.2.5.3(1): q_d atua "em
    adição" às ações externas (issue 65). Planos não somam entre si."""
    r = _res()
    theta = math.radians(r["theta_deg"])
    V = r["R_ext_kN"] + r["R_vento0_kN"]
    assert r["R_ext_proj_kN"] == pytest.approx(V, rel=1e-3)
    assert r["R_ext_kN"] == pytest.approx(r["q_d_kNpm"] * r["ell_m"] / 2, rel=1e-3)
    assert r["F_diag_kN"] == pytest.approx(V / math.cos(theta), rel=1e-3)


def test_flecha_da_trelica():
    """δ = q·ℓ²/(8·C_h·s) + 5·q·ℓ⁴/(384·EI_eq), limite ℓ/500."""
    fl = flecha_sistema_estabilizador(q_d_kNpm=10.0, ell_m=20.0, C_h_kNpm=1.0e4,
                                      s_painel_m=2.5, EA_banzo_kN=1.0e6,
                                      dist_banzos_m=6.0)
    dV = 10.0 * 20.0**2 / (8 * 1.0e4 * 2.5)
    dM = 5 * 10.0 * 20.0**4 / (384 * 2 * 1.0e6 * 3.0**2)
    assert fl["delta_mm"] == pytest.approx((dV + dM) * 1000, rel=1e-3)
    assert fl["delta_lim_mm"] == pytest.approx(40.0)


def test_l1_penalizado_e_o_vao_da_viga():
    """Sem sistema válido, l_1 passa ao vão da própria viga, não a 46 m."""
    r = _res(d_barra=18.0)
    assert r["cobertura_ok"] is False
    assert r["l_1_efetivo_m"] == pytest.approx(20.25)


def test_diagonal_36mm_passa_e_cobertura_ok():
    """Com o vento longitudinal majorado por γ_Q (issue 109) a Ø28 reprova; a Ø36
    adotada passa e a cobertura valida a restrição das terças."""
    assert _res(d_barra=28.0)["eta_diag_N"] > 1.0
    r = _res(d_barra=36.0)
    assert r["eta_diag_N"] <= 0.90
    assert r["cobertura_ok"] is True
    assert r["l_1_efetivo_m"] == pytest.approx(2.53, abs=1e-6)  # terças válidas


def test_diametros_insuficientes_reprovam():
    """Ø18 e Ø22 NÃO servem sob a ação longitudinal normativa.

    Guarda contra regressão do dimensionamento: se alguém reduzir o diâmetro
    de volta, o η tem de reprovar e a cobertura deixa de validar a restrição
    lateral das terças. Nunca relaxar estes limites.
    """
    for d in (18.0, 22.0):
        r = _res(d_barra=d)
        assert r["eta_diag_N"] > 1.0, f"Ø{d:.0f} deveria reprovar"
        assert r["cobertura_ok"] is False


def test_flecha_soma_q_d_e_vento():
    """§9.2.5.3(2): deslocamento sob q_d E as ações externas — soma (issue 65)."""
    r = _res(d_barra=28.0)
    q_w = 2 * r["R_vento0_kN"] / r["ell_m"]
    q = r["q_d_kNpm"] + q_w
    dV = q * r["ell_m"] ** 2 / (8 * r["C_h_kNpm"] * 2.53)
    assert r["delta_V_mm"] == pytest.approx(dV * 1000, rel=1e-2)
