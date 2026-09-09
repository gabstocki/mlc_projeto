"""Issue 16 — Terça-biela: interação flexão + compressão COMBINADA
(EC5 §6.3.2 Eq. 6.23/6.24), substituindo os dois η isolados.

Verifica-se:
  1. A forma normativa das Eq. 6.23/6.24 (termo de compressão LINEAR ÷k_c,
     NÃO ao quadrado — a forma quadrada é §6.2.4, só para peças curtas).
  2. Concomitância: a flexão usada é idêntica à de `verifica_terca` (mesma
     combinação ELU_C2), e a compressão é a força de estabilização §9.2.5.
  3. Um único η combinado é reportado, ≥ cada parcela isolada e menor que
     a soma linear das duas (o k_c e o k_m redistribuem).
"""

import math

import pytest

from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.checks.elu.tercas import (
    verifica_terca,
    verifica_terca_flexocompressao,
)


# Parâmetros do projeto (main.py): terça 0,20×0,58 m, L_t=5,75 m, s=2,53 m
MAT = GlulamMaterial("GL24h", 3, "curta")
KW = dict(
    L_t=5.75, s=2.53, b=0.20, h=0.58, alpha_deg=10.0,
    g_k_m2=0.389, q_k_m2=0.40, w_kNm2=0.7158,
)


def test_concomitancia_flexao_igual_verifica_terca():
    """A flexão da interação é a MESMA de verifica_terca (mesma combinação)."""
    rt = verifica_terca(MAT, k_m=0.7, **KW)
    rc = verifica_terca_flexocompressao(MAT, N_c_kN=47.36, k_m=0.7, **KW)
    assert rc["sigma_my_MPa"] == pytest.approx(rt["sigma_my_MPa"], rel=1e-9)
    assert rc["sigma_mz_MPa"] == pytest.approx(rt["sigma_mz_MPa"], rel=1e-9)
    assert rc["f_md_MPa"] == pytest.approx(rt["f_md_MPa"], rel=1e-9)
    # [D2] O rótulo era "ELU_C2 (1,35G+1,5W+1,05Q)" — um ALIAS a fingir de
    # fórmula, com ψ0,Q = 0,70 de outra categoria de uso. A terça passa a fazer
    # o envelope das combinações reais e a publicar a que governou; a exigência
    # que interessa é que a interação use A MESMA que a flexão.
    assert rc["comb"] == rt["comb_gov"]
    assert rc["comb"] in rt["etas_por_combinacao"]
    assert "1,05Q" not in rc["comb"]


def test_eq_623_624_formula_linear_kc():
    """η bate com a fórmula §6.3.2 recalculada à mão (compressão LINEAR ÷k_c)."""
    N_c = 47.36
    rc = verifica_terca_flexocompressao(MAT, N_c_kN=N_c, k_m=0.7, **KW)

    b, h, L_t = KW["b"], KW["h"], KW["L_t"]
    A = b * h
    sigma_c = N_c * 1e3 / A
    f_c0d = MAT.f_c0_d
    f_c0k, E005 = MAT.f_c0_k, MAT.E0_05
    f_md = rc["f_md_MPa"] * 1e6
    smy = rc["sigma_my_MPa"] * 1e6
    smz = rc["sigma_mz_MPa"] * 1e6

    def kc(i):
        lam = L_t / i
        lr = (lam / math.pi) * math.sqrt(f_c0k / E005)
        k = 0.5 * (1 + 0.10 * (lr - 0.3) + lr**2)
        return 1.0 / (k + math.sqrt(k**2 - lr**2))

    kcy = kc(h / math.sqrt(12.0))
    kcz = kc(b / math.sqrt(12.0))
    e623 = sigma_c / (kcy * f_c0d) + smy / f_md + 0.7 * smz / f_md
    e624 = sigma_c / (kcz * f_c0d) + 0.7 * smy / f_md + smz / f_md

    assert rc["eta_623"] == pytest.approx(e623, rel=1e-3)
    assert rc["eta_624"] == pytest.approx(e624, rel=1e-3)
    assert rc["eta"] == pytest.approx(max(e623, e624), rel=1e-3)


def test_compressao_termo_nao_e_quadratico():
    """O termo de compressão é linear: dobrar σ_c ~dobra o termo (não ×4)."""
    r1 = verifica_terca_flexocompressao(MAT, N_c_kN=40.0, **KW)
    r2 = verifica_terca_flexocompressao(MAT, N_c_kN=80.0, **KW)
    # termo_c_624 é σ_c/(k_c,z·f_c0d): linear em N_c → razão ≈ 2 (não 4)
    assert r2["termo_c_624"] / r1["termo_c_624"] == pytest.approx(2.0, rel=1e-6)


def test_eq624_governa_flambagem_fraca():
    """k_c,z (plano fraco) « k_c,y → Eq.6.24 governa a terça-biela esbelta."""
    rc = verifica_terca_flexocompressao(MAT, N_c_kN=47.36, **KW)
    assert rc["k_c_z"] < rc["k_c_y"]
    assert rc["lambda_z"] > rc["lambda_y"]
    assert rc["verif_gov"] == "Eq.6.24"


def test_eta_combinado_unico_entre_parcela_e_soma():
    """η combinado ≥ cada parcela isolada e ≤ soma linear das duas."""
    N_c = 47.36
    rt = verifica_terca(MAT, **KW)
    rc = verifica_terca_flexocompressao(MAT, N_c_kN=N_c, **KW)

    A = KW["b"] * KW["h"]
    sigma_c = N_c * 1e3 / A
    eta_compr_puro = sigma_c / (rc["k_c_z"] * MAT.f_c0_d)  # sem flexão
    eta_flexao = rt["eta_flexao"]

    assert rc["eta"] >= eta_flexao - 1e-9
    assert rc["eta"] >= eta_compr_puro - 1e-9
    assert rc["eta"] <= eta_flexao + eta_compr_puro + 1e-9


def test_sem_compressao_reduz_a_flexao():
    """N_c=0 → interação recai na flexão biaxial pura (Eq.6.12 embutida)."""
    rt = verifica_terca(MAT, k_m=0.7, **KW)
    rc = verifica_terca_flexocompressao(MAT, N_c_kN=0.0, k_m=0.7, **KW)
    assert rc["eta"] == pytest.approx(rt["eta_flexao"], rel=1e-6)


def test_ok_flag_consistente():
    rc = verifica_terca_flexocompressao(MAT, N_c_kN=47.36, **KW)
    assert rc["ok"] == (rc["eta"] <= 1.0)
    assert rc["norma"].startswith("EC5 §6.3.2")
