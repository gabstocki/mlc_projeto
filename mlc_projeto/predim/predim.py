"""
predim/predim.py — Varredura paramétrica completa com carregamento correto.

CORREÇÃO v2:
    Área tributária da viga principal = L_t/2 (metade do vão das terças)
    Não L_t inteiro como estava anteriormente.

    Cada terça é biapoiada nos dois pórticos.
    Cada pórtico recebe metade da carga de cada terça.
    Por metro de viga: q = g_area × L_t/2

Variáveis varridas: h0, α, b, l_ap, s (espaçamento entre terças)
Para cada s: recalcula l_ef da viga principal e carga linear.

Combinação governante ELU_C2: 1,35G + 1,5W_C1bv + 1,05Q
k_mod = 0,90 (duração curta — vento dominante)

Referência: EN 1990 §6.4, EC5 §6.x
"""

from __future__ import annotations

import math
import numpy as np
import pandas as pd
from scipy.integrate import cumulative_trapezoid

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.wind      import ParametrosVento, calcular_vento

from mlc_projeto.checks.elu.cumeeira import (
    calcular_k_p, calcular_k_vol, calcular_sigma_t90d, K_DIS,
)
from mlc_projeto.checks.elu.flambagem_lateral import (
    calcular_l_ef, calcular_sigma_m_crit,
    calcular_lambda_rel_m, calcular_k_crit,
)
from mlc_projeto.checks.elu.apoio import f_c_alpha_d
from mlc_projeto.checks.els.creep import calcular_flecha_inst


def pre_dimensionar(
    g_area:        float,
    q_area:        float,
    params_vento:  ParametrosVento,
    L_v:           float,
    L_t:           float,
    classe:        str   = "GL24h",
    classe_servico: int  = 2,
    h0_range:      tuple = (0.60, 1.60, 0.10),
    alpha_range:   tuple = (3.0,  9.0,  0.5),
    b_range:       tuple = (0.14, 0.32, 0.02),
    l_ap_range:    tuple = (0.30, 0.70, 0.05),
    s_range:       tuple = (1.00, 2.10, 0.25),
    eta_max:       float = 1.0,
) -> pd.DataFrame:
    """
    Varredura paramétrica com carregamento correto e s varrido.

    Área tributária por metro de viga = L_t/2
    (metade do vão das terças, pois cada pórtico recebe metade da carga)

    Args:
        g_area        : Carga permanente por área (kN/m²)
        q_area        : Sobrecarga por área (kN/m²)
        params_vento  : Parâmetros de vento NBR 6123
        L_v           : Vão da viga principal (m)
        L_t           : Vão das terças = espaçamento entre pórticos (m)
        classe        : Classe resistente do glulam
        classe_servico: Classe de serviço
        h0_range      : (mín, máx, passo) para h0 (m)
        alpha_range   : (mín, máx, passo) para α (graus)
        b_range       : (mín, máx, passo) para b (m)
        l_ap_range    : (mín, máx, passo) para l_ap (m)
        s_range       : (mín, máx, passo) para espaçamento s entre terças (m)
        eta_max       : Taxa máxima para aprovação

    Returns:
        DataFrame com geometrias aprovadas, ordenado por η governante
    """

    # ── Material por duração ──────────────────────────────────
    mat_curta = GlulamMaterial(classe, classe_servico, duracao="curta")
    mat_longa = GlulamMaterial(classe, classe_servico, duracao="longa")

    # ── Vento — pressões por m² ───────────────────────────────
    res_vento  = calcular_vento(params_vento)
    w_C1bv_m2  = res_vento.pressoes["C1"]["barlavento_kNm2"]  # kN/m²

    # ── Área tributária CORRETA = L_t/2 ──────────────────────
    # (independe de s — s define apenas o l_ef)
    area_trib = L_t / 2   # m — área tributária por metro de viga

    g_k = g_area * area_trib   # kN/m — permanente
    q_k = q_area * area_trib   # kN/m — sobrecarga
    w_k = w_C1bv_m2 * area_trib  # kN/m — vento C1 barlavento

    # ── Combinação ELU_C2: 1,35G + 1,5W + 1,05Q ─────────────
    q_C2    = 1.35*g_k + 1.5*w_k + 1.05*q_k
    M_C2_Nm = (q_C2 * L_v**2 / 8) * 1e3   # N·m
    V_C2_N  = (q_C2 * L_v / 2)    * 1e3   # N

    # ── ELS — componentes separadas ───────────────────────────
    k_def   = mat_longa.k_def
    lim_inst = L_v / 300
    lim_fin  = L_v / 250

    # ── Varredura ─────────────────────────────────────────────
    h0_vals    = np.arange(*h0_range)
    alpha_vals = np.arange(*alpha_range)
    b_vals     = np.arange(*b_range)
    l_ap_vals  = np.arange(*l_ap_range)
    s_vals     = np.arange(*s_range)

    resultados = []

    for s in s_vals:
        s_f  = round(float(s), 3)
        l_ef = calcular_l_ef(s_f, restricao="continua_topo")

        for h0 in h0_vals:
            for alpha in alpha_vals:
                for b in b_vals:

                    geo = GeometriaViga(
                        L=L_v,
                        h0=round(float(h0), 3),
                        alpha_deg=round(float(alpha), 2),
                        b=round(float(b), 3),
                    )

                    h_ap = geo.h_ap
                    b_f  = float(b)
                    h0_f = float(h0)
                    al_f = float(alpha)

                    # ── 1. CUMEEIRA §6.4.3 ────────────────────
                    kp      = calcular_k_p(al_f)
                    kvol    = calcular_k_vol(b_f, h_ap)
                    sig_t90 = calcular_sigma_t90d(kp, M_C2_Nm, b_f, h_ap)
                    eta_cum = sig_t90 / (K_DIS * kvol * mat_curta.f_t90_d)

                    # ── 2. FLAMBAGEM LATERAL §6.3.3 ───────────
                    sig_crit = calcular_sigma_m_crit(
                        mat_curta.E0_05, mat_curta.G_mean,
                        b_f, h_ap, l_ef
                    )
                    lam_rel  = calcular_lambda_rel_m(mat_curta.f_m_k, sig_crit)
                    k_crit   = calcular_k_crit(lam_rel)
                    W_y      = b_f * h_ap**2 / 6
                    sig_md   = M_C2_Nm / W_y
                    eta_fl   = sig_md / (k_crit * mat_curta.f_m_d)

                    # ── 3. FLEXÃO SIMPLES §6.1.6 ──────────────
                    eta_fx   = sig_md / mat_curta.f_m_d

                    # ── 4. CISALHAMENTO §6.1.7 ────────────────
                    tau_d    = 1.5 * V_C2_N / (b_f * h0_f)
                    eta_ci   = tau_d / mat_curta.f_v_d

                    # ── 6. ELS — FLECHA ───────────────────────
                    x = geo.x
                    M_g_Nm = g_k * x * (L_v - x) / 2 * 1e3
                    M_q_Nm = q_k * x * (L_v - x) / 2 * 1e3

                    w_G,  _ = calcular_flecha_inst(geo, mat_longa, M_g_Nm)
                    w_Q1, _ = calcular_flecha_inst(geo, mat_longa, M_q_Nm)

                    w_fin    = w_G*(1+k_def) + w_Q1
                    eta_inst = w_Q1 / lim_inst
                    eta_fin  = w_fin / lim_fin
                    eta_els  = max(eta_inst, eta_fin)

                    # ── 5. APOIO §6.1.5 + §6.2.2 — varrer l_ap
                    f_ca    = f_c_alpha_d(mat_curta, al_f)
                    sig_ca  = V_C2_N / (b_f * h0_f)
                    eta_ca  = sig_ca / f_ca

                    for l_ap in l_ap_vals:
                        l_ap_f  = round(float(l_ap), 3)
                        sig_c90 = V_C2_N / (b_f * l_ap_f)
                        eta_c90 = sig_c90 / mat_curta.f_c90_d
                        eta_ap  = max(eta_c90, eta_ca)

                        etas = {
                            "cumeeira":  eta_cum,
                            "flambagem": eta_fl,
                            "flexao":    eta_fx,
                            "cisalh.":   eta_ci,
                            "apoio":     eta_ap,
                            "ELS":       eta_els,
                        }

                        ok        = all(e <= eta_max for e in etas.values())
                        eta_gov   = max(etas.values())
                        verif_gov = max(etas, key=etas.get)

                        if ok:
                            resultados.append({
                                "s_m":           s_f,
                                "h0_m":          round(h0_f,         3),
                                "alpha_deg":     round(al_f,          2),
                                "b_m":           round(b_f,           3),
                                "l_ap_m":        l_ap_f,
                                "h_ap_m":        round(h_ap,          3),
                                "h_b":           round(h_ap / b_f,    2),
                                "l_ef_m":        round(l_ef,          3),
                                "eta_cumeeira":  round(eta_cum,       4),
                                "eta_flambagem": round(eta_fl,        4),
                                "eta_flexao":    round(eta_fx,        4),
                                "eta_cisalh":    round(eta_ci,        4),
                                "eta_apoio":     round(eta_ap,        4),
                                "eta_ELS":       round(eta_els,       4),
                                "eta_gov":       round(eta_gov,       4),
                                "verif_gov":     verif_gov,
                                "w_G_mm":        round(w_G   *1000,   2),
                                "w_Q1_mm":       round(w_Q1  *1000,   2),
                                "w_fin_mm":      round(w_fin *1000,   2),
                                "M_C2_kNm":      round(q_C2*L_v**2/8, 2),
                                "V_C2_kN":       round(q_C2*L_v/2,    2),
                                "q_C2_kNm":      round(q_C2,          4),
                                "g_k_kNm":       round(g_k,           4),
                                "k_mod":         mat_curta.k_mod,
                                "area_trib_m":   round(area_trib,     3),
                            })

    df = pd.DataFrame(resultados)
    if not df.empty:
        df = df.sort_values(["eta_gov", "l_ap_m", "s_m"]).reset_index(drop=True)
    return df


def relatorio(df: pd.DataFrame, n: int = 30) -> None:
    """Relatório completo do pré-dimensionamento."""
    print("=" * 118)
    print("  PRÉ-DIMENSIONAMENTO COMPLETO v2 — EN 1990 + EC5")
    print("  Carregamento CORRETO: área tributária = L_t/2 = 2,875 m")
    print("  Combinação governante: ELU_C2 = 1,35G + 1,5W_C1bv + 1,05Q | k_mod = 0,90")
    print("  Varrendo: h0 | α | b | l_ap | s (espaçamento entre terças → l_ef)")
    print("=" * 118)

    if df.empty:
        print("\n  Nenhuma geometria aprovada.")
        print("=" * 118)
        return

    m0 = df.iloc[0]
    print(f"\n  Carregamento: g_k = {m0['g_k_kNm']:.4f} kN/m | "
          f"q_C2 = {m0['q_C2_kNm']:.4f} kN/m | "
          f"M_C2 = {m0['M_C2_kNm']:.1f} kN·m | "
          f"V_C2 = {m0['V_C2_kN']:.1f} kN")
    print(f"  Área tributária = {m0['area_trib_m']:.3f} m (L_t/2)")
    print(f"  Total de combinações aprovadas: {len(df)}\n")

    hdr = (
        f"  {'#':>3}  {'s':>5}  {'h0':>6}  {'α':>5}  {'b':>6}  "
        f"{'l_ap':>6}  {'h_ap':>7}  {'h/b':>5}  {'l_ef':>6}  "
        f"{'η_cum':>7}  {'η_fla':>7}  {'η_fle':>7}  "
        f"{'η_cis':>7}  {'η_apo':>7}  {'η_ELS':>7}  "
        f"{'η_gov':>7}  {'Governa'}"
    )
    print(hdr)
    print("  " + "-" * 112)

    for i, row in df.head(n).iterrows():
        print(
            f"  {i+1:>3}  {row['s_m']:>5.2f}  {row['h0_m']:>6.3f}  "
            f"{row['alpha_deg']:>5.1f}  {row['b_m']:>6.3f}  "
            f"{row['l_ap_m']:>6.3f}  {row['h_ap_m']:>7.3f}  "
            f"{row['h_b']:>5.1f}  {row['l_ef_m']:>6.3f}  "
            f"{row['eta_cumeeira']:>7.4f}  {row['eta_flambagem']:>7.4f}  "
            f"{row['eta_flexao']:>7.4f}  {row['eta_cisalh']:>7.4f}  "
            f"{row['eta_apoio']:>7.4f}  {row['eta_ELS']:>7.4f}  "
            f"{row['eta_gov']:>7.4f}  {row['verif_gov']}"
        )

    m = df.iloc[0]
    print(f"\n  ── Geometria recomendada ──────────────────────────────────────────")
    print(f"  Espaçamento terças s = {m['s_m']} m  → l_ef viga = {m['l_ef_m']} m")
    print(f"  h0    = {m['h0_m']} m   α = {m['alpha_deg']}°   b = {m['b_m']} m   l_ap = {m['l_ap_m']} m")
    print(f"  h_ap  = {m['h_ap_m']} m   h/b = {m['h_b']}")
    print(f"  ─────────────────────────────────────────────────────────────────")
    print(f"  M_C2           = {m['M_C2_kNm']:.2f} kN·m  |  V_C2 = {m['V_C2_kN']:.2f} kN")
    print(f"  k_mod          = {m['k_mod']:.2f} (duração curta — vento dominante)")
    print(f"  η cumeeira     = {m['eta_cumeeira']:.4f}")
    print(f"  η flambagem    = {m['eta_flambagem']:.4f}  (l_ef = {m['l_ef_m']} m)")
    print(f"  η flexão       = {m['eta_flexao']:.4f}")
    print(f"  η cisalhamento = {m['eta_cisalh']:.4f}")
    print(f"  η apoio        = {m['eta_apoio']:.4f}")
    print(f"  η ELS          = {m['eta_ELS']:.4f}")
    print(f"  η GOVERNANTE   = {m['eta_gov']:.4f}  ← {m['verif_gov']}")
    print(f"  w_G = {m['w_G_mm']:.2f} mm  |  w_Q1 = {m['w_Q1_mm']:.2f} mm  |  "
          f"w_fin = {m['w_fin_mm']:.2f} mm  (limite L/250 = {20.25/250*1000:.1f} mm)")
    print("=" * 118)


if __name__ == "__main__":

    params_vento = ParametrosVento(
        V0=45.0, S1=1.0, categoria="IV", classe="B", S3=1.0,
        L=20.25, H1=1.0, h=7.0, dist_portico=5.75,
    )

    print("PRÉ-DIMENSIONAMENTO v2 — carregamento corrigido\n")

    df = pre_dimensionar(
        g_area        = 1.50,
        q_area        = 0.25,
        params_vento  = params_vento,
        L_v           = 20.25,
        L_t           = 5.75,
        classe        = "GL24h",
        classe_servico= 2,
        h0_range      = (0.40, 1.20, 0.10),
        alpha_range   = (3.0,  9.0,  0.5),
        b_range       = (0.10, 0.28, 0.02),
        l_ap_range    = (0.20, 0.60, 0.05),
        s_range       = (1.00, 2.10, 0.25),
    )

    relatorio(df, n=30)