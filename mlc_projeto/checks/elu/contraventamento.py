"""
checks/elu/contraventamento.py — Contraventamento horizontal da cobertura.

Dimensiona as cruzes de St. André no plano da cobertura que estabilizam
lateralmente as vigas duplo-bisel.

SISTEMA ADOTADO:
    Cruzes de St. André em barra redonda de aço nos 2 módulos extremos.
    Painéis: 5,75 m (entre vigas) × 2,53 m (entre terças).
    Apenas a diagonal tracionada é dimensionada — a comprimida flambase
    e é desprezada (hipótese usual para barras esbeltas em tração).

MECANISMO:
    1. As vigas comprimidas têm imperfeição geométrica inicial e₀ = a/500
    2. Essa imperfeição gera força transversal de estabilização q_d
    3. As terças transmitem q_d como força axial até os módulos extremos
    4. As cruzes de St. André resistem à força acumulada nas diagonais

REFERÊNCIAS NORMATIVAS:
    EC5 §9.2.1     — Forças de estabilização
    EC5 §9.2.2     — Rigidez mínima do contraventamento
    EN 1993-1-1 §6.2 — Resistência à tração da barra de aço
    EN 1993-1-1 Tab.3.1 — Propriedades do aço S235/S355
"""

from __future__ import annotations

import math

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.loads     import Carregamentos


# ── Constantes de aço — EN 1993-1-1 Tab.3.1 ─────────────────────────────────

AÇO = {
    "S235": {"f_y": 235.0, "f_u": 360.0},   # MPa
    "S355": {"f_y": 355.0, "f_u": 510.0},
}

GAMMA_M0 = 1.00   # EN 1993-1-1 §6.1 — resistência de seção transversal


# ── Forças de estabilização — EC5 §9.2.1 ─────────────────────────────────────

def calcular_forcas_estabilizacao(
    N_d:      float,
    n_vigas:  int,
    L_comp:   float,
    a:        float,
) -> dict:
    """
    Calcula as forças de estabilização — EC5 §9.2.1.

    Para cada viga comprimida com imperfeição inicial e₀ = a/500,
    a força de estabilização por viga é:

        F_est,i = N_d × (e₀ + δ) / a

    onde δ = a/500 (deslocamento admissível — EC5 §9.2.2)
    e₀ = a/500 (imperfeição geométrica inicial — EC5 §9.2.1)

    A força total considera n_vigas trabalhando em conjunto.

    Args:
        N_d      : Força normal de cálculo por viga (kN)
        n_vigas  : Número de vigas contraventadas
        L_comp   : Comprimento total do galpão (m)
        a        : Distância entre apoios do contraventamento (m)

    Returns:
        dict com e0, delta, F_por_viga, F_total
    """
    e0    = a / 500   # m — imperfeição geométrica inicial (EC5 §9.2.1)
    delta = a / 500   # m — deslocamento admissível (EC5 §9.2.2)

    # Força de estabilização por viga
    F_por_viga = N_d * (e0 + delta) / a   # kN

    # Força total — n vigas
    # EC5 §9.2.2 não aplica fator de redução para grupos quando
    # as vigas são paralelas e carregadas igualmente
    F_total = n_vigas * F_por_viga   # kN

    # Força distribuída ao longo do galpão
    q_estab = F_total / L_comp   # kN/m

    return {
        "e0_m":          round(e0,         5),
        "delta_m":       round(delta,      5),
        "F_por_viga_kN": round(F_por_viga, 4),
        "F_total_kN":    round(F_total,    4),
        "q_estab_kNm":   round(q_estab,    5),
        "n_vigas":       n_vigas,
        "a_m":           a,
    }


# ── Geometria do painel ───────────────────────────────────────────────────────

def geometria_painel(
    L_panel: float,
    s_terca: float,
) -> dict:
    """
    Calcula as propriedades geométricas do painel de contraventamento.

    Painel retangular: L_panel × s_terca
    Diagonal: d = √(L² + s²)
    Ângulo: θ = arctan(s/L)

    Args:
        L_panel : Comprimento do painel = espaçamento entre vigas (m)
        s_terca : Altura do painel = espaçamento entre terças (m)

    Returns:
        dict com diagonal, angulo, cos_theta, sin_theta
    """
    d     = math.sqrt(L_panel**2 + s_terca**2)
    theta = math.atan(s_terca / L_panel)

    return {
        "L_panel_m":  L_panel,
        "s_terca_m":  s_terca,
        "d_diag_m":   round(d,               4),
        "theta_rad":  round(theta,            6),
        "theta_deg":  round(math.degrees(theta), 2),
        "cos_theta":  round(math.cos(theta),  6),
        "sin_theta":  round(math.sin(theta),  6),
    }


# ── Força na diagonal ─────────────────────────────────────────────────────────

def forca_diagonal(
    F_mod:      float,
    n_paineis:  int,
    cos_theta:  float,
) -> dict:
    """
    Calcula a força de tração na diagonal da cruz.

    A força horizontal do módulo é distribuída pelos painéis.
    Cada painel transmite sua parcela pela diagonal tracionada:

        F_diag = (F_mod / n_paineis) / cos(θ)

    Args:
        F_mod     : Força horizontal por módulo de contraventamento (kN)
        n_paineis : Número de painéis por módulo
        cos_theta : Cosseno do ângulo da diagonal

    Returns:
        dict com F_painel e F_diag
    """
    F_painel = F_mod / n_paineis
    F_diag   = F_painel / cos_theta

    return {
        "F_mod_kN":    round(F_mod,    4),
        "n_paineis":   n_paineis,
        "F_painel_kN": round(F_painel, 4),
        "F_diag_kN":   round(F_diag,   4),
    }


# ── Verificação da barra — EN 1993-1-1 §6.2 ──────────────────────────────────

def verificar_barra(
    F_diag_kN: float,
    d_mm:      float,
    aco:       str = "S235",
) -> dict:
    """
    Verifica barra circular maciça sob tração — EN 1993-1-1 §6.2.

    Condição de resistência:
        N_Ed ≤ N_t,Rd = A × f_y / γ_M0

    Não há verificação de flambagem — barra trabalha exclusivamente
    em tração (a diagonal comprimida é desprezada).

    Args:
        F_diag_kN : Força de tração na diagonal (kN)
        d_mm      : Diâmetro da barra (mm)
        aco       : Classe do aço ("S235" ou "S355")

    Returns:
        dict com A, F_Rd, η e ok
    """
    if aco not in AÇO:
        raise ValueError(f"Aço '{aco}' não reconhecido. Use S235 ou S355.")

    f_y   = AÇO[aco]["f_y"]   # MPa
    A_mm2 = math.pi * d_mm**2 / 4   # mm²

    # Resistência à tração — EN 1993-1-1 §6.2.3
    N_t_Rd_kN = A_mm2 * f_y / GAMMA_M0 / 1e3   # kN

    eta = F_diag_kN / N_t_Rd_kN

    return {
        "d_mm":        d_mm,
        "aco":         aco,
        "f_y_MPa":     f_y,
        "A_mm2":       round(A_mm2,      2),
        "N_t_Rd_kN":   round(N_t_Rd_kN,  4),
        "F_diag_kN":   round(F_diag_kN,  4),
        "eta":         round(eta,         4),
        "ok":          eta <= 1.0,
        "norma":       "EN 1993-1-1 §6.2.3",
    }


# ── Verificação completa ──────────────────────────────────────────────────────

def verificar_contraventamento(
    geo:          GeometriaViga,
    mat:          GlulamMaterial,
    load:         Carregamentos,
    L_comp:       float = 46.0,
    n_modulos_cv: int   = 2,
    s_terca:      float = 2.53,
    d_barra_mm:   float = 12.0,
    aco:          str   = "S235",
    n_porticos:   int   = 2,
) -> dict:
    """
    Verificação completa do contraventamento horizontal — EC5 §9.2.

    Sequência:
        1. Calcular N_d na viga (força normal do pórtico de 3 rótulas)
        2. Calcular forças de estabilização EC5 §9.2.1
        3. Distribuir pelos módulos extremos e painéis
        4. Calcular força na diagonal
        5. Verificar barra de aço EN 1993-1-1 §6.2

    Args:
        geo          : Geometria da viga principal
        mat          : Material (para f_c,0 — não usado no cálculo mas mantido
                       por consistência com a interface do pipeline)
        load         : Carregamentos (fornece N_d via N_max_ELU)
        L_comp       : Comprimento total do galpão (m)
        n_modulos_cv : Número de módulos com contraventamento (padrão: 2)
        s_terca      : Espaçamento entre terças (m)
        d_barra_mm   : Diâmetro da barra de aço (mm)
        aco          : Classe do aço ("S235" ou "S355")
        n_porticos   : Número de pórticos lado a lado

    Returns:
        dict com todos os resultados intermediários, η e ok
    """
    # ── Dados da viga ──────────────────────────────────────────
    N_d = load.N_max_ELU()   # kN — força normal na viga

    # ── Número total de vigas contraventadas ──────────────────
    # Por pórtico: n_modulos + 1 vigas ao longo do comprimento
    n_vigas_por_portico = int(L_comp / geo.L * geo.L / geo.L) + 1
    # Simplificação: L_comp / dist_portico + 1
    # Com L_comp=46m e dist_portico=5.75m: 8 módulos → 9 vigas
    n_vigas_portico = round(L_comp / (geo.L / (L_comp / 5.75))) + 1
    # Mais direto:
    n_mod_total = round(L_comp / 5.75)   # 8 módulos
    n_vigas = (n_mod_total + 1) * n_porticos   # 9 × 2 = 18 vigas

    # ── Distância entre apoios do contraventamento ────────────
    # Com n_modulos_cv=2 (só extremos): a = L_comp
    # Com n_modulos_cv=3 (extremos+central): a = L_comp/2
    a = L_comp / (n_modulos_cv - 1)   # m

    # ── Forças de estabilização ───────────────────────────────
    est = calcular_forcas_estabilizacao(N_d, n_vigas, L_comp, a)

    # ── Geometria do painel ───────────────────────────────────
    L_panel = 5.75   # m — espaçamento entre vigas = dist_portico
    pan = geometria_painel(L_panel, s_terca)

    # ── Painéis por módulo extremo ────────────────────────────
    # Por módulo de 5,75m com s=2,53m:
    # Posições terças: 0, 2.53, 5.06, 5.75
    # Espaços iguais de 2,53m: 2 painéis por água
    # Dois pórticos × 2 águas: mas contraventamento é por pórtico
    # n_paineis por módulo = 2 espaços × 2 pórticos = 4
    n_paineis_por_mod = int(L_panel / s_terca) * n_porticos
    # = int(5.75/2.53) × 2 = 2 × 2 = 4

    # ── Força por módulo extremo ──────────────────────────────
    # Cada módulo extremo recebe metade da força total (simetria)
    F_mod = est["F_total_kN"] / 2   # kN

    # ── Força na diagonal ─────────────────────────────────────
    fd = forca_diagonal(F_mod, n_paineis_por_mod, pan["cos_theta"])

    # ── Verificação da barra ──────────────────────────────────
    bar = verificar_barra(fd["F_diag_kN"], d_barra_mm, aco)

    # ── Quantidade de barras ──────────────────────────────────
    n_barras_total = n_modulos_cv * n_paineis_por_mod * 2   # ×2 diagonais
    L_total_m      = n_barras_total * pan["d_diag_m"]
    peso_kg_m      = math.pi * (d_barra_mm/1000)**2 / 4 * 7850   # kg/m
    peso_total_kg  = L_total_m * peso_kg_m

    return {
        # ── Identificação ─────────────────────────────────────
        "sistema":           "Cruzes de St. André — plano cobertura",
        "modulos_cv":        n_modulos_cv,
        "posicao":           "2 módulos extremos",
        # ── Dados da viga ─────────────────────────────────────
        "N_d_kN":            round(N_d,            3),
        "n_vigas":           n_vigas,
        # ── Forças de estabilização (EC5 §9.2.1) ─────────────
        "a_m":               round(a,              2),
        "e0_m":              est["e0_m"],
        "delta_m":           est["delta_m"],
        "F_por_viga_kN":     est["F_por_viga_kN"],
        "F_total_kN":        est["F_total_kN"],
        # ── Geometria do painel ───────────────────────────────
        "L_panel_m":         pan["L_panel_m"],
        "s_terca_m":         pan["s_terca_m"],
        "d_diag_m":          pan["d_diag_m"],
        "theta_deg":         pan["theta_deg"],
        "n_paineis_por_mod": n_paineis_por_mod,
        # ── Força na diagonal ─────────────────────────────────
        "F_mod_kN":          fd["F_mod_kN"],
        "F_painel_kN":       fd["F_painel_kN"],
        "F_diag_kN":         fd["F_diag_kN"],
        # ── Verificação da barra (EN 1993-1-1 §6.2) ──────────
        "d_barra_mm":        d_barra_mm,
        "aco":               aco,
        "A_mm2":             bar["A_mm2"],
        "N_t_Rd_kN":         bar["N_t_Rd_kN"],
        "eta":               bar["eta"],
        "ok":                bar["ok"],
        "norma_barra":       bar["norma"],
        # ── Quantitativo ─────────────────────────────────────
        "n_barras":          n_barras_total,
        "L_barra_m":         round(pan["d_diag_m"],  4),
        "L_total_m":         round(L_total_m,        2),
        "peso_total_kg":     round(peso_total_kg,    1),
        # ── Norma ─────────────────────────────────────────────
        "norma":             "EC5 §9.2.1+§9.2.2 | EN 1993-1-1 §6.2",
    }


# ── Execução direta ───────────────────────────────────────────────────────────

if __name__ == "__main__":

    from mlc_projeto.core.geometry  import GeometriaViga
    from mlc_projeto.core.materials import GlulamMaterial
    from mlc_projeto.core.wind      import ParametrosVento
    from mlc_projeto.core.loads     import carregamentos_com_vento

    geo = GeometriaViga(L=20.25, h0=0.60, alpha_deg=4.5, b=0.26)
    mat = GlulamMaterial(classe="GL24h", classe_servico=2, duracao="curta")
    params = ParametrosVento(V0=45,S1=1,categoria="IV",classe="B",
                              S3=1,L=20.25,H1=1,h=7,dist_portico=5.75)
    load = carregamentos_com_vento(geo=geo,mat=mat,g_area=1.5,q_area=0.25,
                                    L_t=5.75,params_vento=params)

    res = verificar_contraventamento(
        geo=geo, mat=mat, load=load,
        L_comp=46.0, n_modulos_cv=2,
        s_terca=2.53, d_barra_mm=12.0, aco="S235",
        n_porticos=2,
    )

    print("=" * 64)
    print("  CONTRAVENTAMENTO HORIZONTAL — EC5 §9.2")
    print("=" * 64)
    print(f"\n  Sistema : {res['sistema']}")
    print(f"  Módulos : {res['modulos_cv']} ({res['posicao']})")
    print(f"\n  Dados da viga:")
    print(f"    N_d    = {res['N_d_kN']:.2f} kN  (força normal ELU_C2)")
    print(f"    Vigas  = {res['n_vigas']}  ({res['n_vigas']//2} por pórtico × 2 pórticos)")
    print(f"\n  Forças de estabilização (EC5 §9.2.1):")
    print(f"    a      = {res['a_m']:.1f} m  (distância entre contraventamentos)")
    print(f"    e₀     = a/500 = {res['e0_m']:.5f} m")
    print(f"    δ      = a/500 = {res['delta_m']:.5f} m")
    print(f"    F/viga = {res['F_por_viga_kN']:.4f} kN")
    print(f"    F_tot  = {res['F_total_kN']:.4f} kN  ({res['n_vigas']} vigas)")
    print(f"\n  Geometria do painel:")
    print(f"    {res['L_panel_m']} × {res['s_terca_m']} m  "
          f"| d={res['d_diag_m']} m | θ={res['theta_deg']}°")
    print(f"    Painéis por módulo: {res['n_paineis_por_mod']}")
    print(f"\n  Força na diagonal:")
    print(f"    F_mod    = {res['F_mod_kN']:.4f} kN  (por módulo extremo)")
    print(f"    F_painel = {res['F_painel_kN']:.4f} kN  (por painel)")
    print(f"    F_diag   = {res['F_diag_kN']:.4f} kN  (tração na barra)")
    print(f"\n  Verificação da barra (EN 1993-1-1 §6.2):")
    print(f"    d={res['d_barra_mm']:.0f}mm {res['aco']} | "
          f"A={res['A_mm2']:.1f}mm² | N_t,Rd={res['N_t_Rd_kN']:.4f}kN")
    print(f"    η = {res['F_diag_kN']:.4f} / {res['N_t_Rd_kN']:.4f} = {res['eta']:.4f}")
    ok = "✓ APROVADO" if res["ok"] else "✗ REPROVADO"
    print(f"    {ok}")
    print(f"\n  Quantitativo:")
    print(f"    {res['n_barras']} barras × {res['L_barra_m']:.2f} m = "
          f"{res['L_total_m']:.1f} m total")
    print(f"    Peso total: {res['peso_total_kg']:.1f} kg de barra d=12mm S235")
    print(f"\n  Norma: {res['norma']}")
    print("=" * 64)
