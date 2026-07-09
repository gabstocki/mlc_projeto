"""
checks/elu/tercas.py — Dimensionamento das terças em MLC GL24h.

As terças são vigas secundárias biapoiadas que conectam os pórticos,
apoiando diretamente a telha metálica trapezoidal.

Sistema:
    Telha metálica → Terça MLC GL24h → Viga principal MLC GL24h

Geometria:
    Vão das terças    L_t = 5,75 m  (espaçamento entre pórticos)
    Inclinação        α   = igual à viga principal
    Espaçamento s entre terças varrido de 1,00 a 2,00 m

Verificações EC5:
    ELU: Flexão biaxial §6.1.6 Eq. 6.12
         Cisalhamento    §6.1.7
    ELS: Flecha         §2.3.2.2 + Tab. 7.2

Nota sobre flexão biaxial:
    A terça inclinada recebe:
    - Momento My (eixo forte): carga perpendicular ao plano da cobertura
    - Momento Mz (eixo fraco): componente de peso próprio ao longo da inclinação
    A telha metálica fixa a terça contra deslizamento lateral —
    componente Mz é resistida pela própria telha.
    Para o pré-dimensionamento: verificar My apenas (conservador e usual).
    Flexão biaxial completa na verificação final quando seção for definida.

Efeito adicional:
    Espaçamento s adotado = 2,53 m (3 terças intermediárias por meia água)
    Justificativa: telha metálica de 5 m apoiada em 3 pontos
    (2 × 2,53 m = 5,06 m — comprimento comercial da telha).
    l_ef viga principal = 0,9 × 2,53 = 2,277 m

Referência: EC5 §6.1.6 Eq. 6.11–6.12, §6.1.7, §2.3.2.2, Tab. 7.2
"""

from __future__ import annotations

import math
import numpy as np
import pandas as pd
from scipy.integrate import cumulative_trapezoid

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.wind      import ParametrosVento, calcular_vento
from mlc_projeto.checks.elu.flambagem_lateral import calcular_l_ef


# ── Flecha numérica para terça (seção constante) ─────────────────────────────

def flecha_terca(
    q:    float,
    L:    float,
    E:    float,
    b:    float,
    h:    float,
) -> float:
    """
    Flecha máxima analítica para viga bi-apoiada de seção retangular
    constante com carga uniforme.

        w_max = 5·q·L⁴ / (384·E·I)

    Args:
        q : Carga uniforme (N/m)
        L : Vão (m)
        E : Módulo de elasticidade (Pa)
        b : Largura da seção (m)
        h : Altura da seção (m)

    Returns:
        w_max (m)
    """
    I = b * h**3 / 12
    return 5 * q * L**4 / (384 * E * I)


# ── Verificação pontual de uma terça ─────────────────────────────────────────

def verifica_terca(
    mat:     GlulamMaterial,
    L_t:     float,
    s:       float,
    b:       float,
    h:       float,
    alpha_deg: float,
    g_k_m2:  float,
    q_k_m2:  float,
    w_kNm2:  float,
    k_m:     float = 0.7,
) -> dict:
    """
    Verifica uma terça de seção retangular (b × h) sob flexão e cisalhamento.

    Args:
        mat      : Material GL24h
        L_t      : Vão da terça (m) = espaçamento entre pórticos
        s        : Espaçamento entre terças (m) = área tributária
        b        : Largura da seção (m)
        h        : Altura da seção (m)
        alpha_deg: Inclinação da cobertura (graus) — mesma da viga
        g_k_m2   : Carga permanente por área (kN/m²)
        q_k_m2   : Sobrecarga por área (kN/m²)
        w_kNm2   : Pressão de vento resultante (kN/m²) — positivo=baixo
        k_m      : Coeficiente para seção retangular = 0,7 (EC5 §6.1.6)

    Returns:
        dict com todos os resultados, η por verificação e ok
    """
    # ── Cargas lineares na terça (kN/m) ──────────────────────
    # Área tributária por metro de terça = s × 1,0 m
    g_k_lin = g_k_m2 * s    # kN/m — permanente
    q_k_lin = q_k_m2 * s    # kN/m — sobrecarga
    w_k_lin = w_kNm2  * s   # kN/m — vento

    # ── Combinação ELU governante ─────────────────────────────
    # ELU_C2: 1,35G + 1,5W + 1,05Q — vento dominante (curta duração)
    q_ELU = 1.35*g_k_lin + 1.50*w_k_lin + 1.05*q_k_lin  # kN/m

    # Para sucção: 0,9G + 1,5W_suc (verificar separadamente se necessário)

    # ── Propriedades da seção ─────────────────────────────────
    A   = b * h                  # m²
    I_y = b * h**3 / 12         # m⁴ — eixo forte
    W_y = b * h**2 / 6          # m³ — módulo resistente eixo forte
    I_z = h * b**3 / 12         # m⁴ — eixo fraco
    W_z = h * b**2 / 6          # m³ — módulo resistente eixo fraco

    # ── Esforços ELU (bi-apoiada, carga uniforme) ─────────────
    M_d_Nm   = q_ELU * L_t**2 / 8 * 1e3   # N·m — momento máximo
    V_d_N    = q_ELU * L_t / 2  * 1e3    # N   — cortante máximo

    # ── Componente lateral (Mz) ───────────────────────────────
    # A componente do peso próprio ao longo da inclinação cria Mz
    # Como a telha metálica restringe o deslizamento, Mz ≈ 0
    # Para verificação conservadora, incluímos 10% do momento total
    # como Mz (equivalente a considerar fixação imperfeita)
    alpha_rad = math.radians(alpha_deg)
    g_lin_lat = g_k_lin * math.sin(alpha_rad)   # componente lateral
    M_z_Nm    = 1.35 * g_lin_lat * L_t**2 / 8 * 1e3  # N·m

    # ── Tensões ───────────────────────────────────────────────
    sigma_my = M_d_Nm / W_y    # Pa — flexão eixo forte
    sigma_mz = M_z_Nm / W_z   # Pa — flexão eixo fraco
    # EC5 §6.1.7: b_ef = k_cr · b → A_ef = k_cr · A
    tau_d    = 1.5 * V_d_N / (mat.k_cr * A)  # Pa — cisalhamento

    # ── Resistências de cálculo (k_mod curta duração) ─────────
    mat_curta = GlulamMaterial(mat.classe, mat.classe_servico, "curta")
    f_md = mat_curta.f_m_d    # Pa
    f_vd = mat_curta.f_v_d    # Pa

    # ── Verificação flexão biaxial — EC5 §6.1.6 Eq. 6.12 ─────
    # Condição 1: σ_my/f_md + k_m·σ_mz/f_md ≤ 1,0
    # Condição 2: k_m·σ_my/f_md + σ_mz/f_md ≤ 1,0
    eta_bx1 = sigma_my/f_md + k_m * sigma_mz/f_md
    eta_bx2 = k_m * sigma_my/f_md + sigma_mz/f_md
    eta_flex = max(eta_bx1, eta_bx2)

    # ── Verificação cisalhamento — EC5 §6.1.7 ────────────────
    eta_cis = tau_d / f_vd

    # ── Verificação flecha ELS ────────────────────────────────
    # ELS S1: G + Q + 0,6W
    q_ELS_S1 = (g_k_lin + q_k_lin + 0.6*w_k_lin) * 1e3  # N/m
    mat_longa = GlulamMaterial(mat.classe, mat.classe_servico, "longa")
    w_inst = flecha_terca(q_ELS_S1, L_t, mat_longa.E0_mean, b, h)

    # Flecha final com fluência
    w_G  = flecha_terca(g_k_lin*1e3, L_t, mat_longa.E0_mean, b, h)
    w_Q1 = flecha_terca(q_k_lin*1e3, L_t, mat_longa.E0_mean, b, h)
    w_fin = w_G*(1+mat_longa.k_def) + w_Q1

    lim_inst = L_t / 300
    lim_fin  = L_t / 250
    eta_inst = w_inst / lim_inst
    eta_fin  = w_fin  / lim_fin
    eta_els  = max(eta_inst, eta_fin)

    # ── Resultado global ──────────────────────────────────────
    etas = {
        "flexao":      eta_flex,
        "cisalh.":     eta_cis,
        "ELS":         eta_els,
    }
    eta_gov   = max(etas.values())
    verif_gov = max(etas, key=etas.get)

    return {
        # Geometria
        "L_t_m":        L_t,
        "s_m":          s,
        "b_m":          b,
        "h_m":          h,
        "h_b":          round(h/b, 2),
        "alpha_deg":    alpha_deg,
        # Cargas
        "q_ELU_kNm":   round(q_ELU,         4),
        "g_lin_kNm":   round(g_k_lin,        4),
        "q_lin_kNm":   round(q_k_lin,        4),
        "w_lin_kNm":   round(w_k_lin,        4),
        # Esforços
        "M_d_kNm":     round(M_d_Nm/1e3,    4),
        "V_d_kN":      round(V_d_N/1e3,     4),
        "M_z_kNm":     round(M_z_Nm/1e3,    4),
        # Tensões (MPa)
        "sigma_my_MPa":round(sigma_my/1e6,  4),
        "sigma_mz_MPa":round(sigma_mz/1e6,  4),
        "tau_d_MPa":   round(tau_d/1e6,     4),
        "f_md_MPa":    round(f_md/1e6,      4),
        "f_vd_MPa":    round(f_vd/1e6,      4),
        # Taxas de utilização
        "eta_flexao":  round(eta_flex,       4),
        "eta_cisalh":  round(eta_cis,        4),
        "eta_ELS":     round(eta_els,        4),
        "eta_gov":     round(eta_gov,        4),
        "verif_gov":   verif_gov,
        "ok":          eta_gov <= 1.0,
        # Flechas
        "w_inst_mm":   round(w_inst*1000,    2),
        "w_fin_mm":    round(w_fin*1000,     2),
        "lim_inst_mm": round(lim_inst*1000,  2),
        "lim_fin_mm":  round(lim_fin*1000,   2),
        # Referência
        "norma":       "EC5 §6.1.6 Eq.6.12, §6.1.7, Tab.7.2",
    }


# ── Varredura paramétrica das terças ─────────────────────────────────────────

def varrer_tercas(
    mat:          GlulamMaterial,
    L_t:          float,
    alpha_deg:    float,
    g_k_m2:       float,
    q_k_m2:       float,
    params_vento: ParametrosVento,
    s_range:      tuple = (1.00, 2.75, 0.25),
    b_range:      tuple = (0.10, 0.22, 0.02),
    h_range:      tuple = (0.16, 0.60, 0.02),
    eta_max:      float = 1.0,
) -> pd.DataFrame:
    """
    Varre (s, b, h) e verifica flexão biaxial, cisalhamento e flecha.

    Para cada espaçamento s varrido, calcula também o l_ef
    correspondente para a viga principal (restrição lateral).

    Args:
        mat          : Material GL24h
        L_t          : Vão da terça (m)
        alpha_deg    : Inclinação da cobertura (graus)
        g_k_m2       : Carga permanente por área (kN/m²)
        q_k_m2       : Sobrecarga por área (kN/m²)
        params_vento : Parâmetros de vento NBR 6123
        s_range      : (mín, máx, passo) para espaçamento s (m)
        b_range      : (mín, máx, passo) para largura b (m)
        h_range      : (mín, máx, passo) para altura h (m)
        eta_max      : Taxa máxima para aprovação

    Returns:
        DataFrame com geometrias aprovadas, ordenado por η governante
    """
    # Pressão de vento C1 barlavento (mais desfavorável)
    res_vento = calcular_vento(params_vento)
    w_C1bv_m2 = res_vento.pressoes["C1"]["barlavento_kNm2"]

    s_vals = np.arange(*s_range)
    b_vals = np.arange(*b_range)
    h_vals = np.arange(*h_range)

    resultados = []

    for s in s_vals:
        s_f = round(float(s), 3)

        # l_ef da viga principal para este espaçamento
        l_ef_viga = calcular_l_ef(s_f, restricao="continua_topo")

        for b in b_vals:
            for h in h_vals:
                b_f = round(float(b), 3)
                h_f = round(float(h), 3)

                # Seção mínima: h ≥ b (evitar seção deitada)
                if h_f < b_f:
                    continue

                res = verifica_terca(
                    mat=mat,
                    L_t=L_t,
                    s=s_f,
                    b=b_f,
                    h=h_f,
                    alpha_deg=alpha_deg,
                    g_k_m2=g_k_m2,
                    q_k_m2=q_k_m2,
                    w_kNm2=w_C1bv_m2,
                )

                if res["ok"]:
                    resultados.append({
                        "s_m":          s_f,
                        "b_m":          b_f,
                        "h_m":          h_f,
                        "h_b":          res["h_b"],
                        "l_ef_viga_m":  round(l_ef_viga, 3),
                        "q_ELU_kNm":    res["q_ELU_kNm"],
                        "M_d_kNm":      res["M_d_kNm"],
                        "eta_flexao":   res["eta_flexao"],
                        "eta_cisalh":   res["eta_cisalh"],
                        "eta_ELS":      res["eta_ELS"],
                        "eta_gov":      res["eta_gov"],
                        "verif_gov":    res["verif_gov"],
                        "w_inst_mm":    res["w_inst_mm"],
                        "w_fin_mm":     res["w_fin_mm"],
                        "lim_inst_mm":  res["lim_inst_mm"],
                        "lim_fin_mm":   res["lim_fin_mm"],
                        "sigma_my_MPa": res["sigma_my_MPa"],
                        "sigma_mz_MPa": res["sigma_mz_MPa"],
                        "f_md_MPa":     res["f_md_MPa"],
                    })

    df = pd.DataFrame(resultados)
    if not df.empty:
        df = df.sort_values(["eta_gov", "h_m"]).reset_index(drop=True)
    return df


# ── Relatório ─────────────────────────────────────────────────────────────────

def relatorio_tercas(df: pd.DataFrame, n: int = 25) -> None:
    """Imprime relatório das terças com impacto em l_ef da viga principal."""
    print("=" * 100)
    print("  DIMENSIONAMENTO DAS TERÇAS — GL24h")
    print("  EC5 §6.1.6 (flexão biaxial) | §6.1.7 (cisalhamento) | Tab.7.2 (flecha)")
    print("  Inclui l_ef recalculado para a viga principal")
    print("=" * 100)

    if df.empty:
        print("\n  Nenhuma seção aprovada no intervalo varrido.")
        print("  Sugestões:")
        print("  — Aumentar h (altura da terça)")
        print("  — Reduzir s (espaçamento entre terças)")
        print("=" * 100)
        return

    print(f"\n  Total de seções aprovadas: {len(df)}")
    print(f"  Exibindo as {min(n, len(df))} melhores:\n")

    hdr = (
        f"  {'#':>3}  {'s(m)':>6}  {'b(m)':>6}  {'h(m)':>6}  "
        f"{'h/b':>5}  {'l_ef_viga':>10}  "
        f"{'η_flex':>8}  {'η_cis':>7}  "
        f"{'η_ELS':>7}  {'η_gov':>7}  "
        f"{'w_inst':>8}  {'w_fin':>7}  {'Governa'}"
    )
    print(hdr)
    print("  " + "-" * 94)

    for i, row in df.head(n).iterrows():
        print(
            f"  {i+1:>3}  {row['s_m']:>6.2f}  {row['b_m']:>6.3f}  "
            f"{row['h_m']:>6.3f}  {row['h_b']:>5.1f}  "
            f"{row['l_ef_viga_m']:>10.3f}  "
            f"{row['eta_flexao']:>8.4f}  {row['eta_cisalh']:>7.4f}  "
            f"{row['eta_ELS']:>7.4f}  {row['eta_gov']:>7.4f}  "
            f"{row['w_inst_mm']:>6.1f}mm  "
            f"{row['w_fin_mm']:>5.1f}mm  {row['verif_gov']}"
        )

    m = df.iloc[0]
    print(f"\n  ── Terça recomendada ──────────────────────────────────────")
    print(f"  Espaçamento s  = {m['s_m']} m")
    print(f"  Seção          = {m['b_m']} × {m['h_m']} m  (b × h)")
    print(f"  h/b            = {m['h_b']}")
    print(f"  q_ELU          = {m['q_ELU_kNm']:.4f} kN/m")
    print(f"  M_d            = {m['M_d_kNm']:.4f} kN·m")
    print(f"  σ_m,y,d        = {m['sigma_my_MPa']:.4f} MPa")
    print(f"  σ_m,z,d        = {m['sigma_mz_MPa']:.4f} MPa")
    print(f"  f_m,d          = {m['f_md_MPa']:.4f} MPa")
    print(f"  η flexão       = {m['eta_flexao']:.4f}")
    print(f"  η cisalhamento = {m['eta_cisalh']:.4f}")
    print(f"  η ELS          = {m['eta_ELS']:.4f}")
    print(f"  η governante   = {m['eta_gov']:.4f}  ({m['verif_gov']})")
    print(f"  w_inst         = {m['w_inst_mm']:.1f} mm  "
          f"(limite {m['lim_inst_mm']:.1f} mm)")
    print(f"  w_fin          = {m['w_fin_mm']:.1f} mm  "
          f"(limite {m['lim_fin_mm']:.1f} mm)")
    print(f"  ───────────────────────────────────────────────────────────")
    print(f"  Impacto na viga principal:")
    print(f"  l_ef (viga) com s={m['s_m']}m = {m['l_ef_viga_m']} m")
    print(f"  (antes: l_ef = 5,175 m com s=5,75 m assumido)")
    delta = 5.175 - m['l_ef_viga_m']
    print(f"  Redução de l_ef = {delta:.3f} m → "
          f"{'melhora' if delta > 0 else 'piora'} a flambagem lateral da viga")
    print("=" * 100)


# ── Execução direta ───────────────────────────────────────────────────────────

if __name__ == "__main__":

    mat = GlulamMaterial(classe="GL24h", classe_servico=2, duracao="longa")

    params_vento = ParametrosVento(
        V0=45.0, S1=1.0, categoria="IV", classe="B", S3=1.0,
        L=20.25, H1=1.0, h=7.0, dist_portico=5.75,
    )

    print(f"Material : {mat.classe} | CS {mat.classe_servico}")
    print(f"Vão das terças : 5,75 m")
    print(f"Inclinação     : 5,64°\n")

    df = varrer_tercas(
        mat          = mat,
        L_t          = 5.75,
        alpha_deg    = 5.64,
        g_k_m2       = 1.50,
        q_k_m2       = 0.25,
        params_vento = params_vento,
        s_range      = (1.00, 2.75, 0.25),   # cobre s=2,53m adotado
        b_range      = (0.10, 0.22, 0.02),
        h_range      = (0.16, 0.60, 0.02),
    )

    relatorio_tercas(df, n=25)