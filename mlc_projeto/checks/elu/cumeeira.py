"""
checks/elu/cumeeira.py — Tensão de tração perpendicular na cumeeira.

VERIFICAÇÃO CRÍTICA — frequentemente governa o projeto para α > 3°.

A mudança de inclinação na cumeeira de uma viga de duplo-bisel gera
tensões de tração perpendicular às fibras — a direção mais fraca da
madeira. Esta verificação impõe os limites mais restritivos à geometria.

Referência: EC5 §6.4.3, Eq. 6.50, 6.51, 6.54
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.loads     import Carregamentos


# ── Constantes EC5 §6.4.3 ────────────────────────────────────────────────────

K_DIS   = 1.4    # fator de distribuição de tensão — duplo-bisel (EC5 §6.4.3)
V0_KVOL = 0.01   # volume de referência para k_vol (m³) — EC5 Eq. 6.51


# ── Funções auxiliares ────────────────────────────────────────────────────────

def calcular_k_p(alpha_deg: float) -> float:
    """
    Coeficiente de forma k_p para viga de duplo-bisel sem curvatura.

    Para viga de duplo-bisel (sem raio de curvatura), os termos com
    h_ap/r desaparecem (r → ∞) e a equação reduz a:

        k_p = k_5 = 0,2 · tan(α)

    EC5 §6.4.3, coeficientes abaixo da Eq. 6.54 para double tapered beam.

    Args:
        alpha_deg: Ângulo de inclinação da cumeeira (graus)

    Returns:
        Coeficiente k_p (adimensional)
    """
    return 0.2 * math.tan(math.radians(alpha_deg))


def calcular_k_vol(b: float, h_ap: float, f_vol: float = 0.15) -> float:
    """
    Fator de volume k_vol — EC5 §6.4.3 Eq. 6.51.

        k_vol = (V0 / V)^0,20

    O volume V da zona estressada é estimado como uma fração f_vol
    da altura h_ap ao longo da largura b:

        V = b · h_ap · (f_vol · h_ap)

    A fração padrão adotada na literatura é f_vol = 0,15 (15% de h_ap),
    correspondendo à zona onde σ_t,90 supera 50% do valor máximo.

    Args:
        b     : Largura da seção (m)
        h_ap  : Altura na cumeeira (m)
        f_vol : Fração de h_ap que define a profundidade da zona (padrão 0,15)

    Returns:
        Fator k_vol (adimensional, ≤ 1,0)
    """
    V = b * h_ap * (f_vol * h_ap)        # m³
    k_vol = (V0_KVOL / V) ** 0.20
    return min(k_vol, 1.0)               # k_vol não pode exceder 1,0


def calcular_sigma_t90d(
    k_p:    float,
    M_ap_d: float,
    b:      float,
    h_ap:   float,
) -> float:
    """
    Tensão de tração perpendicular na cumeeira — EC5 §6.4.3 Eq. 6.54.

        σ_t,90,d = k_p · 6·M_ap,d / (b · h_ap²)

    Args:
        k_p    : Coeficiente de forma
        M_ap_d : Momento fletor de cálculo na cumeeira (N·m)
        b      : Largura da seção (m)
        h_ap   : Altura na cumeeira (m)

    Returns:
        σ_t,90,d (Pa)
    """
    return k_p * 6.0 * M_ap_d / (b * h_ap ** 2)


# ── Verificação principal ─────────────────────────────────────────────────────

@dataclass
class ResultadoCumeeira:
    """Resultado completo da verificação da cumeeira."""
    # Geometria
    L_m:       float
    h0_m:      float
    h_ap_m:    float
    alpha_deg: float
    b_m:       float
    # Coeficientes
    k_p:       float
    k_vol:     float
    k_dis:     float
    # Tensões
    sigma_t90d_MPa: float
    f_t90d_MPa:     float
    resistencia_MPa: float
    # Resultado
    eta:       float
    ok:        bool
    # Momento
    M_ap_d_kNm: float


def verifica_cumeeira(
    geo:  GeometriaViga,
    mat:  GlulamMaterial,
    load: Carregamentos,
) -> dict:
    """
    Verifica tensão de tração perpendicular na cumeeira (EC5 §6.4.3).

    Condição:
        σ_t,90,d ≤ k_dis · k_vol · f_t,90,d     (Eq. 6.50)

    onde:
        σ_t,90,d = k_p · 6·M_ap,d / (b·h_ap²)  (Eq. 6.54)
        k_vol    = (V0/V)^0,20                   (Eq. 6.51)
        k_dis    = 1,4  para duplo-bisel

    Args:
        geo  : Geometria da viga (GeometriaViga)
        mat  : Material (GlulamMaterial)
        load : Carregamentos (Carregamentos)

    Returns:
        dict com todos os resultados intermediários, η e ok
    """
    # ── Geometria ─────────────────────────────────────────────
    h_ap      = geo.h_ap          # altura na cumeeira (m)
    b         = geo.b             # largura (m)
    alpha_deg = geo.alpha_deg     # ângulo (graus)

    # ── Momento na cumeeira ───────────────────────────────────
    # Para viga bi-apoiada com carga uniforme: M_max = q·L²/8
    # O momento máximo ocorre no meio do vão = posição da cumeeira
    M_ap_d_Nm = load.M_max_ELU() * 1e3   # kN·m → N·m

    # ── Coeficientes EC5 §6.4.3 ───────────────────────────────
    k_p   = calcular_k_p(alpha_deg)
    k_vol = calcular_k_vol(b, h_ap)

    # ── Resistência de cálculo ────────────────────────────────
    f_t90d_Pa = mat.f_t90_d                          # Pa
    resist_Pa = K_DIS * k_vol * f_t90d_Pa            # Pa

    # ── Tensão atuante ────────────────────────────────────────
    sigma_t90d_Pa = calcular_sigma_t90d(k_p, M_ap_d_Nm, b, h_ap)

    # ── Taxa de utilização ────────────────────────────────────
    eta = sigma_t90d_Pa / resist_Pa

    return {
        # Geometria
        "L_m":           geo.L,
        "h0_m":          geo.h0,
        "h_ap_m":        h_ap,
        "alpha_deg":     alpha_deg,
        "b_m":           b,
        # Coeficientes
        "k_p":           round(k_p,   6),
        "k_vol":         round(k_vol, 4),
        "k_dis":         K_DIS,
        # Tensões (MPa para leitura)
        "sigma_t90d_MPa": round(sigma_t90d_Pa / 1e6, 4),
        "f_t90d_MPa":     round(f_t90d_Pa      / 1e6, 4),
        "resistencia_MPa":round(resist_Pa       / 1e6, 4),
        # Momento
        "M_ap_d_kNm":    round(load.M_max_ELU(), 2),
        # Resultado
        "eta":           round(eta, 4),
        "ok":            eta <= 1.0,
        # Referência
        "norma":         "EC5 §6.4.3 Eq. 6.50, 6.51, 6.54",
    }


# ── Varredura paramétrica ─────────────────────────────────────────────────────

def varrer_cumeeira(
    mat:          GlulamMaterial,
    L:            float,
    g_k:          float,
    q_k:          float,
    h0_range:     tuple[float, float, float] = (0.60, 1.20, 0.10),
    alpha_range:  tuple[float, float, float] = (3.0,  8.0,  0.5),
    b_range:      tuple[float, float, float] = (0.14, 0.26, 0.02),
    eta_max:      float = 1.0,
) -> pd.DataFrame:
    """
    Varre combinações de (h0, α, b) e verifica a cumeeira para cada uma.

    Retorna DataFrame com todas as combinações aprovadas (η ≤ eta_max),
    ordenado por η crescente — as melhores geometrias aparecem primeiro.

    Args:
        mat         : Material GlulamMaterial
        L           : Vão de cada pórtico (m)
        g_k         : Carga permanente característica (kN/m)
        q_k         : Sobrecarga característica (kN/m)
        h0_range    : (mínimo, máximo, passo) para h0 (m)
        alpha_range : (mínimo, máximo, passo) para α (graus)
        b_range     : (mínimo, máximo, passo) para b (m)
        eta_max     : Taxa de utilização máxima para filtrar resultados

    Returns:
        DataFrame com colunas: h0, alpha, b, h_ap, k_p, k_vol,
                                sigma_t90d, resistencia, eta, ok
    """
    h0_vals    = np.arange(*h0_range)
    alpha_vals = np.arange(*alpha_range)
    b_vals     = np.arange(*b_range)

    resultados = []

    for h0 in h0_vals:
        for alpha in alpha_vals:
            for b in b_vals:

                # Geometria
                geo = GeometriaViga(
                    L=L,
                    h0=round(float(h0), 3),
                    alpha_deg=round(float(alpha), 2),
                    b=round(float(b), 3),
                )

                # Carregamento simplificado para varredura
                # (sem objeto Carregamentos completo — cálculo direto)
                q_ELU = 1.35 * g_k + 1.5 * q_k   # kN/m
                M_ap_d_kNm = q_ELU * L**2 / 8.0   # kN·m

                # Coeficientes
                k_p   = calcular_k_p(alpha)
                k_vol = calcular_k_vol(b, geo.h_ap)

                # Resistência
                f_t90d   = mat.f_t90_d              # Pa
                resist   = K_DIS * k_vol * f_t90d   # Pa

                # Tensão atuante
                sigma = calcular_sigma_t90d(
                    k_p, M_ap_d_kNm * 1e3, b, geo.h_ap
                )

                eta = sigma / resist

                resultados.append({
                    "h0_m":           round(float(h0),       3),
                    "alpha_deg":      round(float(alpha),     2),
                    "b_m":            round(float(b),         3),
                    "h_ap_m":         round(geo.h_ap,         3),
                    "h_ap_h0":        round(geo.h_ap / float(h0), 2),
                    "k_p":            round(k_p,              5),
                    "k_vol":          round(k_vol,            4),
                    "sigma_t90d_MPa": round(sigma / 1e6,      4),
                    "resist_MPa":     round(resist / 1e6,     4),
                    "eta":            round(eta,               4),
                    "ok":             eta <= eta_max,
                })

    df = pd.DataFrame(resultados)
    df_ok = df[df["ok"]].sort_values("eta").reset_index(drop=True)
    return df_ok


def relatorio_varredura(df: pd.DataFrame, n: int = 15) -> None:
    """
    Imprime relatório formatado das melhores geometrias da varredura.

    Args:
        df : DataFrame retornado por varrer_cumeeira()
        n  : Número de geometrias a exibir
    """
    print("=" * 78)
    print("  VARREDURA — CUMEEIRA EC5 §6.4.3  |  Melhores geometrias aprovadas")
    print("=" * 78)

    if df.empty:
        print("\n  Nenhuma geometria aprovada no intervalo varrido.")
        print("  Sugestões:")
        print("  - Aumentar b (largura) além de 0,26 m")
        print("  - Reduzir α (ângulo) abaixo de 3°")
        print("  - Considerar classe resistente superior (GL28h ou GL32h)")
        print("=" * 78)
        return

    print(f"\n  Total de geometrias aprovadas: {len(df)}")
    print(f"  Exibindo as {min(n, len(df))} melhores:\n")

    header = (
        f"  {'#':>3}  {'h0(m)':>6}  {'α(°)':>6}  {'b(m)':>6}  "
        f"{'h_ap(m)':>8}  {'k_p':>7}  {'k_vol':>6}  "
        f"{'σ(MPa)':>8}  {'R(MPa)':>8}  {'η':>6}"
    )
    print(header)
    print("  " + "-" * 74)

    for i, row in df.head(n).iterrows():
        linha = (
            f"  {i+1:>3}  {row['h0_m']:>6.3f}  {row['alpha_deg']:>6.2f}  "
            f"{row['b_m']:>6.3f}  {row['h_ap_m']:>8.3f}  "
            f"{row['k_p']:>7.5f}  {row['k_vol']:>6.4f}  "
            f"{row['sigma_t90d_MPa']:>8.4f}  {row['resist_MPa']:>8.4f}  "
            f"{row['eta']:>6.4f}"
        )
        print(linha)

    print("\n  Legenda:")
    print("  h0    = altura da seção no apoio (m)")
    print("  α     = ângulo de inclinação da cumeeira (graus)")
    print("  b     = largura da seção transversal (m)")
    print("  h_ap  = altura na cumeeira (m)")
    print("  σ     = tensão de tração perpendicular σ_t,90,d (MPa)")
    print("  R     = resistência efetiva k_dis·k_vol·f_t,90,d (MPa)")
    print("  η     = taxa de utilização σ/R (aprovado se η ≤ 1,0)")
    print("=" * 78)


# ── Execução direta para teste ────────────────────────────────────────────────

if __name__ == "__main__":

    # Material
    mat = GlulamMaterial(
        classe="GL24h",
        classe_servico=2,
        duracao="longa",
    )

    print(f"\nMaterial: {mat.classe} | CS {mat.classe_servico} | "
          f"duração longa")
    print(f"k_mod = {mat.k_mod:.2f} | "
          f"f_t,90,k = {mat.f_t90_k/1e6:.3f} MPa | "
          f"f_t,90,d = {mat.f_t90_d/1e6:.4f} MPa\n")

    # Carregamentos típicos (por metro linear de viga)
    dist_porticos = 5.75   # m
    g_k = 1.50 * dist_porticos   # kN/m — peso próprio + cobertura
    q_k = 0.25 * dist_porticos   # kN/m — sobrecarga

    print(f"Carregamentos: g_k = {g_k:.2f} kN/m | q_k = {q_k:.2f} kN/m")
    print(f"q_ELU = 1,35·g + 1,5·q = "
          f"{1.35*g_k + 1.5*q_k:.2f} kN/m\n")

    # Varredura
    df = varrer_cumeeira(
        mat=mat,
        L=20.25,
        g_k=g_k,
        q_k=q_k,
        h0_range=(0.60, 1.30, 0.10),
        alpha_range=(3.0, 8.5, 0.5),
        b_range=(0.14, 0.28, 0.02),
    )

    relatorio_varredura(df, n=20)

    # Verificação pontual com a geometria mais favorável
    if not df.empty:
        melhor = df.iloc[0]
        print(f"\nGeometria mais favorável:")
        print(f"  h0 = {melhor['h0_m']} m | "
              f"α = {melhor['alpha_deg']}° | "
              f"b = {melhor['b_m']} m | "
              f"h_ap = {melhor['h_ap_m']} m")
        print(f"  η_cumeeira = {melhor['eta']:.4f}")