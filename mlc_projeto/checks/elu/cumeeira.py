"""
checks/elu/cumeeira.py — Tração perpendicular na cumeeira.

Viga monolítica de MLC (biarticulada): NÃO há rótula na cumeeira.
M_ap = M(L/2) da análise de compatibilidade (em geral ≠ 0).

    σ_t,90,d = k_p · 6·M_ap / (b·h_ap²)     EC5 §6.4.3 Eq. (6.54)
    σ_t,90,d ≤ k_dis · k_vol · f_t,90,d

    k_p   = 0,2 · tan(α)   (duplo-bisel, r → ∞)
    k_vol = (V0/V)^0,2 ≤ 1
    k_dis = 1,4            (duplo-bisel)

Referência: EC5 §6.4.3 Eq. 6.50, 6.51, 6.54
"""

from __future__ import annotations

import math

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.loads     import Carregamentos


K_DIS   = 1.4    # fator de distribuição — duplo-bisel (EC5 §6.4.3)
V0_KVOL = 0.01   # volume de referência (m³) — EC5 Eq. 6.51


def calcular_k_p(alpha_deg: float) -> float:
    """k_p = 0,2 · tan(α) — viga duplo-bisel sem curvatura (r → ∞)."""
    return 0.2 * math.tan(math.radians(alpha_deg))


def calcular_k_vol(b: float, h_ap: float, f_vol: float = 0.15) -> float:
    """
    k_vol = (V0 / V)^0,20 ≤ 1,0
    V = b · h_ap · (f_vol · h_ap)  — volume de tensão na zona de cumeeira
    """
    V = b * h_ap * (f_vol * h_ap)
    if V <= 0:
        return 1.0
    return min((V0_KVOL / V) ** 0.20, 1.0)


def calcular_sigma_t90d(
    k_p:     float,
    M_ap_Nm: float,
    b:       float,
    h_ap:    float,
) -> float:
    """σ_t,90,d = k_p · 6·M_ap / (b · h_ap²) — EC5 Eq. (6.54)."""
    if abs(M_ap_Nm) < 1e-9:
        return 0.0
    return k_p * 6.0 * abs(M_ap_Nm) / (b * h_ap ** 2)


def verifica_cumeeira(
    geo:  GeometriaViga,
    mat:  GlulamMaterial,
    load: Carregamentos,
) -> dict:
    """
    Tração perpendicular na cumeeira — EC5 §6.4.3.

    M_ap da combinação ELU governante (análise biarticulada).
    """
    gov  = load.combinacao_ELU_governante()
    L    = geo.L
    h_ap = geo.h_ap
    b    = geo.b

    M_ap_kNm = gov.M_cumeeira_kNm
    M_ap_Nm  = abs(M_ap_kNm) * 1e3

    k_p   = calcular_k_p(geo.alpha_deg)
    k_vol = calcular_k_vol(b, h_ap)
    sigma = calcular_sigma_t90d(k_p, M_ap_Nm, b, h_ap)
    resist = K_DIS * k_vol * mat.f_t90_d
    eta    = sigma / resist if resist > 0 else 999.0

    return {
        "L_m":             L,
        "h_ap_m":          h_ap,
        "b_m":             b,
        "alpha_deg":       geo.alpha_deg,
        "M_cumeeira_kNm":  round(M_ap_kNm, 3),
        "sistema":         "biarticulada",
        "k_p":             round(k_p, 6),
        "k_vol":           round(k_vol, 4),
        "k_dis":           K_DIS,
        "sigma_t90d_MPa":  round(sigma / 1e6, 4),
        "f_t90d_MPa":      round(mat.f_t90_d / 1e6, 4),
        "resistencia_MPa": round(resist / 1e6, 4),
        "eta":             round(eta, 4),
        "ok":              eta <= 1.0,
        "justificativa": (
            "Peça monolítica de MLC — continuidade na cumeeira; "
            f"M_ap = {M_ap_kNm:.2f} kN·m da análise biarticulada"
        ),
        "norma": "EC5 §6.4.3 Eq. 6.50, 6.51, 6.54",
    }


if __name__ == "__main__":
    from mlc_projeto.core.wind import ParametrosVento
    from mlc_projeto.core.loads import carregamentos_com_vento

    geo = GeometriaViga(L=20.25, h0=0.70, alpha_deg=10.0, b=0.30)
    mat = GlulamMaterial(classe="GL24h", classe_servico=3, duracao="curta")
    pv = ParametrosVento(
        V0=45, S1=1, categoria="IV", classe="B", S3=1,
        L=20.25, H1=geo.h_ap - geo.h0, h=7, dist_portico=5.75,
    )
    load = carregamentos_com_vento(
        geo=geo, mat=mat, g_area=1.5, q_area=0.25, L_t=5.75, params_vento=pv,
    )
    res = verifica_cumeeira(geo, mat, load)
    print("CUMEEIRA EC5 §6.4.3 — biarticulada")
    print(f"M_ap={res['M_cumeeira_kNm']:.2f} kN·m | σ={res['sigma_t90d_MPa']:.4f} MPa")
    print(f"η={res['eta']:.4f}  {'OK' if res['ok'] else 'FALHA'}")
