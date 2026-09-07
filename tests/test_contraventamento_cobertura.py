"""Issue 15 — contraventamento da cobertura (EC5 §9.2.5.2/§9.2.5.3):
fatores da Tab. 9.2, dois planos independentes (n=9 por plano), sem duplicação."""
import math

import pytest

from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.wind import ParametrosVento
from mlc_projeto.core.loads import carregamentos_com_vento
from mlc_projeto.checks.elu.contraventamento import (



    verificar_contraventamento,
    verifica_sistema_vigas,
    K_S, K_F1, K_F2, K_F3,
)



def _res(d_barra=22.0):
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
    mat = GlulamMaterial("GL24h", 3, "curta")
    pv = ParametrosVento(V0=45, S1=1, categoria="IV", classe="B", S3=1,
                         L=20.25, H1=geo.h_ap - geo.h0, h=7, dist_portico=5.75,
                         # cobertura real: 2 tramos + veículos sob a cobertura (Onda 2)
                         l2=40.5, n_tramos=2, obstrucoes_sob_cobertura=True)
    load = carregamentos_com_vento(geo, mat, 1.5, 0.40, 5.75, pv,
                                   L_cob_m=46.0, B_cob_m=2 * geo.L)
    r = verificar_contraventamento(
        geo, mat, load, L_comp=46.0, n_modulos_cv=2, s_terca=2.53,
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
    """Modelado como dois planos (um por vão), n=9 por plano, não n=18 único."""
    r = _res()
    assert r["n_planos"] == 2
    assert r["n_por_plano"] == 9
    assert r["n_vigas"] == 18          # total informativo
    assert r["n_paineis_por_plano"] == 2


def test_q_d_formula_9_37_e_k_ell_9_38():
    """q_d = k_ℓ·n·N_d/(k_f3·ℓ) e k_ℓ = min(1, √(15/ℓ)) — por plano."""
    r = _res()
    N_d = r["N_d_kN"]
    sis = verifica_sistema_vigas(N_d, r["n_por_plano"], r["ell_m"], k_f3=K_F3)
    k_ell = min(1.0, math.sqrt(15.0 / r["ell_m"]))
    assert sis["k_ell"] == pytest.approx(k_ell, abs=1e-4)
    assert sis["q_d_kNpm"] == pytest.approx(
        k_ell * r["n_por_plano"] * N_d / (K_F3 * r["ell_m"]), rel=1e-4)
    # bate com o valor reportado (por plano)
    assert r["q_d_kNpm"] == pytest.approx(sis["q_d_kNpm"], rel=1e-4)


def test_sem_duplicacao_forca():
    """A força por diagonal = R_ext(plano)/(painéis do plano); dois planos
    independentes não somam força um no outro (sem duplicação)."""
    r = _res()
    # F_diag deduzido do R_ext por plano e dos painéis do plano
    theta = math.radians(r["theta_deg"])
    F_painel = r["R_ext_kN"] / r["n_paineis_por_plano"]
    F_diag_esperado = F_painel / math.cos(theta)
    # (vale quando a estabilização governa sobre o vento θ=0°)
    if r["gov_forca"] == "estab_9.2.5":
        assert r["F_diag_kN"] == pytest.approx(F_diag_esperado, rel=1e-3)


def test_diagonal_28mm_passa_e_cobertura_ok():
    """Ø28 mm (redimensionada) passa e a cobertura valida a restrição das terças.

    Redimensionamento pós-Onda 2: com a ação longitudinal normativa (§7.2.2) a
    Ø22 passou a dar η=1,280 E deixou de validar a restrição lateral — o l_1 da
    flambagem lateral saltava de s=2,53 m para ℓ=46 m. Varredura: Ø25 → 0,991
    (sem margem); Ø28 → 0,790 ← adotada; Ø30 → 0,688.
    """
    r = _res(d_barra=28.0)
    assert r["eta_diag_N"] < 1.0
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
