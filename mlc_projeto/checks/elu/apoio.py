"""
checks/elu/apoio.py — Verificações no apoio da viga.

Duas verificações obrigatórias no apoio:

1. Compressão perpendicular às fibras na placa de apoio (EC5 §6.1.5):
       σ_c,90,d = R_d / (b · l_ap) ≤ k_c,90 · f_c,90,d

2. Compressão na direção inclinada — fórmula de Hankinson (EC5 §6.2.2):
       f_c,α,d = f_c,0,d · f_c,90,d / (f_c,0,d·sin²α + f_c,90,d·cos²α)
       σ_c,α,d = R_d / (b · h0) ≤ f_c,α,d

O ângulo α é a inclinação da viga no apoio.
l_ap é varrido simultaneamente com (h0, α, b) para encontrar
a combinação construtivamente viável com menor η governante.

Referência: EC5 §6.1.5, §6.2.2
"""

from __future__ import annotations

import math
import numpy as np
import pandas as pd

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.loads     import Carregamentos


# ── Fórmula de Hankinson — EC5 §6.2.2 ────────────────────────────────────────

def f_c_alpha_d(mat: GlulamMaterial, alpha_deg: float) -> float:
    """
    Resistência de cálculo à compressão na direção α — Hankinson (EC5 §6.2.2).

        f_c,α,d = f_c,0,d · f_c,90,d /
                  (f_c,0,d · sin²α + f_c,90,d · cos²α)

    Args:
        mat       : Material
        alpha_deg : Ângulo entre força e direção das fibras (graus)

    Returns:
        f_c,α,d (Pa)
    """
    a    = math.radians(alpha_deg)
    f_c0 = mat.f_c0_d
    f_c90= mat.f_c90_d
    return (f_c0 * f_c90) / (f_c0 * math.sin(a)**2 + f_c90 * math.cos(a)**2)


# ── Verificação pontual ───────────────────────────────────────────────────────

def verifica_apoio(
    geo:  GeometriaViga,
    mat:  GlulamMaterial,
    load: Carregamentos,
    l_ap: float = 0.40,
) -> dict:
    """
    Verifica compressão perpendicular e Hankinson no apoio.

    Args:
        geo  : Geometria da viga
        mat  : Material
        load : Carregamentos
        l_ap : Comprimento da placa de apoio (m)

    Returns:
        dict com resultados de ambas as verificações, η e ok
    """
    b         = geo.b
    h0        = geo.h0
    alpha_deg = geo.alpha_deg
    R_d_N     = load.V_max_ELU() * 1e3   # N

    # ── 1. Compressão perpendicular (EC5 §6.1.5) ─────────────
    sigma_c90 = R_d_N / (b * l_ap)
    eta_c90   = sigma_c90 / mat.f_c90_d

    # ── 2. Hankinson (EC5 §6.2.2) ────────────────────────────
    f_ca    = f_c_alpha_d(mat, alpha_deg)
    sigma_ca= R_d_N / (b * h0)
    eta_ca  = sigma_ca / f_ca

    eta_gov   = max(eta_c90, eta_ca)
    verif_gov = "perp." if eta_c90 >= eta_ca else "Hankinson"

    return {
        "L_m":             geo.L,
        "h0_m":            h0,
        "b_m":             b,
        "alpha_deg":       alpha_deg,
        "l_ap_m":          l_ap,
        "R_d_kN":          round(R_d_N / 1e3,      3),
        "sigma_c90d_MPa":  round(sigma_c90 / 1e6,  4),
        "f_c90d_MPa":      round(mat.f_c90_d / 1e6,4),
        "eta_c90":         round(eta_c90,           4),
        "ok_c90":          eta_c90 <= 1.0,
        "sigma_cad_MPa":   round(sigma_ca / 1e6,   4),
        "f_cad_MPa":       round(f_ca / 1e6,       4),
        "eta_ca":          round(eta_ca,            4),
        "ok_ca":           eta_ca <= 1.0,
        "eta":             round(eta_gov,           4),
        "ok":              eta_gov <= 1.0,
        "verif_gov":       verif_gov,
        "norma":           "EC5 §6.1.5 + §6.2.2",
    }


# ── Varredura acumulada: 5 verificações + l_ap ───────────────────────────────

def varrer_acumulado(
    mat:          GlulamMaterial,
    L:            float,
    g_k:          float,
    q_k:          float,
    l_1:          float = 5.75,
    h0_range:     tuple = (0.60, 1.30, 0.10),
    alpha_range:  tuple = (3.0,  8.5,  0.5),
    b_range:      tuple = (0.14, 0.28, 0.02),
    l_ap_range:   tuple = (0.30, 0.60, 0.05),
    eta_max:      float = 1.0,
) -> pd.DataFrame:
    """
    Varre (h0, α, b, l_ap) verificando SIMULTANEAMENTE:
        1. Cumeeira              — EC5 §6.4.3
        2. Flambagem lateral     — EC5 §6.3.3
        3. Flexão simples        — EC5 §6.1.6
        4. Cisalhamento          — EC5 §6.1.7
        5. Apoio (perp.+Hankinson) — EC5 §6.1.5 + §6.2.2

    Returns:
        DataFrame com geometrias aprovadas nas CINCO verificações,
        ordenadas pelo maior η governante.
    """
    from mlc_projeto.checks.elu.cumeeira import (
        calcular_k_p, calcular_k_vol, calcular_sigma_t90d, K_DIS,
    )
    from mlc_projeto.checks.elu.flambagem_lateral import (
        calcular_l_ef, calcular_sigma_m_crit,
        calcular_lambda_rel_m, calcular_k_crit,
    )

    l_ef       = calcular_l_ef(l_1, restricao="continua_topo")
    h0_vals    = np.arange(*h0_range)
    alpha_vals = np.arange(*alpha_range)
    b_vals     = np.arange(*b_range)
    l_ap_vals  = np.arange(*l_ap_range)

    resultados = []

    for h0 in h0_vals:
        for alpha in alpha_vals:
            for b in b_vals:

                geo = GeometriaViga(
                    L=L,
                    h0=round(float(h0), 3),
                    alpha_deg=round(float(alpha), 2),
                    b=round(float(b), 3),
                )

                h_ap  = geo.h_ap
                b_f   = float(b)
                h0_f  = float(h0)
                al_f  = float(alpha)

                # Carregamento ELU
                q_ELU    = 1.35 * g_k + 1.5 * q_k
                M_max_Nm = (q_ELU * L**2 / 8) * 1e3
                V_max_N  = (q_ELU * L / 2)    * 1e3

                # ── 1. CUMEEIRA §6.4.3 ───────────────────────
                k_p     = calcular_k_p(al_f)
                k_vol   = calcular_k_vol(b_f, h_ap)
                sig_t90 = calcular_sigma_t90d(k_p, M_max_Nm, b_f, h_ap)
                eta_cum = sig_t90 / (K_DIS * k_vol * mat.f_t90_d)

                # ── 2. FLAMBAGEM LATERAL §6.3.3 ──────────────
                sig_crit = calcular_sigma_m_crit(
                    mat.E0_05, b_f, h_ap, l_ef
                )
                lam_rel  = calcular_lambda_rel_m(mat.f_m_k, sig_crit)
                k_crit   = calcular_k_crit(lam_rel)
                W_y      = b_f * h_ap**2 / 6
                sig_md   = M_max_Nm / W_y
                eta_fl   = sig_md / (k_crit * mat.f_m_d)

                # ── 3. FLEXÃO SIMPLES §6.1.6 ─────────────────
                eta_fx   = sig_md / mat.f_m_d

                # ── 4. CISALHAMENTO §6.1.7 (b_ef = k_cr · b) ──
                tau_d    = 1.5 * V_max_N / (mat.k_cr * b_f * h0_f)
                eta_ci   = tau_d / mat.f_v_d

                # ── 5. APOIO — varrer l_ap ────────────────────
                # Hankinson (independe de l_ap)
                f_ca     = f_c_alpha_d(mat, al_f)
                sig_ca   = V_max_N / (b_f * h0_f)
                eta_ca   = sig_ca / f_ca

                # Para cada l_ap, verificar compressão perpendicular
                for l_ap in l_ap_vals:
                    l_ap_f   = round(float(l_ap), 3)
                    sig_c90  = V_max_N / (b_f * l_ap_f)
                    eta_c90  = sig_c90 / mat.f_c90_d
                    eta_ap   = max(eta_c90, eta_ca)

                    etas = {
                        "cumeeira":  eta_cum,
                        "flambagem": eta_fl,
                        "flexao":    eta_fx,
                        "cisalh.":   eta_ci,
                        "apoio":     eta_ap,
                    }
                    ok        = all(e <= eta_max for e in etas.values())
                    eta_gov   = max(etas.values())
                    verif_gov = max(etas, key=etas.get)

                    if ok:
                        resultados.append({
                            "h0_m":          round(h0_f,         3),
                            "alpha_deg":     round(al_f,          2),
                            "b_m":           round(b_f,           3),
                            "l_ap_m":        l_ap_f,
                            "h_ap_m":        round(h_ap,          3),
                            "h_b":           round(h_ap / b_f,    2),
                            "eta_cumeeira":  round(eta_cum,       4),
                            "eta_flambagem": round(eta_fl,        4),
                            "eta_flexao":    round(eta_fx,        4),
                            "eta_cisalh":    round(eta_ci,        4),
                            "eta_apoio":     round(eta_ap,        4),
                            "eta_gov":       round(eta_gov,       4),
                            "verif_gov":     verif_gov,
                            "sig_c90_MPa":   round(sig_c90/1e6,  4),
                            "f_c90d_MPa":    round(mat.f_c90_d/1e6, 4),
                            "f_cad_MPa":     round(f_ca/1e6,     4),
                            "V_d_kN":        round(V_max_N/1e3,  2),
                        })

    df = pd.DataFrame(resultados)
    if not df.empty:
        df = df.sort_values(["eta_gov", "l_ap_m"]).reset_index(drop=True)
    return df


def relatorio_acumulado(df: pd.DataFrame, n: int = 25) -> None:
    """Imprime relatório consolidado das cinco verificações com l_ap."""
    print("=" * 104)
    print("  VARREDURA ACUMULADA — 5 Verificações ELU + l_ap")
    print("  Cumeeira §6.4.3 | Flambagem §6.3.3 | Flexão §6.1.6 |"
          " Cisalhamento §6.1.7 | Apoio §6.1.5+§6.2.2")
    print("=" * 104)

    if df.empty:
        print("\n  Nenhuma geometria aprovada. Ampliar intervalos de varredura.")
        print("=" * 104)
        return

    print(f"\n  Total de combinações aprovadas: {len(df)}")
    print(f"  Exibindo as {min(n, len(df))} melhores:\n")

    header = (
        f"  {'#':>3}  {'h0':>6}  {'α':>5}  {'b':>6}  {'l_ap':>6}  "
        f"{'h_ap':>7}  {'h/b':>5}  "
        f"{'η_cum':>7}  {'η_fla':>7}  "
        f"{'η_fle':>7}  {'η_cis':>7}  "
        f"{'η_apo':>7}  {'η_gov':>7}  {'Governa'}"
    )
    print(header)
    print("  " + "-" * 98)

    for i, row in df.head(n).iterrows():
        linha = (
            f"  {i+1:>3}  {row['h0_m']:>6.3f}  {row['alpha_deg']:>5.1f}  "
            f"{row['b_m']:>6.3f}  {row['l_ap_m']:>6.3f}  "
            f"{row['h_ap_m']:>7.3f}  {row['h_b']:>5.1f}  "
            f"{row['eta_cumeeira']:>7.4f}  {row['eta_flambagem']:>7.4f}  "
            f"{row['eta_flexao']:>7.4f}  {row['eta_cisalh']:>7.4f}  "
            f"{row['eta_apoio']:>7.4f}  {row['eta_gov']:>7.4f}  "
            f"{row['verif_gov']}"
        )
        print(linha)

    melhor = df.iloc[0]
    print(f"\n  ── Geometria recomendada após 5 verificações ELU ──")
    print(f"  h0             = {melhor['h0_m']} m")
    print(f"  α              = {melhor['alpha_deg']}°")
    print(f"  b              = {melhor['b_m']} m")
    print(f"  l_ap           = {melhor['l_ap_m']} m")
    print(f"  h_ap           = {melhor['h_ap_m']} m")
    print(f"  h/b            = {melhor['h_b']}")
    print(f"  V_d            = {melhor['V_d_kN']:.2f} kN")
    print(f"  σ_c90,d        = {melhor['sig_c90_MPa']:.4f} MPa")
    print(f"  f_c90,d        = {melhor['f_c90d_MPa']:.4f} MPa")
    print(f"  f_c,α,d (Hank) = {melhor['f_cad_MPa']:.4f} MPa")
    print(f"  η cumeeira     = {melhor['eta_cumeeira']:.4f}")
    print(f"  η flambagem    = {melhor['eta_flambagem']:.4f}")
    print(f"  η flexão       = {melhor['eta_flexao']:.4f}")
    print(f"  η cisalhamento = {melhor['eta_cisalh']:.4f}")
    print(f"  η apoio        = {melhor['eta_apoio']:.4f}")
    print(f"  η governante   = {melhor['eta_gov']:.4f}  ({melhor['verif_gov']})")
    print("=" * 104)


# ── Execução direta ───────────────────────────────────────────────────────────

if __name__ == "__main__":

    mat = GlulamMaterial(
        classe="GL24h",
        classe_servico=2,
        duracao="longa",
    )

    dist_porticos = 5.75
    g_k = 1.50 * dist_porticos
    q_k = 0.25 * dist_porticos
    L   = 20.25
    l_1 = 5.75

    print(f"Material  : {mat.classe} | CS {mat.classe_servico} | longa duração")
    print(f"k_mod     = {mat.k_mod:.2f}")
    print(f"f_c90,d   = {mat.f_c90_d/1e6:.4f} MPa")
    print(f"f_c0,d    = {mat.f_c0_d/1e6:.4f} MPa\n")

    df = varrer_acumulado(
        mat=mat, L=L, g_k=g_k, q_k=q_k, l_1=l_1,
        h0_range=(0.60, 1.30, 0.10),
        alpha_range=(3.0, 8.5, 0.5),
        b_range=(0.14, 0.28, 0.02),
        l_ap_range=(0.30, 0.65, 0.05),
    )

    relatorio_acumulado(df, n=25)