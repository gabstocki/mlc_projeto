"""
predim/predim.py — Varredura paramétrica completa com combinações EN 1990.

Executa todas as verificações EC5 simultaneamente para as combinações
ELU e ELS, usando os carregamentos corretos de cada combinação.

Combinação governante para as verificações de resistência:
    ELU_C2: 1,35G + 1,5W_C1bv + 1,05Q
    k_mod = 0,90 (duração curta — vento dominante)
    M_max = 990,65 kN·m | V_max = 195,68 kN

Verificações implementadas:
    ELU: Cumeeira §6.4.3 | Flambagem §6.3.3 | Flexão §6.1.6
         Cisalhamento §6.1.7 | Apoio §6.1.5+§6.2.2
    ELS: Flecha §2.3.2.2 + Tab.7.2

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
from mlc_projeto.core.loads     import carregamentos_com_vento

from mlc_projeto.checks.elu.cumeeira import (
    calcular_k_p, calcular_k_vol, calcular_sigma_t90d, K_DIS,
)
from mlc_projeto.checks.elu.flambagem_lateral import (
    calcular_l_ef, calcular_sigma_m_crit,
    calcular_lambda_rel_m, calcular_k_crit,
)
from mlc_projeto.checks.elu.apoio import f_c_alpha_d
from mlc_projeto.checks.els.creep import calcular_flecha_inst


# ── Varredura principal ───────────────────────────────────────────────────────

def pre_dimensionar(
    g_k_m2:       float,
    q_k_m2:       float,
    params_vento:  ParametrosVento,
    dist_portico:  float,
    L:             float,
    l_1:           float,
    classe:        str   = "GL24h",
    classe_servico: int  = 2,
    h0_range:      tuple = (0.60, 1.60, 0.10),
    alpha_range:   tuple = (3.0,  9.0,  0.5),
    b_range:       tuple = (0.14, 0.32, 0.02),
    l_ap_range:    tuple = (0.30, 0.70, 0.05),
    eta_max:       float = 1.0,
) -> pd.DataFrame:
    """
    Varredura paramétrica completa com combinações EN 1990 corretas.

    Usa duas instâncias de material:
    - mat_curta: k_mod=0,90 — combinação C2 (vento dominante) governa ELU
    - mat_longa: k_mod=0,70 — fluência ELS

    Para cada combinação (h0, α, b, l_ap), verifica:
        ELU_C2: Cumeeira | Flambagem | Flexão | Cisalhamento | Apoio
        ELS   : Flecha instantânea | Flecha final com fluência

    Args:
        g_k_m2        : Carga permanente por área (kN/m²)
        q_k_m2        : Sobrecarga por área (kN/m²)
        params_vento  : Parâmetros de vento NBR 6123
        dist_portico  : Distância entre pórticos (m)
        L             : Vão de cada pórtico (m)
        l_1           : Espaçamento entre terças (m)
        classe        : Classe resistente do glulam
        classe_servico: Classe de serviço (1, 2 ou 3)
        h0_range      : (mín, máx, passo) para h0 (m)
        alpha_range   : (mín, máx, passo) para α (graus)
        b_range       : (mín, máx, passo) para b (m)
        l_ap_range    : (mín, máx, passo) para l_ap (m)
        eta_max       : Taxa máxima para aprovação

    Returns:
        DataFrame com geometrias aprovadas, ordenado por η governante
    """

    # ── Material por duração ──────────────────────────────────
    mat_curta = GlulamMaterial(classe, classe_servico, duracao="curta")
    mat_longa = GlulamMaterial(classe, classe_servico, duracao="longa")

    # ── Cargas lineares ───────────────────────────────────────
    res_vento = calcular_vento(params_vento)
    d   = dist_portico
    g_k = g_k_m2 * d
    q_k = q_k_m2 * d

    # Cargas de vento lineares (kN/m)
    w_C1bv = res_vento.cargas["C1"]["barlavento_kNm"]
    w_C2st = res_vento.cargas["C2"]["sotavento_kNm"]

    # ── Combinação ELU_C2 governante ─────────────────────────
    # 1,35G + 1,5W_C1bv + 1,05Q — vento dominante
    q_C2     = 1.35*g_k + 1.5*w_C1bv + 1.05*q_k
    M_C2_Nm  = (q_C2 * L**2 / 8) * 1e3   # N·m
    V_C2_N   = (q_C2 * L / 2)    * 1e3   # N

    # ── Combinação ELS — componentes separadas ────────────────
    # ELS S3 quase-permanente → só G → base para fluência
    # ELS S1 característico → G + Q + 0,6W → flecha total
    q_g_ELS  = g_k          # permanente
    q_q_ELS  = q_k          # variável
    k_def    = mat_longa.k_def
    psi_2_Q  = 0.0

    # Limites de flecha
    lim_inst   = L / 300
    lim_fin    = L / 250

    # ── Comprimento efetivo de flambagem ─────────────────────
    l_ef = calcular_l_ef(l_1, restricao="continua_topo")

    # ── Varredura ─────────────────────────────────────────────
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

                h_ap = geo.h_ap
                b_f  = float(b)
                h0_f = float(h0)
                al_f = float(alpha)

                # ── ELU: Cumeeira §6.4.3 ─────────────────────
                kp      = calcular_k_p(al_f)
                kvol    = calcular_k_vol(b_f, h_ap)
                sig_t90 = calcular_sigma_t90d(kp, M_C2_Nm, b_f, h_ap)
                eta_cum = sig_t90 / (K_DIS * kvol * mat_curta.f_t90_d)

                # ── ELU: Flambagem §6.3.3 ─────────────────────
                sig_crit = calcular_sigma_m_crit(
                    mat_curta.E0_05, mat_curta.G_mean,
                    b_f, h_ap, l_ef
                )
                lam_rel  = calcular_lambda_rel_m(mat_curta.f_m_k, sig_crit)
                k_crit   = calcular_k_crit(lam_rel)
                W_y      = b_f * h_ap**2 / 6
                sig_md   = M_C2_Nm / W_y
                eta_fl   = sig_md / (k_crit * mat_curta.f_m_d)

                # ── ELU: Flexão §6.1.6 ───────────────────────
                eta_fx   = sig_md / mat_curta.f_m_d

                # ── ELU: Cisalhamento §6.1.7 ─────────────────
                tau_d    = 1.5 * V_C2_N / (b_f * h0_f)
                eta_ci   = tau_d / mat_curta.f_v_d

                # ── ELS: Flecha ───────────────────────────────
                x = geo.x
                M_g_Nm = q_g_ELS * x * (L - x) / 2 * 1e3
                M_q_Nm = q_q_ELS * x * (L - x) / 2 * 1e3

                w_G,  _ = calcular_flecha_inst(geo, mat_longa, M_g_Nm)
                w_Q1, _ = calcular_flecha_inst(geo, mat_longa, M_q_Nm)

                w_fin     = w_G*(1+k_def) + w_Q1*(1+psi_2_Q*k_def)
                eta_inst  = w_Q1 / lim_inst
                eta_fin   = w_fin / lim_fin
                eta_els   = max(eta_inst, eta_fin)

                # ── ELU: Apoio §6.1.5+§6.2.2 — varrer l_ap ──
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
                            "eta_ELS":       round(eta_els,       4),
                            "eta_gov":       round(eta_gov,       4),
                            "verif_gov":     verif_gov,
                            "w_G_mm":        round(w_G  * 1000,  2),
                            "w_Q1_mm":       round(w_Q1 * 1000,  2),
                            "w_fin_mm":      round(w_fin* 1000,  2),
                            "M_max_kNm":     round(q_C2*L**2/8,  2),
                            "V_max_kN":      round(q_C2*L/2,     2),
                            "q_C2_kNm":      round(q_C2,         4),
                            "k_mod":         mat_curta.k_mod,
                            "comb_gov":      "ELU_C2",
                        })

    df = pd.DataFrame(resultados)
    if not df.empty:
        df = df.sort_values(["eta_gov", "l_ap_m"]).reset_index(drop=True)
    return df


# ── Relatório ─────────────────────────────────────────────────────────────────

def relatorio(df: pd.DataFrame, n: int = 25) -> None:
    """Imprime relatório completo do pré-dimensionamento."""
    print("=" * 112)
    print("  PRÉ-DIMENSIONAMENTO COMPLETO — EN 1990 + EC5")
    print("  Combinação governante: ELU_C2 = 1,35G + 1,5W_C1bv + 1,05Q")
    print("  k_mod = 0,90 (duração curta — vento dominante)")
    print("  Verificações: Cumeeira §6.4.3 | Flambagem §6.3.3 | "
          "Flexão §6.1.6 | Cisalh. §6.1.7 | Apoio §6.1.5 | ELS Tab.7.2")
    print("=" * 112)

    if df.empty:
        print("\n  Nenhuma geometria aprovada.")
        print("  Sugestões:")
        print("  — Aumentar h0 (seção no apoio)")
        print("  — Aumentar b (largura)")
        print("  — Aumentar l_ap (placa de apoio)")
        print("  — Considerar GL28h")
        print("=" * 112)
        return

    print(f"\n  Combinação ELU_C2: q = {df['q_C2_kNm'].iloc[0]:.3f} kN/m | "
          f"M = {df['M_max_kNm'].iloc[0]:.1f} kN·m | "
          f"V = {df['V_max_kN'].iloc[0]:.1f} kN")
    print(f"  Total de geometrias aprovadas: {len(df)}")
    print(f"  Exibindo as {min(n, len(df))} melhores:\n")

    hdr = (
        f"  {'#':>3}  {'h0':>6}  {'α':>5}  {'b':>6}  {'l_ap':>6}  "
        f"{'h_ap':>7}  {'h/b':>5}  "
        f"{'η_cum':>7}  {'η_fla':>7}  "
        f"{'η_fle':>7}  {'η_cis':>7}  "
        f"{'η_apo':>7}  {'η_ELS':>7}  "
        f"{'η_gov':>7}  {'Governa'}"
    )
    print(hdr)
    print("  " + "-" * 106)

    for i, row in df.head(n).iterrows():
        print(
            f"  {i+1:>3}  {row['h0_m']:>6.3f}  {row['alpha_deg']:>5.1f}  "
            f"{row['b_m']:>6.3f}  {row['l_ap_m']:>6.3f}  "
            f"{row['h_ap_m']:>7.3f}  {row['h_b']:>5.1f}  "
            f"{row['eta_cumeeira']:>7.4f}  {row['eta_flambagem']:>7.4f}  "
            f"{row['eta_flexao']:>7.4f}  {row['eta_cisalh']:>7.4f}  "
            f"{row['eta_apoio']:>7.4f}  {row['eta_ELS']:>7.4f}  "
            f"{row['eta_gov']:>7.4f}  {row['verif_gov']}"
        )

    m = df.iloc[0]
    print(f"\n  ── Geometria recomendada ──────────────────────────────")
    print(f"  h0             = {m['h0_m']} m        (altura da seção no apoio)")
    print(f"  α              = {m['alpha_deg']}°       (inclinação da cumeeira)")
    print(f"  b              = {m['b_m']} m        (largura da seção)")
    print(f"  l_ap           = {m['l_ap_m']} m        (comprimento da placa de apoio)")
    print(f"  h_ap           = {m['h_ap_m']} m     (altura na cumeeira)")
    print(f"  h/b            = {m['h_b']}")
    print(f"  ───────────────────────────────────────────────────────")
    print(f"  Combinação     = ELU_C2 | k_mod = {m['k_mod']:.2f} | M = {m['M_max_kNm']:.1f} kN·m")
    print(f"  η cumeeira     = {m['eta_cumeeira']:.4f}  (EC5 §6.4.3)")
    print(f"  η flambagem    = {m['eta_flambagem']:.4f}  (EC5 §6.3.3)")
    print(f"  η flexão       = {m['eta_flexao']:.4f}  (EC5 §6.1.6)")
    print(f"  η cisalhamento = {m['eta_cisalh']:.4f}  (EC5 §6.1.7)")
    print(f"  η apoio        = {m['eta_apoio']:.4f}  (EC5 §6.1.5+§6.2.2)")
    print(f"  η ELS          = {m['eta_ELS']:.4f}  (EC5 §2.3.2.2)")
    print(f"  η GOVERNANTE   = {m['eta_gov']:.4f}  ← {m['verif_gov']}")
    print(f"  ───────────────────────────────────────────────────────")
    print(f"  w_G            = {m['w_G_mm']:.2f} mm")
    print(f"  w_Q1           = {m['w_Q1_mm']:.2f} mm")
    print(f"  w_fin          = {m['w_fin_mm']:.2f} mm  (limite L/250 = {20.25/250*1000:.1f} mm)")
    print("=" * 112)


# ── Execução direta ───────────────────────────────────────────────────────────

if __name__ == "__main__":

    params_vento = ParametrosVento(
        V0=45.0, S1=1.0, categoria="IV", classe="B", S3=1.0,
        L=20.25, H1=1.0, h=7.0, dist_portico=5.75,
    )

    print("Rodando varredura completa com EN 1990 + vento NBR 6123...")
    print("Combinação governante: ELU_C2 (vento C1 barlavento dominante)\n")

    df = pre_dimensionar(
        g_k_m2        = 1.50,
        q_k_m2        = 0.25,
        params_vento  = params_vento,
        dist_portico  = 5.75,
        L             = 20.25,
        l_1           = 5.75,
        classe        = "GL24h",
        classe_servico= 2,
        h0_range      = (0.60, 1.60, 0.10),
        alpha_range   = (3.0,  9.0,  0.5),
        b_range       = (0.14, 0.32, 0.02),
        l_ap_range    = (0.30, 0.70, 0.05),
    )

    relatorio(df, n=25)