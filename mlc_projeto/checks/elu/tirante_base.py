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
        "nota": (
            f"T_d = H_arco = {T_d_kN:.1f} kN absorvido pelo tirante; "
            f"H_sapata ≈ 0. Barra ∅{d_mm:.0f} mm {aco}, "
            f"N_t,Rd = {N_t_Rd:.1f} kN, η = {eta:.3f} "
            f"(alvo {eta_alvo:.2f}). "
            f"δ_el ≈ {delta_mm:.1f} mm em L = {L_m:.2f} m. "
            "Ancoragem nas bases e proteção a impacto (estacionamento) "
            "a detalhar em projeto de execução."
        ),
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
