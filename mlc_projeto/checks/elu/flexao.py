"""
checks/elu/flexao.py — Flexo-compressão da viga — EC5 §6.3.2.

ATUALIZAÇÃO v2 — Pórtico de 3 rótulas:
    A viga está submetida simultaneamente a:
    - Momento fletor M_d (máximo em x ≈ L/4)
    - Força normal N_d (compressão — empuxo horizontal interno)

    Verificação: EC5 §6.3.2 Eq. 6.23
        (σ_c,0,d / (k_c · f_c,0,d))² + σ_m,d / f_m,d ≤ 1,0

    Comprimento efetivo para flambagem da viga no plano do pórtico:
        l_ef,y = L/2  (entre rótulas: base e cumeeira)

    Comprimento efetivo fora do plano (flambagem lateral):
        l_ef,z = 0,9 · s  (restringido pelas terças — EC5 Tab. 6.1)

    Nota sobre EC5 §6.1.6 (flexão simples):
        Não aplicável aqui — substituída por §6.3.2 devido à força normal.
        η_§6.1.6 seria conservador (ignora k_c) e incorreto (ignora N).

Referência: EC5 §6.3.2 Eq. 6.23
"""

from __future__ import annotations

import math
import numpy as np

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.loads     import Carregamentos


def verifica_flexao(
    geo:  GeometriaViga,
    mat:  GlulamMaterial,
    load: Carregamentos,
    s:    float = 1.00,
) -> dict:
    """
    Verifica flexo-compressão da viga — EC5 §6.3.2 Eq. 6.23.

    Verifica na seção de momento máximo (x_Mmax), onde h = h(x_Mmax).

    Condição:
        (σ_c,0,d / (k_c,y · f_c,0,d))² + σ_m,d / f_m,d ≤ 1,0

    onde k_c,y considera flambagem no plano do pórtico (l_ef = L/2).

    Args:
        geo  : Geometria da viga
        mat  : Material (k_mod já reflete duração do carregamento)
        load : Carregamentos (pórtico de 3 rótulas)
        s    : Espaçamento entre terças (m) — define l_ef fora do plano

    Returns:
        dict com σ_c, σ_m, k_c, η e ok
    """
    gov = load.combinacao_ELU_governante()

    # ── Esforços da combinação governante ─────────────────────
    M_max_Nm = gov.M_max_kNm * 1e3    # N·m
    N_d_N    = gov.N_viga_kN  * 1e3   # N — compressão
    x_Mmax   = gov.x_Mmax_m           # m — posição do M_max

    # ── Seção no ponto de momento máximo ─────────────────────
    h_x = geo.h0 + x_Mmax * math.tan(geo.alpha_rad)
    b   = geo.b

    A_sec = b * h_x
    W_y   = b * h_x**2 / 6
    I_y   = b * h_x**3 / 12
    i_y   = math.sqrt(I_y / A_sec)

    # ── Flambagem no plano do pórtico (eixo y — eixo forte) ──
    # Entre rótulas: base articulada e cumeeira articulada
    # l_ef,y = L/2 (distância entre rótulas)
    l_ef_y   = geo.L / 2
    lam_y    = l_ef_y / i_y
    lam_rel_y = (lam_y / math.pi) * math.sqrt(
        mat.f_c0_k / mat.E0_05
    )

    beta_c = 0.1   # glulam — EC5 §6.3.2
    k_y    = 0.5 * (1 + beta_c*(lam_rel_y - 0.3) + lam_rel_y**2)
    k_c_y  = min(1.0 / (k_y + math.sqrt(k_y**2 - lam_rel_y**2)), 1.0)

    # ── Tensões de cálculo ────────────────────────────────────
    sigma_c = N_d_N  / A_sec   # Pa — compressão
    sigma_m = M_max_Nm / W_y   # Pa — flexão

    # ── Verificação EC5 §6.3.2 Eq. 6.23 ──────────────────────
    eta = (sigma_c / (k_c_y * mat.f_c0_d))**2 + sigma_m / mat.f_m_d

    # ── Verificação complementar — flambagem fora do plano ───
    # (eixo z — eixo fraco, restringido pelas terças)
    I_z    = h_x * b**3 / 12
    i_z    = math.sqrt(I_z / A_sec)
    l_ef_z = 0.9 * s   # restringido pelas terças
    lam_z  = l_ef_z / i_z
    lam_rel_z = (lam_z / math.pi) * math.sqrt(
        mat.f_c0_k / mat.E0_05
    )
    k_z   = 0.5 * (1 + beta_c*(lam_rel_z - 0.3) + lam_rel_z**2)
    k_c_z = min(1.0 / (k_z + math.sqrt(k_z**2 - lam_rel_z**2)), 1.0)

    # EC5 §6.3.2 Eq. 6.24 — flambagem fora do plano
    eta_z = (sigma_c / (k_c_z * mat.f_c0_d))**2 + sigma_m / mat.f_m_d

    eta_gov = max(eta, eta_z)
    plano_gov = "no plano" if eta >= eta_z else "fora do plano"

    return {
        # Geometria da seção verificada
        "x_Mmax_m":      round(x_Mmax,           3),
        "h_x_m":         round(h_x,               4),
        "b_m":           b,
        "A_m2":          round(A_sec,              6),
        # Esforços
        "M_max_kNm":     round(gov.M_max_kNm,     3),
        "N_d_kN":        round(gov.N_viga_kN,     3),
        # Flambagem no plano (eixo y)
        "l_ef_y_m":      round(l_ef_y,            3),
        "lambda_y":      round(lam_y,              2),
        "lambda_rel_y":  round(lam_rel_y,          4),
        "k_c_y":         round(k_c_y,              4),
        "eta_no_plano":  round(eta,                4),
        # Flambagem fora do plano (eixo z)
        "l_ef_z_m":      round(l_ef_z,            3),
        "lambda_z":      round(lam_z,              2),
        "lambda_rel_z":  round(lam_rel_z,          4),
        "k_c_z":         round(k_c_z,              4),
        "eta_fora_plano":round(eta_z,              4),
        # Tensões
        "sigma_c_MPa":   round(sigma_c / 1e6,     4),
        "sigma_m_MPa":   round(sigma_m / 1e6,     4),
        "f_c0d_MPa":     round(mat.f_c0_d / 1e6,  4),
        "f_md_MPa":      round(mat.f_m_d  / 1e6,  4),
        # Resultado
        "eta":           round(eta_gov,            4),
        "ok":            eta_gov <= 1.0,
        "plano_gov":     plano_gov,
        "norma":         "EC5 §6.3.2 Eq. 6.23+6.24",
    }


# ── Execução direta ───────────────────────────────────────────────────────────

if __name__ == "__main__":

    from mlc_projeto.core.geometry  import GeometriaViga
    from mlc_projeto.core.materials import GlulamMaterial
    from mlc_projeto.core.wind      import ParametrosVento
    from mlc_projeto.core.loads     import carregamentos_com_vento

    geo = GeometriaViga(L=20.25, h0=0.60, alpha_deg=4.5, b=0.26)
    mat = GlulamMaterial(classe="GL24h", classe_servico=2, duracao="curta")

    params_vento = ParametrosVento(
        V0=45.0, S1=1.0, categoria="IV", classe="B", S3=1.0,
        L=20.25, H1=1.0, h=7.0, dist_portico=5.75,
    )

    load = carregamentos_com_vento(
        geo=geo, mat=mat,
        g_area=1.50, q_area=0.25,
        L_t=5.75, params_vento=params_vento,
    )

    res = verifica_flexao(geo, mat, load, s=1.00)

    print("VERIFICAÇÃO DE FLEXO-COMPRESSÃO DA VIGA — EC5 §6.3.2")
    print(f"Seção em x={res['x_Mmax_m']} m | h={res['h_x_m']} m | b={res['b_m']} m")
    print(f"M_d = {res['M_max_kNm']:.2f} kN·m | N_d = {res['N_d_kN']:.2f} kN")
    print()
    print(f"Flambagem no plano  (l_ef={res['l_ef_y_m']} m):")
    print(f"  λ={res['lambda_y']:.1f} | λ_rel={res['lambda_rel_y']:.4f} | "
          f"k_c={res['k_c_y']:.4f} | η={res['eta_no_plano']:.4f}")
    print(f"Flambagem fora plano (l_ef={res['l_ef_z_m']} m):")
    print(f"  λ={res['lambda_z']:.1f} | λ_rel={res['lambda_rel_z']:.4f} | "
          f"k_c={res['k_c_z']:.4f} | η={res['eta_fora_plano']:.4f}")
    print()
    print(f"σ_c = {res['sigma_c_MPa']:.4f} MPa | σ_m = {res['sigma_m_MPa']:.4f} MPa")
    print(f"f_c0,d = {res['f_c0d_MPa']:.4f} MPa | f_m,d = {res['f_md_MPa']:.4f} MPa")
    print()
    ok = "✓ APROVADO" if res['ok'] else "✗ REPROVADO"
    print(f"η = {res['eta']:.4f}  ({res['plano_gov']} governa)  → {ok}")
    print(f"Norma: {res['norma']}")