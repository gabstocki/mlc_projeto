"""
connections/ligacao_topo_pilar.py — Chapa de topo e sela ao pilar (issue 69).

O arrancamento que chega à chapa de topo (L1, L1f) ou à sela (L1c) precisa de
um caminho até o pilar de madeira, e daí à base. A ligação espelha a do pé do
pilar (issue 52):

    chapa embutida da viga → chapa de topo / sela → chapa vertical embutida em
    rasgo no topo do pilar → cavilhas Ø20 em corte duplo, // às fibras

  · A chapa vertical do pilar fica no MESMO PLANO da chapa embutida da viga: o
    arrancamento atravessa a chapa de topo na espessura, sem flexioná-la; exige-se
    aço com propriedades na direção da espessura (EN 1993-1-10, classe Z).
  · Retração impedida (issue 81): malha limitada a 3 fileiras ⊥ às fibras.
  · Esforço de projeto: a mesma tração da base correspondente (o que chega ao
    pé passa antes pelo topo); compressão // fibras no topo do pilar sob a chapa;
    cortante do próprio pilar (vento, choque) ⊥ às fibras nas cavilhas.
  · Nas baías contraventadas, as forças horizontais do nó seguem em aço: da chapa
    de topo e do nó às diagonais. A escora, apoiada na viga, move-se na vertical
    em relação ao pilar (levantamento da issue 72 e umidade da viga); liga-se ao
    nó por parafusos em furos ovalizados VERTICAIS — interface deslizante, com a
    força horizontal ⊥ ao furo (EN 1993-1-8 Tab. 3.4: F_b,Rd × 0,6).
"""

from __future__ import annotations

import math

from mlc_projeto.checks.elu.no_contraventamento import dimensionar_ligacao_axial_escora
from mlc_projeto.connections.chapas_aco import ACO_CHAPA, GAMMA_M2, d0_furo
from mlc_projeto.connections.connections import (
    F_U_K_PINO, GAMMA_M_LIGACAO, distancias_minimas, johansen_chapa_embutida,
)
from mlc_projeto.connections.oblongo_L1 import (
    ALPHA_PERP, TOLERANCIA_MM, U_MONTAGEM, U_SERVICO,
)
from mlc_projeto.connections.pilarete import _soldas
from mlc_projeto.connections.retracao import n_perp_max
from mlc_projeto.core.materials import GlulamMaterial

D_CAVILHA_MM = 20.0
ETA_ALVO_FRAGIL = 0.75


def verificar_ligacao_topo(*, rotulo: str, N_t_kN: float, N_c_kN: float, V_kN: float,
                           b_pilar_m: float, h_pilar_m: float, mat: GlulamMaterial,
                           d_mm: float = D_CAVILHA_MM, n_min: int = 2,
                           furo_central_mm: float | None = None) -> dict:
    """Cavilhas no topo do pilar, solda à chapa de topo e compressão no topo."""
    from mlc_projeto.connections.retracao import n_perp_max_borda_carregada
    a2 = distancias_minimas(d_mm, 0.0)["a2_mm"]
    a4t = distancias_minimas(d_mm, 90.0)["a4t_mm"]           # cortante ⊥ (issue 76)
    from mlc_projeto.connections.retracao import D_perp_max_mm
    # Com tirante interno, N_t = 0: as cavilhas só posicionam e levam o cortante; a malha
    # mínima é de duas cavilhas (n_min) e cresce, se preciso, até atender ao cortante.
    F_dim = max(float(N_t_kN), 1.0)
    for _ in range(40):
        lig = dimensionar_ligacao_axial_escora(
            F_Ed_kN=F_dim, mat=mat, b_m=b_pilar_m, h_m=h_pilar_m, d_mm=d_mm,
            rotulo=f"{rotulo} — topo do pilar",
            D_perp_max_mm=D_perp_max_mm(d_mm), a4_min_mm=a4t, n_horiz_max=16,
            **(dict(n_vert_min=2, a2_min_mm=furo_central_mm + d_mm + 10.0)
               if furo_central_mm else {}),
        )
        # cortante do próprio pilar ⊥ às fibras nas mesmas cavilhas
        joh90 = johansen_chapa_embutida(mat.rho_k, d_mm, lig["t1_mm"], F_U_K_PINO,
                                        theta_deg=90.0)
        R_perp = lig["n_pinos"] * 2.0 * mat.k_mod * joh90["F_v_Rk_N"] / GAMMA_M_LIGACAO / 1e3
        eta_V = V_kN / R_perp if R_perp > 0 else 999.0
        if eta_V <= ETA_ALVO_FRAGIL and lig["n_pinos"] >= n_min:
            break
        F_dim *= 1.25
    if F_dim > N_t_kN:
        lig = dict(lig, F_Ed_kN=round(float(N_t_kN), 2),
                   eta=round(max(N_t_kN / lig["R_d_kN"], lig["eta_bloco"] * N_t_kN / F_dim), 4))
    # solda de filete dupla chapa vertical × chapa de topo, ao longo da largura
    l_w = h_pilar_m * 1e3 - 60.0
    a_w, eta_w = _soldas(N_t_kN * 1e3 / (2.0 * l_w), V_kN * 1e3 / (2.0 * l_w), "S275")
    # compressão // fibras no topo do pilar, descontado o rasgo
    t_r = float(lig["t_chapa_mm"]) + 4.0
    A_liq = b_pilar_m * 1e3 * h_pilar_m * 1e3 - t_r * l_w
    sig_c = N_c_kN * 1e3 / A_liq
    eta_c = sig_c / (mat.com_duracao("media").f_c0_d / 1e6)
    partes = {"cavilhas_tracao": lig["eta"], "cavilhas_cortante": eta_V,
              "solda": eta_w, "compressao_topo": eta_c}
    gov = max(partes, key=partes.get)
    return {
        "rotulo": rotulo, "N_t_kN": round(N_t_kN, 1), "N_c_kN": round(N_c_kN, 1),
        "V_kN": round(V_kN, 2), "cavilhas": lig,
        "R_perp_kN": round(R_perp, 1), "a_solda_mm": a_w, "l_solda_mm": l_w,
        "t_rasgo_mm": t_r, "sigma_c0_MPa": round(sig_c, 3),
        "partes": {k: round(v, 4) for k, v in partes.items()},
        "governa": gov, "eta": round(partes[gov], 4),
        "ok": lig["ok"] and eta_V <= ETA_ALVO_FRAGIL and eta_w <= 1.0 and eta_c <= 1.0,
        "norma": "EC5 §8.2.3/§8.5.1.1/An. A + §6.1.4 + EN 1993-1-8 §4.5.3.3",
    }


def movimento_vertical_escora(*, h0_mm: float, levantamento_mm: float,
                              fluencia_mm: float) -> dict:
    """Movimento vertical do topo da viga (escora) em relação ao topo do pilar."""
    cima = (levantamento_mm + ALPHA_PERP * (U_SERVICO[1] - U_MONTAGEM[0]) * h0_mm
            + TOLERANCIA_MM)
    baixo = ALPHA_PERP * (U_MONTAGEM[1] - U_SERVICO[0]) * h0_mm + fluencia_mm + TOLERANCIA_MM
    return {"cima_mm": round(cima, 1), "baixo_mm": round(baixo, 1)}


def verificar_interface_deslizante(*, rotulo: str, H_kN: float, cima_mm: float,
                                   baixo_mm: float, d_mm: float = 24.0,
                                   f_ub_MPa: float = 800.0, t_chapa_mm: float = 20.0,
                                   aco: str = "S275", n_min: int = 2,
                                   eta_alvo: float = ETA_ALVO_FRAGIL) -> dict:
    """
    Parafusos 8.8 em corte duplo, em furos ovalizados verticais longos no nó:
    corte EN 1993-1-8 Tab. 3.4 (α_v = 0,6 na rosca) e pressão de contato na
    chapa da escora reduzida a 0,6 por furo ovalizado ⊥ à força.
    """
    A_s = {20: 245.0, 24: 353.0, 27: 459.0, 30: 561.0}[int(d_mm)]
    F_v = 0.6 * f_ub_MPa * A_s / GAMMA_M2 / 1e3                  # kN por plano
    f_u = ACO_CHAPA[aco]["f_u"]
    F_b = 0.6 * 2.5 * 1.0 * f_u * d_mm * t_chapa_mm / GAMMA_M2 / 1e3
    R1 = min(2.0 * F_v, F_b)
    n = max(n_min, math.ceil(H_kN / (eta_alvo * R1)))
    d0 = d0_furo(d_mm)
    curso = 5.0 * math.ceil((cima_mm + baixo_mm) / 5.0)
    return {
        "rotulo": rotulo, "H_kN": round(H_kN, 1), "n_parafusos": n, "d_mm": d_mm,
        "F_v_Rd_kN": round(2.0 * F_v, 1), "F_b_Rd_kN": round(F_b, 1),
        "cima_mm": cima_mm, "baixo_mm": baixo_mm,
        "comprimento_furo_mm": d0 + curso, "largura_furo_mm": d0,
        "eta": round(H_kN / (n * R1), 4), "ok": H_kN <= n * R1,
        "norma": "EN 1993-1-8 Tab. 3.4 (furo ovalizado longo ⊥ à força: 0,6·F_b,Rd)",
    }
