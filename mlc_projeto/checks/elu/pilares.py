"""
checks/elu/pilares.py — Dimensionamento dos pilares. v2

ATUALIZAÇÃO v2 — Pórtico de 3 rótulas:
    Rótulas em ambas as extremidades do pilar:
    - Base: rótula na sapata
    - Topo: rótula na ligação com a viga

    Esforços no pilar:
    - N_d = R_v = q·L/2  (compressão — reação vertical da viga)
    - M_d = 0            (rótulas em ambas as extremidades)
    - V_d = 0            (empuxo H vai para a sapata, não para o pilar)

    Verificação: compressão simples com instabilidade
    EC5 §6.3.2 Eq. 6.23 simplificada (sem momento):
        (σ_c,0,d / (k_c · f_c,0,d))² ≤ 1,0

    Comprimento efetivo — pilar com duas rótulas:
        l_ef = 1,0 · H  (EC5 §6.3.2 — articulado-articulado)

    Nota sobre o empuxo horizontal H:
        H = 621 kN vai direto para a sapata via chumbadores.
        O pilar NÃO resiste ao empuxo — ele é transferido pelo
        mecanismo de apoio articulado (pino na base).
        A sapata e os chumbadores resistem a H.

Referência: EC5 §6.3.2 Eq. 6.23
"""

from __future__ import annotations

import math
import numpy as np
import pandas as pd

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.loads     import Carregamentos


# ── Verificação pontual ───────────────────────────────────────────────────────

def verifica_pilar(
    mat:   GlulamMaterial,
    b:     float,
    h:     float,
    H:     float,
    N_d:   float,
) -> dict:
    """
    Verifica pilar em compressão simples com instabilidade — EC5 §6.3.2.

    Pilar com rótulas em ambas as extremidades:
        l_ef = 1,0 · H

    Condição (sem momento):
        (σ_c,0,d / (k_c · f_c,0,d))² ≤ 1,0

    Args:
        mat : Material do pilar
        b   : Largura da seção (m)
        h   : Altura da seção no plano do pórtico (m)
        H   : Comprimento do pilar (m)
        N_d : Força normal de cálculo (kN) — compressão

    Returns:
        dict com k_c, λ_rel, η e ok
    """
    # ── Propriedades da seção ─────────────────────────────────
    A     = b * h
    I_min = min(b * h**3, h * b**3) / 12   # inércia mínima
    i_min = math.sqrt(I_min / A)           # raio de giração mínimo

    # ── Comprimento efetivo ───────────────────────────────────
    # Articulado-articulado: l_ef = 1,0·H
    l_ef = 1.0 * H

    # ── Esbeltez ─────────────────────────────────────────────
    lam     = l_ef / i_min
    lam_rel = (lam / math.pi) * math.sqrt(
        mat.f_c0_k / mat.E0_05
    )

    # ── Fator k_c — EC5 §6.3.2 ───────────────────────────────
    beta_c = 0.1   # glulam
    k      = 0.5 * (1 + beta_c*(lam_rel - 0.3) + lam_rel**2)
    k_c    = min(1.0 / (k + math.sqrt(k**2 - lam_rel**2)), 1.0)

    # ── Tensão de compressão ──────────────────────────────────
    sigma_c = N_d * 1e3 / A   # Pa

    # ── Verificação EC5 §6.3.2 ────────────────────────────────
    eta = (sigma_c / (k_c * mat.f_c0_d))**2

    return {
        "b_m":          b,
        "h_m":          h,
        "H_m":          H,
        "l_ef_m":       round(l_ef,          3),
        "lambda":       round(lam,           2),
        "lambda_rel":   round(lam_rel,       4),
        "k_c":          round(k_c,           4),
        "N_d_kN":       round(N_d,           3),
        "sigma_c_MPa":  round(sigma_c/1e6,   4),
        "f_c0d_MPa":    round(mat.f_c0_d/1e6,4),
        "eta":          round(eta,            4),
        "ok":           eta <= 1.0,
        "norma":        "EC5 §6.3.2 Eq. 6.23 (compressão pura)",
    }


# ── Varredura paramétrica ─────────────────────────────────────────────────────

def varrer_pilares(
    mat:      GlulamMaterial,
    load:     Carregamentos,
    H_pilar:  float = 7.0,
    b_range:  tuple = (0.10, 0.28, 0.02),
    h_range:  tuple = (0.10, 0.40, 0.02),
    eta_max:  float = 1.0,
) -> pd.DataFrame:
    """
    Varre seções (b × h) para o pilar em compressão simples.

    A força normal N_d é a reação vertical da viga:
        N_d = V_max_ELU = q·L/2

    Args:
        mat      : Material do pilar (GL24h duração curta)
        load     : Carregamentos — fornece N_d
        H_pilar  : Altura do pilar (m)
        b_range  : (mín, máx, passo) para largura (m)
        h_range  : (mín, máx, passo) para altura (m)
        eta_max  : Taxa máxima para aprovação

    Returns:
        DataFrame com seções aprovadas, ordenado por volume crescente
    """
    N_d = load.V_max_ELU()   # kN — reação vertical = N no pilar

    b_vals = np.arange(*b_range)
    h_vals = np.arange(*h_range)

    resultados = []

    for b in b_vals:
        for h in h_vals:
            b_f = round(float(b), 3)
            h_f = round(float(h), 3)

            res = verifica_pilar(mat, b_f, h_f, H_pilar, N_d)

            if res["ok"]:
                V_pilar = H_pilar * b_f * h_f
                resultados.append({
                    "b_m":         b_f,
                    "h_m":         h_f,
                    "h_b":         round(h_f/b_f,       2),
                    "l_ef_m":      res["l_ef_m"],
                    "lambda":      res["lambda"],
                    "lambda_rel":  res["lambda_rel"],
                    "k_c":         res["k_c"],
                    "N_d_kN":      res["N_d_kN"],
                    "sigma_c_MPa": res["sigma_c_MPa"],
                    "f_c0d_MPa":   res["f_c0d_MPa"],
                    "eta":         res["eta"],
                    "V_pilar_m3":  round(V_pilar,       4),
                })

    df = pd.DataFrame(resultados)
    if not df.empty:
        df = df.sort_values(["V_pilar_m3", "eta"]).reset_index(drop=True)
    return df


def relatorio_pilares(
    df:      pd.DataFrame,
    load:    Carregamentos,
    H_pilar: float,
    n:       int = 15,
) -> None:
    """Imprime relatório do dimensionamento dos pilares."""
    print("=" * 78)
    print("  DIMENSIONAMENTO DOS PILARES — GL24h")
    print("  Pórtico de 3 rótulas — compressão simples EC5 §6.3.2")
    print("  l_ef = 1,0·H  (articulado-articulado)")
    print("=" * 78)

    N_d = load.V_max_ELU()
    H_f = load.H_ELU()
    print(f"\n  Esforços no pilar:")
    print(f"    N_d = {N_d:.2f} kN  (compressão — reação vertical)")
    print(f"    M_d = 0 kN·m  (rótulas em ambas as extremidades)")
    print(f"    H_fund = {H_f:.2f} kN  (empuxo → sapata, não passa pelo pilar)")
    print(f"    H_pilar = {H_pilar} m")

    if df.empty:
        print("\n  Nenhuma seção aprovada. Aumentar b ou h.")
        print("=" * 78)
        return

    print(f"\n  Seções aprovadas: {len(df)}")
    print(f"  Exibindo as {min(n, len(df))} mais econômicas:\n")

    hdr = (
        f"  {'#':>3}  {'b(m)':>6}  {'h(m)':>6}  {'h/b':>5}  "
        f"{'l_ef':>6}  {'λ':>6}  {'λ_rel':>7}  "
        f"{'k_c':>6}  {'σ_c(MPa)':>9}  {'η':>7}  {'V(m³)':>7}"
    )
    print(hdr)
    print("  " + "-" * 74)

    for i, row in df.head(n).iterrows():
        print(
            f"  {i+1:>3}  {row['b_m']:>6.3f}  {row['h_m']:>6.3f}  "
            f"{row['h_b']:>5.1f}  {row['l_ef_m']:>6.2f}  "
            f"{row['lambda']:>6.1f}  {row['lambda_rel']:>7.4f}  "
            f"{row['k_c']:>6.4f}  {row['sigma_c_MPa']:>9.4f}  "
            f"{row['eta']:>7.4f}  {row['V_pilar_m3']:>7.4f}"
        )

    m = df.iloc[0]
    print(f"\n  ── Pilar recomendado ─────────────────────────────────────")
    print(f"  Seção        : {m['b_m']} × {m['h_m']} m  (b × h)")
    print(f"  l_ef         : {m['l_ef_m']} m  (= 1,0 × H)")
    print(f"  λ            : {m['lambda']:.1f}")
    print(f"  λ_rel        : {m['lambda_rel']:.4f}")
    print(f"  k_c          : {m['k_c']:.4f}")
    print(f"  σ_c,0,d      : {m['sigma_c_MPa']:.4f} MPa")
    print(f"  f_c,0,d      : {m['f_c0d_MPa']:.4f} MPa")
    print(f"  η            : {m['eta']:.4f}")
    print(f"  Volume pilar : {m['V_pilar_m3']:.4f} m³")
    print(f"  ─────────────────────────────────────────────────────────")
    print(f"  Comparação com pórtico rígido (Sistema A):")
    print(f"  Seção rígido : 0,22 × 0,80 m  (V = 1,232 m³)")
    print(f"  Economia     : "
          f"{(1-m['V_pilar_m3']/1.232)*100:.1f}% de madeira no pilar")
    print("=" * 78)


# ── Execução direta ───────────────────────────────────────────────────────────

if __name__ == "__main__":

    from mlc_projeto.core.geometry  import GeometriaViga
    from mlc_projeto.core.wind      import ParametrosVento
    from mlc_projeto.core.loads     import carregamentos_com_vento

    geo = GeometriaViga(L=20.25, h0=0.60, alpha_deg=4.5, b=0.26)
    mat = GlulamMaterial(classe="GL24h", classe_servico=3, duracao="curta")

    params_vento = ParametrosVento(
        V0=45.0, S1=1.0, categoria="IV", classe="B", S3=1.0,
        L=20.25, H1=1.0, h=7.0, dist_portico=5.75,
    )

    load = carregamentos_com_vento(
        geo=geo, mat=mat,
        g_area=1.50, q_area=0.25,
        L_t=5.75, params_vento=params_vento,
    )

    print(f"N_d = {load.V_max_ELU():.2f} kN  "
          f"| H_fund = {load.H_ELU():.2f} kN\n")

    df = varrer_pilares(
        mat=mat, load=load, H_pilar=7.0,
        b_range=(0.10, 0.28, 0.02),
        h_range=(0.10, 0.40, 0.02),
    )

    relatorio_pilares(df, load, H_pilar=7.0, n=15)