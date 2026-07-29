"""
checks/elu/flexao.py — Flexo-compressão da viga — EC5 §6.3.2 + §6.3.3.

Viga biarticulada monolítica: M + N na seção de M_max.

Verificações:
    EC5 §6.3.2 Eq. (6.23) — instabilidade no plano (k_c,y)
    EC5 §6.3.2 Eq. (6.24) — instabilidade fora do plano (k_c,z)
    EC5 §6.3.3 Eq. (6.35) — compressão + flexão com flambagem lateral

Comprimentos efetivos:
    l_ef,y = L      (rótulas só nos apoios)
    l_ef,z = 0,9 · s  (terças — EC5 Tab. 6.1)
    l_ef,m = 0,9 · s  (flambagem lateral — Tab. 6.1)

Referência: EC5 §6.3.2 Eq. 6.23–6.24; §6.3.3 Eq. 6.32–6.35
"""

from __future__ import annotations

import math

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.loads     import Carregamentos
from mlc_projeto.checks.elu.flambagem_lateral import (
    calcular_l_ef,
    calcular_sigma_m_crit,
    calcular_lambda_rel_m,
    calcular_k_crit,
)

# EC5 §6.1.6 — fator de redistribuição para seção retangular
K_M = 0.7


def verifica_flexao(
    geo:  GeometriaViga,
    mat:  GlulamMaterial,
    load: Carregamentos,
    s:    float = 1.00,
) -> dict:
    """
    Verifica flexo-compressão da viga na seção de M_max.

    Eq. (6.23): (σ_c,0,d/(k_c,y·f_c,0,d))² + σ_m,y,d/f_m,d ≤ 1
    Eq. (6.24): (σ_c,0,d/(k_c,z·f_c,0,d))² + k_m·σ_m,y,d/f_m,d ≤ 1
    Eq. (6.35): σ_m,d/(k_crit·f_m,d) + (σ_c,d/(k_c,z·f_c,0,d))² ≤ 1

    Args:
        geo  : Geometria da viga
        mat  : Material com k_mod da duração da combinação
        load : Carregamentos (viga biarticulada)
        s    : Espaçamento entre terças (m)

    Returns:
        dict com tensões, fatores e η governante
    """
    gov = load.combinacao_ELU_governante()

    M_max_Nm = abs(gov.M_max_kNm) * 1e3
    N_d_N    = abs(gov.N_viga_kN) * 1e3   # compressão no eixo
    x_Mmax   = gov.x_Mmax_m

    h_x = float(geo.h(x_Mmax))
    b   = geo.b

    A_sec = b * h_x
    W_y   = b * h_x ** 2 / 6
    I_y   = b * h_x ** 3 / 12
    i_y   = math.sqrt(I_y / A_sec)

    beta_c = 0.1  # glulam — EC5 §6.3.2

    # ── Flambagem no plano (eixo y) ───────────────────────────
    # Biarticulada: rótulas apenas nos apoios → l_ef,y = L
    l_ef_y    = geo.L
    lam_y     = l_ef_y / i_y
    lam_rel_y = (lam_y / math.pi) * math.sqrt(mat.f_c0_k / mat.E0_05)
    k_y       = 0.5 * (1 + beta_c * (lam_rel_y - 0.3) + lam_rel_y ** 2)
    k_c_y     = min(1.0 / (k_y + math.sqrt(max(k_y ** 2 - lam_rel_y ** 2, 0.0))), 1.0)

    # ── Flambagem fora do plano (eixo z) ──────────────────────
    I_z       = h_x * b ** 3 / 12
    i_z       = math.sqrt(I_z / A_sec)
    l_ef_z    = calcular_l_ef(s, restricao="continua_topo", tipo_carga="distribuida")
    lam_z     = l_ef_z / i_z
    lam_rel_z = (lam_z / math.pi) * math.sqrt(mat.f_c0_k / mat.E0_05)
    k_z       = 0.5 * (1 + beta_c * (lam_rel_z - 0.3) + lam_rel_z ** 2)
    k_c_z     = min(1.0 / (k_z + math.sqrt(max(k_z ** 2 - lam_rel_z ** 2, 0.0))), 1.0)

    # ── Tensões (valores absolutos para taxa de utilização) ───
    sigma_c = N_d_N / A_sec
    sigma_m = M_max_Nm / W_y

    # ── EC5 §6.3.2 Eq. (6.23) e (6.24) ────────────────────────
    # Flexão uniaxial My: σ_m,z = 0
    eta_623 = (sigma_c / (k_c_y * mat.f_c0_d)) ** 2 + sigma_m / mat.f_m_d
    eta_624 = (sigma_c / (k_c_z * mat.f_c0_d)) ** 2 + K_M * sigma_m / mat.f_m_d

    # ── EC5 §6.3.3 — k_crit na mesma seção ───────────────────
    sigma_crit = calcular_sigma_m_crit(mat.E0_05, b, h_x, l_ef_z)
    lam_rel_m  = calcular_lambda_rel_m(mat.f_m_k, sigma_crit)
    k_crit     = calcular_k_crit(lam_rel_m)

    # ── EC5 §6.3.3 Eq. (6.35) ─────────────────────────────────
    eta_635 = (
        sigma_m / (k_crit * mat.f_m_d)
        + (sigma_c / (k_c_z * mat.f_c0_d)) ** 2
    )

    eta_gov = max(eta_623, eta_624, eta_635)
    if eta_gov == eta_635:
        verif_gov = "Eq.6.35"
    elif eta_gov == eta_623:
        verif_gov = "Eq.6.23"
    else:
        verif_gov = "Eq.6.24"

    return {
        "x_Mmax_m":       round(x_Mmax, 3),
        "h_x_m":          round(h_x, 4),
        "b_m":            b,
        "A_m2":           round(A_sec, 6),
        "M_max_kNm":      round(gov.M_max_kNm, 3),
        "N_d_kN":         round(gov.N_viga_kN, 3),
        "l_ef_y_m":       round(l_ef_y, 3),
        "lambda_y":       round(lam_y, 2),
        "lambda_rel_y":   round(lam_rel_y, 4),
        "k_c_y":          round(k_c_y, 4),
        "eta_no_plano":   round(eta_623, 4),
        "l_ef_z_m":       round(l_ef_z, 3),
        "lambda_z":       round(lam_z, 2),
        "lambda_rel_z":   round(lam_rel_z, 4),
        "k_c_z":          round(k_c_z, 4),
        "eta_fora_plano": round(eta_624, 4),
        "k_crit":         round(k_crit, 4),
        "lambda_rel_m":   round(lam_rel_m, 4),
        "eta_635":        round(eta_635, 4),
        "sigma_c_MPa":    round(sigma_c / 1e6, 4),
        "sigma_m_MPa":    round(sigma_m / 1e6, 4),
        "f_c0d_MPa":      round(mat.f_c0_d / 1e6, 4),
        "f_md_MPa":       round(mat.f_m_d / 1e6, 4),
        "k_mod":          mat.k_mod,
        "duracao":        mat.duracao,
        "eta":            round(eta_gov, 4),
        "ok":             eta_gov <= 1.0,
        "plano_gov":      verif_gov,
        "verif_gov":      verif_gov,
        "norma":          "EC5 §6.3.2 Eq.6.23+6.24 + §6.3.3 Eq.6.35",
    }


if __name__ == "__main__":

    from mlc_projeto.core.geometry  import GeometriaViga
    from mlc_projeto.core.materials import GlulamMaterial
    from mlc_projeto.core.wind      import ParametrosVento
    from mlc_projeto.core.loads     import carregamentos_com_vento

    geo = GeometriaViga(L=20.25, h0=0.60, alpha_deg=4.5, b=0.26)
    mat = GlulamMaterial(classe="GL24h", classe_servico=3, duracao="curta")

    params_vento = ParametrosVento(
        V0=45.0, S1=1.0, categoria="IV", classe="B", S3=1.0,
        L=20.25, H1=1.0, h=7.0, dist_portico=5.75,
    )

    load = carregamentos_com_vento(
        geo=geo, mat=mat,
        g_area=1.50, q_area=0.25,
        L_t=5.75, params_vento=params_vento,
    )

    res = verifica_flexao(geo, mat, load, s=2.53)

    print("FLEXO-COMPRESSÃO + LTB — EC5 §6.3.2 + §6.3.3")
    print(f"x={res['x_Mmax_m']} m | h={res['h_x_m']} m | b={res['b_m']} m")
    print(f"M={res['M_max_kNm']:.2f} kN·m | N={res['N_d_kN']:.2f} kN")
    print(f"η_6.23={res['eta_no_plano']:.4f} | η_6.24={res['eta_fora_plano']:.4f} "
          f"| η_6.35={res['eta_635']:.4f} | k_crit={res['k_crit']:.4f}")
    ok = "✓" if res["ok"] else "✗"
    print(f"η={res['eta']:.4f} ({res['verif_gov']}) → {ok}")
