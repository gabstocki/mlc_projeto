"""
checks/elu/cumeeira.py — Zona do ápice (cumeeira) — EC5 §6.4.3.

Viga monolítica de MLC de DUPLO-BISEL (biarticulada): NÃO há rótula na cumeeira.
M_ap = M(L/2) da análise de compatibilidade (em geral ≠ 0). Para duplo-bisel o
raio de curvatura r → ∞, logo h_ap/r = 0 e todos os termos em (h_ap/r) somem.

Verificações do ápice (EC5 §6.4.3):
  (a) Flexão no ápice — Eq. (6.41), (6.42), (6.43), (6.44):
        σ_m,d = k_l · 6·M_ap / (b·h_ap²) ≤ k_r · f_m,d
        k_l   = k1 = 1 + 1,4·tan(α_ap) + 5,4·tan²(α_ap)   (r → ∞)
        k_r   = 1,0                                        (duplo-bisel; §6.4.3(5))
  (b) Tração perpendicular à fibra — Eq. (6.50), (6.51), (6.52), (6.54), (6.56):
        σ_t,90,d = k_p · 6·M_ap / (b·h_ap²) ≤ k_dis · k_vol · f_t,90,d
        k_p   = 0,2·tan(α_ap)                              (r → ∞; Eq. 6.56/6.57)
        k_dis = 1,4                                        (duplo-bisel; Eq. 6.52)
        k_vol = (V0/V)^0,2 ≤ 1                             (Eq. 6.51; V0 = 0,01 m³)

Volumes (viga duplo-bisel simétrica):
    V_b  = b · L · [h_ap − 0,25·L·tan(α_ap)]               (volume total)
    V    = b · h_ap² · [1 − 0,25·tan(α_ap)] ≤ (2/3)·V_b    (volume tensionado)

α_ap = ângulo do bisel no meio da zona do ápice = inclinação do extradorso.

Referência: EC5 §6.4.3, Eq. 6.41–6.56.
"""

from __future__ import annotations

import math

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.loads     import Carregamentos


K_DIS   = 1.4    # fator de distribuição — duplo-bisel (EC5 Eq. 6.52)
K_R     = 1.0    # redução por curvatura das lâminas — duplo-bisel (EC5 §6.4.3(5))
V0_KVOL = 0.01   # volume de referência (m³) — EC5 Eq. 6.51


def calcular_k_p(alpha_deg: float) -> float:
    """k_p = 0,2 · tan(α_ap) — duplo-bisel sem curvatura (r → ∞), Eq. (6.56/6.57)."""
    return 0.2 * math.tan(math.radians(alpha_deg))


def calcular_k_l(alpha_deg: float) -> float:
    """
    k_l — fator de amplificação do momento no ápice, EC5 Eq. (6.43).
    Duplo-bisel: r → ∞ ⇒ h_ap/r = 0 ⇒ k_l = k1 (Eq. 6.44):
        k_l = 1 + 1,4·tan(α_ap) + 5,4·tan²(α_ap)
    """
    tan_a = math.tan(math.radians(alpha_deg))
    return 1.0 + 1.4 * tan_a + 5.4 * tan_a ** 2


def calcular_volumes_apice(
    b: float, h_ap: float, L: float, alpha_deg: float
) -> dict:
    """
    Volumes da zona do ápice — viga duplo-bisel (EC5 §6.4.3, Fig. 6.9).

        V_b = b·L·[h_ap − 0,25·L·tan(α_ap)]        volume total da viga
        V_ap = b·h_ap²·[1 − 0,25·tan(α_ap)]         volume tensionado (bruto)
        V   = min(V_ap, 2·V_b/3)                     volume tensionado (limitado)

    Referência: SCIA/EN 1995-1-1 §6.4.3(6) (Ref. Blaß).
    """
    tan_a = math.tan(math.radians(alpha_deg))
    V_b   = b * L * (h_ap - 0.25 * L * tan_a)
    V_ap  = b * h_ap ** 2 * (1.0 - 0.25 * tan_a)
    V     = min(V_ap, (2.0 / 3.0) * V_b) if V_b > 0 else V_ap
    return {"V_b_m3": V_b, "V_ap_bruto_m3": V_ap, "V_m3": V}


def calcular_k_vol(b: float, h_ap: float, L: float, alpha_deg: float) -> float:
    """
    k_vol = (V0 / V)^0,20 ≤ 1,0 — EC5 Eq. (6.51), com V da zona do ápice
    (duplo-bisel, Fig. 6.9), limitado a 2·V_b/3.
    """
    V = calcular_volumes_apice(b, h_ap, L, alpha_deg)["V_m3"]
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


def calcular_sigma_m_ap(
    k_l:     float,
    M_ap_Nm: float,
    b:       float,
    h_ap:    float,
) -> float:
    """σ_m,d = k_l · 6·M_ap / (b · h_ap²) — flexão no ápice, EC5 Eq. (6.42)."""
    if abs(M_ap_Nm) < 1e-9:
        return 0.0
    return k_l * 6.0 * abs(M_ap_Nm) / (b * h_ap ** 2)


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

    # ── Volumes da zona do ápice (Fig. 6.9) ───────────────────
    vols  = calcular_volumes_apice(b, h_ap, L, geo.alpha_deg)
    V     = vols["V_m3"]
    V_lim = V < vols["V_ap_bruto_m3"] - 1e-12   # True se limitado por 2Vb/3

    # ── (a) Tração perpendicular à fibra — Eq. (6.50/6.54) ────
    k_p    = calcular_k_p(geo.alpha_deg)
    k_vol  = calcular_k_vol(b, h_ap, L, geo.alpha_deg)
    sig_t90 = calcular_sigma_t90d(k_p, M_ap_Nm, b, h_ap)
    resist_t90 = K_DIS * k_vol * mat.f_t90_d
    eta_t90 = sig_t90 / resist_t90 if resist_t90 > 0 else 999.0

    # ── (b) Flexão no ápice — Eq. (6.41/6.42) ─────────────────
    k_l    = calcular_k_l(geo.alpha_deg)
    sig_m  = calcular_sigma_m_ap(k_l, M_ap_Nm, b, h_ap)
    resist_m = K_R * mat.f_m_d
    eta_m  = sig_m / resist_m if resist_m > 0 else 999.0

    eta = max(eta_t90, eta_m)
    verif_gov = "t90 (Eq.6.54)" if eta_t90 >= eta_m else "flexão (Eq.6.42)"

    return {
        "L_m":             L,
        "h_ap_m":          h_ap,
        "b_m":             b,
        "alpha_deg":       geo.alpha_deg,
        "alpha_ap_deg":    geo.alpha_deg,     # α_ap = inclinação do extradorso
        "M_cumeeira_kNm":  round(M_ap_kNm, 3),
        "sistema":         "biarticulada",
        # Volumes (Fig. 6.9)
        "V_b_m3":          round(vols["V_b_m3"], 4),
        "V_ap_bruto_m3":   round(vols["V_ap_bruto_m3"], 4),
        "V_m3":            round(V, 4),
        "V_limitado_2Vb3": V_lim,
        # Tração perpendicular (Eq. 6.50/6.54)
        "k_p":             round(k_p, 6),
        "k_vol":           round(k_vol, 4),
        "k_dis":           K_DIS,
        "sigma_t90d_MPa":  round(sig_t90 / 1e6, 4),
        "f_t90d_MPa":      round(mat.f_t90_d / 1e6, 4),
        "resistencia_MPa": round(resist_t90 / 1e6, 4),   # compat. (t90)
        "resist_t90_MPa":  round(resist_t90 / 1e6, 4),
        "eta_t90":         round(eta_t90, 4),
        # Flexão no ápice (Eq. 6.41/6.42)
        "k_l":             round(k_l, 4),
        "k_r":             K_R,
        "sigma_m_ap_MPa":  round(sig_m / 1e6, 4),
        "f_md_MPa":        round(mat.f_m_d / 1e6, 4),
        "resist_m_MPa":    round(resist_m / 1e6, 4),
        "eta_flexao_ap":   round(eta_m, 4),
        # Governante
        "eta":             round(float(eta), 4),
        "ok":              bool(eta <= 1.0),
        "verif_gov":       verif_gov,
        "justificativa": (
            "Peça monolítica de MLC — continuidade na cumeeira; "
            f"M_ap = {M_ap_kNm:.2f} kN·m (análise biarticulada). "
            f"Duplo-bisel: r→∞, k_r=1, k_l={k_l:.3f}; governa {verif_gov}"
        ),
        "norma": "EC5 §6.4.3 Eq. 6.41–6.56",
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
    print("ZONA DO ÁPICE — EC5 §6.4.3 (viga duplo-bisel, biarticulada)")
    print(f"M_ap = {res['M_cumeeira_kNm']:.2f} kN·m | α_ap = {res['alpha_ap_deg']}°")
    print(f"V_b = {res['V_b_m3']:.3f} m³ | V = {res['V_m3']:.3f} m³ "
          f"(limitado a 2Vb/3: {res['V_limitado_2Vb3']})")
    print(f"(a) Tração ⊥: k_p={res['k_p']:.4f} k_dis={res['k_dis']} "
          f"k_vol={res['k_vol']:.4f} → σ_t90={res['sigma_t90d_MPa']:.4f} MPa "
          f"≤ {res['resist_t90_MPa']:.4f} MPa | η={res['eta_t90']:.4f}")
    print(f"(b) Flexão ápice: k_l={res['k_l']:.4f} k_r={res['k_r']} → "
          f"σ_m={res['sigma_m_ap_MPa']:.4f} MPa ≤ {res['resist_m_MPa']:.4f} MPa | "
          f"η={res['eta_flexao_ap']:.4f}")
    print(f"η = {res['eta']:.4f} ({res['verif_gov']})  "
          f"{'OK' if res['ok'] else 'FALHA'}")
