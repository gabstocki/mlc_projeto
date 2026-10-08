"""
checks/elu/no_contraventamento.py — Nó de topo dos pilares nas baías contraventadas.

Issue 66 (desdobramento da 42; fecha a pendência da escora central da 64)
-------------------------------------------------------------------------
Nas baías rígidas, a treliça de contraventamento da cobertura (EC5 §9.2.5.3,
issue 41) entrega em cada apoio — beiral e alinhamento central — uma força
LONGITUDINAL (⊥ ao plano do pórtico). Essa força não passa pela ligação L1/L1c
viga–pilar, cuja chapa embutida trabalha no plano do pórtico: o caminho adotado é

    treliça da cobertura (montante de extremidade = terça sobre o apoio)
        ↓  ESCORA longitudinal (terça de beiral / terça sobre a linha central)
    NÓ METÁLICO no topo do pilar (chapa-gousset soldada à chapa de topo / sela),
    onde concorrem a diagonal da cobertura e a diagonal do painel vertical
        ↓
    painel de contraventamento vertical → fundação

A escora é o banzo superior do painel vertical e o montante de extremidade da
treliça da cobertura. Verifica-se aqui:

  1. a escora como peça flexo-axial (EC5 §6.3.2 / §6.2.3), reaproveitando a
     verificação da corda de beiral (flexão local da cobertura + N axial);
  2. a ligação axial da escora ao nó: cavilhas em chapa embutida, força
     PARALELA às fibras (EC5 §8.2.3, §8.5.1.1 n_ef, §8.6) e ruptura de bloco
     (Anexo A).

Força de projeto na escora: o cortante do painel vertical que ela alimenta
(V_painel); na linha central, a escora entre as baías 1–2 recebe a reação das
duas águas e alimenta os dois painéis contíguos: N = n_paineis_por_extremidade ·
V_painel (envoltória conservadora).

O vento longitudinal (θ=0°) que gera esta força NÃO é concomitante com o vento
transversal (θ=90°) que gera a força de corda do diafragma — são direções
diferentes; adota-se o maior dos dois na escora de beiral.
"""

from __future__ import annotations

import math

from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.connections.connections import (
    F_U_K_PINO, GAMMA_M_LIGACAO, distancias_minimas, johansen_chapa_embutida,
    n_ef, ruptura_de_bloco,
)

ETA_ALVO_FRAGIL = 0.75


def dimensionar_ligacao_axial_escora(
    F_Ed_kN:   float,
    mat:       GlulamMaterial,
    b_m:       float,
    h_m:       float,
    d_mm:      float = 20.0,
    gamma_M:   float = GAMMA_M_LIGACAO,
    eta_alvo:  float = ETA_ALVO_FRAGIL,
    n_horiz_max: int = 8,
    rotulo:    str = "escora",
) -> dict:
    """
    Ligação da escora (MLC) ao nó metálico: cavilhas em chapa embutida central,
    força axial PARALELA às fibras (θ = 0°), corte duplo.

        F_v,Rd,pino = 2 · k_mod · min{(f),(g),(h)} / γ_M     (EC5 §8.2.3)
        R_d = n_vert · n_ef(n_horiz) · F_v,Rd,pino           (EC5 §8.5.1.1)

    Menor malha com R_d ≥ F_Ed/η_alvo (modo frágil, alvo 0,75), mais a ruptura
    de bloco (Anexo A).
    """
    t_chapa = float(d_mm)                       # chapa rígida: t ≥ d (issue 23)
    t1_mm = (b_m * 1000.0 - t_chapa) / 2.0
    joh = johansen_chapa_embutida(mat.rho_k, d_mm, t1_mm, F_U_K_PINO, theta_deg=0.0)
    F_v_Rd = 2.0 * mat.k_mod * joh["F_v_Rk_N"] / gamma_M / 1e3      # kN/pino
    dist = distancias_minimas(d_mm, theta_deg=0.0)
    a1, a2, a3t, a4c = dist["a1_mm"], dist["a2_mm"], dist["a3t_mm"], dist["a4c_mm"]
    n_vert_max = max(1, int((h_m * 1000.0 - 2.0 * a4c) / a2) + 1)

    best = None
    for n_vert in range(1, n_vert_max + 1):
        for n_horiz in range(1, n_horiz_max + 1):
            R = n_vert * n_ef(n_horiz, a1, d_mm) * F_v_Rd
            if R * eta_alvo < F_Ed_kN:
                continue
            n = n_vert * n_horiz
            if best is None or n < best["n"] or (n == best["n"] and R > best["R"]):
                best = dict(n=n, n_vert=n_vert, n_horiz=n_horiz, R=R)
    if best is None:                              # não cabe: reporta a maior malha
        n_vert, n_horiz = n_vert_max, n_horiz_max
        best = dict(n=n_vert * n_horiz, n_vert=n_vert, n_horiz=n_horiz,
                    R=n_vert * n_ef(n_horiz, a1, d_mm) * F_v_Rd)
    eta_pinos = F_Ed_kN / best["R"] if best["R"] > 0 else 999.0

    bloco = ruptura_de_bloco(
        n_par=best["n_horiz"], n_perp=best["n_vert"],
        a1_m=a1 / 1000.0, a2_m=a2 / 1000.0, a3t_m=a3t / 1000.0, t1_m=b_m,
        f_t0_k=mat.f_t0_k, f_v_k=mat.f_v_k, k_mod=mat.k_mod, gamma_M=gamma_M,
        F_par_kN=F_Ed_kN,
    )
    eta = max(eta_pinos, bloco["eta"])
    L_ocup = a3t + (best["n_horiz"] - 1) * a1
    return {
        "rotulo":       rotulo,
        "F_Ed_kN":      round(F_Ed_kN, 2),
        "d_mm":         d_mm,
        "t_chapa_mm":   t_chapa,
        "t1_mm":        round(t1_mm, 1),
        "F_v_Rd_pino_kN": round(F_v_Rd, 2),
        "n_horiz":      best["n_horiz"],
        "n_vert":       best["n_vert"],
        "n_pinos":      best["n"],
        "n_ef":         round(best["n_vert"] * n_ef(best["n_horiz"], a1, d_mm), 2),
        "R_d_kN":       round(best["R"], 2),
        "a1_mm": round(a1, 1), "a2_mm": round(a2, 1),
        "a3t_mm": round(a3t, 1), "a4c_mm": round(a4c, 1),
        "L_ocupado_mm": round(L_ocup, 0),
        "eta_pinos":    round(eta_pinos, 4),
        "eta_bloco":    bloco["eta"],
        "eta":          round(eta, 4),
        "ok":           eta <= eta_alvo + 1e-9,
        "eta_limite":   eta_alvo,
        "norma":        "EC5 §8.2.3 + §8.5.1.1 + §8.6 + Anexo A (θ = 0°)",
    }


def verificar_no_contraventamento(
    *,
    mat_curta:         GlulamMaterial,
    V_painel_fachada_kN: float,
    V_painel_central_kN: float,
    n_paineis_central_por_extremidade: int,
    N_corda_diafragma_kN: float,
    verificar_escora,
    d_mm: float = 20.0,
    b_terca_m: float,
    h_terca_m: float,
) -> dict:
    """
    Escoras e ligações do nó de topo nas baías contraventadas (issue 66).

    `verificar_escora(N_kN, s_trib_m)` verifica a terça como peça flexo-axial
    (injetado do main para reaproveitar `verificar_corda_beiral` com as cargas
    do projeto).
    """
    N_beiral = max(float(V_painel_fachada_kN), float(N_corda_diafragma_kN))
    N_central = float(V_painel_central_kN) * max(1, int(n_paineis_central_por_extremidade))

    escora_beiral = verificar_escora(N_beiral, "beiral")
    escora_central = verificar_escora(N_central, "central")
    lig_beiral = dimensionar_ligacao_axial_escora(
        N_beiral, mat_curta, b_terca_m, h_terca_m, d_mm=d_mm, rotulo="escora de beiral")
    lig_central = dimensionar_ligacao_axial_escora(
        N_central, mat_curta, b_terca_m, h_terca_m, d_mm=d_mm, rotulo="escora central")

    etas = {
        "escora_beiral": escora_beiral["eta"],
        "escora_central": escora_central["eta"],
        "lig_escora_beiral": lig_beiral["eta"],
        "lig_escora_central": lig_central["eta"],
    }
    gov = max(etas, key=etas.get)
    return {
        "sistema": "Nó de topo das baías contraventadas — escoras e ligações",
        "caminho": ("treliça da cobertura → escora (terça sobre o apoio) → nó "
                    "metálico no topo do pilar → painel vertical → fundação; "
                    "a L1/L1c não recebe a força longitudinal"),
        "N_escora_beiral_kN": round(N_beiral, 2),
        "N_escora_central_kN": round(N_central, 2),
        "escora_beiral": escora_beiral,
        "escora_central": escora_central,
        "ligacao_escora_beiral": lig_beiral,
        "ligacao_escora_central": lig_central,
        "etas": etas,
        "eta_gov_key": gov,
        "eta": round(etas[gov], 4),
        "ok": all(x["ok"] for x in (escora_beiral, escora_central,
                                     lig_beiral, lig_central)),
        "norma": "EC5 §6.2.3/§6.3.2 + §8.2.3/§8.5.1.1/§8.6 + Anexo A",
    }
