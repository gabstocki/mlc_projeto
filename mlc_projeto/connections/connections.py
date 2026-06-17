"""
connections/connections.py — Ligações do pórtico de 3 rótulas. v2

Três ligações dimensionadas:

LIGAÇÃO 1 — Viga na base do pilar (rótula):
    V_d = 97,84 kN  (cortante vertical)
    N_d = 97,84 kN  (compressão — reação vertical)
    M_d = 0         (rótula)
    Resultante = 138,37 kN
    Solução: pinos lisos em chapa embutida — EC5 §8.6
    Os pinos resistem à resultante de V+N por cisalhamento.

LIGAÇÃO 2 — Cumeeira (rótula):
    H   = 621,60 kN  (empuxo horizontal — ao longo do eixo da viga)
    M_d = 0          (rótula)
    V_d ≈ 0          (simétrico) — V pequeno por assimetria de vento
    Verificação de compressão na seção: σ_c,0 e σ_c,90 (EC5 §6.1.4+§6.1.5)
    Pino passante para cisalhamento assimétrico (EC5 §8.6)

LIGAÇÃO 3 — Sapata na fundação:
    N_d = 97,84 kN  (compressão vertical — pilar)
    H_d = 621,60 kN (empuxo horizontal — chumbadores)
    M_d = 0         (rótula)
    Solução: chapa metálica com chumbadores de ancoragem
    Chumbadores dimensionados pelo cisalhamento H_d.

Referências normativas:
    EC5 §8.2   — teoria de Johansen
    EC5 §8.3   — número efetivo e distâncias mínimas
    EC5 §8.6   — pinos lisos
    EC5 §6.1.4 — compressão paralela às fibras
    EC5 §6.1.5 — compressão perpendicular às fibras
    EN 14592   — especificação dos pinos de aço
    EN 1993-1-8 — chapa metálica e chumbadores
"""

from __future__ import annotations

import math
import numpy as np
import pandas as pd

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.loads     import Carregamentos

# Base functions (inlined from connections core)
F_U_K_PINO = 400.0   # MPa — resistência última do aço S355 (EN 14592)
GAMMA_M_ACO = 1.25   # coeficiente parcial do aço


# ── Resistência por esmagamento (embedding) — EC5 §8.2 Eq. 8.25 ──────────────

def f_h_k(rho_k: float, d_mm: float) -> float:
    """
    Resistência de esmagamento característica da madeira — EC5 §8.2 Eq. 8.25.

        f_h,k = 0,082 · (1 - 0,01·d) · ρ_k   [N/mm² = MPa]

    Válido para pinos com θ=0° (paralelo às fibras).
    Para ângulos diferentes, usar equação de Hankinson para f_h,α,k.

    Args:
        rho_k : Massa volúmica característica (kg/m³)
        d_mm  : Diâmetro do pino (mm)

    Returns:
        f_h,k (MPa)
    """
    return 0.082 * (1 - 0.01 * d_mm) * rho_k


def M_y_Rk(f_u_k: float, d_mm: float) -> float:
    """
    Momento plástico característico do pino — EC5 §8.2 Eq. 8.30.

        M_y,Rk = 0,3 · f_u,k · d^2,6   [N·mm]

    Args:
        f_u_k : Resistência última do aço do pino (MPa)
        d_mm  : Diâmetro do pino (mm)

    Returns:
        M_y,Rk (N·mm)
    """
    return 0.3 * f_u_k * d_mm ** 2.6


# ── Modos de Johansen — EC5 §8.2 Tabela 8.2 ─────────────────────────────────

def johansen_chapa_embutida(
    rho_k: float,
    d_mm:  float,
    t_mm:  float,
    f_u_k: float = F_U_K_PINO,
) -> dict:
    """
    Resistência lateral característica por plano de corte — chapa embutida.

    Para ligação madeira-chapa com chapa embutida na ranhura central:
    A chapa divide a peça em dois elementos com espessura t = b/2 cada.
    Cada lado tem UM plano de corte com a chapa.

    Modos aplicáveis (EC5 §8.2 Tabela 8.2 — madeira-chapa, chapa grossa):
        Modo I   : esmagamento na madeira
        Modo IIIb: plastificação do pino + esmagamento na madeira
        Modo IV  : dupla plastificação do pino

    Resistência de cálculo = mínimo entre os modos / γ_M

    Args:
        rho_k : Massa volúmica característica da madeira (kg/m³)
        d_mm  : Diâmetro do pino (mm)
        t_mm  : Espessura do elemento de madeira (mm) = b/2 em mm
        f_u_k : Resistência última do aço (MPa)

    Returns:
        dict com F_v,Rk por modo (N) e modo governante
    """
    f_hk   = f_h_k(rho_k, d_mm)   # MPa
    M_y    = M_y_Rk(f_u_k, d_mm)  # N·mm
    d      = d_mm                   # mm
    t      = t_mm                   # mm

    # ── Modo I — esmagamento na madeira ──────────────────────
    F_I = f_hk * t * d   # N por plano de corte

    # ── Modo IIIb — uma rótula plástica no pino ──────────────
    # EC5 Tabela 8.2 linha 3 (chapa grossa):
    # F_v,Rk = sqrt(2·M_y·f_h,k·d) × 1,15 (fator para chapa grossa)
    # Na verdade para chapa embutida (espessura chapa >> d/2):
    # F_IIIb = 1,15 · sqrt(2 · M_y · f_hk · d)
    F_IIIb = 1.15 * math.sqrt(2 * M_y * f_hk * d)   # N

    # ── Modo IV — duas rótulas plásticas no pino ─────────────
    # EC5 Tabela 8.2 linha 4:
    # F_v,Rk = 2,3 · sqrt(M_y · f_h,k · d)
    F_IV = 2.3 * math.sqrt(M_y * f_hk * d)   # N

    modos = {
        "modo_I_N":    round(F_I,    1),
        "modo_IIIb_N": round(F_IIIb, 1),
        "modo_IV_N":   round(F_IV,   1),
    }

    # Resistência característica por plano de corte = mínimo dos modos
    F_v_Rk = min(F_I, F_IIIb, F_IV)
    modo_gov = min(modos, key=modos.get)

    modos["F_v_Rk_N"]  = round(F_v_Rk, 1)
    modos["modo_gov"]  = modo_gov
    modos["f_hk_MPa"]  = round(f_hk, 3)
    modos["M_y_Nmm"]   = round(M_y, 1)

    return modos


# ── Número efetivo — EC5 §8.3.1.1 ────────────────────────────────────────────

def n_ef(n: int, a1_mm: float, d_mm: float) -> float:
    """
    Número efetivo de pinos em linha paralela às fibras — EC5 §8.3.1.1.

        n_ef = n^0,9 · (a₁ / (13·d))^(1/4)

    Reduz a resistência total do grupo por redistribuição plástica.
    Aplica-se a grupos de pinos alinhados na direção das fibras.

    Args:
        n     : Número de pinos na linha
        a1_mm : Espaçamento entre pinos na direção das fibras (mm)
        d_mm  : Diâmetro do pino (mm)

    Returns:
        n_ef (adimensional, ≤ n)
    """
    return min(n ** 0.9 * (a1_mm / (13 * d_mm)) ** 0.25, float(n))


# ── Distâncias mínimas — EC5 §8.3.1.2 Tabela 8.2 ────────────────────────────

def distancias_minimas(d_mm: float, theta_deg: float = 0.0) -> dict:
    """
    Distâncias mínimas para pinos — EC5 §8.3.1.2 Tabela 8.2.

    Args:
        d_mm      : Diâmetro do pino (mm)
        theta_deg : Ângulo entre força e direção das fibras (graus)
                    0° = força paralela às fibras
                    90° = força perpendicular às fibras

    Returns:
        dict com a1, a2, a3t, a3c, a4t, a4c em mm
    """
    theta = math.radians(theta_deg)
    cos_t = abs(math.cos(theta))

    a1  = (3 + 2 * cos_t) * d_mm          # entre pinos, dir. fibras
    a2  = 3.0 * d_mm                       # entre pinos, perp. fibras
    a3t = max(7.0 * d_mm, 80.0)           # borda carregada
    a3c = max(3.0 * d_mm, 0.0)            # borda não carregada
    a4t = max(3.0 * d_mm, 0.0)            # borda lateral carregada
    a4c = max(3.0 * d_mm, 0.0)            # borda lateral não carregada

    return {
        "a1_mm":  round(a1,  1),
        "a2_mm":  round(a2,  1),
        "a3t_mm": round(a3t, 1),
        "a3c_mm": round(a3c, 1),
        "a4t_mm": round(a4t, 1),
        "a4c_mm": round(a4c, 1),
    }


# ── Verificação geométrica ────────────────────────────────────────────────────

def verificar_geometria_grupo(
    n_total: int,
    d_mm:    float,
    b_mm:    float,
    h0_mm:   float,
    theta_deg: float = 0.0,
) -> dict:
    """
    Verifica se n_total pinos cabem na seção com distâncias mínimas.

    Configura os pinos em linhas perpendiculares às fibras (direção h0).
    Cada linha tem n_linha pinos na direção b.

    Layout:
        Direção b (largura): n_linha pinos com espaçamento a2
        Direção h0 (altura): n_linhas com espaçamento a1

    Args:
        n_total   : Número total de pinos necessários por grupo
        d_mm      : Diâmetro do pino (mm)
        b_mm      : Largura da seção (mm)
        h0_mm     : Altura disponível para o grupo (mm) ≈ 0.35*h0
        theta_deg : Ângulo da força com as fibras

    Returns:
        dict com n_linha, n_linhas, dimensões ocupadas e ok
    """
    dist = distancias_minimas(d_mm, theta_deg)
    a1   = dist["a1_mm"]
    a2   = dist["a2_mm"]
    a4   = dist["a4t_mm"]

    # Número máximo de pinos por linha (direção b)
    # b_mm ≥ 2·a4 + (n_linha-1)·a2
    # n_linha ≤ (b_mm - 2·a4) / a2 + 1
    n_linha_max = max(1, int((b_mm - 2 * a4) / a2) + 1)

    # Número de linhas necessárias
    n_linhas = math.ceil(n_total / n_linha_max)
    n_linha  = math.ceil(n_total / n_linhas)

    # Comprimento ocupado na direção h0
    h_ocupado = (n_linhas - 1) * a1 + 2 * dist["a3t_mm"]

    return {
        "n_linha":      n_linha,
        "n_linhas":     n_linhas,
        "n_total":      n_linha * n_linhas,
        "h_ocupado_mm": round(h_ocupado, 1),
        "h_disp_mm":    round(h0_mm, 1),
        "b_mm":         round(b_mm, 1),
        "ok_geometria": h_ocupado <= h0_mm,
        "a1_mm":        a1,
        "a2_mm":        a2,
    }


# ── LIGAÇÃO 1 — Viga-pilar (rótula base) ─────────────────────────────────────

def dimensionar_ligacao_base(
    mat:    GlulamMaterial,
    load:   Carregamentos,
    geo:    GeometriaViga,
    d_mm:   float = 20.0,
    k_mod:  float = 0.90,
    gamma_M:float = 1.25,
) -> dict:
    """
    Dimensiona a ligação viga-pilar — rótula na base.

    Esforços: V_d + N_d (resultante), M_d = 0.
    Solução: pinos lisos em chapa embutida central.
    Os pinos resistem à resultante F_res por cisalhamento lateral.

    Args:
        mat    : Material da madeira
        load   : Carregamentos (fornece V_d e N_d)
        geo    : Geometria da viga (fornece b e h0)
        d_mm   : Diâmetro do pino (mm)
        k_mod  : Coeficiente de modificação
        gamma_M: Coeficiente parcial

    Returns:
        dict com n_pinos, geometria, η e ok
    """
    V_d = load.V_max_ELU()   # kN
    N_d = load.V_max_ELU()   # kN — reação vertical = N no pilar

    # Resultante das forças na ligação
    F_res_kN = math.sqrt(V_d**2 + N_d**2)
    F_res_N  = F_res_kN * 1e3

    b_mm  = geo.b * 1000
    h0_mm = geo.h0 * 1000
    t_mm  = b_mm / 2   # espessura de cada lado da chapa

    rho_k = mat._p["rho_k"]

    # Resistência por pino — Johansen
    joh      = johansen_chapa_embutida(rho_k, d_mm, t_mm, F_U_K_PINO)
    F_v_Rk   = joh["F_v_Rk_N"] * 2   # 2 planos de corte
    F_v_Rd   = k_mod * F_v_Rk / gamma_M   # N

    # Número mínimo de pinos (sem n_ef)
    n_min = math.ceil(F_res_N / F_v_Rd)

    # Número com n_ef (iterativo)
    dist  = distancias_minimas(d_mm, theta_deg=0.0)
    a1_mm = dist["a1_mm"]
    n_pinos = n_min
    for _ in range(100):
        nef     = n_ef(n_pinos, a1_mm, d_mm)
        R_total = nef * F_v_Rd
        if R_total >= F_res_N:
            break
        n_pinos += 1

    nef_final = n_ef(n_pinos, a1_mm, d_mm)
    R_final   = nef_final * F_v_Rd
    eta       = F_res_N / R_final

    # Verificação geométrica — pinos cabem em h0?
    geo_ok = verificar_geometria_grupo(
        n_total=n_pinos, d_mm=d_mm,
        b_mm=b_mm, h0_mm=h0_mm, theta_deg=0.0
    )

    ok = eta <= 1.0 and geo_ok["ok_geometria"]

    return {
        "ligacao":       "L1 — Viga-pilar (rótula base)",
        "V_d_kN":        round(V_d,            3),
        "N_d_kN":        round(N_d,            3),
        "F_res_kN":      round(F_res_kN,       3),
        "d_mm":          d_mm,
        "t_lado_mm":     round(t_mm,           1),
        "F_v_Rd_kN":     round(F_v_Rd/1e3,    3),
        "modo_gov":      joh["modo_gov"],
        "n_pinos":       n_pinos,
        "n_ef":          round(nef_final,      3),
        "R_total_kN":    round(R_final/1e3,    3),
        "n_linha":       geo_ok["n_linha"],
        "n_linhas":      geo_ok["n_linhas"],
        "h_ocupado_mm":  geo_ok["h_ocupado_mm"],
        "h_disp_mm":     round(h0_mm,          1),
        "ok_geometria":  geo_ok["ok_geometria"],
        "a1_mm":         dist["a1_mm"],
        "a2_mm":         dist["a2_mm"],
        "eta":           round(eta,            4),
        "ok":            ok,
        "norma":         "EC5 §8.2+§8.3+§8.6",
    }


# ── LIGAÇÃO 2 — Cumeeira (rótula) ────────────────────────────────────────────

def dimensionar_ligacao_cumeeira(
    mat:    GlulamMaterial,
    load:   Carregamentos,
    geo:    GeometriaViga,
    d_mm:   float = 30.0,
    k_mod:  float = 0.90,
    gamma_M:float = 1.25,
) -> dict:
    """
    Dimensiona a ligação na cumeeira — rótula.

    Esforços:
        H = 621,60 kN ao longo do eixo da viga (compressão interna)
        Componentes na seção transversal:
            N_c0  = H·cos(α) — paralelo às fibras  → EC5 §6.1.4
            N_c90 = H·sin(α) — perpendicular       → EC5 §6.1.5
        V_cumeeira ≈ 0 (simétrico), mas sob vento assimétrico V≠0.

    Para o pino passante: dimensionado pelo cisalhamento assimétrico
    de vento (estimativa: V ≈ w_C1bv × L/4).

    Args:
        mat    : Material
        load   : Carregamentos
        geo    : Geometria
        d_mm   : Diâmetro do pino passante (mm)
        k_mod  : k_mod para duração curta
        gamma_M: γ_M

    Returns:
        dict com verificações de compressão e pino
    """
    H     = load.H_ELU()          # kN — empuxo
    alpha = geo.alpha_rad
    b     = geo.b                  # m
    h_ap  = geo.h_ap               # m

    # Decomposição do empuxo nas fibras
    N_c0_kN  = H * math.cos(alpha)   # kN — paralelo
    N_c90_kN = H * math.sin(alpha)   # kN — perpendicular
    A_sec    = b * h_ap              # m²

    # Tensões de compressão na seção da cumeeira
    sig_c0  = N_c0_kN  * 1e3 / A_sec    # Pa
    sig_c90 = N_c90_kN * 1e3 / A_sec    # Pa

    eta_c0  = sig_c0  / mat.f_c0_d
    eta_c90 = sig_c90 / mat.f_c90_d

    # Cisalhamento assimétrico por vento
    # Estimativa conservadora: carga de vento em meia viga
    gov     = load.combinacao_ELU_governante()
    V_asim  = gov.q_tot * geo.L / 4   # kN — estimativa

    # Pino passante resistindo ao cisalhamento V_asim
    rho_k  = mat._p["rho_k"]
    t_mm   = b * 1000 / 2   # espessura de cada lado
    joh    = johansen_chapa_embutida(rho_k, d_mm, t_mm, F_U_K_PINO)
    F_Rd   = k_mod * joh["F_v_Rk_N"] * 2 / gamma_M   # N (2 planos)
    n_pino = max(1, math.ceil(V_asim * 1e3 / F_Rd))
    eta_pino = V_asim * 1e3 / (n_pino * F_Rd)

    eta_gov = max(eta_c0, eta_c90, eta_pino)
    ok      = eta_gov <= 1.0

    return {
        "ligacao":        "L2 — Cumeeira (rótula)",
        "H_kN":           round(H,          3),
        "alpha_deg":      round(math.degrees(alpha), 2),
        # Compressão paralela
        "N_c0_kN":        round(N_c0_kN,    3),
        "sigma_c0_MPa":   round(sig_c0/1e6, 4),
        "f_c0d_MPa":      round(mat.f_c0_d/1e6, 4),
        "eta_c0":         round(eta_c0,     4),
        # Compressão perpendicular
        "N_c90_kN":       round(N_c90_kN,   3),
        "sigma_c90_MPa":  round(sig_c90/1e6,4),
        "f_c90d_MPa":     round(mat.f_c90_d/1e6, 4),
        "eta_c90":        round(eta_c90,    4),
        # Pino de cisalhamento
        "V_asim_kN":      round(V_asim,     3),
        "d_pino_mm":      d_mm,
        "F_Rd_pino_kN":   round(F_Rd/1e3,  3),
        "n_pino":         n_pino,
        "eta_pino":       round(eta_pino,   4),
        # Resultado
        "eta":            round(eta_gov,    4),
        "ok":             ok,
        "norma":          "EC5 §6.1.4+§6.1.5+§8.6",
    }


# ── LIGAÇÃO 3 — Sapata na fundação ───────────────────────────────────────────

def dimensionar_sapata(
    load:     Carregamentos,
    geo:      GeometriaViga,
    F_chu_kN: float = 80.0,
    d_chu_mm: float = 20.0,
) -> dict:
    """
    Dimensiona a sapata articulada na base do pilar.

    Esforços:
        N_d = V_max_ELU = 97,84 kN  (compressão vertical)
        H_d = H_ELU     = 621,60 kN (empuxo horizontal → chumbadores)
        M_d = 0                      (rótula)

    Chumbadores: resistem ao cisalhamento H_d.
    Resistência típica por chumbador M20 S355 em concreto:
        Calculada por EN 1992-4 (ancoragem) ou conservadoramente
        pela resistência ao cisalhamento da seção do chumbador.

    F_v,Rd por chumbador = A_s × f_y / (γ_M × √3)
    Para M20 S355: A_s = 245 mm², f_y = 355 MPa
        F_v,Rd = 245 × 355 / (1,25 × 1,732) = 40,2 kN

    Args:
        load      : Carregamentos
        geo       : Geometria
        F_chu_kN  : Resistência por chumbador ao cisalhamento (kN)
        d_chu_mm  : Diâmetro do chumbador (mm)

    Returns:
        dict com número de chumbadores, η e ok
    """
    N_d = load.V_max_ELU()   # kN
    H_d = load.H_ELU()       # kN

    # Número de chumbadores para H_d
    n_chu = math.ceil(H_d / F_chu_kN)
    eta_H = H_d / (n_chu * F_chu_kN)

    # Chapa de base — compressão N_d no pilar
    # Área da chapa: N_d / f_c,90,concreto
    # f_c,90,concreto ≈ 1,5 MPa (C25/30 sob carga localizada)
    f_c_conc = 1.5   # MPa — conservador
    A_chapa_m2 = N_d * 1e3 / (f_c_conc * 1e6)
    A_chapa_cm2 = A_chapa_m2 * 1e4

    # Dimensões mínimas da chapa (quadrada)
    lado_chapa = math.sqrt(A_chapa_m2) * 100   # cm

    return {
        "ligacao":        "L3 — Sapata na fundação",
        "N_d_kN":         round(N_d,          3),
        "H_d_kN":         round(H_d,          3),
        # Chumbadores
        "d_chu_mm":       d_chu_mm,
        "F_chu_kN":       F_chu_kN,
        "n_chumbadores":  n_chu,
        "eta_H":          round(eta_H,         4),
        # Chapa de base
        "A_chapa_cm2":    round(A_chapa_cm2,  2),
        "lado_chapa_cm":  round(lado_chapa,   1),
        # Resultado
        "eta":            round(eta_H,         4),
        "ok":             eta_H <= 1.0,
        "norma":          "EN 1993-1-8 + EN 1992-4",
        "nota":           "Chumbadores dimensionados conservadoramente. "
                          "Verificação final conforme EN 1992-4.",
    }


# ── Dimensionamento completo ──────────────────────────────────────────────────

def dimensionar_ligacoes(
    mat:   GlulamMaterial,
    load:  Carregamentos,
    geo:   GeometriaViga,
    d_base_mm:    float = 20.0,
    d_cum_mm:     float = 30.0,
    F_chu_kN:     float = 80.0,
) -> dict:
    """
    Dimensiona as três ligações do pórtico de 3 rótulas.

    Returns:
        dict com resultados das três ligações e η governante global
    """
    L1 = dimensionar_ligacao_base(mat, load, geo, d_mm=d_base_mm)
    L2 = dimensionar_ligacao_cumeeira(mat, load, geo, d_mm=d_cum_mm)
    L3 = dimensionar_sapata(load, geo, F_chu_kN=F_chu_kN)

    eta_gov = max(L1["eta"], L2["eta"], L3["eta"])
    lig_gov = (
        "L1 base"    if L1["eta"] >= L2["eta"] and L1["eta"] >= L3["eta"]
        else "L2 cumeeira" if L2["eta"] >= L3["eta"]
        else "L3 sapata"
    )

    return {
        "L1": L1,
        "L2": L2,
        "L3": L3,
        "eta":     round(eta_gov, 4),
        "ok":      L1["ok"] and L2["ok"] and L3["ok"],
        "lig_gov": lig_gov,
    }


# ── Varredura de diâmetros ────────────────────────────────────────────────────

def varrer_ligacao_base(
    mat:      GlulamMaterial,
    load:     Carregamentos,
    geo:      GeometriaViga,
    d_opcoes: list = [12, 16, 20, 24],
    k_mod:    float = 0.90,
) -> pd.DataFrame:
    """Varre diâmetros de pino para Ligação 1."""
    resultados = []
    for d in d_opcoes:
        r = dimensionar_ligacao_base(mat, load, geo, d_mm=d, k_mod=k_mod)
        resultados.append({
            "d_mm":          d,
            "n_pinos":       r["n_pinos"],
            "n_ef":          r["n_ef"],
            "F_Rd_kN":       r["F_v_Rd_kN"],
            "R_total_kN":    r["R_total_kN"],
            "layout":        f"{r['n_linha']}×{r['n_linhas']}",
            "h_ocup_mm":     r["h_ocupado_mm"],
            "h_disp_mm":     r["h_disp_mm"],
            "ok_geom":       r["ok_geometria"],
            "eta":           r["eta"],
            "ok":            r["ok"],
            "modo":          r["modo_gov"],
        })
    return pd.DataFrame(resultados)


# ── Relatório ─────────────────────────────────────────────────────────────────

def relatorio_ligacoes(res: dict) -> None:
    """Imprime relatório completo das três ligações."""
    print("=" * 70)
    print("  LIGAÇÕES DO PÓRTICO DE 3 RÓTULAS")
    print("  EC5 §8.2+§8.3+§8.6 | EC5 §6.1.4+§6.1.5 | EN 1993-1-8")
    print("=" * 70)

    for key in ["L1", "L2", "L3"]:
        r = res[key]
        ok = "✓" if r["ok"] else "✗"
        print(f"\n  {ok} {r['ligacao']}")
        print(f"     Norma: {r['norma']}")

        if key == "L1":
            print(f"     V_d={r['V_d_kN']:.2f} kN | N_d={r['N_d_kN']:.2f} kN | "
                  f"F_res={r['F_res_kN']:.2f} kN")
            print(f"     Pinos: d={r['d_mm']:.0f}mm | n={r['n_pinos']} | "
                  f"n_ef={r['n_ef']:.2f} | layout={r['n_linha']}×{r['n_linhas']}")
            print(f"     F_Rd/pino={r['F_v_Rd_kN']:.3f} kN | "
                  f"R_total={r['R_total_kN']:.3f} kN")
            print(f"     Geom: {r['h_ocupado_mm']:.0f}mm ocupado / "
                  f"{r['h_disp_mm']:.0f}mm disponível | "
                  f"a1={r['a1_mm']:.0f}mm a2={r['a2_mm']:.0f}mm")
            print(f"     η = {r['eta']:.4f}")

        elif key == "L2":
            print(f"     H={r['H_kN']:.2f} kN @ α={r['alpha_deg']}°")
            print(f"     σ_c,0={r['sigma_c0_MPa']:.4f} MPa ≤ "
                  f"{r['f_c0d_MPa']:.4f} MPa | η={r['eta_c0']:.4f}")
            print(f"     σ_c,90={r['sigma_c90_MPa']:.4f} MPa ≤ "
                  f"{r['f_c90d_MPa']:.4f} MPa | η={r['eta_c90']:.4f}")
            print(f"     Pino passante: d={r['d_pino_mm']:.0f}mm | "
                  f"n={r['n_pino']} | V_asim={r['V_asim_kN']:.2f} kN | "
                  f"η={r['eta_pino']:.4f}")
            print(f"     η = {r['eta']:.4f}")

        elif key == "L3":
            print(f"     N_d={r['N_d_kN']:.2f} kN | H_d={r['H_d_kN']:.2f} kN")
            print(f"     Chumbadores: d={r['d_chu_mm']:.0f}mm | "
                  f"n={r['n_chumbadores']} | "
                  f"F_chu={r['F_chu_kN']:.0f} kN/chu | η={r['eta_H']:.4f}")
            print(f"     Chapa base: {r['lado_chapa_cm']:.1f}×"
                  f"{r['lado_chapa_cm']:.1f} cm  "
                  f"(A={r['A_chapa_cm2']:.1f} cm²)")
            print(f"     Nota: {r['nota']}")
            print(f"     η = {r['eta']:.4f}")

    print(f"\n  ── Resumo ──────────────────────────────────────────────")
    print(f"  η L1 (base)     = {res['L1']['eta']:.4f}")
    print(f"  η L2 (cumeeira) = {res['L2']['eta']:.4f}")
    print(f"  η L3 (sapata)   = {res['L3']['eta']:.4f}")
    print(f"  η GOVERNANTE    = {res['eta']:.4f}  ({res['lig_gov']})")
    status = "✓ TODAS APROVADAS" if res["ok"] else "✗ VERIFICAR"
    print(f"  Status: {status}")
    print("=" * 70)


# ── Execução direta ───────────────────────────────────────────────────────────

if __name__ == "__main__":

    from mlc_projeto.core.geometry  import GeometriaViga
    from mlc_projeto.core.wind      import ParametrosVento
    from mlc_projeto.core.loads     import carregamentos_com_vento

    geo = GeometriaViga(L=20.25, h0=0.60, alpha_deg=4.5, b=0.26)
    mat = GlulamMaterial(classe="GL24h", classe_servico=2, duracao="curta")

    params_vento = ParametrosVento(
        V0=45.0, S1=1.0, categoria="IV", classe="B", S3=1.0,
        L=20.25, H1=1.0, h=7.0, dist_portico=5.75,
    )

    load = carregamentos_com_vento(
        geo=geo, mat=mat,
        g_area=1.50, q_area=0.25,
        L_t=5.75, params_vento=params_vento,
    )

    print("── Varredura Ligação 1 (base) por diâmetro ──\n")
    df = varrer_ligacao_base(mat, load, geo, d_opcoes=[12,16,20,24])
    print(df.to_string(index=False))

    print("\n── Dimensionamento completo ──\n")
    res = dimensionar_ligacoes(
        mat=mat, load=load, geo=geo,
        d_base_mm=20, d_cum_mm=30, F_chu_kN=80,
    )
    relatorio_ligacoes(res)