"""
checks/elu/flambagem_lateral.py — Flambagem lateral por flexo-torção.

VERIFICAÇÃO CRÍTICA — governa vigas esbeltas sem restrição lateral contínua.

A aba comprimida de uma viga em flexão tende a deslocar-se lateralmente
(flambagem lateral), reduzindo a resistência efetiva à flexão. O EC5 §6.3.3
controla isso pelo fator k_crit, que depende da esbeltez relativa λ_rel,m.

Comprimento efetivo adotado:
    Terças com chumbador lateral — restrição contínua no topo
    l_ef = 0,9 · l_1  (EC5 Tab. 6.1 — carga dist. + restrição no topo)
    l_ef = 0,9 × 5,75 = 5,175 m

Referência: EC5 §6.3.3
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.loads     import Carregamentos


# ── Comprimento efetivo ───────────────────────────────────────────────────────

def calcular_l_ef(
    l_1:          float,
    restricao:    str = "continua_topo",
    tipo_carga:   str = "distribuida",
) -> float:
    """
    Comprimento efetivo l_ef para flambagem lateral — EC5 Tabela 6.1.

    Args:
        l_1        : Distância entre pontos de restrição lateral (m)
        restricao  : Tipo de restrição lateral
                     "continua_topo"  — terças com chumbador (usado neste projeto)
                     "so_apoios"      — restrição apenas nos apoios
                     "apoios_e_topo"  — apoios + restrição no topo sem rotação
        tipo_carga : "distribuida" ou "pontual"

    Returns:
        l_ef (m)
    """
    if restricao == "continua_topo":
        # EC5 Tab. 6.1 — carga distribuída + restrição contínua no topo
        if tipo_carga == "distribuida":
            return 0.9 * l_1
        else:
            return 0.8 * l_1

    elif restricao == "so_apoios":
        if tipo_carga == "distribuida":
            return 0.9 * l_1 + 2 * 0.0   # simplificado
        else:
            return 0.8 * l_1

    elif restricao == "apoios_e_topo":
        if tipo_carga == "distribuida":
            return 0.9 * l_1
        else:
            return 0.8 * l_1

    else:
        raise ValueError(f"Tipo de restrição '{restricao}' não reconhecido.")


# ── Funções principais EC5 §6.3.3 ────────────────────────────────────────────

def calcular_sigma_m_crit(
    E_005:  float,
    b:      float,
    h:      float,
    l_ef:   float,
    G_05:   float | None = None,
) -> float:
    """
    Tensão crítica de flambagem lateral σ_m,crit — EC5 §6.3.3.

    Secção retangular de coníferas — EC5 §6.3.3(2) Eq. (6.32):

        σ_m,crit = 0,78 · b² · E_0,05 / (h · l_ef)

    Esta expressão decorre da formulação geral (6.31) com
    G_0,05 = E_0,05/16 e I_tor ≈ h·b³/3.

    Se G_05 for fornecido, usa-se a formulação geral EC5 Eq. (6.31):
        σ_m,crit = π · √(E_0,05·I_z·G_0,05·I_tor) / (l_ef · W_y)

    Args:
        E_005  : Módulo de elasticidade característico E_0,05 (Pa)
        b      : Largura da seção (m)
        h      : Altura da seção no ponto verificado (m)
        l_ef   : Comprimento efetivo de flambagem lateral (m)
        G_05   : Opcional — G_0,05 (Pa). Se None, usa Eq. (6.32).

    Returns:
        σ_m,crit (Pa)
    """
    if G_05 is None:
        # EC5 §6.3.3(2) Eq. (6.32) — retangular, coníferas
        return 0.78 * (b ** 2) * E_005 / (h * l_ef)

    # EC5 §6.3.3 Eq. (6.31) — formulação geral
    I_z   = h * b ** 3 / 12
    I_tor = h * b ** 3 / 3
    W_y   = b * h ** 2 / 6
    return (math.pi / (W_y * l_ef)) * math.sqrt(
        E_005 * I_z * G_05 * I_tor
    )


def calcular_lambda_rel_m(
    f_m_k:       float,
    sigma_m_crit: float,
) -> float:
    """
    Esbeltez relativa λ_rel,m — EC5 §6.3.3.

        λ_rel,m = √(f_m,k / σ_m,crit)

    Args:
        f_m_k        : Resistência característica à flexão (Pa)
        sigma_m_crit : Tensão crítica de flambagem lateral (Pa)

    Returns:
        λ_rel,m (adimensional)
    """
    return math.sqrt(f_m_k / sigma_m_crit)


def calcular_k_crit(lambda_rel_m: float) -> float:
    """
    Fator de instabilidade k_crit — EC5 §6.3.3.

    Três regimes conforme a esbeltez relativa λ_rel,m:

        λ_rel,m ≤ 0,75          → k_crit = 1,0
        0,75 < λ_rel,m ≤ 1,4   → k_crit = 1,56 - 0,75·λ_rel,m
        λ_rel,m > 1,4           → k_crit = 1 / λ_rel,m²

    Args:
        lambda_rel_m: Esbeltez relativa (adimensional)

    Returns:
        k_crit (adimensional, entre 0 e 1)
    """
    if lambda_rel_m <= 0.75:
        return 1.0
    elif lambda_rel_m <= 1.4:
        return 1.56 - 0.75 * lambda_rel_m
    else:
        return 1.0 / lambda_rel_m**2


# ── Verificação principal ─────────────────────────────────────────────────────

def verifica_flambagem_lateral(
    geo:   GeometriaViga,
    mat:   GlulamMaterial,
    load:  Carregamentos,
    l_1:   float = 5.75,
) -> dict:
    """
    Verifica estabilidade lateral por flexo-torção — EC5 §6.3.3.

    Condição (flexão simples):
        σ_m,d ≤ k_crit · f_m,d

    Secção crítica: ponto de M_max (não a cumeeira no pórtico de
    3 rótulas, onde M ≈ 0). Altura h = h(x_Mmax).

    σ_m,crit: EC5 §6.3.3(2) Eq. (6.32) — secção retangular.

    Args:
        geo  : Geometria da viga
        mat  : Material
        load : Carregamentos
        l_1  : Espaçamento entre terças (m)

    Returns:
        dict com resultados intermediários, η e ok
    """
    # ── Comprimento efetivo ───────────────────────────────────
    l_ef = calcular_l_ef(l_1, restricao="continua_topo", tipo_carga="distribuida")

    # ── Seção crítica — ponto de momento máximo ───────────────
    gov    = load.combinacao_ELU_governante()
    x_Mmax = gov.x_Mmax_m
    h_crit = float(geo.h(x_Mmax))
    b      = geo.b

    # ── Tensão crítica de flambagem — EC5 Eq. (6.32) ──────────
    sigma_crit = calcular_sigma_m_crit(
        E_005 = mat.E0_05,
        b     = b,
        h     = h_crit,
        l_ef  = l_ef,
    )

    # ── Esbeltez relativa e k_crit ────────────────────────────
    lam_rel = calcular_lambda_rel_m(mat.f_m_k, sigma_crit)
    k_crit  = calcular_k_crit(lam_rel)

    # ── Tensão atuante ────────────────────────────────────────
    M_max_Nm = gov.M_max_kNm * 1e3        # N·m
    W_y      = b * h_crit ** 2 / 6
    sigma_md = M_max_Nm / W_y             # Pa

    # ── Resistência de cálculo ────────────────────────────────
    f_md   = mat.f_m_d
    resist = k_crit * f_md

    # ── Taxa de utilização ────────────────────────────────────
    eta = sigma_md / resist

    # ── Regime de instabilidade ───────────────────────────────
    if lam_rel <= 0.75:
        regime = "estável — sem redução (λ ≤ 0,75)"
    elif lam_rel <= 1.4:
        regime = "instabilidade parcial (0,75 < λ ≤ 1,4)"
    else:
        regime = "instabilidade severa (λ > 1,4)"

    return {
        # Geometria
        "L_m":           geo.L,
        "x_Mmax_m":      round(x_Mmax, 3),
        "h_crit_m":      round(h_crit, 4),
        "h_ap_m":        geo.h_ap,
        "b_m":           b,
        "h_b":           round(h_crit / b, 2),
        # Comprimento efetivo
        "l_1_m":         l_1,
        "l_ef_m":        round(l_ef, 3),
        # Tensão crítica
        "sigma_m_crit_MPa": round(sigma_crit / 1e6, 3),
        "lambda_rel_m":     round(lam_rel, 4),
        "k_crit":           round(k_crit,  4),
        "regime":           regime,
        # Tensões
        "sigma_md_MPa":  round(sigma_md / 1e6, 4),
        "f_md_MPa":      round(f_md     / 1e6, 4),
        "resist_MPa":    round(resist   / 1e6, 4),
        # Momento
        "M_max_ELU_kNm": round(gov.M_max_kNm, 2),
        # Resultado
        "eta":           round(eta, 4),
        "ok":            eta <= 1.0,
        # Referência
        "norma":         "EC5 §6.3.3 Eq. 6.32 + 6.33",
    }


# ── Varredura paramétrica ─────────────────────────────────────────────────────

def varrer_flambagem_lateral(
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
    Varre combinações (h0, α, b) e verifica flambagem lateral para cada uma.

    Args:
        mat         : Material GlulamMaterial
        L           : Vão de cada pórtico (m)
        g_k         : Carga permanente característica (kN/m)
        q_k         : Sobrecarga característica (kN/m)
        l_1         : Espaçamento entre terças (m)
        h0_range    : (mín, máx, passo) para h0 (m)
        alpha_range : (mín, máx, passo) para α (graus)
        b_range     : (mín, máx, passo) para b (m)
        eta_max     : Taxa de utilização máxima para filtrar

    Returns:
        DataFrame com geometrias aprovadas, ordenado por η crescente
    """
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

                h_crit = geo.h_ap

                # Tensão crítica de flambagem
                sigma_crit = calcular_sigma_m_crit(
                    mat.E0_05, float(b), h_crit, l_ef
                )

                lam_rel = calcular_lambda_rel_m(mat.f_m_k, sigma_crit)
                k_crit  = calcular_k_crit(lam_rel)

                # Tensão atuante — seção da cumeeira
                q_ELU    = 1.35 * g_k + 1.5 * q_k
                M_max_Nm = (q_ELU * L**2 / 8) * 1e3   # N·m
                W_y      = float(b) * h_crit**2 / 6
                sigma_md = M_max_Nm / W_y

                # Resistência
                resist = k_crit * mat.f_m_d
                eta    = sigma_md / resist

                # Regime
                if lam_rel <= 0.75:
                    regime = "estável"
                elif lam_rel <= 1.4:
                    regime = "parcial"
                else:
                    regime = "severo"

                resultados.append({
                    "h0_m":          round(float(h0),    3),
                    "alpha_deg":     round(float(alpha),  2),
                    "b_m":           round(float(b),      3),
                    "h_ap_m":        round(h_crit,        3),
                    "h_b":           round(h_crit / float(b), 2),
                    "lambda_rel_m":  round(lam_rel,       4),
                    "k_crit":        round(k_crit,        4),
                    "sigma_md_MPa":  round(sigma_md/1e6,  4),
                    "resist_MPa":    round(resist/1e6,    4),
                    "eta":           round(eta,            4),
                    "regime":        regime,
                    "ok":            eta <= eta_max,
                })

    df = pd.DataFrame(resultados)
    df_ok = df[df["ok"]].sort_values("eta").reset_index(drop=True)
    return df_ok


def relatorio_flambagem(df: pd.DataFrame, n: int = 20) -> None:
    """Imprime relatório formatado das melhores geometrias."""
    print("=" * 82)
    print("  VARREDURA — FLAMBAGEM LATERAL EC5 §6.3.3  |  Geometrias aprovadas")
    print("=" * 82)

    if df.empty:
        print("\n  Nenhuma geometria aprovada no intervalo varrido.")
        print("  Sugestões:")
        print("  - Aumentar b (largura da seção)")
        print("  - Reduzir l_1 (espaçamento entre terças)")
        print("  - Usar classe resistente superior (GL28h)")
        print("=" * 82)
        return

    print(f"\n  Total de geometrias aprovadas: {len(df)}")
    print(f"  Exibindo as {min(n, len(df))} melhores:\n")

    header = (
        f"  {'#':>3}  {'h0(m)':>6}  {'α(°)':>5}  {'b(m)':>6}  "
        f"{'h_ap(m)':>8}  {'h/b':>5}  {'λ_rel':>7}  "
        f"{'k_crit':>7}  {'σ(MPa)':>8}  {'R(MPa)':>8}  {'η':>6}  {'Regime'}"
    )
    print(header)
    print("  " + "-" * 78)

    for i, row in df.head(n).iterrows():
        linha = (
            f"  {i+1:>3}  {row['h0_m']:>6.3f}  {row['alpha_deg']:>5.1f}  "
            f"{row['b_m']:>6.3f}  {row['h_ap_m']:>8.3f}  "
            f"{row['h_b']:>5.1f}  {row['lambda_rel_m']:>7.4f}  "
            f"{row['k_crit']:>7.4f}  {row['sigma_md_MPa']:>8.4f}  "
            f"{row['resist_MPa']:>8.4f}  {row['eta']:>6.4f}  {row['regime']}"
        )
        print(linha)

    print("\n  Legenda:")
    print("  h/b    = relação altura/largura (recomendado ≤ 5 para estabilidade)")
    print("  λ_rel  = esbeltez relativa (≤ 0,75: estável | ≤ 1,4: parcial | > 1,4: severo)")
    print("  k_crit = fator de redução por instabilidade lateral (1,0 = sem redução)")
    print("  σ      = tensão de flexão de cálculo σ_m,d (MPa)")
    print("  R      = resistência efetiva k_crit·f_m,d (MPa)")
    print("  η      = taxa de utilização (aprovado se η ≤ 1,0)")
    print("=" * 82)


# ── Varredura combinada: cumeeira + flambagem lateral ────────────────────────

def varrer_combinado(
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
    Varre (h0, α, b) verificando SIMULTANEAMENTE cumeeira E flambagem lateral.

    Retorna apenas geometrias aprovadas em AMBAS as verificações,
    ordenadas pelo maior η entre as duas (geometria mais restrita).

    Este é o resultado mais útil para o pré-dimensionamento — elimina
    todas as geometrias que falham em qualquer uma das duas verificações
    críticas antes de avançar para as demais verificações EC5.

    Returns:
        DataFrame com colunas de ambas as verificações + eta_gov (governante)
    """
    from mlc_projeto.checks.elu.cumeeira import (
        calcular_k_p, calcular_k_vol, calcular_sigma_t90d,
        K_DIS, V0_KVOL
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

                # ── CUMEEIRA ─────────────────────────────────
                k_p     = calcular_k_p(float(alpha))
                k_vol   = calcular_k_vol(b_f, h_ap)
                sig_t90 = calcular_sigma_t90d(k_p, M_max_Nm, b_f, h_ap)
                res_t90 = K_DIS * k_vol * mat.f_t90_d
                eta_cum = sig_t90 / res_t90

                # ── FLAMBAGEM LATERAL ─────────────────────────
                sig_crit = calcular_sigma_m_crit(
                    mat.E0_05, b_f, h_ap, l_ef
                )
                lam_rel  = calcular_lambda_rel_m(mat.f_m_k, sig_crit)
                k_crit   = calcular_k_crit(lam_rel)
                W_y      = b_f * h_ap**2 / 6
                sig_md   = M_max_Nm / W_y
                res_fl   = k_crit * mat.f_m_d
                eta_fl   = sig_md / res_fl

                # ── Ambas aprovadas? ──────────────────────────
                ok = (eta_cum <= eta_max) and (eta_fl <= eta_max)
                eta_gov = max(eta_cum, eta_fl)   # verificação governante

                if ok:
                    resultados.append({
                        "h0_m":          round(float(h0),   3),
                        "alpha_deg":     round(float(alpha), 2),
                        "b_m":           round(b_f,          3),
                        "h_ap_m":        round(h_ap,         3),
                        "h_b":           round(h_ap / b_f,   2),
                        # Cumeeira
                        "eta_cumeeira":  round(eta_cum,      4),
                        # Flambagem
                        "lambda_rel_m":  round(lam_rel,      4),
                        "k_crit":        round(k_crit,       4),
                        "eta_flambagem": round(eta_fl,       4),
                        # Governante
                        "eta_gov":       round(eta_gov,      4),
                        "verif_gov":     "cumeeira" if eta_cum >= eta_fl
                                         else "flambagem",
                    })

    df = pd.DataFrame(resultados)
    if not df.empty:
        df = df.sort_values("eta_gov").reset_index(drop=True)
    return df


def relatorio_combinado(df: pd.DataFrame, n: int = 20) -> None:
    """Imprime relatório das geometrias aprovadas nas duas verificações."""
    print("=" * 86)
    print("  VARREDURA COMBINADA — Cumeeira §6.4.3 + Flambagem Lateral §6.3.3")
    print("  Geometrias aprovadas em AMBAS as verificações críticas")
    print("=" * 86)

    if df.empty:
        print("\n  Nenhuma geometria aprovada simultaneamente nas duas verificações.")
        print("  Sugestões:")
        print("  - Ampliar os intervalos de varredura")
        print("  - Considerar GL28h ou GL32h")
        print("  - Reduzir espaçamento entre terças")
        print("=" * 86)
        return

    print(f"\n  Total de geometrias aprovadas: {len(df)}")
    print(f"  Exibindo as {min(n, len(df))} melhores (ordenadas por η governante):\n")

    header = (
        f"  {'#':>3}  {'h0(m)':>6}  {'α(°)':>5}  {'b(m)':>6}  "
        f"{'h_ap(m)':>8}  {'h/b':>5}  "
        f"{'η_cumeeira':>11}  {'η_flamb':>9}  "
        f"{'η_gov':>7}  {'Governa'}"
    )
    print(header)
    print("  " + "-" * 80)

    for i, row in df.head(n).iterrows():
        linha = (
            f"  {i+1:>3}  {row['h0_m']:>6.3f}  {row['alpha_deg']:>5.1f}  "
            f"{row['b_m']:>6.3f}  {row['h_ap_m']:>8.3f}  "
            f"{row['h_b']:>5.1f}  "
            f"{row['eta_cumeeira']:>11.4f}  {row['eta_flambagem']:>9.4f}  "
            f"{row['eta_gov']:>7.4f}  {row['verif_gov']}"
        )
        print(linha)

    melhor = df.iloc[0]
    print(f"\n  ── Geometria recomendada para prosseguir ──")
    print(f"  h0    = {melhor['h0_m']} m")
    print(f"  α     = {melhor['alpha_deg']}°")
    print(f"  b     = {melhor['b_m']} m")
    print(f"  h_ap  = {melhor['h_ap_m']} m")
    print(f"  h/b   = {melhor['h_b']}")
    print(f"  η_cumeeira  = {melhor['eta_cumeeira']:.4f}")
    print(f"  η_flambagem = {melhor['eta_flambagem']:.4f}")
    print(f"  η_governante = {melhor['eta_gov']:.4f}  ({melhor['verif_gov']})")
    print("=" * 86)


# ── Execução direta para teste ────────────────────────────────────────────────

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
    print(f"k_mod    = {mat.k_mod:.2f} | f_m,d = {mat.f_m_d/1e6:.3f} MPa")
    print(f"E_0,05   = {mat.E0_05/1e9:.2f} GPa | G_mean = {mat.G_mean/1e9:.3f} GPa")
    print(f"l_ef     = 0,9 × {l_1} = {0.9*l_1:.3f} m\n")

    # ── Varredura individual: flambagem lateral ───────────────
    print("── Varredura: Flambagem Lateral ──\n")
    df_fl = varrer_flambagem_lateral(
        mat=mat, L=L, g_k=g_k, q_k=q_k, l_1=l_1,
        h0_range=(0.60, 1.30, 0.10),
        alpha_range=(3.0, 8.5, 0.5),
        b_range=(0.14, 0.28, 0.02),
    )
    relatorio_flambagem(df_fl, n=10)

    # ── Varredura combinada ───────────────────────────────────
    print("\n── Varredura Combinada: Cumeeira + Flambagem Lateral ──\n")
    df_comb = varrer_combinado(
        mat=mat, L=L, g_k=g_k, q_k=q_k, l_1=l_1,
        h0_range=(0.60, 1.30, 0.10),
        alpha_range=(3.0, 8.5, 0.5),
        b_range=(0.14, 0.28, 0.02),
    )
    relatorio_combinado(df_comb, n=20)