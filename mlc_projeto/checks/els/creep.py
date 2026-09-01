"""
checks/els/creep.py — Flecha final com fluência.

Calcula a flecha instantânea por integração numérica de M(x)/(E·I(x))
e aplica os coeficientes de fluência k_def para obter a flecha final.

Limites EC5 Tabela 7.2:
    w_inst    ≤ L/300   (flecha instantânea sob carga variável)
    w_net,fin ≤ L/250   (flecha líquida final)

Fluência — EC5 §2.3.2.2:
    w_fin = w_G·(1+k_def) + w_Q1·(1+ψ₂·k_def)

k_def por classe de serviço (EC5 Tab. 3.2):
    CS1 = 0,60  |  CS2 = 0,80  |  CS3 = 2,00

Nota: ELS usa E_mean (não E_0,05) — EC5 §2.2.3

Referência: EC5 §2.3.2.2, Tab. 3.2, Tab. 7.2
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.integrate import cumulative_trapezoid

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.loads     import Carregamentos


# ── Integração numérica da flecha ─────────────────────────────────────────────

def calcular_flecha_inst(
    geo:   GeometriaViga,
    mat:   GlulamMaterial,
    M_x:   np.ndarray,
) -> tuple[float, np.ndarray]:
    """
    Flecha instantânea por integração numérica de κ(x) = M(x)/(E·I(x)).

    Condições de contorno: w(0) = w(L) = 0 (viga bi-apoiada).
    Usa E_mean para ELS conforme EC5 §2.2.3.

    Args:
        geo  : Geometria da viga
        mat  : Material (E_mean)
        M_x  : Diagrama de momento (N·m) nos pontos geo.x

    Returns:
        (w_max_m, w_x) — flecha máxima (m) e perfil completo (m)
    """
    x     = geo.x
    E     = mat.E0_mean                    # Pa — ELS usa E_mean
    I_x   = geo.I(x)                       # m⁴
    kappa = M_x / (E * I_x)               # curvatura (1/m)

    # Integração dupla com ajuste de condição de contorno
    theta = cumulative_trapezoid(kappa, x, initial=0.0)
    theta -= theta[-1] * x / geo.L        # garante w(L) = 0

    w = cumulative_trapezoid(theta, x, initial=0.0)
    w -= w[-1] * x / geo.L               # garante w(L) = 0

    return float(np.max(np.abs(w))), w


# ── Verificação principal ─────────────────────────────────────────────────────

def calcular_flecha_final(
    geo:   GeometriaViga,
    mat:   GlulamMaterial,
    load:  Carregamentos,
    psi_2: float = 0.0,
) -> dict:
    """
    Calcula flecha instantânea e final com fluência — EC5 §2.3.2.2.

    Componentes:
        w_G    : flecha sob carga permanente (kN/m → g_k)
        w_Q1   : flecha sob sobrecarga variável dominante (kN/m → q_k)

    Flecha final:
        w_fin = w_G·(1+k_def) + w_Q1·(1+ψ₂·k_def)

    Limites verificados (EC5 Tab. 7.2):
        w_inst = w_Q1           ≤ L/300
        w_net,fin = w_fin - w_G ≤ L/250  (descontando contra-flecha)

    Args:
        geo   : Geometria da viga
        mat   : Material
        load  : Carregamentos
        psi_2 : Coeficiente ψ₂ para sobrecarga (cobertura inacessível = 0,0)

    Returns:
        dict com w_inst, w_fin, limites, η e ok
    """
    x = geo.x

    # ── Diagramas de momento por componente (N·m) ─────────────
    M_g_Nm  = load.M_g()  * 1e3    # permanente
    M_q_Nm  = load.M_q()  * 1e3    # variável dominante

    # ── Flechas instantâneas ──────────────────────────────────
    w_G_max,  w_G_x  = calcular_flecha_inst(geo, mat, M_g_Nm)
    w_Q1_max, w_Q1_x = calcular_flecha_inst(geo, mat, M_q_Nm)

    # ── k_def por classe de serviço ───────────────────────────
    k_def = mat.k_def

    # ── Flecha final — EC5 §2.3.2.2 ──────────────────────────
    w_fin = w_G_max * (1 + k_def) + w_Q1_max * (1 + psi_2 * k_def)

    # ── Flecha líquida final (descontando contra-flecha se houver) ──
    # Sem contra-flecha: w_net,fin = w_fin
    w_net_fin = w_fin

    # ── Limites EC5 Tab. 7.2 ─────────────────────────────────
    lim_inst    = geo.L / 300
    lim_net_fin = geo.L / 250

    eta_inst    = w_Q1_max / lim_inst
    eta_net_fin = w_net_fin / lim_net_fin
    eta         = max(eta_inst, eta_net_fin)

    return {
        # Geometria
        "L_m":          geo.L,
        "h_ap_m":       geo.h_ap,
        "b_m":          geo.b,
        # k_def
        "k_def":        k_def,
        "psi_2":        psi_2,
        # Flechas instantâneas (mm para leitura)
        "w_G_mm":       round(w_G_max   * 1000, 2),
        "w_Q1_mm":      round(w_Q1_max  * 1000, 2),
        # Flecha final
        "w_fin_mm":     round(w_fin     * 1000, 2),
        "w_net_fin_mm": round(w_net_fin * 1000, 2),
        # Limites
        "lim_inst_mm":  round(lim_inst    * 1000, 2),
        "lim_fin_mm":   round(lim_net_fin * 1000, 2),
        # Taxas de utilização
        "eta_inst":     round(eta_inst,    4),
        "eta_net_fin":  round(eta_net_fin, 4),
        "eta":          round(eta,         4),
        "ok":           eta <= 1.0,
        "verif_gov":    "inst" if eta_inst >= eta_net_fin else "net_fin",
        # Referência
        "norma":        "EC5 §2.3.2.2, Tab. 7.2",
    }


# ── Flecha por integração direta (simplificada para varredura) ────────────────

def flecha_max_approx(
    q:    float,
    L:    float,
    E:    float,
    b:    float,
    h_ap: float,
    n:    int = 80,
) -> float:
    """
    Flecha máxima aproximada por integração numérica para viga duplo-bisel.

    Usa a geometria variável h(x) calculada internamente.
    Mais rápido que instanciar GeometriaViga + Carregamentos na varredura.

    Args:
        q    : Carga uniforme (N/m)
        L    : Vão (m)
        E    : Módulo de elasticidade (Pa)
        b    : Largura (m)
        h_ap : Altura na cumeeira (m)
        n    : Número de pontos de integração

    Returns:
        w_max (m)
    """
    x      = np.linspace(0, L, n)
    # h(x) para duplo-bisel — simetria
    h0     = h_ap - h_ap * (1 - 0.5)   # não temos h0 aqui
    # Alternativa: interpolar h linearmente de h0 até h_ap
    # h(x) = h0 + (h_ap - h0) * 2x/L para x <= L/2, simétrico
    # Sem h0 explícito, usar aproximação com I_medio
    I_x    = b * (h_ap * np.where(
                    x <= L/2,
                    (0.5 + x/L),
                    (0.5 + (L-x)/L)
                ))**3 / 12
    M_x    = q * x * (L - x) / 2      # N·m
    kappa  = M_x / (E * I_x)

    theta  = cumulative_trapezoid(kappa, x, initial=0.0)
    theta -= theta[-1] * x / L

    w      = cumulative_trapezoid(theta, x, initial=0.0)
    w     -= w[-1] * x / L

    return float(np.max(np.abs(w)))


# ── Varredura acumulada: ELU completo + ELS ───────────────────────────────────

def varrer_acumulado(
    mat:          GlulamMaterial,
    L:            float,
    g_k:          float,
    q_k:          float,
    l_1:          float = 5.75,
    h0_range:     tuple = (0.60, 1.30, 0.10),
    alpha_range:  tuple = (3.0,  8.5,  0.5),
    b_range:      tuple = (0.14, 0.28, 0.02),
    l_ap_range:   tuple = (0.30, 0.65, 0.05),
    psi_2:        float = 0.0,
    eta_max:      float = 1.0,
) -> pd.DataFrame:
    """
    Varre (h0, α, b, l_ap) verificando SIMULTANEAMENTE:

    ELU:
        1. Cumeeira              — EC5 §6.4.3
        2. Flambagem lateral     — EC5 §6.3.3
        3. Flexão simples        — EC5 §6.1.6
        4. Cisalhamento          — EC5 §6.1.7
        5. Apoio (perp.+Hankinson) — EC5 §6.1.5 + §6.2.2

    ELS:
        6. Flecha instantânea    — w_inst ≤ L/300
        7. Flecha final fluência — w_net,fin ≤ L/250

    Returns:
        DataFrame com geometrias aprovadas em TODAS as verificações,
        ordenadas pelo maior η governante.
    """
    from mlc_projeto.checks.elu.cumeeira import (
        calcular_k_p, calcular_k_vol, calcular_sigma_t90d, K_DIS,
    )
    from mlc_projeto.checks.elu.flambagem_lateral import (
        calcular_l_ef, calcular_sigma_m_crit,
        calcular_lambda_rel_m, calcular_k_crit,
    )
    from mlc_projeto.checks.elu.apoio import f_c_alpha_d

    l_ef       = calcular_l_ef(l_1, restricao="continua_topo")
    k_def      = mat.k_def
    lim_inst   = L / 300
    lim_fin    = L / 250

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

                # ── Carregamento ELU ──────────────────────────
                q_ELU    = 1.35 * g_k + 1.5 * q_k
                M_max_Nm = (q_ELU * L**2 / 8) * 1e3
                V_max_N  = (q_ELU * L / 2)    * 1e3

                # ── 1. CUMEEIRA §6.4.3 ────────────────────────
                k_p     = calcular_k_p(al_f)
                k_vol   = calcular_k_vol(b_f, h_ap, L, al_f)
                sig_t90 = calcular_sigma_t90d(k_p, M_max_Nm, b_f, h_ap)
                eta_cum = sig_t90 / (K_DIS * k_vol * mat.f_t90_d)

                # ── 2. FLAMBAGEM LATERAL §6.3.3 ───────────────
                sig_crit = calcular_sigma_m_crit(
                    mat.E0_05, b_f, h_ap, l_ef
                )
                lam_rel  = calcular_lambda_rel_m(mat.f_m_k, sig_crit)
                k_crit   = calcular_k_crit(lam_rel)
                W_y      = b_f * h_ap**2 / 6
                sig_md   = M_max_Nm / W_y
                eta_fl   = sig_md / (k_crit * mat.f_m_d)

                # ── 3. FLEXÃO SIMPLES §6.1.6 ──────────────────
                eta_fx   = sig_md / mat.f_m_d

                # ── 4. CISALHAMENTO §6.1.7 (b_ef = k_cr · b) ───
                tau_d    = 1.5 * V_max_N / (mat.k_cr * b_f * h0_f)
                eta_ci   = tau_d / mat.f_v_d

                # ── 6-7. ELS — FLECHA ─────────────────────────
                # Diagramas de momento ELS (N·m)
                x      = geo.x
                E_mean = mat.E0_mean
                I_x    = geo.I(x)

                M_g_Nm  = g_k * x * (L - x) / 2 * 1e3
                M_q_Nm  = q_k * x * (L - x) / 2 * 1e3

                w_G_max,  _ = calcular_flecha_inst(geo, mat, M_g_Nm)
                w_Q1_max, _ = calcular_flecha_inst(geo, mat, M_q_Nm)

                w_fin     = (w_G_max * (1 + k_def)
                             + w_Q1_max * (1 + psi_2 * k_def))
                w_net_fin = w_fin

                eta_inst    = w_Q1_max / lim_inst
                eta_net_fin = w_net_fin / lim_fin
                eta_els     = max(eta_inst, eta_net_fin)

                # ── 5. APOIO §6.1.5 + §6.2.2 — varrer l_ap ───
                f_ca    = f_c_alpha_d(mat, al_f)
                sig_ca  = V_max_N / (b_f * h0_f)
                eta_ca  = sig_ca / f_ca

                for l_ap in l_ap_vals:
                    l_ap_f  = round(float(l_ap), 3)
                    sig_c90 = V_max_N / (b_f * l_ap_f)
                    eta_c90 = sig_c90 / mat.f_c90_d
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
                            # ELS detalhes
                            "w_G_mm":        round(w_G_max  *1000, 2),
                            "w_Q1_mm":       round(w_Q1_max *1000, 2),
                            "w_fin_mm":      round(w_fin    *1000, 2),
                            "lim_inst_mm":   round(lim_inst *1000, 2),
                            "lim_fin_mm":    round(lim_fin  *1000, 2),
                            "V_d_kN":        round(V_max_N/1e3,   2),
                        })

    df = pd.DataFrame(resultados)
    if not df.empty:
        df = df.sort_values(["eta_gov", "l_ap_m"]).reset_index(drop=True)
    return df


def relatorio_acumulado(df: pd.DataFrame, n: int = 25) -> None:
    """Imprime relatório consolidado de todas as verificações ELU + ELS."""
    print("=" * 108)
    print("  VARREDURA COMPLETA — ELU (5 verif.) + ELS (flecha)")
    print("  EC5: §6.4.3 | §6.3.3 | §6.1.6 | §6.1.7 | §6.1.5+§6.2.2 | §2.3.2.2 + Tab.7.2")
    print("=" * 108)

    if df.empty:
        print("\n  Nenhuma geometria aprovada em todas as verificações.")
        print("  Sugestões:")
        print("  - Aumentar h0 ou h_ap (reduz flecha)")
        print("  - Aumentar b (reduz flecha e cisalhamento)")
        print("  - Aumentar l_ap (reduz compressão perpendicular)")
        print("=" * 108)
        return

    print(f"\n  Total de combinações aprovadas: {len(df)}")
    print(f"  Exibindo as {min(n, len(df))} melhores:\n")

    header = (
        f"  {'#':>3}  {'h0':>6}  {'α':>5}  {'b':>6}  {'l_ap':>6}  "
        f"{'h_ap':>7}  {'h/b':>5}  "
        f"{'η_cum':>7}  {'η_fla':>7}  "
        f"{'η_fle':>7}  {'η_cis':>7}  "
        f"{'η_apo':>7}  {'η_ELS':>7}  "
        f"{'η_gov':>7}  {'Governa'}"
    )
    print(header)
    print("  " + "-" * 102)

    for i, row in df.head(n).iterrows():
        linha = (
            f"  {i+1:>3}  {row['h0_m']:>6.3f}  {row['alpha_deg']:>5.1f}  "
            f"{row['b_m']:>6.3f}  {row['l_ap_m']:>6.3f}  "
            f"{row['h_ap_m']:>7.3f}  {row['h_b']:>5.1f}  "
            f"{row['eta_cumeeira']:>7.4f}  {row['eta_flambagem']:>7.4f}  "
            f"{row['eta_flexao']:>7.4f}  {row['eta_cisalh']:>7.4f}  "
            f"{row['eta_apoio']:>7.4f}  {row['eta_ELS']:>7.4f}  "
            f"{row['eta_gov']:>7.4f}  {row['verif_gov']}"
        )
        print(linha)

    melhor = df.iloc[0]
    print(f"\n  ── Geometria recomendada — ELU completo + ELS ──")
    print(f"  h0             = {melhor['h0_m']} m")
    print(f"  α              = {melhor['alpha_deg']}°")
    print(f"  b              = {melhor['b_m']} m")
    print(f"  l_ap           = {melhor['l_ap_m']} m")
    print(f"  h_ap           = {melhor['h_ap_m']} m")
    print(f"  h/b            = {melhor['h_b']}")
    print(f"  η cumeeira     = {melhor['eta_cumeeira']:.4f}")
    print(f"  η flambagem    = {melhor['eta_flambagem']:.4f}")
    print(f"  η flexão       = {melhor['eta_flexao']:.4f}")
    print(f"  η cisalhamento = {melhor['eta_cisalh']:.4f}")
    print(f"  η apoio        = {melhor['eta_apoio']:.4f}")
    print(f"  η ELS          = {melhor['eta_ELS']:.4f}")
    print(f"  η governante   = {melhor['eta_gov']:.4f}  ({melhor['verif_gov']})")
    print(f"  w_G            = {melhor['w_G_mm']:.2f} mm")
    print(f"  w_Q1           = {melhor['w_Q1_mm']:.2f} mm")
    print(f"  w_fin          = {melhor['w_fin_mm']:.2f} mm")
    print(f"  Limite inst.   = {melhor['lim_inst_mm']:.2f} mm  (L/300)")
    print(f"  Limite fin.    = {melhor['lim_fin_mm']:.2f} mm  (L/250)")
    print("=" * 108)


# ── Execução direta ───────────────────────────────────────────────────────────

if __name__ == "__main__":

    mat = GlulamMaterial(
        classe="GL24h",
        classe_servico=3,
        duracao="longa",
    )

    dist_porticos = 5.75
    g_k = 1.50 * dist_porticos
    q_k = 0.25 * dist_porticos
    L   = 20.25
    l_1 = 5.75

    print(f"Material  : {mat.classe} | CS {mat.classe_servico} | longa duração")
    print(f"k_mod     = {mat.k_mod:.2f} | k_def = {mat.k_def:.2f}")
    print(f"E_mean    = {mat.E0_mean/1e9:.2f} GPa")
    print(f"Limites   : w_inst ≤ L/300 = {L/300*1000:.1f} mm")
    print(f"            w_fin  ≤ L/250 = {L/250*1000:.1f} mm\n")

    df = varrer_acumulado(
        mat=mat, L=L, g_k=g_k, q_k=q_k, l_1=l_1,
        h0_range=(0.60, 1.30, 0.10),
        alpha_range=(3.0, 8.5, 0.5),
        b_range=(0.14, 0.28, 0.02),
        l_ap_range=(0.30, 0.65, 0.05),
        psi_2=0.0,
    )

    relatorio_acumulado(df, n=25)