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
from mlc_projeto.core.materials import GlulamMaterial, GAMMA_M_LIGACAO
from mlc_projeto.core.loads     import Carregamentos

# Pinos de aço — EN 14592 (grau típico de cavilha; f_u a confirmar na ficha)
F_U_K_PINO = 400.0   # MPa — f_u,k do pino (não confundir com f_y do S355)


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


# ── Verificação geométrica — chapa embutida no extremo da viga ───────────────

def verificar_geometria_grupo(
    n_horiz: int,
    n_vert:  int,
    d_mm:    float,
    h0_mm:   float,
    theta_deg: float = 0.0,
    L_max_mm: float = 1500.0,
) -> dict:
    """
    Verifica o grupo de pinos na chapa embutida no extremo da viga.

    Orientação EC5 Tab. 8.2 (fibras ≈ eixo longitudinal da viga):
        - Horizontal (// fibras, no plano da chapa): espaçamento a1, extremos a3t/a3c
        - Vertical   (⊥ fibras, altura da secção):   espaçamento a2, bordas a4t/a4c

    A chapa fica no plano longitudinal-vertical (fenda central em b).
    Os pinos atravessam a largura b (espessura de madeira t = b/2 por lado).

    Args:
        n_horiz  : pinos por fileira // fibras
        n_vert   : número de fileiras na altura
        d_mm     : diâmetro do pino (mm)
        h0_mm    : altura disponível na secção do apoio (mm)
        theta_deg: ângulo força–fibras (para distâncias mínimas)
        L_max_mm : comprimento máximo da ligação ao longo da viga (mm)
                   — critério de pormenorização (não EC5); default 1,5 m

    Returns:
        dict com ocupação e ok_geometria
    """
    dist = distancias_minimas(d_mm, theta_deg)
    a1   = dist["a1_mm"]
    a2   = dist["a2_mm"]
    a3t  = dist["a3t_mm"]
    a3c  = dist["a3c_mm"]
    a4   = dist["a4t_mm"]

    n_horiz = max(1, n_horiz)
    n_vert  = max(1, n_vert)

    # Altura ocupada (⊥ fibras): 2·a4 + (n_vert−1)·a2
    h_ocupado = 2 * a4 + (n_vert - 1) * a2
    # Comprimento ao longo da viga (// fibras): a3t + (n_horiz−1)·a1 + a3c
    L_ocupado = a3t + (n_horiz - 1) * a1 + a3c

    n_vert_max = max(1, int((h0_mm - 2 * a4) / a2) + 1) if a2 > 0 else 1

    ok = (h_ocupado <= h0_mm + 1e-6) and (L_ocupado <= L_max_mm + 1e-6)

    return {
        "n_linha":      n_horiz,   # pinos // fibras (por fileira)
        "n_linhas":     n_vert,    # fileiras na altura
        "n_total":      n_horiz * n_vert,
        "h_ocupado_mm": round(h_ocupado, 1),
        "L_ocupado_mm": round(L_ocupado, 1),
        "h_disp_mm":    round(h0_mm, 1),
        "n_vert_max":   n_vert_max,
        "ok_geometria": ok,
        "a1_mm":        a1,
        "a2_mm":        a2,
        "a3t_mm":       a3t,
        "a4t_mm":       a4,
    }


# ── LIGAÇÃO 1 — Viga-pilar (rótula base) ─────────────────────────────────────

def dimensionar_ligacao_base(
    mat:     GlulamMaterial,
    load:    Carregamentos,
    geo:     GeometriaViga,
    d_mm:    float = 20.0,
    k_mod:   float | None = None,
    gamma_M: float = GAMMA_M_LIGACAO,
    eta_alvo: float = 0.85,
) -> dict:
    """
    Dimensiona a ligação viga-pilar — rótula na base.

    Esforços no eixo da viga (biarticulada):
        N_d = N_viga  (compressão axial no apoio)
        V_d = V_viga  (cortante no eixo no apoio)
        M_d = 0       (rótula)
        F_res = √(N_d² + V_d²)

    Solução: pinos lisos em chapa embutida central (EC5 §8.2+§8.5.1.1+§8.6).
    γ_M = 1,30 (EC5 Tab. 2.3 — ligações).
    k_mod: duração da combinação (padrão = mat.k_mod).
    eta_alvo: margem de projecto (uso público) — R ≥ F_res / eta_alvo.
              EC5 exige η ≤ 1,0; o alvo 0,85 é critério de projecto.
    """
    if k_mod is None:
        k_mod = mat.k_mod
    if eta_alvo <= 0 or eta_alvo > 1.0:
        raise ValueError("eta_alvo deve estar em (0, 1]")

    # Componentes no eixo da viga — análise biarticulada
    N_d = load.N_max_ELU()     # kN — axial (// fibras)
    V_d = load.V_viga_ELU()    # kN — cortante (⊥ eixo)
    R_v = load.V_max_ELU()
    H   = load.H_ELU()

    F_res_kN = math.sqrt(N_d ** 2 + V_d ** 2)
    F_res_N  = F_res_kN * 1e3
    # Capacidade mínima de projecto (margem)
    R_req_N  = F_res_N / eta_alvo
    # Ângulo da resultante com as fibras (eixo) — EC5 §8.3 distâncias
    theta_deg = math.degrees(math.atan2(abs(V_d), max(abs(N_d), 1e-9)))

    b_mm  = geo.b * 1000
    h0_mm = geo.h0 * 1000
    t_mm  = b_mm / 2   # espessura de madeira de cada lado da chapa

    rho_k = mat.rho_k

    # Resistência por pino — Johansen; 2 planos de corte
    joh      = johansen_chapa_embutida(rho_k, d_mm, t_mm, F_U_K_PINO)
    F_v_Rk   = joh["F_v_Rk_N"] * 2
    F_v_Rd   = k_mod * F_v_Rk / gamma_M   # N

    dist  = distancias_minimas(d_mm, theta_deg=theta_deg)
    a1_mm = dist["a1_mm"]
    a2_mm = dist["a2_mm"]
    a4_mm = dist["a4t_mm"]

    # Máximo de fileiras na altura (⊥ fibras)
    n_vert_max = max(1, int((h0_mm - 2 * a4_mm) / a2_mm) + 1) if a2_mm > 0 else 1

    # Procura malha (n_horiz × n_vert) com n_ef por fileira // fibras
    # EC5 §8.5.1.1 (pernos/pinos): n_ef = n^0,9·(a1/(13d))^1/4 ≤ n
    best = None
    for n_vert in range(1, n_vert_max + 1):
        for n_horiz in range(1, 21):  # limite prático ao longo da viga
            nef_row = n_ef(n_horiz, a1_mm, d_mm)
            R_N = n_vert * nef_row * F_v_Rd
            if R_N < R_req_N:
                continue
            geo_ok = verificar_geometria_grupo(
                n_horiz=n_horiz, n_vert=n_vert, d_mm=d_mm,
                h0_mm=h0_mm, theta_deg=theta_deg,
            )
            if not geo_ok["ok_geometria"]:
                continue
            n_tot = n_horiz * n_vert
            eta_i = F_res_N / R_N
            cand = {
                "n_horiz": n_horiz, "n_vert": n_vert, "n_tot": n_tot,
                "nef_row": nef_row, "R_N": R_N, "eta": eta_i, "geo": geo_ok,
            }
            if best is None or n_tot < best["n_tot"] or (
                n_tot == best["n_tot"] and eta_i < best["eta"]
            ):
                best = cand

    if best is None:
        # Sem malha factível com eta_alvo — tenta pelo menos η ≤ 1,0
        best_norm = None
        for n_vert in range(1, n_vert_max + 1):
            for n_horiz in range(1, 21):
                nef_row = n_ef(n_horiz, a1_mm, d_mm)
                R_N = n_vert * nef_row * F_v_Rd
                if R_N < F_res_N:
                    continue
                geo_ok = verificar_geometria_grupo(
                    n_horiz=n_horiz, n_vert=n_vert, d_mm=d_mm,
                    h0_mm=h0_mm, theta_deg=theta_deg,
                )
                if not geo_ok["ok_geometria"]:
                    continue
                n_tot = n_horiz * n_vert
                eta_i = F_res_N / R_N
                cand = {
                    "n_horiz": n_horiz, "n_vert": n_vert, "n_tot": n_tot,
                    "nef_row": nef_row, "R_N": R_N, "eta": eta_i, "geo": geo_ok,
                }
                if best_norm is None or n_tot < best_norm["n_tot"]:
                    best_norm = cand
        if best_norm is not None:
            best = best_norm
        else:
            n_horiz = 12
            n_vert  = n_vert_max
            nef_row = n_ef(n_horiz, a1_mm, d_mm)
            R_N     = n_vert * nef_row * F_v_Rd
            geo_ok  = verificar_geometria_grupo(
                n_horiz=n_horiz, n_vert=n_vert, d_mm=d_mm,
                h0_mm=h0_mm, theta_deg=theta_deg,
            )
            eta = F_res_N / R_N if R_N > 0 else 999.0
            n_pinos = n_horiz * n_vert
            nef_final = n_vert * nef_row
            best = None

    if best is not None:
        n_horiz   = best["n_horiz"]
        n_vert    = best["n_vert"]
        n_pinos   = best["n_tot"]
        nef_row   = best["nef_row"]
        nef_final = n_vert * nef_row
        R_N       = best["R_N"]
        eta       = best["eta"]
        geo_ok    = best["geo"]

    ok_norma = eta <= 1.0 and geo_ok["ok_geometria"]
    ok_alvo  = eta <= eta_alvo + 1e-9 and geo_ok["ok_geometria"]
    ok       = ok_norma and ok_alvo

    return {
        "ligacao":       "L1 — Viga-pilar (rótula base)",
        "V_d_kN":        round(V_d,            3),
        "N_d_kN":        round(N_d,            3),
        "R_v_kN":        round(R_v,            3),
        "H_kN":          round(H,              3),
        "F_res_kN":      round(F_res_kN,       3),
        "theta_deg":     round(theta_deg,      2),
        "d_mm":          d_mm,
        "t_lado_mm":     round(t_mm,           1),
        "k_mod":         k_mod,
        "gamma_M":       gamma_M,
        "eta_alvo":      eta_alvo,
        "F_v_Rd_kN":     round(F_v_Rd/1e3,    3),
        "modo_gov":      joh["modo_gov"],
        "n_pinos":       n_pinos,
        "n_ef":          round(nef_final,      3),
        "n_ef_row":      round(nef_row,        3),
        "R_total_kN":    round(R_N/1e3,        3),
        "n_linha":       n_horiz,
        "n_linhas":      n_vert,
        "h_ocupado_mm":  geo_ok["h_ocupado_mm"],
        "L_ocupado_mm":  geo_ok.get("L_ocupado_mm", 0),
        "h_disp_mm":     round(h0_mm,          1),
        "ok_geometria":  geo_ok["ok_geometria"],
        "a1_mm":         dist["a1_mm"],
        "a2_mm":         dist["a2_mm"],
        "eta":           round(eta,            4),
        "ok_alvo":       ok_alvo,
        "ok":            ok,
        "norma":         "EC5 §8.2+§8.5.1.1+§8.6 | γ_M=1,30 | η_alvo projecto",
    }


# ── LIGAÇÃO 2 — Cumeeira (rótula) ────────────────────────────────────────────

def dimensionar_ligacao_cumeeira(
    mat:     GlulamMaterial,
    load:    Carregamentos,
    geo:     GeometriaViga,
    d_mm:    float = 30.0,
    k_mod:   float | None = None,
    gamma_M: float = GAMMA_M_LIGACAO,
) -> dict:
    """
    Verifica a zona de cumeeira da peça monolítica (sem rótula).

    Esforços (simetria de carga vertical + empuxo H):
        M_ap da análise biarticulada (verificação t90 em cumeeira.py)
        Componentes de compressão na secção (H decomposoto):
            N_c0  = H · cos(α)  → EC5 §6.1.4
            N_c90 = H · sin(α)  → EC5 §6.1.5

    Pino passante (se detalhe de montagem): cortante residual por
    assimetria de vento |w_C1bv − w_C1st| · (L/4).
    """
    if k_mod is None:
        k_mod = mat.k_mod

    H     = load.H_ELU()
    alpha = geo.alpha_rad
    b     = geo.b
    h_ap  = geo.h_ap

    N_c0_kN  = H * math.cos(alpha)
    N_c90_kN = H * math.sin(alpha)
    A_sec    = b * h_ap

    sig_c0  = N_c0_kN  * 1e3 / A_sec
    sig_c90 = N_c90_kN * 1e3 / A_sec

    eta_c0  = sig_c0  / mat.f_c0_d
    eta_c90 = sig_c90 / mat.f_c90_d

    # Cortante residual por assimetria de vento (diferença barlavento/sotavento)
    dw = abs(load.w_C1bv_k - load.w_C1st_k)
    V_asim = dw * geo.L / 4.0   # kN — meia viga com Δw

    rho_k = mat.rho_k
    t_mm  = b * 1000 / 2
    joh   = johansen_chapa_embutida(rho_k, d_mm, t_mm, F_U_K_PINO)
    F_Rd  = k_mod * joh["F_v_Rk_N"] * 2 / gamma_M
    n_pino = max(1, math.ceil(V_asim * 1e3 / F_Rd) if F_Rd > 0 else 1)
    eta_pino = (V_asim * 1e3 / (n_pino * F_Rd)) if F_Rd > 0 else 0.0

    eta_gov = max(eta_c0, eta_c90, eta_pino)
    ok      = eta_gov <= 1.0

    return {
        "ligacao":        "L2 — Cumeeira (continuidade MLC)",
        "H_kN":           round(H,          3),
        "alpha_deg":      round(math.degrees(alpha), 2),
        "N_c0_kN":        round(N_c0_kN,    3),
        "sigma_c0_MPa":   round(sig_c0/1e6, 4),
        "f_c0d_MPa":      round(mat.f_c0_d/1e6, 4),
        "eta_c0":         round(eta_c0,     4),
        "N_c90_kN":       round(N_c90_kN,   3),
        "sigma_c90_MPa":  round(sig_c90/1e6,4),
        "f_c90d_MPa":     round(mat.f_c90_d/1e6, 4),
        "eta_c90":        round(eta_c90,    4),
        "V_asim_kN":      round(V_asim,     3),
        "d_pino_mm":      d_mm,
        "k_mod":          k_mod,
        "gamma_M":        gamma_M,
        "F_Rd_pino_kN":   round(F_Rd/1e3,  3),
        "n_pino":         n_pino,
        "eta_pino":       round(eta_pino,   4),
        "eta":            round(eta_gov,    4),
        "ok":             ok,
        "norma":          "EC5 §6.1.4+§6.1.5+§8.6 | γ_M=1,30",
    }


# ── LIGAÇÃO 3 — Sapata na fundação ───────────────────────────────────────────

def dimensionar_sapata(
    load:     Carregamentos,
    geo:      GeometriaViga,
    F_chu_kN: float = 80.0,
    d_chu_mm: float = 20.0,
    eta_alvo: float = 0.85,
) -> dict:
    """
    Dimensiona a sapata articulada na base do pilar.

    Esforços (biarticulada):
        N_d = V_max_ELU  (compressão vertical do pilar)
        H_d = H_ELU      (empuxo horizontal → chumbadores)
        M_d = 0          (rótula)

    Chumbadores: resistem ao cisalhamento H_d.
    n = ceil(H_d / (F_chu · eta_alvo))  — margem de projecto (uso público).
    EC5/EN não impõem eta_alvo; 0,85 é critério de projecto.

    Args:
        load      : Carregamentos
        geo       : Geometria
        F_chu_kN  : Resistência por chumbador ao cisalhamento (kN)
        d_chu_mm  : Diâmetro do chumbador (mm)
        eta_alvo  : taxa de utilização máxima de projecto

    Returns:
        dict com número de chumbadores, η e ok
    """
    if eta_alvo <= 0 or eta_alvo > 1.0:
        raise ValueError("eta_alvo deve estar em (0, 1]")

    N_d = load.V_max_ELU()   # kN
    H_d = load.H_ELU()       # kN

    # Número de chumbadores com margem: H_d ≤ eta_alvo · n · F_chu
    n_chu = max(1, math.ceil(H_d / (F_chu_kN * eta_alvo)))
    eta_H = H_d / (n_chu * F_chu_kN)

    # Chapa de base — compressão N_d no pilar
    f_c_conc = 1.5   # MPa — conservador (C25/30 localizado)
    A_chapa_m2 = N_d * 1e3 / (f_c_conc * 1e6)
    A_chapa_cm2 = A_chapa_m2 * 1e4
    lado_chapa = math.sqrt(A_chapa_m2) * 100   # cm

    ok_norma = eta_H <= 1.0
    ok_alvo  = eta_H <= eta_alvo + 1e-9

    return {
        "ligacao":        "L3 — Sapata na fundação",
        "N_d_kN":         round(N_d,          3),
        "H_d_kN":         round(H_d,          3),
        "d_chu_mm":       d_chu_mm,
        "F_chu_kN":       F_chu_kN,
        "n_chumbadores":  n_chu,
        "eta_alvo":       eta_alvo,
        "eta_H":          round(eta_H,         4),
        "A_chapa_cm2":    round(A_chapa_cm2,  2),
        "lado_chapa_cm":  round(lado_chapa,   1),
        "eta":            round(eta_H,         4),
        "ok_alvo":        ok_alvo,
        "ok":             ok_norma and ok_alvo,
        "norma":          "EN 1993-1-8 + EN 1992-4 | η_alvo projecto",
        "nota":           "Chumbadores com margem eta_alvo. "
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
    eta_alvo:     float = 0.85,
) -> dict:
    """
    Dimensiona as três ligações do pórtico (biarticulada).

    eta_alvo: margem de projecto para L1 e L3 (uso público). L2 usa η ≤ 1,0.
    """
    L1 = dimensionar_ligacao_base(
        mat, load, geo, d_mm=d_base_mm, eta_alvo=eta_alvo,
    )
    L2 = dimensionar_ligacao_cumeeira(mat, load, geo, d_mm=d_cum_mm)
    L3 = dimensionar_sapata(
        load, geo, F_chu_kN=F_chu_kN, eta_alvo=eta_alvo,
    )

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
    k_mod:    float | None = None,
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



# ── LIGAÇÕES DO PILAR CENTRAL ─────────────────────────────────────────────────

def dimensionar_ligacao_base_central(
    mat:       GlulamMaterial,
    load:      Carregamentos,
    geo:       GeometriaViga,
    b_pilar_c: float = 0.26,
    d_mm:      float = 20.0,
    k_mod:     float | None = None,
    gamma_M:   float = GAMMA_M_LIGACAO,
    eta_alvo:  float = 0.85,
) -> dict:
    """
    Ligação viga-pilar central — duas chapas independentes.

    Cada chapa recebe a força de uma viga (mesmos N_d, V_d da lateral).
    Espessura de madeira por lado = b_pilar_c/2 (chapa embutida no pilar).
    """
    if k_mod is None:
        k_mod = mat.k_mod
    if eta_alvo <= 0 or eta_alvo > 1.0:
        raise ValueError("eta_alvo deve estar em (0, 1]")

    # Base com eta_alvo; redimensiona malha se t do pilar ≠ b/2 da viga
    res = dimensionar_ligacao_base(
        mat=mat, load=load, geo=geo,
        d_mm=d_mm, k_mod=k_mod, gamma_M=gamma_M, eta_alvo=eta_alvo,
    )
    rho_k = mat.rho_k
    t_mm  = b_pilar_c / 2 * 1000
    joh   = johansen_chapa_embutida(rho_k, d_mm, t_mm, F_U_K_PINO)
    F_v_Rd = k_mod * joh["F_v_Rk_N"] * 2 / gamma_M
    F_res_N = res["F_res_kN"] * 1e3
    R_req_N = F_res_N / eta_alvo
    theta_deg = res.get("theta_deg", 0.0)
    dist = distancias_minimas(d_mm, theta_deg=theta_deg)
    a1_mm = dist["a1_mm"]
    a2_mm = dist["a2_mm"]
    a4_mm = dist["a4t_mm"]
    h0_mm = geo.h0 * 1000
    n_vert_max = max(1, int((h0_mm - 2 * a4_mm) / a2_mm) + 1) if a2_mm > 0 else 1

    best = None
    for n_vert in range(1, n_vert_max + 1):
        for n_horiz in range(1, 21):
            nef_row = n_ef(n_horiz, a1_mm, d_mm)
            R_N = n_vert * nef_row * F_v_Rd
            if R_N < R_req_N:
                continue
            geo_ok = verificar_geometria_grupo(
                n_horiz=n_horiz, n_vert=n_vert, d_mm=d_mm,
                h0_mm=h0_mm, theta_deg=theta_deg,
            )
            if not geo_ok["ok_geometria"]:
                continue
            n_tot = n_horiz * n_vert
            if best is None or n_tot < best["n_tot"]:
                best = dict(
                    n_horiz=n_horiz, n_vert=n_vert, n_tot=n_tot,
                    nef=n_vert * nef_row, nef_row=nef_row,
                    R_N=R_N, eta=F_res_N / R_N, geo=geo_ok,
                )

    res["ligacao"]   = "L1c — Viga-pilar central (por chapa)"
    res["t_lado_mm"] = round(t_mm, 1)
    res["F_v_Rd_kN"] = round(F_v_Rd / 1e3, 3)
    res["eta_alvo"]  = eta_alvo
    res["nota"]      = "2 chapas independentes por pilar central"
    if best is not None:
        res["n_pinos"]      = best["n_tot"]
        res["n_linha"]      = best["n_horiz"]
        res["n_linhas"]     = best["n_vert"]
        res["n_ef"]         = round(best["nef"], 3)
        res["n_ef_row"]     = round(best["nef_row"], 3)
        res["R_total_kN"]   = round(best["R_N"] / 1e3, 3)
        res["eta"]          = round(best["eta"], 4)
        res["h_ocupado_mm"] = best["geo"]["h_ocupado_mm"]
        res["L_ocupado_mm"] = best["geo"]["L_ocupado_mm"]
        res["ok_geometria"] = best["geo"]["ok_geometria"]
        res["ok_alvo"]      = best["eta"] <= eta_alvo + 1e-9
        res["ok"]           = (
            best["eta"] <= 1.0
            and best["eta"] <= eta_alvo + 1e-9
            and best["geo"]["ok_geometria"]
        )
    return res


def dimensionar_sapata_central(
    load:     Carregamentos,
    geo:      GeometriaViga,
    d_chu_mm: float = 20.0,
) -> dict:
    """
    Sapata do pilar central — sem empuxo horizontal.

    N_d = 2 × R_v = 195,68 kN (dois pórticos)
    H_d ≈ 0 (empuxos horizontais se cancelam)
    Chumbadores: mínimo construtivo = 4 M20

    A chapa de base é dimensionada para N_d / f_c,concreto.
    """
    import math
    N_d = 2 * load.V_max_ELU()   # kN
    H_d = 0.0                     # kN — cancelamento

    f_c_conc   = 1.5   # MPa — C25/30 sob carga localizada
    A_chapa_m2 = N_d * 1e3 / (f_c_conc * 1e6)
    lado_cm    = math.sqrt(A_chapa_m2) * 100

    n_chu_min  = 4   # construtivo — sem esforço horizontal
    eta_H      = 0.0   # H_d = 0

    return {
        "ligacao":        "L3c — Sapata central (sem empuxo)",
        "N_d_kN":         round(N_d,         3),
        "H_d_kN":         0.0,
        "d_chu_mm":       d_chu_mm,
        "n_chumbadores":  n_chu_min,
        "nota_chu":       "Mínimo construtivo — H_d ≈ 0",
        "A_chapa_cm2":    round(A_chapa_m2 * 1e4, 1),
        "lado_chapa_cm":  round(lado_cm,    1),
        "eta_H":          0.0,
        "eta":            0.0,
        "ok":             True,
        "norma":          "EN 1993-1-8 + EN 1992-4",
        "nota":           "Empuxos horizontais cancelam no pilar central",
    }


def dimensionar_ligacoes_central(
    mat:   GlulamMaterial,
    load:  Carregamentos,
    geo:   GeometriaViga,
    b_pilar_c: float = 0.26,
    d_base_mm: float = 20.0,
    d_cum_mm:  float = 30.0,
    eta_alvo:  float = 0.85,
) -> dict:
    """
    Dimensiona as ligações do pilar central compartilhado.

    L1c: viga-pilar — 2 chapas independentes, mesma força que lateral
    L2c: cumeeira — idêntica à lateral (força igual, geometria igual)
    L3c: sapata — sem empuxo horizontal, chumbadores construtivos
    """
    L1c = dimensionar_ligacao_base_central(
        mat, load, geo, b_pilar_c, d_base_mm, eta_alvo=eta_alvo,
    )
    # Cumeeira central: mesma análise EC5 que a lateral (geometria e esforços iguais)
    L2c = dimensionar_ligacao_cumeeira(mat, load, geo, d_mm=d_cum_mm)
    L2c = {**L2c, "ligacao": "L2c — Cumeeira central (rótula)"}
    L3c = dimensionar_sapata_central(load, geo, d_cum_mm)

    eta_gov = max(L1c["eta"], L2c["eta"], L3c["eta"])
    if L1c["eta"] >= L2c["eta"] and L1c["eta"] >= L3c["eta"]:
        lig_gov = "L1c base"
    elif L2c["eta"] >= L3c["eta"]:
        lig_gov = "L2c cumeeira"
    else:
        lig_gov = "L3c sapata"

    return {
        "L1c": L1c,
        "L2c": L2c,
        "L3c": L3c,
        "eta":     round(eta_gov, 4),
        "ok":      L1c["ok"] and L2c["ok"] and L3c["ok"],
        "lig_gov": lig_gov,
    }


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

    print("── Varredura Ligação 1 (base) por diâmetro ──\n")
    df = varrer_ligacao_base(mat, load, geo, d_opcoes=[12,16,20,24])
    print(df.to_string(index=False))

    print("\n── Dimensionamento completo ──\n")
    res = dimensionar_ligacoes(
        mat=mat, load=load, geo=geo,
        d_base_mm=20, d_cum_mm=30, F_chu_kN=80,
    )
    relatorio_ligacoes(res)