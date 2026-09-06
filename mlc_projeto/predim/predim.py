"""
predim/predim.py — Varredura paramétrica v3 — Pórtico de 3 rótulas.

MUDANÇAS v3:
    - M_max calculado pela análise estrutural correta de 3 rótulas
    - Verificação de flexo-compressão na viga (EC5 §6.3.2) — M + N axial
    - Cumeeira: M=0 → verificação de tração perp. irrelevante (removida)
    - H_fund registrado para cada geometria
    - N_viga = H·cos(α) + R_v·sin(α) entra na verificação da viga

Verificações implementadas:
    ELU: Flexo-compressão viga §6.3.2 | Flambagem lateral §6.3.3
         Cisalhamento §6.1.7 | Apoio §6.1.5+§6.2.2
    ELS: Flecha §2.3.2.2 + Tab.7.2

Nota sobre cumeeira:
    No pórtico de 3 rótulas, M=0 na cumeeira → σ_t,90,d = 0.
    A verificação de EC5 §6.4.3 não governa.
    Mantida como verificação informativa com resultado η≈0.

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
from mlc_projeto.core.loads     import analisar_biarticulada

from mlc_projeto.checks.elu.flambagem_lateral import (
    calcular_l_ef, calcular_sigma_m_crit,
    calcular_lambda_rel_m, calcular_k_crit,
)
from mlc_projeto.checks.elu.apoio import f_c_alpha_d
from mlc_projeto.checks.els.creep import calcular_flecha_inst


# ── Flexo-compressão na viga — EC5 §6.3.2 ───────────────────────────────────

def eta_flexo_compressao_viga(
    mat:     GlulamMaterial,
    b:       float,
    h_x:    float,
    L:       float,
    l_ef:   float,
    M_d_Nm: float,
    N_d_N:  float,
) -> float:
    """
    Taxa de utilização em flexo-compressão na viga — EC5 §6.3.2 Eq. 6.23.

    Para a viga do pórtico de 3 rótulas, a força normal N é compressão.
    A verificação combina:
        (σ_c,0,d / (k_c · f_c,0,d))² + σ_m,d / f_m,d ≤ 1,0

    Comprimento efetivo para flambagem da viga:
        No plano do pórtico: l_ef = distância entre rótulas = L/2
        Fora do plano: l_ef = espaçamento entre terças (já verificado)

    Args:
        mat     : Material
        b       : Largura da seção (m)
        h_x     : Altura da seção no ponto verificado (m)
        L       : Vão da viga (m)
        l_ef    : Comprimento efetivo para flambagem fora do plano (m)
        M_d_Nm  : Momento de cálculo (N·m)
        N_d_N   : Força normal de cálculo (N) — compressão positiva

    Returns:
        η (taxa de utilização)
    """
    A    = b * h_x
    I_y  = b * h_x**3 / 12
    W_y  = b * h_x**2 / 6
    i_y  = math.sqrt(I_y / A)

    # Esbeltez no plano — biarticulada: l_ef = L
    lam_y  = L / i_y
    lam_rel_y = (lam_y / math.pi) * math.sqrt(mat.f_c0_k / mat.E0_05)

    beta_c = 0.1   # glulam
    k_y    = 0.5 * (1 + beta_c*(lam_rel_y - 0.3) + lam_rel_y**2)
    k_c_y  = min(1.0 / (k_y + math.sqrt(k_y**2 - lam_rel_y**2)), 1.0)

    sigma_c = N_d_N / A
    sigma_m = M_d_Nm / W_y

    eta = (sigma_c / (k_c_y * mat.f_c0_d))**2 + sigma_m / mat.f_m_d
    return eta


# ── Varredura principal ───────────────────────────────────────────────────────

def pre_dimensionar(
    g_area:        float,
    q_area:        float,
    params_vento:  ParametrosVento,
    L_v:           float,
    L_t:           float,
    classe:        str   = "GL24h",
    classe_servico: int  = 3,
    h0_range:      tuple = (0.40, 1.20, 0.05),
    alpha_range:   tuple = (3.0,  8.0,  0.5),
    b_range:       tuple = (0.10, 0.28, 0.02),
    l_ap_range:    tuple = (0.20, 0.60, 0.05),
    s_range:       tuple = (1.00, 2.10, 0.25),
    eta_max:       float = 1.0,
) -> pd.DataFrame:
    """
    Varredura paramétrica para pórtico de 3 rótulas.

    Para cada (h0, α, b, l_ap, s):
        1. Calcula M_max e N_viga pela análise de 3 rótulas
        2. Verifica flexo-compressão na viga (EC5 §6.3.2)
        3. Verifica flambagem lateral (EC5 §6.3.3)
        4. Verifica cisalhamento (EC5 §6.1.7)
        5. Verifica apoio (EC5 §6.1.5+§6.2.2)
        6. Verifica flecha ELS

    Returns:
        DataFrame com geometrias aprovadas, ordenado por η governante
    """
    mat_curta = GlulamMaterial(classe, classe_servico, duracao="curta")
    mat_longa = GlulamMaterial(classe, classe_servico, duracao="longa")

    # Vento
    res_vento  = calcular_vento(params_vento)
    w_C1bv_m2  = res_vento.pressoes["C1"]["barlavento_kNm2"]

    # Cargas lineares — pórtico intermediário: área tributária = L_t
    area_trib = L_t
    g_k = g_area * area_trib
    q_k = q_area * area_trib
    w_k = w_C1bv_m2 * area_trib

    # Combinação ELU_C2: 1,35G + 1,5W + 1,05Q
    q_C2 = 1.35*g_k + 1.5*w_k + 1.05*q_k

    # ELS
    q_S1     = g_k + q_k + 0.6*w_k   # característico
    k_def    = mat_longa.k_def
    lim_inst = L_v / 300
    lim_fin  = L_v / 250

    h0_vals    = np.arange(*h0_range)
    alpha_vals = np.arange(*alpha_range)
    b_vals     = np.arange(*b_range)
    l_ap_vals  = np.arange(*l_ap_range)
    s_vals     = np.arange(*s_range)

    resultados = []

    for h0 in h0_vals:
        for alpha in alpha_vals:
            for b in b_vals:

                h0_f  = round(float(h0),    3)
                al_f  = round(float(alpha),  2)
                b_f   = round(float(b),      3)
                al_r  = math.radians(al_f)

                geo = GeometriaViga(
                    L=L_v, h0=h0_f, alpha_deg=al_f, b=b_f
                )
                h_ap = geo.h_ap
                f_geo = h_ap - h0_f   # variação de altura

                if f_geo <= 0:
                    continue

                # ── Análise biarticulada (continuidade cumeeira)
                # AUD-007/AUD-010: modelo rígido explícito (legado do predim).
                # O parâmetro passou a ser obrigatório para que nenhum caminho
                # analise outra estrutura por omissão; a convergência com o
                # pipeline principal (H=0) é item da Onda 3 da auditoria.
                r_C2 = analisar_biarticulada(
                    q=q_C2, L=L_v, h0=h0_f, h_ap=h_ap,
                    alpha_rad=al_r, b=b_f,
                    desenvolve_empuxo=True,
                )

                M_max_Nm = r_C2["M_max_kNm"] * 1e3   # N·m
                N_viga_N = r_C2["N_apoio_kN"] * 1e3  # N
                V_max_N  = r_C2["R_v_kN"]     * 1e3  # N
                x_Mmax   = r_C2["x_Mmax_m"]
                H_fund   = r_C2["H_kN"]

                # Altura da seção no ponto de M_max
                h_Mmax = h0_f + x_Mmax * math.tan(al_r)

                for s in s_vals:
                    s_f  = round(float(s), 3)
                    l_ef = calcular_l_ef(s_f, restricao="continua_topo")

                    # ── 1. FLEXO-COMPRESSÃO §6.3.2 ────────────
                    eta_fc = eta_flexo_compressao_viga(
                        mat     = mat_curta,
                        b       = b_f,
                        h_x     = h_Mmax,
                        L       = L_v,
                        l_ef    = l_ef,
                        M_d_Nm  = M_max_Nm,
                        N_d_N   = N_viga_N,
                    )

                    # ── 2. FLAMBAGEM LATERAL §6.3.3 ───────────
                    sig_crit = calcular_sigma_m_crit(
                        mat_curta.E0_05, b_f, h_Mmax, l_ef
                    )
                    lam_rel  = calcular_lambda_rel_m(
                        mat_curta.f_m_k, sig_crit
                    )
                    k_crit   = calcular_k_crit(lam_rel)
                    W_y      = b_f * h_Mmax**2 / 6
                    sig_md   = M_max_Nm / W_y
                    eta_fl   = sig_md / (k_crit * mat_curta.f_m_d)

                    # ── 3. CISALHAMENTO §6.1.7 (b_ef = k_cr · b)
                    tau_d  = 1.5 * V_max_N / (mat_curta.k_cr * b_f * h0_f)
                    eta_ci = tau_d / mat_curta.f_v_d

                    # ── 4. ELS — FLECHA ───────────────────────
                    r_g  = analisar_biarticulada(
                        g_k, L_v, h0_f, h_ap, al_r, b_f,
                        desenvolve_empuxo=True)   # legado — ver nota acima
                    r_q  = analisar_biarticulada(
                        q_k, L_v, h0_f, h_ap, al_r, b_f,
                        desenvolve_empuxo=True)   # legado — ver nota acima

                    x_pts = geo.x
                    M_g_Nm = np.interp(x_pts, r_g["x"], r_g["M_x"]) * 1e3
                    M_q_Nm = np.interp(x_pts, r_q["x"], r_q["M_x"]) * 1e3

                    w_G,  _ = calcular_flecha_inst(geo, mat_longa, M_g_Nm)
                    w_Q1, _ = calcular_flecha_inst(geo, mat_longa, M_q_Nm)

                    w_fin    = w_G*(1+k_def) + w_Q1
                    eta_inst = w_Q1 / lim_inst
                    eta_fin  = w_fin / lim_fin
                    eta_els  = max(eta_inst, eta_fin)

                    # ── 5. APOIO §6.1.5+§6.2.2 — varrer l_ap ─
                    f_ca   = f_c_alpha_d(mat_curta, al_f)
                    sig_ca = V_max_N / (b_f * h0_f)
                    eta_ca = sig_ca / f_ca

                    for l_ap in l_ap_vals:
                        l_ap_f  = round(float(l_ap), 3)
                        sig_c90 = V_max_N / (b_f * l_ap_f)
                        eta_c90 = sig_c90 / mat_curta.f_c90_d
                        eta_ap  = max(eta_c90, eta_ca)

                        etas = {
                            "flexo_comp": eta_fc,
                            "flambagem":  eta_fl,
                            "cisalh.":    eta_ci,
                            "apoio":      eta_ap,
                            "ELS":        eta_els,
                        }
                        ok        = all(e <= eta_max for e in etas.values())
                        eta_gov   = max(etas.values())
                        verif_gov = max(etas, key=etas.get)

                        if ok:
                            resultados.append({
                                "h0_m":        h0_f,
                                "alpha_deg":   al_f,
                                "b_m":         b_f,
                                "l_ap_m":      l_ap_f,
                                "s_m":         s_f,
                                "h_ap_m":      round(h_ap,        3),
                                "h_Mmax_m":    round(h_Mmax,      3),
                                "x_Mmax_m":    round(x_Mmax,      3),
                                "h_b":         round(h_ap/b_f,    2),
                                "l_ef_m":      round(l_ef,        3),
                                "M_max_kNm":   round(r_C2["M_max_kNm"], 2),
                                "N_viga_kN":   round(r_C2["N_apoio_kN"],2),
                                "V_max_kN":    round(r_C2["R_v_kN"],    2),
                                "H_fund_kN":   round(H_fund,      2),
                                "eta_fc":      round(eta_fc,      4),
                                "eta_flamb":   round(eta_fl,      4),
                                "eta_cisalh":  round(eta_ci,      4),
                                "eta_apoio":   round(eta_ap,      4),
                                "eta_ELS":     round(eta_els,     4),
                                "eta_gov":     round(eta_gov,     4),
                                "verif_gov":   verif_gov,
                                "w_G_mm":      round(w_G  *1000,  2),
                                "w_Q1_mm":     round(w_Q1 *1000,  2),
                                "w_fin_mm":    round(w_fin*1000,  2),
                                "q_C2_kNm":    round(q_C2,       4),
                                "k_mod":       mat_curta.k_mod,
                            })

    df = pd.DataFrame(resultados)
    if not df.empty:
        df = df.sort_values(
            ["eta_gov", "l_ap_m", "s_m"]
        ).reset_index(drop=True)
    return df


# ── Relatório ─────────────────────────────────────────────────────────────────

def relatorio(df: pd.DataFrame, n: int = 25) -> None:
    """Relatório do pré-dimensionamento para pórtico de 3 rótulas."""
    print("=" * 114)
    print("  PRÉ-DIMENSIONAMENTO v3 — PÓRTICO DE 3 RÓTULAS")
    print("  ELU: Flexo-compressão §6.3.2 | Flambagem §6.3.3 | "
          "Cisalh. §6.1.7 | Apoio §6.1.5")
    print("  ELS: Flecha §2.3.2.2 + Tab.7.2")
    print("=" * 114)

    if df.empty:
        print("\n  Nenhuma geometria aprovada.")
        print("  Sugestões: aumentar h0, b ou l_ap.")
        print("=" * 114)
        return

    m0 = df.iloc[0]
    print(f"\n  ELU_C2: q={m0['q_C2_kNm']:.4f} kN/m | "
          f"k_mod={m0['k_mod']:.2f} (duração curta)")
    print(f"  Total aprovadas: {len(df)}\n")

    hdr = (
        f"  {'#':>3}  {'h0':>5}  {'α':>5}  {'b':>6}  "
        f"{'l_ap':>6}  {'s':>5}  {'h_ap':>7}  "
        f"{'M_max':>7}  {'N_vig':>7}  {'H_fun':>7}  "
        f"{'η_fc':>7}  {'η_fla':>7}  {'η_cis':>7}  "
        f"{'η_apo':>7}  {'η_ELS':>7}  {'η_gov':>7}  Governa"
    )
    print(hdr)
    print("  " + "-" * 108)

    for i, row in df.head(n).iterrows():
        print(
            f"  {i+1:>3}  {row['h0_m']:>5.2f}  {row['alpha_deg']:>5.1f}  "
            f"{row['b_m']:>6.3f}  {row['l_ap_m']:>6.3f}  "
            f"{row['s_m']:>5.2f}  {row['h_ap_m']:>7.3f}  "
            f"{row['M_max_kNm']:>7.1f}  {row['N_viga_kN']:>7.1f}  "
            f"{row['H_fund_kN']:>7.1f}  "
            f"{row['eta_fc']:>7.4f}  {row['eta_flamb']:>7.4f}  "
            f"{row['eta_cisalh']:>7.4f}  {row['eta_apoio']:>7.4f}  "
            f"{row['eta_ELS']:>7.4f}  {row['eta_gov']:>7.4f}  "
            f"{row['verif_gov']}"
        )

    m = df.iloc[0]
    print(f"\n  ── Geometria recomendada ──────────────────────────────────────")
    print(f"  h0           = {m['h0_m']} m")
    print(f"  α            = {m['alpha_deg']}°")
    print(f"  b            = {m['b_m']} m")
    print(f"  l_ap         = {m['l_ap_m']} m")
    print(f"  s            = {m['s_m']} m  → l_ef = {m['l_ef_m']} m")
    print(f"  h_ap         = {m['h_ap_m']} m")
    print(f"  h/b          = {m['h_b']}")
    print(f"  ─────────────────────────────────────────────────────────────")
    print(f"  M_max        = {m['M_max_kNm']:.2f} kN·m  em x={m['x_Mmax_m']:.3f} m")
    print(f"  N_viga       = {m['N_viga_kN']:.2f} kN  (flexo-compressão)")
    print(f"  V_max        = {m['V_max_kN']:.2f} kN")
    print(f"  H_fund       = {m['H_fund_kN']:.2f} kN  (empuxo → sapata)")
    print(f"  η flexo-comp = {m['eta_fc']:.4f}  (EC5 §6.3.2)")
    print(f"  η flambagem  = {m['eta_flamb']:.4f}  (EC5 §6.3.3)")
    print(f"  η cisalh.    = {m['eta_cisalh']:.4f}  (EC5 §6.1.7)")
    print(f"  η apoio      = {m['eta_apoio']:.4f}  (EC5 §6.1.5)")
    print(f"  η ELS        = {m['eta_ELS']:.4f}  (EC5 §2.3.2.2)")
    print(f"  η GOVERNANTE = {m['eta_gov']:.4f}  ← {m['verif_gov']}")
    print(f"  w_fin        = {m['w_fin_mm']:.2f} mm  "
          f"(limite L/250 = {20.25/250*1000:.1f} mm)")
    print("=" * 114)


# ── Execução direta ───────────────────────────────────────────────────────────

if __name__ == "__main__":

    params_vento = ParametrosVento(
        V0=45.0, S1=1.0, categoria="IV", classe="B", S3=1.0,
        L=20.25, H1=1.0, h=7.0, dist_portico=5.75,
    )

    print("PRÉ-DIMENSIONAMENTO v3 — Pórtico de 3 Rótulas\n")

    df = pre_dimensionar(
        g_area        = 1.50,
        q_area        = 0.25,
        params_vento  = params_vento,
        L_v           = 20.25,
        L_t           = 5.75,
        classe        = "GL24h",
        classe_servico=3,
        h0_range      = (0.40, 1.20, 0.05),
        alpha_range   = (3.0,  8.0,  0.5),
        b_range       = (0.10, 0.28, 0.02),
        l_ap_range    = (0.20, 0.55, 0.05),
        s_range       = (1.00, 2.10, 0.25),
    )

    relatorio(df, n=25)