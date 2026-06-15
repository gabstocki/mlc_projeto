"""
checks/elu/flexao.py — Verificação de flexão simples.

Verifica a tensão de flexão na seção crítica da viga de duplo-bisel.
Para carga simétrica, o momento máximo ocorre no meio do vão (cumeeira).

Condição: σ_m,d = M_d / W_y ≤ f_m,d     (EC5 §6.1.6 Eq. 6.11)

Nota: Esta verificação complementa a flambagem lateral (§6.3.3).
A diferença é que aqui f_m,d não é reduzida por k_crit — verifica
a resistência plena da seção sem penalização por instabilidade.

Referência: EC5 §6.1.6, Eq. 6.11
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.loads     import Carregamentos


# ── Verificação principal ─────────────────────────────────────────────────────

def verifica_flexao(
    geo:  GeometriaViga,
    mat:  GlulamMaterial,
    load: Carregamentos,
) -> dict:
    """
    Verifica resistência à flexão simples — EC5 §6.1.6 Eq. 6.11.

    Condição:
        σ_m,d = M_d / W_y ≤ f_m,d

    A seção crítica é o meio do vão (cumeeira), onde:
    - Momento é máximo: M_d = q·L²/8
    - Altura é máxima: h = h_ap → W_y = b·h_ap²/6

    Para viga de seção variável, W_y cresce junto com M — por isso
    a posição crítica real deve ser verificada numericamente.
    O método pontual na cumeeira é conservador para carga simétrica.

    Args:
        geo  : Geometria da viga
        mat  : Material
        load : Carregamentos

    Returns:
        dict com σ_m,d, f_m,d, η e ok
    """
    # ── Seção crítica — cumeeira ──────────────────────────────
    h_ap = geo.h_ap
    b    = geo.b
    W_y  = b * h_ap**2 / 6       # m³

    # ── Momento máximo ELU ────────────────────────────────────
    M_max_Nm = load.M_max_ELU() * 1e3    # kN·m → N·m

    # ── Tensão atuante ────────────────────────────────────────
    sigma_md = M_max_Nm / W_y            # Pa

    # ── Resistência de cálculo ────────────────────────────────
    f_md = mat.f_m_d                     # Pa

    # ── Taxa de utilização ────────────────────────────────────
    eta = sigma_md / f_md

    # ── Verificação ao longo do vão ───────────────────────────
    # Encontra a posição real de η máximo para seção variável
    x       = geo.x
    M_x_Nm  = load.M_ELU() * 1e3        # N·m ao longo do vão
    W_y_x   = geo.W(x)                  # m³ ao longo do vão
    eta_x   = (M_x_Nm / W_y_x) / f_md
    x_crit  = float(x[np.argmax(eta_x)])
    eta_max = float(np.max(eta_x))

    return {
        # Geometria
        "L_m":          geo.L,
        "h_ap_m":       h_ap,
        "b_m":          b,
        # Seção crítica (cumeeira)
        "W_y_m3":       round(W_y,       6),
        "M_max_kNm":    round(load.M_max_ELU(), 2),
        # Tensões
        "sigma_md_MPa": round(sigma_md / 1e6, 4),
        "f_md_MPa":     round(f_md     / 1e6, 4),
        # Verificação ao longo do vão
        "x_crit_m":     round(x_crit,   3),
        "eta_x_max":    round(eta_max,  4),
        # Resultado conservador (cumeeira)
        "eta":          round(eta,       4),
        "ok":           eta <= 1.0,
        # Referência
        "norma":        "EC5 §6.1.6 Eq. 6.11",
    }


# ── Varredura paramétrica ─────────────────────────────────────────────────────

def varrer_flexao(
    mat:         GlulamMaterial,
    L:           float,
    g_k:         float,
    q_k:         float,
    h0_range:    tuple = (0.60, 1.30, 0.10),
    alpha_range: tuple = (3.0,  8.5,  0.5),
    b_range:     tuple = (0.14, 0.28, 0.02),
    eta_max:     float = 1.0,
) -> pd.DataFrame:
    """
    Varre (h0, α, b) e verifica flexão simples para cada combinação.

    Returns:
        DataFrame com geometrias aprovadas, ordenado por η crescente
    """
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

                h_ap    = geo.h_ap
                W_y     = float(b) * h_ap**2 / 6

                q_ELU   = 1.35 * g_k + 1.5 * q_k
                M_max   = (q_ELU * L**2 / 8) * 1e3   # N·m

                sigma   = M_max / W_y
                eta     = sigma / mat.f_m_d

                resultados.append({
                    "h0_m":         round(float(h0),    3),
                    "alpha_deg":    round(float(alpha),  2),
                    "b_m":          round(float(b),      3),
                    "h_ap_m":       round(h_ap,          3),
                    "h_b":          round(h_ap / float(b), 2),
                    "W_y_m3":       round(W_y,           6),
                    "sigma_md_MPa": round(sigma / 1e6,   4),
                    "f_md_MPa":     round(mat.f_m_d/1e6, 4),
                    "eta":          round(eta,            4),
                    "ok":           eta <= eta_max,
                })

    df = pd.DataFrame(resultados)
    return df[df["ok"]].sort_values("eta").reset_index(drop=True)


# ── Varredura acumulada: cumeeira + flambagem + flexão ────────────────────────

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
        1. Cumeeira        — EC5 §6.4.3
        2. Flambagem lateral — EC5 §6.3.3
        3. Flexão simples  — EC5 §6.1.6

    Retorna geometrias aprovadas nas TRÊS verificações,
    ordenadas pelo maior η entre as três (verificação governante).

    Returns:
        DataFrame consolidado com η de cada verificação + η governante
    """
    from mlc_projeto.checks.elu.cumeeira import (
        calcular_k_p, calcular_k_vol, calcular_sigma_t90d,
        K_DIS,
    )
    from mlc_projeto.checks.elu.flambagem_lateral import (
        calcular_l_ef, calcular_sigma_m_crit,
        calcular_lambda_rel_m, calcular_k_crit,
    )

    l_ef = calcular_l_ef(l_1, restricao="continua_topo")

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

                # Carregamento ELU
                q_ELU    = 1.35 * g_k + 1.5 * q_k
                M_max_Nm = (q_ELU * L**2 / 8) * 1e3

                # ── 1. CUMEEIRA §6.4.3 ───────────────────────
                k_p     = calcular_k_p(float(alpha))
                k_vol   = calcular_k_vol(b_f, h_ap)
                sig_t90 = calcular_sigma_t90d(k_p, M_max_Nm, b_f, h_ap)
                res_t90 = K_DIS * k_vol * mat.f_t90_d
                eta_cum = sig_t90 / res_t90

                # ── 2. FLAMBAGEM LATERAL §6.3.3 ──────────────
                sig_crit = calcular_sigma_m_crit(
                    mat.E0_05, mat.G_mean, b_f, h_ap, l_ef
                )
                lam_rel  = calcular_lambda_rel_m(mat.f_m_k, sig_crit)
                k_crit   = calcular_k_crit(lam_rel)
                W_y      = b_f * h_ap**2 / 6
                sig_md   = M_max_Nm / W_y
                res_fl   = k_crit * mat.f_m_d
                eta_fl   = sig_md / res_fl

                # ── 3. FLEXÃO SIMPLES §6.1.6 ─────────────────
                eta_fx   = sig_md / mat.f_m_d   # sem redução k_crit

                # ── Todas aprovadas? ──────────────────────────
                etas = {
                    "cumeeira":   eta_cum,
                    "flambagem":  eta_fl,
                    "flexao":     eta_fx,
                }
                ok      = all(e <= eta_max for e in etas.values())
                eta_gov = max(etas.values())
                verif_gov = max(etas, key=etas.get)

                if ok:
                    resultados.append({
                        "h0_m":          round(float(h0),   3),
                        "alpha_deg":     round(float(alpha), 2),
                        "b_m":           round(b_f,          3),
                        "h_ap_m":        round(h_ap,         3),
                        "h_b":           round(h_ap / b_f,   2),
                        "eta_cumeeira":  round(eta_cum,      4),
                        "eta_flambagem": round(eta_fl,       4),
                        "eta_flexao":    round(eta_fx,       4),
                        "eta_gov":       round(eta_gov,      4),
                        "verif_gov":     verif_gov,
                        "lambda_rel_m":  round(lam_rel,      4),
                        "k_crit":        round(k_crit,       4),
                    })

    df = pd.DataFrame(resultados)
    if not df.empty:
        df = df.sort_values("eta_gov").reset_index(drop=True)
    return df


def relatorio_acumulado(df: pd.DataFrame, n: int = 20) -> None:
    """Imprime relatório consolidado das três verificações."""
    print("=" * 90)
    print("  VARREDURA ACUMULADA — Cumeeira §6.4.3 + Flambagem §6.3.3 + Flexão §6.1.6")
    print("  Geometrias aprovadas nas TRÊS verificações")
    print("=" * 90)

    if df.empty:
        print("\n  Nenhuma geometria aprovada nas três verificações.")
        print("=" * 90)
        return

    print(f"\n  Total de geometrias aprovadas: {len(df)}")
    print(f"  Exibindo as {min(n, len(df))} melhores:\n")

    header = (
        f"  {'#':>3}  {'h0(m)':>6}  {'α(°)':>5}  {'b(m)':>6}  "
        f"{'h_ap(m)':>8}  {'h/b':>5}  "
        f"{'η_cum':>7}  {'η_fla':>7}  {'η_flex':>7}  "
        f"{'η_gov':>7}  {'Governa'}"
    )
    print(header)
    print("  " + "-" * 84)

    for i, row in df.head(n).iterrows():
        linha = (
            f"  {i+1:>3}  {row['h0_m']:>6.3f}  {row['alpha_deg']:>5.1f}  "
            f"{row['b_m']:>6.3f}  {row['h_ap_m']:>8.3f}  "
            f"{row['h_b']:>5.1f}  "
            f"{row['eta_cumeeira']:>7.4f}  "
            f"{row['eta_flambagem']:>7.4f}  "
            f"{row['eta_flexao']:>7.4f}  "
            f"{row['eta_gov']:>7.4f}  {row['verif_gov']}"
        )
        print(linha)

    melhor = df.iloc[0]
    print(f"\n  ── Geometria recomendada após 3 verificações ──")
    print(f"  h0           = {melhor['h0_m']} m")
    print(f"  α            = {melhor['alpha_deg']}°")
    print(f"  b            = {melhor['b_m']} m")
    print(f"  h_ap         = {melhor['h_ap_m']} m")
    print(f"  h/b          = {melhor['h_b']}")
    print(f"  η cumeeira   = {melhor['eta_cumeeira']:.4f}")
    print(f"  η flambagem  = {melhor['eta_flambagem']:.4f}")
    print(f"  η flexão     = {melhor['eta_flexao']:.4f}")
    print(f"  η governante = {melhor['eta_gov']:.4f}  ({melhor['verif_gov']})")
    print("=" * 90)


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

    print(f"Material : {mat.classe} | CS {mat.classe_servico} | longa duração")
    print(f"k_mod    = {mat.k_mod:.2f} | f_m,d = {mat.f_m_d/1e6:.3f} MPa\n")

    df = varrer_acumulado(
        mat=mat, L=L, g_k=g_k, q_k=q_k, l_1=l_1,
        h0_range=(0.60, 1.30, 0.10),
        alpha_range=(3.0, 8.5, 0.5),
        b_range=(0.14, 0.28, 0.02),
    )

    relatorio_acumulado(df, n=20)