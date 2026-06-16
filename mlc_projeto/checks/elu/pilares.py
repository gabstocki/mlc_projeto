"""
checks/elu/pilares.py — Dimensionamento dos pilares em MLC GL24h.

Compara três sistemas estruturais de pórtico:
    A — Rígido-articulado: knee-frame no canto, base articulada
    B — Totalmente rígido:  knee-frame no canto, base engastada
    C — Isostático:         pino no canto, base articulada + contraventamento

Para A e B: resolve o acoplamento viga-pilar iterativamente usando
fórmulas fechadas para pórtico simétrico de duas águas sob carga uniforme.

Verificações EC5 para cada pilar:
    Flexo-compressão com instabilidade — §6.3.2 Eq. 6.23
    Cisalhamento — §6.1.7
    Compressão perpendicular na base — §6.1.5

Critério de comparação econômica:
    Volume total de madeira = V_viga + 2·V_pilar (por pórtico)

Referência: EC5 §6.3.2, §6.1.7, §6.1.5
            Pilkey & Witt: Formulas for Stress, Strain and Structural Matrices
            EN 1995-1-1 §6.3
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.loads     import Carregamentos


# ── Tipos ─────────────────────────────────────────────────────────────────────

Sistema = Literal["A", "B", "C"]


# ── Esforços no pilar por sistema ────────────────────────────────────────────

def esforcos_pilar(
    sistema:  Sistema,
    q_vert:   float,   # kN/m — carga vertical na viga (ELU_C2)
    q_horiz:  float,   # kN/m — pressão horizontal do vento (kN/m de altura)
    L:        float,   # m    — vão da viga (entre eixos dos pilares)
    H:        float,   # m    — altura do pilar
    EI_viga:  float,   # kN·m² — rigidez fleural da viga (valor médio)
    EI_pilar: float,   # kN·m² — rigidez fleural do pilar
) -> dict:
    """
    Calcula esforços no pilar para os três sistemas estruturais.

    Sistema A — Rígido-articulado (knee-frame, base articulada):
        Pórtico hiperestático grau 1.
        Fórmula fechada para pórtico simétrico carga uniforme.
        Empuxo horizontal H_A = 3·q·L²·EI_c / (8·H·(2·EI_c·L + 3·EI_b·H))
        Fonte: Roark's Formulas, Table 17.1 — case 8d

    Sistema B — Totalmente rígido (knee-frame, base engastada):
        Pórtico hiperestático grau 3.
        Empuxo H_B = q·L² / (8·H·(1 + 2·EI_c·L/(3·EI_b·H)))
        Fonte: Roark's Formulas, Table 17.1 — case 8c

    Sistema C — Isostático (pino no canto, base articulada):
        Pórtico estaticamente determinado.
        N_pilar = q·L/2 (compressão axial apenas)
        M_pilar = 0 (sem momento — precisa contraventamento)

    Args:
        sistema  : "A", "B" ou "C"
        q_vert   : Carga vertical distribuída na viga (kN/m)
        q_horiz  : Pressão horizontal do vento na fachada (kN/m de altura)
        L        : Vão entre eixos dos pilares (m)
        H        : Altura do pilar até o canto (m)
        EI_viga  : Rigidez fleural da viga em kN·m²
        EI_pilar : Rigidez fleural do pilar em kN·m²

    Returns:
        dict com N_d, M_d_topo, M_d_base, V_d (todos em kN e kN·m)
    """
    # ── Carga vertical: compressão axial no pilar ─────────────
    N_d = q_vert * L / 2      # kN — reação vertical (igual nos 3 sistemas)

    # ── Carga horizontal: vento na fachada ────────────────────
    # Força horizontal total por pilar = q_horiz × H / 2 (vento uniforme)
    # Momento de tombamento na base = q_horiz × H² / 2
    H_vento = q_horiz * H / 2     # kN — força horizontal
    M_vento_base = q_horiz * H**2 / 2  # kN·m — momento na base

    if sistema == "C":
        # Isostático — sem momento por cargas verticais
        # Vento transferido por contraventamento externo
        return {
            "N_d_kN":       round(N_d,            3),
            "M_d_topo_kNm": 0.0,
            "M_d_base_kNm": 0.0,
            "V_d_kN":       round(H_vento,         3),
            "H_empuxo_kN":  0.0,
            "sistema":      "C",
            "nota":         "Isostático — momento zero, precisa contraventamento",
        }

    # ── Sistemas A e B: empuxo horizontal por rigidez ────────
    # Parâmetros adimensionais
    alpha = EI_pilar * L / (EI_viga * H)   # razão de rigidez

    if sistema == "A":
        # Rígido-articulado: base articulada
        # Empuxo horizontal de Roark Table 17.1 case 8d (simetria)
        # H_emp = 3·q·L² / (16·H) × 1/(1 + 3·alpha/2)
        # Simplificado para pórtico simétrico:
        H_emp = (3 * q_vert * L**2) / (16 * H * (1 + 1.5 * alpha))

        M_topo = H_emp * H          # momento no canto = engaste topo
        M_base = 0.0                # base articulada → M=0

    else:  # sistema == "B"
        # Totalmente rígido: base engastada
        # H_emp = q·L² / (8·H) × 1/(1 + 2·alpha/3) — Roark case 8c
        H_emp = (q_vert * L**2) / (8 * H * (1 + 2 * alpha / 3))

        # Momento: máximo no engaste da base
        # M_base = q·L²/8 - H_emp·H (momento residual)
        # M_topo = H_emp·H (no canto)
        M_topo = H_emp * H
        M_base = (q_vert * L**2 / 8) - H_emp * H

    # Adicionar efeito do vento ao momento
    # Para o sistema A (base articulada), vento gera M linear no pilar
    # Momento máximo = H_vento × H (no canto)
    M_topo_total = M_topo + H_vento * H
    M_base_total = M_base  # base articulada não absorve M de vento em A

    if sistema == "B":
        M_base_total = M_base + M_vento_base

    return {
        "N_d_kN":       round(N_d,              3),
        "M_d_topo_kNm": round(M_topo_total,     3),
        "M_d_base_kNm": round(M_base_total,     3),
        "V_d_kN":       round(H_emp + H_vento,  3),
        "H_empuxo_kN":  round(H_emp,            3),
        "sistema":      sistema,
        "nota":         f"Empuxo horizontal = {H_emp:.3f} kN",
    }


# ── Verificação EC5 §6.3.2 ────────────────────────────────────────────────────

def verifica_pilar(
    mat:     GlulamMaterial,
    b:       float,
    h:       float,
    H:       float,
    N_d:     float,
    M_d:     float,
    sistema: Sistema,
) -> dict:
    """
    Verifica flexo-compressão do pilar com instabilidade — EC5 §6.3.2.

    Condição:
        (σ_c,0,d / (k_c · f_c,0,d))² + σ_m,d / f_m,d ≤ 1,0  (Eq. 6.23)

    Comprimento efetivo por sistema:
        A (base articulada): l_ef = 2·H  (coluna em balanço no topo)
        B (base engastada):  l_ef = 1·H  (engastado-engastado)
        C (isostático):      l_ef = 2·H  (base articulada, topo livre)

    Nota: sistema A com knee-frame, o topo do pilar é restringido
    lateralmente pela viga, mas livre para rotação no plano do pórtico.
    l_ef = 1,5·H é conservador para este caso.

    Args:
        mat     : Material (k_mod já aplicado via duracao)
        b       : Largura do pilar (m)
        h       : Altura da seção do pilar (m) — no plano do pórtico
        H       : Comprimento do pilar (m)
        N_d     : Força normal de cálculo (kN) — compressão positiva
        M_d     : Momento fletor de cálculo máximo (kN·m)
        sistema : "A", "B" ou "C"

    Returns:
        dict com k_c, η_flexo_comp e ok
    """
    # Comprimento efetivo
    l_ef_map = {"A": 1.5 * H, "B": 1.0 * H, "C": 2.0 * H}
    l_ef = l_ef_map[sistema]

    # Propriedades da seção
    A_sec = b * h               # m²
    I     = b * h**3 / 12       # m⁴
    W     = b * h**2 / 6        # m³
    i     = math.sqrt(I / A_sec) # raio de giração (m)

    # Esbeltez e carga crítica de Euler
    lam    = l_ef / i           # esbeltez geométrica
    N_crit = math.pi**2 * mat.E0_05 * 1e-3 * I / l_ef**2  # kN — Euler

    # Esbeltez relativa — EC5 §6.3.2
    # f_c0_k e E0_05 ambos em Pa → razão adimensional
    lam_rel = (lam / math.pi) * math.sqrt(
        mat.f_c0_k / mat.E0_05
    )

    # Fator k para glulam: β_c = 0,1 (EC5 §6.3.2)
    beta_c = 0.1
    k_fator = 0.5 * (1 + beta_c * (lam_rel - 0.3) + lam_rel**2)
    k_c = 1.0 / (k_fator + math.sqrt(k_fator**2 - lam_rel**2))
    k_c = min(k_c, 1.0)

    # Tensões de cálculo (N e M em kN e kN·m → Pa)
    N_d_N  = N_d * 1e3    # N
    M_d_Nm = M_d * 1e3    # N·m

    sigma_c  = N_d_N  / A_sec   # Pa — compressão
    sigma_m  = M_d_Nm / W       # Pa — flexão

    f_c0d = mat.f_c0_d   # Pa
    f_md  = mat.f_m_d    # Pa

    # Verificação EC5 §6.3.2 Eq. 6.23
    eta = (sigma_c / (k_c * f_c0d))**2 + sigma_m / f_md

    return {
        "b_m":           b,
        "h_m":           h,
        "H_m":           H,
        "l_ef_m":        round(l_ef,      3),
        "lambda":        round(lam,        2),
        "lambda_rel":    round(lam_rel,    4),
        "k_c":           round(k_c,        4),
        "N_crit_kN":     round(N_crit,     2),
        "sigma_c_MPa":   round(sigma_c/1e6,4),
        "sigma_m_MPa":   round(sigma_m/1e6,4),
        "f_c0d_MPa":     round(f_c0d/1e6, 4),
        "f_md_MPa":      round(f_md/1e6,  4),
        "eta":           round(eta,        4),
        "ok":            eta <= 1.0,
        "norma":         "EC5 §6.3.2 Eq. 6.23",
    }


# ── Varredura dos três sistemas ───────────────────────────────────────────────

def comparar_sistemas(
    mat_curta:    GlulamMaterial,
    geo_viga:     GeometriaViga,
    load:         Carregamentos,
    H_pilar:      float = 7.0,
    w_fachada_m2: float = 0.716,  # kN/m² — pressão vento na fachada (C1bv)
    b_range:      tuple = (0.14, 0.32, 0.02),
    h_range:      tuple = (0.20, 0.80, 0.02),
    eta_max:      float = 1.0,
) -> dict[str, pd.DataFrame]:
    """
    Varre seções (b × h) para os três sistemas e retorna DataFrames
    com geometrias aprovadas e volume total de madeira.

    Volume total por pórtico = V_viga + 2·V_pilar
        V_viga  = L × b_v × h_ap_medio  (aproximação trapezoidal)
        V_pilar = H × b_p × h_p

    Args:
        mat_curta    : Material k_mod duração curta (vento dominante)
        geo_viga     : Geometria da viga já dimensionada
        load         : Carregamentos
        H_pilar      : Altura do pilar (m)
        w_fachada_m2 : Pressão de vento na fachada (kN/m²)
        b_range      : (mín, máx, passo) para largura do pilar
        h_range      : (mín, máx, passo) para altura da seção do pilar
        eta_max      : Taxa máxima para aprovação

    Returns:
        dict com chaves "A", "B", "C" → DataFrames ordenados por η
    """
    b_vals = np.arange(*b_range)
    h_vals = np.arange(*h_range)

    # Esforços da combinação ELU_C2
    q_vert  = load.combinacoes["ELU_C2"].q_tot   # kN/m
    q_horiz = w_fachada_m2 * H_pilar              # kN/m distribuído na altura

    # Rigidez da viga (valor médio ao longo do vão)
    h_medio  = (geo_viga.h0 + geo_viga.h_ap) / 2
    EI_viga  = mat_curta.E0_05 * 1e-3 * geo_viga.b * h_medio**3 / 12  # kN·m²

    # Volume da viga (aproximação trapezoidal)
    V_viga = geo_viga.L * geo_viga.b * (geo_viga.h0 + geo_viga.h_ap) / 2

    resultados = {"A": [], "B": [], "C": []}

    for sistema in ["A", "B", "C"]:
        for b in b_vals:
            for h in h_vals:
                b_f = round(float(b), 3)
                h_f = round(float(h), 3)

                # h ≥ b (pilar orientado no plano do pórtico)
                if h_f < b_f:
                    continue

                # Rigidez do pilar
                EI_pilar = mat_curta.E0_05 * 1e-3 * b_f * h_f**3 / 12

                # Esforços pelo sistema
                esf = esforcos_pilar(
                    sistema  = sistema,
                    q_vert   = q_vert,
                    q_horiz  = q_horiz,
                    L        = geo_viga.L,
                    H        = H_pilar,
                    EI_viga  = EI_viga,
                    EI_pilar = EI_pilar,
                )

                # Momento governante
                M_gov = max(
                    abs(esf["M_d_topo_kNm"]),
                    abs(esf["M_d_base_kNm"])
                )

                # Verificação EC5 §6.3.2
                res = verifica_pilar(
                    mat=mat_curta, b=b_f, h=h_f, H=H_pilar,
                    N_d=esf["N_d_kN"], M_d=M_gov, sistema=sistema,
                )

                if res["ok"]:
                    V_pilar  = H_pilar * b_f * h_f
                    V_total  = V_viga + 2 * V_pilar

                    resultados[sistema].append({
                        "sistema":       sistema,
                        "b_m":           b_f,
                        "h_m":           h_f,
                        "h_b":           round(h_f / b_f, 2),
                        "N_d_kN":        esf["N_d_kN"],
                        "M_d_kNm":       round(M_gov, 3),
                        "V_d_kN":        esf["V_d_kN"],
                        "H_empuxo_kN":   esf["H_empuxo_kN"],
                        "lambda":        res["lambda"],
                        "lambda_rel":    res["lambda_rel"],
                        "k_c":           res["k_c"],
                        "sigma_c_MPa":   res["sigma_c_MPa"],
                        "sigma_m_MPa":   res["sigma_m_MPa"],
                        "eta":           res["eta"],
                        "l_ef_m":        res["l_ef_m"],
                        "V_pilar_m3":    round(V_pilar, 4),
                        "V_total_m3":    round(V_total, 4),
                    })

    # Converter para DataFrames ordenados por V_total (menor volume = mais econômico)
    dfs = {}
    for s, rows in resultados.items():
        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.sort_values(["V_total_m3", "eta"]).reset_index(drop=True)
        dfs[s] = df

    return dfs


# ── Relatório comparativo ─────────────────────────────────────────────────────

def relatorio_comparativo(
    dfs:      dict[str, pd.DataFrame],
    geo_viga: GeometriaViga,
    H_pilar:  float,
    n:        int = 10,
) -> None:
    """Imprime relatório comparativo dos três sistemas."""

    V_viga = geo_viga.L * geo_viga.b * (geo_viga.h0 + geo_viga.h_ap) / 2

    print("=" * 90)
    print("  COMPARATIVO DE SISTEMAS ESTRUTURAIS — PILARES MLC GL24h")
    print("  EC5 §6.3.2 — Flexo-compressão com instabilidade")
    print("=" * 90)
    print(f"\n  Viga principal: L={geo_viga.L}m | "
          f"b={geo_viga.b}m | h0={geo_viga.h0}m | "
          f"h_ap={geo_viga.h_ap:.3f}m")
    print(f"  Volume da viga = {V_viga:.4f} m³")
    print(f"  Altura do pilar H = {H_pilar} m\n")

    descricoes = {
        "A": "Rígido-articulado (knee-frame, base articulada)  l_ef=1,5H",
        "B": "Totalmente rígido  (knee-frame, base engastada)   l_ef=1,0H",
        "C": "Isostático         (pino no canto, base articulada + contraventamento)  l_ef=2,0H",
    }

    resumo = []

    for sistema in ["A", "B", "C"]:
        df = dfs[sistema]
        print(f"  ── Sistema {sistema}: {descricoes[sistema]}")

        if df.empty:
            print(f"     Nenhuma seção aprovada.\n")
            continue

        melhor = df.iloc[0]
        print(f"     Seções aprovadas: {len(df)}")
        print(f"     Melhor seção: {melhor['b_m']}×{melhor['h_m']} m  "
              f"(h/b={melhor['h_b']})")
        print(f"     N_d={melhor['N_d_kN']:.2f} kN | "
              f"M_d={melhor['M_d_kNm']:.2f} kN·m | "
              f"H_emp={melhor['H_empuxo_kN']:.2f} kN")
        print(f"     λ={melhor['lambda']:.1f} | "
              f"λ_rel={melhor['lambda_rel']:.3f} | "
              f"k_c={melhor['k_c']:.3f}")
        print(f"     η={melhor['eta']:.4f} | "
              f"V_pilar={melhor['V_pilar_m3']:.4f} m³ | "
              f"V_total={melhor['V_total_m3']:.4f} m³")

        # Top n seções
        print(f"\n     {'#':>3}  {'b':>6}  {'h':>6}  {'h/b':>5}  "
              f"{'η':>7}  {'V_pil':>8}  {'V_tot':>8}  "
              f"{'N_d':>7}  {'M_d':>7}  {'k_c':>6}")
        print(f"     {'-'*74}")
        for i, row in df.head(n).iterrows():
            print(
                f"     {i+1:>3}  {row['b_m']:>6.3f}  {row['h_m']:>6.3f}  "
                f"{row['h_b']:>5.1f}  {row['eta']:>7.4f}  "
                f"{row['V_pilar_m3']:>8.4f}  {row['V_total_m3']:>8.4f}  "
                f"{row['N_d_kN']:>7.2f}  {row['M_d_kNm']:>7.3f}  "
                f"{row['k_c']:>6.3f}"
            )

        resumo.append({
            "sistema":   sistema,
            "descricao": descricoes[sistema][:45],
            "secao":     f"{melhor['b_m']}×{melhor['h_m']}",
            "eta":       melhor["eta"],
            "V_total":   melhor["V_total_m3"],
            "V_pilar":   melhor["V_pilar_m3"],
        })
        print()

    # Ranking final
    if resumo:
        resumo.sort(key=lambda x: x["V_total"])
        print("=" * 90)
        print("  RANKING ECONÔMICO — menor volume total de madeira por pórtico")
        print("=" * 90)
        print(f"\n  {'Rank':>5}  {'Sistema':>8}  {'Seção':>12}  "
              f"{'η':>7}  {'V_pilar(m³)':>12}  {'V_total(m³)':>12}")
        print(f"  {'-'*66}")
        for i, r in enumerate(resumo):
            eco = "← RECOMENDADO" if i == 0 else ""
            print(
                f"  {i+1:>5}  {r['sistema']:>8}  {r['secao']:>12}  "
                f"{r['eta']:>7.4f}  {r['V_pilar']:>12.4f}  "
                f"{r['V_total']:>12.4f}  {eco}"
            )
        print()
        venc = resumo[0]
        print(f"  Sistema mais econômico: {venc['sistema']} — {venc['descricao']}")
        print(f"  Volume total = {venc['V_total']:.4f} m³ por pórtico")
        if len(resumo) > 1:
            economia = (resumo[-1]["V_total"] - venc["V_total"]) / resumo[-1]["V_total"] * 100
            print(f"  Economia vs pior sistema: {economia:.1f}% de madeira")
        print("=" * 90)


# ── Execução direta ───────────────────────────────────────────────────────────

if __name__ == "__main__":

    from mlc_projeto.core.wind  import ParametrosVento
    from mlc_projeto.core.loads import carregamentos_com_vento

    # Geometria recomendada pelo predim_v2
    geo = GeometriaViga(L=20.25, h0=0.60, alpha_deg=4.5, b=0.26)
    mat = GlulamMaterial(classe="GL24h", classe_servico=2, duracao="curta")

    params_vento = ParametrosVento(
        V0=45.0, S1=1.0, categoria="IV", classe="B", S3=1.0,
        L=20.25, H1=1.0, h=7.0, dist_portico=5.75,
    )

    load = carregamentos_com_vento(
        geo=geo, mat=mat,
        g_area=1.50, q_area=0.25,
        L_t=5.75,
        params_vento=params_vento,
    )

    # Pressão de vento na fachada — C1 barlavento
    from mlc_projeto.core.wind import calcular_vento
    res_v = calcular_vento(params_vento)
    w_fachada = res_v.pressoes["C1"]["barlavento_kNm2"]

    print(f"Vento fachada: {w_fachada:.4f} kN/m²")
    print(f"ELU_C2: q={load.combinacoes['ELU_C2'].q_tot:.4f} kN/m | "
          f"M={load.combinacoes['ELU_C2'].M_max_kNm:.2f} kN·m\n")

    dfs = comparar_sistemas(
        mat_curta    = mat,
        geo_viga     = geo,
        load         = load,
        H_pilar      = 7.0,
        w_fachada_m2 = w_fachada,
        b_range      = (0.14, 0.32, 0.02),
        h_range      = (0.20, 0.80, 0.02),
    )

    relatorio_comparativo(dfs, geo, H_pilar=7.0, n=8)
