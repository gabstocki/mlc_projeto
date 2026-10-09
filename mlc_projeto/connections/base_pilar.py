"""
connections/base_pilar.py — Detalhe completo da base do pilar (issue 52).

O desenho cotado das bases expôs três lacunas:

  1. GEOMETRIA. A ancoragem no concreto (EN 1992-4) é calculada com
     espaçamento s = 400 mm entre chumbadores, mas a chapa era 400 × 400 mm
     (lado = pilar + 2·40 mm): os chumbadores caíam na face do pilar. Aqui a
     chapa sai da grelha de chumbadores — lado = (n − 1)·s + 2·e — e confere-se
     a folga entre o chumbador (com arruela) e a face do pilar.

  2. CHAPA SOB TRAÇÃO. A espessura só considerava a compressão no concreto.
     Sob arrancamento, a chapa flete entre a chapa vertical (alma, que vem do
     pilar) e os chumbadores: T-stub da EN 1993-1-8 §6.2.4 (modos 1, 2 e 3).

  3. PÉ DO PILAR. O arrancamento sai da madeira por uma chapa vertical embutida
     em rasgo no pé do pilar, soldada à chapa de base, com cavilhas em corte
     duplo — força paralela às fibras (EC5 §8.2.3, §8.5.1.1, Anexo A). O
     cortante da base (choque de veículo, vento no pilar) cruza as mesmas
     cavilhas perpendicularmente às fibras. O cortante dos painéis de
     contraventamento NÃO passa pela madeira: a diagonal liga-se à chapa de
     base pelo olhal.

Referências: EN 1993-1-8 §6.2.4, §6.2.5, Tab. 3.3 e 3.4; EN 1995-1-1 §8.2.3,
             §8.5.1.1, §8.6, Anexo A.
"""

from __future__ import annotations

import math

from mlc_projeto.checks.elu.no_contraventamento import dimensionar_ligacao_axial_escora
from mlc_projeto.connections.chapas_aco import ACO_CHAPA, GAMMA_M0
from mlc_projeto.connections.connections import (
    F_U_K_PINO, GAMMA_M_LIGACAO, johansen_chapa_embutida,
)
from mlc_projeto.core.materials import GlulamMaterial

#: Espessuras comerciais de chapa (mm) — mesma série de chapas_dim.
COMERCIAIS_MM = (8.0, 9.5, 12.5, 16.0, 19.0, 22.4, 25.0, 31.5, 38.0)
E_BORDA_CHAPA_MM = 60.0   # chumbador → borda da chapa (≥ 1,2·d0, EN 1993-1-8 Tab. 3.3)
A_SOLDA_MM = 6.0          # garganta da solda alma–chapa de base
D_CAVILHA_PE_MM = 20.0    # cavilhas do pé do pilar
ETA_ALVO_CHAPA = 0.90     # margem de projeto da chapa (dúctil), como nas diagonais


def geometria_base(n_x: int, n_y: int, s_mm: float, e_mm: float,
                   b_pilar_mm: float, h_pilar_mm: float, d_chu_mm: float) -> dict:
    """Chapa a partir da grelha de chumbadores; x ⊥ pórtico (b), y no pórtico (h)."""
    xs = [(i - (n_x - 1) / 2.0) * s_mm for i in range(n_x)]
    ys = [(j - (n_y - 1) / 2.0) * s_mm for j in range(n_y)]
    B = (n_x - 1) * s_mm + 2.0 * e_mm
    L = (n_y - 1) * s_mm + 2.0 * e_mm
    # folga entre a arruela (Ø ≈ 1,85·d) e a face do pilar, na direção x
    folga = min(abs(x) for x in xs) - b_pilar_mm / 2.0 - 0.925 * d_chu_mm
    return {
        "B_mm": B, "L_mm": L, "s_mm": s_mm, "e_mm": e_mm,
        "n_x": n_x, "n_y": n_y,
        "chumbadores_mm": [(x, y) for x in xs for y in ys],
        "folga_arruela_pilar_mm": round(folga, 1),
        "folga_ok": folga >= 0.0,
    }


def tstub_base(N_t_kN: float, *, n_y: int, s_mm: float, e_mm: float, L_mm: float,
               t_alma_mm: float, F_t_Rd_chu_kN: float, t_mm: float,
               aco: str = "S275") -> dict:
    """
    T-stub da chapa de base sob tração (EN 1993-1-8 §6.2.4, Tab. 6.2), sem
    contra-chapa. Alma = chapa vertical central; um flange de cada lado, com
    n_y chumbadores em fileira. Σl_eff limitado ao comprimento da chapa.
    """
    f_y = ACO_CHAPA[aco]["f_y"]
    m = s_mm / 2.0 - t_alma_mm / 2.0 - 0.8 * A_SOLDA_MM * math.sqrt(2.0)
    n = min(e_mm, 1.25 * m)
    l_eff = min(L_mm, n_y * 2.0 * math.pi * m, n_y * (4.0 * m + 1.25 * e_mm))
    M_pl = 0.25 * l_eff * t_mm ** 2 * f_y / GAMMA_M0 / 1e6        # kN·m
    sum_Ft = n_y * F_t_Rd_chu_kN
    F1 = 4.0 * M_pl / (m / 1e3)
    F2 = (2.0 * M_pl + (n / 1e3) * sum_Ft) / ((m + n) / 1e3)
    F3 = sum_Ft
    F_Rd = min(F1, F2, F3)
    modo = ("modo 1", "modo 2", "modo 3")[(F1, F2, F3).index(F_Rd)]
    F_Ed = N_t_kN / 2.0                                          # por flange
    return {
        "m_mm": round(m, 1), "n_mm": round(n, 1), "l_eff_mm": round(l_eff, 0),
        "F_T1_kN": round(F1, 1), "F_T2_kN": round(F2, 1), "F_T3_kN": round(F3, 1),
        "F_T_Rd_kN": round(F_Rd, 1), "modo": modo, "F_Ed_flange_kN": round(F_Ed, 1),
        "eta": round(F_Ed / F_Rd, 4) if F_Rd > 0 else 999.0,
    }


def verificar_base_pilar(
    *,
    rotulo:        str,
    N_t_kN:        float,
    N_c_kN:        float,
    V_madeira_kN:  float,
    b_pilar_m:     float,
    h_pilar_m:     float,
    mat:           GlulamMaterial,
    n_x:           int,
    n_y:           int,
    s_mm:          float,
    d_chu_mm:      float,
    F_t_Rd_chu_kN: float,
    e_mm:          float = E_BORDA_CHAPA_MM,
    d_cavilha_mm:  float = D_CAVILHA_PE_MM,
    aco:           str = "S275",
    f_cd_MPa:      float = 25.0 / 1.5,
    eta_alvo_chapa: float = ETA_ALVO_CHAPA,
) -> dict:
    """
    Geometria, espessura (compressão + T-stub) e ligação do pé do pilar.

    Args:
        N_t_kN        : arrancamento de cálculo na base (kN)
        N_c_kN        : compressão de cálculo na base (kN)
        V_madeira_kN  : cortante que cruza a madeira do pé do pilar (kN)
        n_x, n_y      : chumbadores ⊥ ao pórtico e no plano do pórtico
        s_mm          : espaçamento da grelha (o MESMO da verificação EN 1992-4)
        F_t_Rd_chu_kN : resistência à tração de um chumbador (kN)
    """
    b_mm, h_mm = b_pilar_m * 1e3, h_pilar_m * 1e3
    geo = geometria_base(n_x, n_y, s_mm, e_mm, b_mm, h_mm, d_chu_mm)
    B, L = geo["B_mm"], geo["L_mm"]

    # Compressão — área efetiva da EN 1993-1-8 §6.2.5: a chapa só apoia numa
    # faixa c = t·√(f_y/(3·f_jd·γ_M0)) em volta do pilar. f_jd = β_j·f_cd com
    # β_j = 2/3 e sem ganho de confinamento (k_j = 1), como na chaveta.
    f_y = ACO_CHAPA[aco]["f_y"]
    f_jd = 2.0 / 3.0 * f_cd_MPa

    def _compressao(t):
        c = t * math.sqrt(f_y / (3.0 * f_jd * GAMMA_M0))
        A_eff = min(b_mm + 2 * c, B) * min(h_mm + 2 * c, L)
        return c, A_eff, f_jd * A_eff / 1e3                           # kN

    # Pé do pilar: chapa vertical embutida + cavilhas, força // fibras
    pe = dimensionar_ligacao_axial_escora(
        F_Ed_kN=float(N_t_kN), mat=mat, b_m=b_pilar_m, h_m=h_pilar_m,
        d_mm=d_cavilha_mm, rotulo=f"{rotulo} — pé do pilar",
    )
    t_alma = float(pe["t_chapa_mm"])
    # Cortante ⊥ fibras nas mesmas cavilhas (n_ef = n para ⊥ fibras)
    joh90 = johansen_chapa_embutida(mat.rho_k, d_cavilha_mm, pe["t1_mm"],
                                    F_U_K_PINO, theta_deg=90.0)
    F_v_Rd_90 = 2.0 * mat.k_mod * joh90["F_v_Rk_N"] / GAMMA_M_LIGACAO / 1e3
    R_perp = pe["n_pinos"] * F_v_Rd_90
    eta_V = V_madeira_kN / R_perp if R_perp > 0 else 999.0

    # Espessura: menor comercial com compressão e T-stub dentro da margem
    t_adot, ts = None, None
    for t in COMERCIAIS_MM:
        ts = tstub_base(N_t_kN, n_y=n_y, s_mm=s_mm, e_mm=e_mm, L_mm=L,
                        t_alma_mm=t_alma, F_t_Rd_chu_kN=F_t_Rd_chu_kN,
                        t_mm=t, aco=aco)
        if ts["eta"] <= eta_alvo_chapa and N_c_kN <= eta_alvo_chapa * _compressao(t)[2]:
            t_adot = t
            break
    if t_adot is None:
        t_adot = COMERCIAIS_MM[-1]
    c_eff, A_eff, N_c_Rd = _compressao(t_adot)
    eta_comp = N_c_kN / N_c_Rd if N_c_Rd > 0 else 999.0

    partes = {"chapa_tstub": ts["eta"], "chapa_compressao": eta_comp,
              "pe_tracao": pe["eta"], "pe_cortante": eta_V}
    gov = max(partes, key=partes.get)
    return {
        "rotulo":       rotulo,
        "geometria":    geo,
        "B_mm":         B, "L_mm": L,
        "f_jd_MPa":     round(f_jd, 2),
        "c_eff_mm":     round(c_eff, 1),
        "A_eff_m2":     round(A_eff / 1e6, 4),
        "N_c_Rd_kN":    round(N_c_Rd, 1),
        "eta_compressao": round(eta_comp, 4),
        "tstub":        ts,
        "t_adotada_mm": t_adot,
        "t_alma_mm":    t_alma,
        "pe_pilar":     pe,
        "F_v_Rd_90_pino_kN": round(F_v_Rd_90, 2),
        "R_perp_kN":    round(R_perp, 1),
        "eta_cortante_pe": round(eta_V, 4),
        "partes":       {k: round(v, 4) for k, v in partes.items()},
        "governa":      gov,
        "eta":          round(partes[gov], 4),
        # O pé do pilar é modo frágil (cavilhas em madeira): alvo 0,75
        "ok":           bool(geo["folga_ok"] and ts["eta"] <= 1.0 and eta_comp <= 1.0
                             and pe["ok"] and eta_V <= 0.75 + 1e-9),
        "norma":        "EN 1993-1-8 §6.2.4/§6.2.5 + EC5 §8.2.3/§8.5.1.1/An. A",
    }
