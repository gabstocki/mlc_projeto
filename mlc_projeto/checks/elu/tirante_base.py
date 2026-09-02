"""
checks/elu/tirante_base.py — Tirante ao nível do piso (fecho do empuxo).

Contexto
--------
No pórtico biarticulado (arco abatido / Castigliano), o empuxo horizontal H
nas bases é da mesma ordem de N na viga. Sem tirante, H vai para a sapata
(chumbadores L3). Com tirante rígido ligando as bases de cada vão:

    T_tirante ≈ H_arco     (tração de cálculo no tirante)
    H_sapata  ≈ 0          (empuxo residual desprezável se k_t >> k_fund)

Solução usual em coberturas MLC / pórticos abatidos para aliviar fundações.

Norma
-----
  EN 1993-1-1 §6.2.3 — resistência à tração de barra
  EN 1993-1-1 §6.2.4 — secção bruta (barra maciça sem furo governante aqui;
                       A_net = A se extremo com engaste/solda ou A_net documentado)

Critério de projeto
-------------------
  η_alvo (uso público, default 0,75): N_t,Rd ≥ T_d / η_alvo
  Diâmetro comercial escolhido automaticamente se d_mm=None.
"""

from __future__ import annotations

import math

# Aços e fatores — alinhados a contraventamento
E_ACO_MPA = 210_000.0
GAMMA_M0  = 1.00

ACO = {
    "S235": {"f_y": 235.0, "f_u": 360.0},
    "S355": {"f_y": 355.0, "f_u": 510.0},
    # Barra redonda de média resistência, f_y=315 MPa — recomendada pelo
    # orientador como a mais adequada ao tamanho do tirante (issue 24).
    # f_u de referência (~aço-carbono SAE 1020/1045 conforme a bitola);
    # confirmar produto/norma no projeto de execução.
    "MR315": {"f_y": 315.0, "f_u": 490.0},
}

# Diâmetros comerciais de barra redonda (mm) — sequência de dimensionamento
D_COMERCIAL_MM = (
    20, 24, 27, 30, 33, 36, 39, 42, 45, 48, 52, 56, 60, 64, 68, 72, 76, 80,
    85, 90, 95, 100, 110, 120,
)


def _n_t_rd_kN(d_mm: float, aco: str) -> float:
    if aco not in ACO:
        raise ValueError(f"Aço '{aco}' não reconhecido. Use {list(ACO)}")
    f_y = ACO[aco]["f_y"]
    A_mm2 = math.pi * d_mm**2 / 4.0
    return A_mm2 * f_y / GAMMA_M0 / 1e3  # kN


def escolher_diametro(
    T_d_kN: float,
    aco: str = "S355",
    eta_alvo: float = 0.75,
    d_lista: tuple[float, ...] = D_COMERCIAL_MM,
) -> float:
    """Menor d comercial com η = T / N_t,Rd ≤ eta_alvo."""
    if T_d_kN < 0:
        raise ValueError("T_d_kN deve ser ≥ 0")
    if eta_alvo <= 0 or eta_alvo > 1.0:
        raise ValueError("eta_alvo deve estar em (0, 1]")
    T_req = T_d_kN / eta_alvo if eta_alvo > 0 else T_d_kN
    for d in d_lista:
        if _n_t_rd_kN(d, aco) >= T_req - 1e-9:
            return float(d)
    # fallback: diâmetro teórico arredondado
    f_y = ACO[aco]["f_y"]
    A_mm2 = T_req * 1e3 * GAMMA_M0 / f_y
    d_teo = math.sqrt(4.0 * A_mm2 / math.pi)
    return float(math.ceil(d_teo / 2.0) * 2.0)  # par, mm


def verificar_tirante_base(
    T_d_kN: float,
    L_m: float,
    aco: str = "S355",
    d_mm: float | None = None,
    eta_alvo: float = 0.75,
    n_vaos_por_linha: int = 2,
    n_linhas: int = 9,
) -> dict:
    """
    Verifica o tirante de base (barra redonda à tração).

    Args:
        T_d_kN : tração de cálculo = H_arco (empuxo Castigliano ELU) [kN]
        L_m    : comprimento do tirante = vão do pórtico [m]
        aco    : S235 ou S355
        d_mm   : diâmetro (None → escolha automática com η ≤ eta_alvo)
        eta_alvo : margem de projeto (0,75 uso público)
        n_vaos_por_linha, n_linhas : quantitativo do galpão (2 vãos × n pórticos)

    Returns:
        dict com T, d, η, alongamento elástico, ok, quantitativo
    """
    if L_m <= 0:
        raise ValueError("L_m deve ser positivo")
    if T_d_kN < 0:
        raise ValueError("T_d_kN deve ser ≥ 0")

    d_auto = d_mm is None
    if d_auto:
        d_mm = escolher_diametro(T_d_kN, aco=aco, eta_alvo=eta_alvo)
    d_mm = float(d_mm)

    f_y = ACO[aco]["f_y"]
    A_mm2 = math.pi * d_mm**2 / 4.0
    N_t_Rd = _n_t_rd_kN(d_mm, aco)
    eta = T_d_kN / N_t_Rd if N_t_Rd > 0 else 999.0
    ok_norma = eta <= 1.0 + 1e-9
    ok_alvo  = eta <= eta_alvo + 1e-9

    # Alongamento elástico instantâneo δ = T L / (E A)
    A_m2 = A_mm2 * 1e-6
    delta_mm = 0.0
    if A_m2 > 0 and E_ACO_MPA > 0:
        # T em N, L em mm, E em MPa=N/mm², A em mm² → δ em mm
        delta_mm = (T_d_kN * 1e3) * (L_m * 1e3) / (E_ACO_MPA * A_mm2)

    n_barras = max(0, int(n_vaos_por_linha) * int(n_linhas))
    L_total_m = n_barras * L_m
    peso_kg = (A_mm2 * 1e-6) * L_total_m * 7850.0  # aço ~7850 kg/m³

    return {
        "ativo":           True,
        "sistema":         "Tirante ao nível do piso (fecho do empuxo)",
        "T_d_kN":          round(T_d_kN, 3),
        "H_arco_kN":       round(T_d_kN, 3),
        "H_sapata_kN":     0.0,
        "L_m":             round(L_m, 3),
        "aco":             aco,
        "f_y_MPa":         f_y,
        "d_mm":            d_mm,
        "d_auto":          d_auto,
        "A_mm2":           round(A_mm2, 1),
        "N_t_Rd_kN":       round(N_t_Rd, 2),
        "eta":             round(eta, 4),
        "eta_alvo":        eta_alvo,
        "ok_norma":        ok_norma,
        "ok_alvo":         ok_alvo,
        "ok":              ok_norma and ok_alvo,
        "delta_el_mm":     round(delta_mm, 2),
        "delta_sobre_L":   round(delta_mm / (L_m * 1e3), 6) if L_m > 0 else 0.0,
        "n_barras":        n_barras,
        "L_total_m":       round(L_total_m, 1),
        "peso_total_kg":   round(peso_kg, 1),
        "n_vaos_por_linha": n_vaos_por_linha,
        "n_linhas":        n_linhas,
        "norma":           "EN 1993-1-1 §6.2.3 | η_alvo projeto",
        # Hipótese de modelagem (issue 24) — registrar no memorial:
        "hipotese_H": (
            "H (empuxo) obtido por Castigliano assumindo APOIO HORIZONTAL "
            "INDESLOCÁVEL nas bases (arco 1× hiperestático); a flexibilidade "
            "axial do tirante (δ=T·L/EA) NÃO foi realimentada na análise. "
            "É conservador para o tirante (H_rígido ≥ H_flexível). O impacto "
            "da flexibilidade é estimado à parte (impacto_flexibilidade_tirante)."
        ),
        "nota": (
            f"T_d = H_arco = {T_d_kN:.1f} kN absorvido pelo tirante; "
            f"H_sapata ≈ 0. Barra ∅{d_mm:.0f} mm {aco} (f_y={f_y:.0f} MPa), "
            f"N_t,Rd = {N_t_Rd:.1f} kN, η = {eta:.3f} "
            f"(alvo {eta_alvo:.2f}). "
            f"δ_el ≈ {delta_mm:.1f} mm em L = {L_m:.2f} m. "
            "Ancoragem nas bases e proteção a impacto (estacionamento) "
            "a detalhar em projeto de execução."
        ),
    }


def impacto_flexibilidade_tirante(
    geo,
    E_glulam_MPa: float,
    H_rigid_kN:   float,
    d_mm:         float,
    aco:          str = "MR315",
    n_pts:        int = 2001,
) -> dict:
    """
    Avalia o impacto da FLEXIBILIDADE AXIAL do tirante sobre o empuxo H (issue 24).

    Diagnóstico por rigidezes horizontais (kN/mm):
        k_arco = 1/f_p,  f_p = ∫ y_c²/(E·I) dx   (mesmo integrando ∫y_c²/I do H)
        k_tir  = 1/f_t,  f_t = L/(E_s·A)         (rigidez axial do tirante)

    LIMITE DE TRIAGEM (modelo de 2 molas em SÉRIE, tirante como único apoio):
        H_flex_2molas = H_rígido · k_tir/(k_tir + k_arco)

    IMPORTANTE — este limite IGNORA a restrição horizontal PARALELA das bases
    (ancoragem/chumbadores nas sapatas + contraventamento vertical/transversal).
    Na estrutura real essas rigidezes somam-se em paralelo ao tirante, tornando
    o apoio muito mais rígido → H permanece próximo de H_rígido. Portanto:
      · H_rígido é CONSERVADOR para o dimensionamento do TIRANTE (T = H máx);
      · o modelo de 2 molas é apenas um indicador de sensibilidade, NÃO o H real.
    """
    import numpy as np

    L = float(geo.L)
    h0 = float(geo.h0)
    b = float(geo.b)
    alpha_rad = float(geo.alpha_rad)

    x = np.linspace(0.0, L, n_pts)
    x_sim = np.where(x <= L / 2.0, x, L - x)
    tan_a = math.tan(alpha_rad)
    y_c = x_sim * tan_a / 2.0
    h_x = h0 + x_sim * tan_a
    I_x = np.maximum(b * h_x ** 3 / 12.0, 1e-18)

    den = float(np.trapezoid(y_c ** 2 / I_x, x))    # ∫ y_c²/I dx  [1/m]
    E_glulam_Pa = E_glulam_MPa * 1e6
    f_p = den / E_glulam_Pa                          # m/N (compliance do arco)

    A_m2 = math.pi * (d_mm * 1e-3) ** 2 / 4.0
    f_t = L / (E_ACO_MPA * 1e6 * A_m2)               # m/N (compliance do tirante)

    k_arco_kNmm = (1.0 / f_p) / 1e6 if f_p > 0 else 0.0   # kN/mm
    k_tir_kNmm = (1.0 / f_t) / 1e6 if f_t > 0 else 0.0    # kN/mm

    # Limite de triagem — tirante como ÚNICO apoio (série)
    r = f_t / f_p if f_p > 0 else 0.0
    H_flex_2molas = H_rigid_kN / (1.0 + r)
    reducao_2molas_pct = r / (1.0 + r) * 100.0

    # δ do tirante sob H_rígido e afastamento livre do arco
    delta_tir_mm = H_rigid_kN * 1e3 * f_t * 1e3      # T·L/EA
    delta_arco_livre_mm = H_rigid_kN * 1e3 * f_p * 1e3

    return {
        "H_rigid_kN":          round(H_rigid_kN, 3),
        "k_arco_kNmm":         round(k_arco_kNmm, 1),
        "k_tirante_kNmm":      round(k_tir_kNmm, 1),
        "razao_ft_fp":         round(r, 4),
        "H_flex_2molas_kN":    round(H_flex_2molas, 1),
        "reducao_2molas_pct":  round(reducao_2molas_pct, 2),
        "delta_tirante_mm":    round(delta_tir_mm, 2),
        "delta_arco_livre_mm": round(delta_arco_livre_mm, 3),
        # Restrição paralela (fundação + contraventamento) NÃO está no modelo de
        # 2 molas → H real fica próximo do rígido; não é necessário acoplar para
        # o TIRANTE (H_rígido é o máximo, conservador).
        "acoplar_para_tirante": False,
        "conclusao": (
            f"Rigidez horizontal: arco {k_arco_kNmm:.0f} kN/mm vs tirante "
            f"{k_tir_kNmm:.0f} kN/mm. O limite de 2 molas (tirante como único "
            f"apoio) daria H≈{H_flex_2molas:.0f} kN (−{reducao_2molas_pct:.0f}%), "
            "MAS ignora a restrição paralela de ancoragem+contraventamento das "
            "bases → na estrutura real H fica próximo do rígido. H_rígido é "
            "CONSERVADOR para o tirante (T=H máx); acoplamento não é necessário "
            "para o dimensionamento do tirante."
        ),
        "norma": "Compatibilidade elástica (diagnóstico de rigidezes)",
    }


def relatorio_tirante(res: dict) -> None:
    """Impressão resumida no console."""
    if not res or not res.get("ativo"):
        print("  · Tirante de base: inativo (empuxo → sapata)")
        return
    ok = "✓" if res.get("ok") else "✗"
    print(
        f"  {ok} Tirante base ∅{res['d_mm']:.0f} mm {res['aco']}  "
        f"η = {res['eta']:.4f}"
    )
    print(
        f"  · T_d = H_arco = {res['T_d_kN']:.1f} kN | "
        f"H_sapata ≈ {res['H_sapata_kN']:.1f} kN | "
        f"N_t,Rd = {res['N_t_Rd_kN']:.1f} kN | "
        f"δ_el = {res['delta_el_mm']:.1f} mm | "
        f"n = {res['n_barras']} barras | "
        f"peso ≈ {res['peso_total_kg']:.0f} kg"
    )
