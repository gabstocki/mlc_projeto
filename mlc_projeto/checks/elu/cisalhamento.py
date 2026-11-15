"""
checks/elu/cisalhamento.py — Verificação de cisalhamento no apoio.

Verifica a tensão de cisalhamento na seção crítica (apoio),
onde o cortante é máximo e a altura da seção é mínima.

Condição EC5 §6.1.7 Eq. 6.13 (+ A1:2008):
    τ_d = 1,5 · V_d / (b_ef · h_ef) ≤ f_v,d
    b_ef = k_cr · b
    k_cr = 0,67 para glulam (madeira maciça e glulam)

Para viga sem entalhe: h_ef = h0 (altura no apoio).
Para viga com entalhe: h_ef reduzida por fator k_v (EC5 §6.5.2).

REFERENCIAL (issue 12) — eixo da peça:
    A tensão de cisalhamento atua na seção transversal, que é PERPENDICULAR ao
    eixo centroidal da peça (inclinado θ = atan(tan α / 2) ≈ 5° face à horizontal).
    Logo V_d é o cortante TRANSVERSAL (⊥ ao eixo):

        V = R_v·cos θ − H·sen θ          (não a reação vertical R_v)

    Para o arco abatido, o grande empuxo H (≈8·R_v) cancela grande parte de
    R_v·cos θ, de modo que V ≪ R_v (a reação de apoio é quase toda axial, N).
    Usar R_v (vertical) como cortante misturava referenciais e era ~3× conservador.
    A compressão no apoio (§6.1.5, apoio.py) permanece referida à VERTICAL R_v,
    pois atua na face horizontal do intradorso — plano distinto da seção.

Referência: EC5 §6.1.7 Eq. 6.13, §6.5.2
"""

from __future__ import annotations

import math
import numpy as np
import pandas as pd

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.loads     import Carregamentos


# ── Fator k_v para entalhe — EC5 §6.5.2 ─────────────────────────────────────

def calcular_k_v(
    h:       float,
    h_n:     float,
    x:       float,
    alpha_n: float,
    i:       float = 1.0,
) -> float:
    """
    Fator de redução k_v para viga com entalhe no apoio — EC5 §6.5.2.

    k_v = min(
        k_n · (1 + 1,1·i^1,5 / √h) / √(h·(0,6·(h_n/h)² + (1-(h_n/h))·(x/h)·tan(α_n))),
        1,0
    )

    Args:
        h      : Altura da seção no apoio (m)
        h_n    : Profundidade do entalhe (m)
        x      : Distância do entalhe ao apoio (m)
        alpha_n: Ângulo do entalhe (graus) — 90° para entalhe reto
        i      : Relação entre comprimento e profundidade do entalhe

    Returns:
        k_v (adimensional, ≤ 1,0)
    """
    # k_n depende da classe do glulam — EC5 §6.5.2 (3)
    k_n = 6.5  # para glulam (valor típico)

    alpha_rad = math.radians(alpha_n)
    r = h_n / h   # relação de entalhe

    numerador   = k_n * (1 + 1.1 * i**1.5 / math.sqrt(h * 1000))
    denominador = math.sqrt(
        h * 1000 * (0.6 * r**2 + (1 - r) * (x / h) * math.tan(alpha_rad))
    )

    if denominador == 0:
        return 1.0

    return min(numerador / denominador, 1.0)


# ── Verificação principal ─────────────────────────────────────────────────────

def verifica_cisalhamento(
    geo:        GeometriaViga,
    mat:        GlulamMaterial,
    load:       Carregamentos,
    entalhe:    bool  = False,
    h_n:        float = 0.0,
    x_n:        float = 0.0,
    alpha_n:    float = 90.0,
    t_rasgo_m:  float = 0.0,
) -> dict:
    """
    Verifica resistência ao cisalhamento no apoio — EC5 §6.1.7 Eq. 6.13.

    Junto ao apoio a seção é cortada pelo rasgo da chapa embutida (issue 70):
    b_ef = k_cr · (b − t_rasgo).

    Condição:
        τ_d = 1,5 · V_d / (b_ef · h_ef) ≤ f_v,d
        b_ef = k_cr · b  (EC5 §6.1.7 A1)

    A seção crítica é o apoio, onde:
    - Cortante é máximo: V_d = q_ELU · L / 2
    - Altura é mínima: h_ef = h0 (sem entalhe) ou h0 - h_n (com entalhe)

    Args:
        geo     : Geometria da viga
        mat     : Material
        load    : Carregamentos
        entalhe : True se houver entalhe no apoio (EC5 §6.5.2)
        h_n     : Profundidade do entalhe (m) — só se entalhe=True
        x_n     : Distância do entalhe ao apoio (m)
        alpha_n : Ângulo do entalhe (graus) — 90° = entalhe reto

    Returns:
        dict com τ_d, f_v,d, η e ok
    """
    # ── Cortante TRANSVERSAL máximo no apoio (⊥ ao eixo) — issue 12 ───────────
    # Referencial do eixo da peça: V = R_v·cosθ − H·senθ (não a reação vertical).
    # Máximo entre TODAS as combinações ELU (o vento assimétrico pode governar
    # o cortante transversal, ≠ da combinação que governa |M|).
    comb_V  = load.combinacao_ELU_Vtransversal()
    V_d_kN  = load.V_viga_max_ELU()   # kN — |V ⊥ eixo| governante
    V_d_N   = V_d_kN * 1e3            # N
    R_v_kN  = abs(comb_V.V_max_kN)    # reação vertical da mesma combinação (comparação)
    N_axis_kN = comb_V.N_viga_kN      # esforço normal no eixo (mesma combinação)
    theta_deg = math.degrees(math.atan(math.tan(geo.alpha_rad) / 2.0))

    # ── Altura efetiva no apoio ───────────────────────────────
    h0    = geo.h0
    b     = geo.b

    if entalhe and h_n > 0:
        # Com entalhe: h_ef = h0 - h_n, corrigida por k_v
        h_ef = h0 - h_n
        k_v  = calcular_k_v(h0, h_n, x_n, alpha_n)
        nota = f"Com entalhe h_n={h_n}m — k_v={k_v:.4f}"
    else:
        h_ef = h0
        k_v  = 1.0
        nota = "Sem entalhe"

    # ── Tensão de cisalhamento ────────────────────────────────
    # EC5 §6.1.7 Eq. 6.13 + A1: b_ef = k_cr · b
    # Com entalhe: k_v reduz a resistência efetiva (EC5 §6.5.2)
    k_cr  = mat.k_cr
    b_ef  = k_cr * (b - t_rasgo_m)
    tau_d = 1.5 * V_d_N / (b_ef * k_v * h_ef)  # Pa

    # ── Resistência de cálculo ────────────────────────────────
    f_vd  = mat.f_v_d                          # Pa

    # ── Taxa de utilização ────────────────────────────────────
    eta   = tau_d / f_vd

    return {
        # Geometria
        "L_m":        geo.L,
        "h0_m":       h0,
        "h_ef_m":     round(h_ef, 4),
        "b_m":        b,
        "k_cr":       k_cr,
        "b_ef_m":     round(b_ef, 6),
        "t_rasgo_m":  t_rasgo_m,
        "k_v":        round(k_v, 4),
        # Esforços — referencial do eixo da peça (issue 12)
        "V_d_kN":         round(V_d_kN, 3),      # cortante transversal (⊥ eixo)
        "R_v_vertical_kN": round(R_v_kN, 3),     # reação vertical (comparação)
        "N_axis_kN":       round(N_axis_kN, 3),  # esforço normal no eixo
        "theta_eixo_deg":  round(theta_deg, 3),  # inclinação do eixo θ=atan(tanα/2)
        "comb_V_gov":      comb_V.nome,          # combinação que governa V transversal
        # Tensões
        "tau_d_MPa":  round(tau_d / 1e6, 4),
        "f_vd_MPa":   round(f_vd  / 1e6, 4),
        # Resultado
        "eta":        round(eta, 4),
        "ok":         eta <= 1.0,
        "nota":       nota,
        "referencial": (
            "cortante ⊥ ao eixo V=R_v·cosθ−H·senθ (não a reação vertical); "
            f"θ={theta_deg:.2f}°; R_v={R_v_kN:.1f} kN → V={V_d_kN:.1f} kN"
        ),
        # Referência
        "norma":      "EC5 §6.1.7 Eq. 6.13 (b_ef=k_cr·(b − t_rasgo)); eixo da peça (issue 12)",
    }


# ── Varredura acumulada: cumeeira + flambagem + flexão + cisalhamento ─────────

def varrer_acumulado(
    mat:         GlulamMaterial,
    L:           float,
    g_k:         float,
    q_k:         float,
    l_1:         float = 5.75,
    h0_range:    tuple = (0.60, 1.30, 0.10),
    alpha_range: tuple = (3.0,  8.5,  0.5),
    b_range:     tuple = (0.14, 0.28, 0.02),
    eta_max:     float = 1.0,
) -> pd.DataFrame:
    """
    Varre (h0, α, b) verificando SIMULTANEAMENTE:
        1. Cumeeira          — EC5 §6.4.3
        2. Flambagem lateral — EC5 §6.3.3
        3. Flexão simples    — EC5 §6.1.6
        4. Cisalhamento      — EC5 §6.1.7

    Returns:
        DataFrame com geometrias aprovadas nas QUATRO verificações,
        ordenadas pelo maior η (verificação governante).
    """
    from mlc_projeto.checks.elu.cumeeira import (
        calcular_k_p, calcular_k_vol, calcular_sigma_t90d, K_DIS,
    )
    from mlc_projeto.checks.elu.flambagem_lateral import (
        calcular_l_ef, calcular_sigma_m_crit,
        calcular_lambda_rel_m, calcular_k_crit,
    )


    h0_vals    = np.arange(*h0_range)
    alpha_vals = np.arange(*alpha_range)
    b_vals     = np.arange(*b_range)

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

                # Carregamento ELU
                q_ELU    = 1.35 * g_k + 1.5 * q_k
                M_max_Nm = (q_ELU * L**2 / 8) * 1e3
                V_max_N  = (q_ELU * L / 2)    * 1e3

                # ── 1. CUMEEIRA §6.4.3 ───────────────────────
                k_p     = calcular_k_p(float(alpha))
                k_vol   = calcular_k_vol(b_f, h_ap, L, float(alpha))
                sig_t90 = calcular_sigma_t90d(k_p, M_max_Nm, b_f, h_ap)
                res_t90 = K_DIS * k_vol * mat.f_t90_d
                eta_cum = sig_t90 / res_t90

                # ── 2. FLAMBAGEM LATERAL §6.3.3 ──────────────
                # F-07: +2h da nota da EC5 Tab. 6.1 (depende de h).
                l_ef = calcular_l_ef(
                    l_1, restricao="continua_topo",
                    posicao_carga="borda_comprimida", h_m=h_ap,
                )
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

                # ── Todas aprovadas? ──────────────────────────
                etas = {
                    "cumeeira":    eta_cum,
                    "flambagem":   eta_fl,
                    "flexao":      eta_fx,
                    "cisalhamento": eta_ci,
                }
                ok      = all(e <= eta_max for e in etas.values())
                eta_gov = max(etas.values())
                verif_gov = max(etas, key=etas.get)

                if ok:
                    resultados.append({
                        "h0_m":           round(h0_f,         3),
                        "alpha_deg":      round(float(alpha),  2),
                        "b_m":            round(b_f,           3),
                        "h_ap_m":         round(h_ap,          3),
                        "h_b":            round(h_ap / b_f,    2),
                        "eta_cumeeira":   round(eta_cum,       4),
                        "eta_flambagem":  round(eta_fl,        4),
                        "eta_flexao":     round(eta_fx,        4),
                        "eta_cisalh":     round(eta_ci,        4),
                        "eta_gov":        round(eta_gov,       4),
                        "verif_gov":      verif_gov,
                        "tau_d_MPa":      round(tau_d / 1e6,  4),
                        "f_vd_MPa":       round(mat.f_v_d/1e6, 4),
                        "V_d_kN":         round(V_max_N/1e3,  2),
                    })

    df = pd.DataFrame(resultados)
    if not df.empty:
        df = df.sort_values("eta_gov").reset_index(drop=True)
    return df


def relatorio_acumulado(df: pd.DataFrame, n: int = 20) -> None:
    """Imprime relatório consolidado das quatro verificações."""
    print("=" * 96)
    print("  VARREDURA ACUMULADA — 4 Verificações ELU")
    print("  Cumeeira §6.4.3 | Flambagem §6.3.3 | Flexão §6.1.6 | Cisalhamento §6.1.7")
    print("=" * 96)

    if df.empty:
        print("\n  Nenhuma geometria aprovada nas quatro verificações.")
        print("=" * 96)
        return

    print(f"\n  Total de geometrias aprovadas: {len(df)}")
    print(f"  Exibindo as {min(n, len(df))} melhores:\n")

    header = (
        f"  {'#':>3}  {'h0(m)':>6}  {'α(°)':>5}  {'b(m)':>6}  "
        f"{'h_ap':>7}  {'h/b':>5}  "
        f"{'η_cum':>7}  {'η_fla':>7}  "
        f"{'η_fle':>7}  {'η_cis':>7}  "
        f"{'η_gov':>7}  {'Governa'}"
    )
    print(header)
    print("  " + "-" * 90)

    for i, row in df.head(n).iterrows():
        linha = (
            f"  {i+1:>3}  {row['h0_m']:>6.3f}  {row['alpha_deg']:>5.1f}  "
            f"{row['b_m']:>6.3f}  {row['h_ap_m']:>7.3f}  "
            f"{row['h_b']:>5.1f}  "
            f"{row['eta_cumeeira']:>7.4f}  "
            f"{row['eta_flambagem']:>7.4f}  "
            f"{row['eta_flexao']:>7.4f}  "
            f"{row['eta_cisalh']:>7.4f}  "
            f"{row['eta_gov']:>7.4f}  {row['verif_gov']}"
        )
        print(linha)

    melhor = df.iloc[0]
    print(f"\n  ── Geometria recomendada após 4 verificações ──")
    print(f"  h0              = {melhor['h0_m']} m")
    print(f"  α               = {melhor['alpha_deg']}°")
    print(f"  b               = {melhor['b_m']} m")
    print(f"  h_ap            = {melhor['h_ap_m']} m")
    print(f"  h/b             = {melhor['h_b']}")
    print(f"  η cumeeira      = {melhor['eta_cumeeira']:.4f}")
    print(f"  η flambagem     = {melhor['eta_flambagem']:.4f}")
    print(f"  η flexão        = {melhor['eta_flexao']:.4f}")
    print(f"  η cisalhamento  = {melhor['eta_cisalh']:.4f}")
    print(f"  τ_d             = {melhor['tau_d_MPa']:.4f} MPa")
    print(f"  f_v,d           = {melhor['f_vd_MPa']:.4f} MPa")
    print(f"  η governante    = {melhor['eta_gov']:.4f}  ({melhor['verif_gov']})")
    print("=" * 96)


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

    print(f"Material : {mat.classe} | CS {mat.classe_servico} | longa duração")
    print(f"k_mod    = {mat.k_mod:.2f} | "
          f"f_v,k = {mat.f_v_k/1e6:.3f} MPa | "
          f"f_v,d = {mat.f_v_d/1e6:.4f} MPa\n")

    df = varrer_acumulado(
        mat=mat, L=L, g_k=g_k, q_k=q_k, l_1=l_1,
        h0_range=(0.60, 1.30, 0.10),
        alpha_range=(3.0, 8.5, 0.5),
        b_range=(0.14, 0.28, 0.02),
    )

    relatorio_acumulado(df, n=20)