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
# Issue 80 — chumbadores moldados no concreto têm tolerância de posição que o
# furo normal (d + 2) não acomoda: furo ALARGADO na chapa de base e arruela-chapa
# com furo normal, soldada na montagem depois de posicionada.
TOL_POSICAO_CHU_MM = 6.0  # tolerância de posição dos chumbadores (exigida da fundação)
ARRUELA_CHAPA_MM = (80.0, 10.0)   # lado e espessura da arruela-chapa (S275)
A_SOLDA_ARRUELA_MM = 5.0


def d0_furo_base(d_chu_mm: float, tol_mm: float = TOL_POSICAO_CHU_MM) -> float:
    """Furo alargado da chapa de base: d + 2·tolerância (≥ furo alargado da EN 1090-2)."""
    return float(d_chu_mm) + 2.0 * tol_mm


def verificar_arruela_chapa(*, V_chu_kN: float, N_chu_kN: float, d_chu_mm: float,
                            lado_mm: float = ARRUELA_CHAPA_MM[0],
                            t_mm: float = ARRUELA_CHAPA_MM[1],
                            a_mm: float = A_SOLDA_ARRUELA_MM) -> dict:
    """
    Arruela-chapa soldada na montagem (issue 80): o cortante de cada chumbador
    passa da porca/fuste à arruela-chapa (pressão de contato no furo normal,
    EN 1993-1-8 Tab. 3.4) e dela à chapa de base pela solda de filete no
    contorno (§4.5.3.3); a tração vai pela porca à arruela-chapa, que a apoia
    na chapa de base em todo o contorno do furo alargado (flexão desprezável
    com lado ≥ 3·d0 e t ≥ 10 mm).
    """
    import math
    from mlc_projeto.connections.chapas_aco import ACO_CHAPA, GAMMA_M2, d0_furo
    f_u = ACO_CHAPA["S275"]["f_u"]
    F_b = 2.5 * 1.0 * f_u * d_chu_mm * t_mm / GAMMA_M2 / 1e3          # kN
    f_vwd = f_u / math.sqrt(3.0) / (ACO_CHAPA["S275"]["beta_w"] * GAMMA_M2)
    F_w = 4.0 * lado_mm * a_mm * f_vwd / 1e3                           # kN
    eta = max(V_chu_kN / F_b, V_chu_kN / F_w)
    return {"lado_mm": lado_mm, "t_mm": t_mm, "furo_mm": d0_furo(d_chu_mm), "a_solda_mm": a_mm,
            "F_b_Rd_kN": round(F_b, 1), "F_w_Rd_kN": round(F_w, 1),
            "V_chu_kN": round(V_chu_kN, 2), "eta": round(eta, 4), "ok": eta <= 1.0}
T_MIN_BASE_PILARETE_MM = 12.5   # chapa de base com pilarete soldado: mínimo construtivo


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


def tstub_base_tubo(N_t_kN: float, *, chumbadores_mm: list, D_tubo_mm: float,
                    a_solda_mm: float, e_mm: float, F_t_Rd_chu_kN: float, t_mm: float,
                    F_extra_kN: float = 0.0, aco: str = "S275") -> dict:
    """
    Chapa de base sob tração entregue por um TUBO central (pilarete, issue 87):
    cada chumbador é um T-stub isolado junto ao canto da chapa (EN 1993-1-8
    Tab. 6.4, fileira de extremidade, padrões circulares e não circulares):
    l_eff = min(2πm; πm + 2e; 4m + 1,25e; 2m + 0,625e + e), com m = distância do
    chumbador à face do tubo menos 0,8·a·√2 e e = distância à borda. Distribuição igual N_t/n (a chapa é rígida o bastante para o
    alvo adotado); F_extra soma-se ao chumbador mais tracionado (binário do
    momento do pilarete). Governa o chumbador de menor F_T,Rd.
    """
    f_y = ACO_CHAPA[aco]["f_y"]
    n_chu = len(chumbadores_mm)
    F_Ed = N_t_kN / n_chu + F_extra_kN
    pior = None
    for (x, y) in chumbadores_mm:
        m = math.hypot(x, y) - D_tubo_mm / 2.0 - 0.8 * a_solda_mm * math.sqrt(2.0)
        n = min(e_mm, 1.25 * m)
        l_eff = min(2.0 * math.pi * m, math.pi * m + 2.0 * e_mm,
                    4.0 * m + 1.25 * e_mm, 2.0 * m + 0.625 * e_mm + e_mm)
        M_pl = 0.25 * l_eff * t_mm ** 2 * f_y / GAMMA_M0 / 1e6        # kN·m
        F1 = 4.0 * M_pl / (m / 1e3)
        F2 = (2.0 * M_pl + (n / 1e3) * F_t_Rd_chu_kN) / ((m + n) / 1e3)
        F_Rd = min(F1, F2, F_t_Rd_chu_kN)
        if pior is None or F_Rd < pior["F_T_Rd_kN"]:
            modo = ("modo 1", "modo 2", "modo 3")[(F1, F2, F_t_Rd_chu_kN).index(F_Rd)]
            pior = {"m_mm": round(m, 1), "n_mm": round(n, 1), "l_eff_mm": round(l_eff, 0),
                    "F_T1_kN": round(F1, 1), "F_T2_kN": round(F2, 1),
                    "F_T3_kN": round(F_t_Rd_chu_kN, 1), "F_T_Rd_kN": round(F_Rd, 1),
                    "modo": modo}
    pior["F_Ed_flange_kN"] = round(F_Ed, 1)          # por chumbador
    pior["eta"] = round(F_Ed / pior["F_T_Rd_kN"], 4) if pior["F_T_Rd_kN"] > 0 else 999.0
    pior["por_chumbador"] = True
    return pior


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
    h_pilarete_m:  float = 0.0,
    V_pilarete_kN: float | None = None,
    N_c_pe_kN:     float | None = None,
    N_t_pe_kN:     float | None = None,
    x_tubos_mm:    tuple = (0.0,),
    tubos:         tuple | None = None,
    N_t_pilarete_kN: float | None = None,
    tirante:       dict | None = None,
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
        N_c_pe_kN, N_t_pe_kN : forças no pé de madeira e no pilarete, quando diferem
                        das da chapa (pilar bipartido, issue 104: cada lâmina tem o seu
                        pilarete e o seu pé; b_pilar/h_pilar são então os da lâmina)
        x_tubos_mm    : posições dos pilaretes na chapa, ⊥ ao pórtico (0 = centrado)
        tirante       : tirante interno (connections.tirante_interno): o arrancamento
                        desce pela barra até a chapa de topo do pilarete, que o recebe
                        no centro; o pé de madeira fica só com o cortante (N_t_pe = 0)
    """
    N_c_pe = float(N_c_kN if N_c_pe_kN is None else N_c_pe_kN)
    N_t_pe = float(N_t_kN if N_t_pe_kN is None else N_t_pe_kN)
    N_t_pil = float(N_t_pe if N_t_pilarete_kN is None else N_t_pilarete_kN)
    b_mm, h_mm = b_pilar_m * 1e3, h_pilar_m * 1e3
    geo = geometria_base(n_x, n_y, s_mm, e_mm, b_mm, h_mm, d_chu_mm)
    B, L = geo["B_mm"], geo["L_mm"]

    # Pilarete (issue 87): tubo entre a chapa de base e o pé do pilar
    pil = None
    if h_pilarete_m > 0.0:
        from mlc_projeto.connections.pilarete import (
            tracao_equivalente_momento, verificar_pilarete,
        )
        V_p = float(V_madeira_kN if V_pilarete_kN is None else V_pilarete_kN)
        pil = verificar_pilarete(rotulo=rotulo, N_c_kN=N_c_pe, N_t_kN=N_t_pil,
                                 V_kN=V_p, h_m=h_pilarete_m, b_pilar_mm=b_mm,
                                 h_pilar_mm=h_mm, tubos=tubos, tirante=tirante)
        # binário do momento do pilarete no chumbador mais tracionado
        F_extra = tracao_equivalente_momento(pil["M_base_kNm"], (n_x, n_y), s_mm) / (n_x * n_y)
        # no nível da chapa de base o obstáculo à chave passa a ser o tubo, não o
        # pilar (a madeira começa h_pilarete acima): folga arruela–tubo
        # a arruela-chapa quadrada (issue 80) é o obstáculo junto ao tubo: menor folga
        # entre a face de cada tubo e a borda da arruela de cada chumbador (Chebyshev)
        meia_arr = max(0.925 * d_chu_mm, ARRUELA_CHAPA_MM[0] / 2.0)
        folga_t = min(max(abs(x - xt), abs(y)) - pil["D_mm"] / 2.0 - meia_arr
                      for xt in x_tubos_mm for x, y in geo["chumbadores_mm"])
        geo["folga_arruela_pilar_mm"] = round(folga_t, 1)
        geo["folga_referencia"] = "tubo do pilarete × arruela-chapa"
        geo["d0_furo_base_mm"] = d0_furo_base(d_chu_mm)
        geo["folga_ok"] = folga_t >= 0.0

    # Compressão — área efetiva da EN 1993-1-8 §6.2.5: a chapa só apoia numa
    # faixa c = t·√(f_y/(3·f_jd·γ_M0)) em volta do pilar. f_jd = β_j·f_cd com
    # β_j = 2/3 e sem ganho de confinamento (k_j = 1), como na chaveta.
    f_y = ACO_CHAPA[aco]["f_y"]
    f_jd = 2.0 / 3.0 * f_cd_MPa

    def _compressao(t):
        c = t * math.sqrt(f_y / (3.0 * f_jd * GAMMA_M0))
        if pil is not None:                     # coroa sob a parede do tubo
            R, tw = pil["D_mm"] / 2.0, pil["t_mm"]
            A_eff = min(math.pi * ((R + c) ** 2 - max(R - tw - c, 0.0) ** 2), B * L)
        else:
            A_eff = min(b_mm + 2 * c, B) * min(h_mm + 2 * c, L)
        return c, A_eff, f_jd * A_eff / 1e3                           # kN

    # Pé do pilar: chapa vertical embutida + cavilhas, força // fibras
    # Retração impedida (issue 81): no pé o cortante do choque cruza as cavilhas
    # ⊥ às fibras, e os furos não podem ser ovalizados — a malha fica limitada à
    # largura que a folga do furo absorve (3 fileiras de Ø20 a 60 mm).
    # Issue 76: o cortante do choque, ⊥ às fibras e de sentido qualquer, torna as
    # duas faces do pilar bordas carregadas — a4,t = max[(2 + 2 sen 90°)d; 3d] = 4d.
    from mlc_projeto.connections.retracao import n_perp_max, n_perp_max_borda_carregada
    from mlc_projeto.connections.connections import distancias_minimas as _dm
    _a2 = _dm(d_cavilha_mm, 0.0)["a2_mm"]
    _a4t = _dm(d_cavilha_mm, 90.0)["a4t_mm"]
    from mlc_projeto.connections.retracao import D_perp_max_mm
    # A malha é a menor que atende à tração // E ao cortante ⊥ do choque: quando a
    # tração é pequena (lâmina do pilar bipartido, issue 104), o cortante governa, e a
    # força de dimensionamento cresce até que as cavilhas o resistam.
    F_dim = max(N_t_pe, 1.0)
    for _ in range(40):
        pe = dimensionar_ligacao_axial_escora(
            F_Ed_kN=F_dim, mat=mat, b_m=b_pilar_m, h_m=h_pilar_m,
            d_mm=d_cavilha_mm, rotulo=f"{rotulo} — pé do pilar",
            D_perp_max_mm=D_perp_max_mm(d_cavilha_mm), a4_min_mm=_a4t, n_horiz_max=16,
            # tirante interno no eixo: duas fileiras que contornam o furo central
            **(dict(n_vert_min=2, a2_min_mm=tirante["furo_pilar_mm"] + d_cavilha_mm + 10.0)
               if tirante else {}),
        )
        # Cortante ⊥ fibras nas mesmas cavilhas (n_ef = n para ⊥ fibras)
        joh90 = johansen_chapa_embutida(mat.rho_k, d_cavilha_mm, pe["t1_mm"],
                                        F_U_K_PINO, theta_deg=90.0)
        F_v_Rd_90 = 2.0 * mat.k_mod * joh90["F_v_Rk_N"] / GAMMA_M_LIGACAO / 1e3
        R_perp = pe["n_pinos"] * F_v_Rd_90
        eta_V = V_madeira_kN / R_perp if R_perp > 0 else 999.0
        if eta_V <= 0.75 + 1e-9 and pe["n_pinos"] >= 2:
            break
        F_dim *= 1.15
    if F_dim > N_t_pe:                  # η da tração com a força real, na malha adotada
        pe = dict(pe, F_Ed_kN=round(N_t_pe, 2),
                  eta_pinos=round(N_t_pe / pe["R_d_kN"], 4),
                  eta=round(max(N_t_pe / pe["R_d_kN"], pe["eta_bloco"] * N_t_pe / F_dim), 4))
    t_alma = float(pe["t_chapa_mm"])

    # ── Issue 76: madeira do pé sob o choque e sob a tração ───────────────
    from mlc_projeto.connections.connections import verificar_fendilhamento
    nv, a2p = int(pe["n_vert"]), float(pe["a2_mm"])
    # choque = situação acidental: k_mod instantâneo (CS3, Tab. 3.1) e γ_M = 1,0
    # (EN 1995-1-1 Tab. 2.3, combinações acidentais)
    K_MOD_INST, GAMMA_M_LIG = 0.90, 1.0
    # fendilhamento (§8.1.4): força ⊥ às fibras no plano da chapa, grupo centrado
    h_e = h_mm / 2.0 + (nv - 1) * a2p / 2.0
    fend = verificar_fendilhamento(F_90_Ed_kN=float(V_madeira_kN), b_mm=b_mm, h_mm=h_mm,
                                   h_e_mm=h_e, k_mod=K_MOD_INST, gamma_M=GAMMA_M_LIG)
    # seção líquida à tração (§6.1.2): descontados o rasgo e os furos de uma fileira
    t_r = t_alma + 4.0
    w_r = h_mm - 60.0 + 10.0
    A_net = b_mm * h_mm - t_r * w_r - nv * d_cavilha_mm * (b_mm - t_r)
    sig_t = N_t_pe * 1e3 / A_net
    eta_net = sig_t / (mat.f_t0_d / 1e6)
    # choque ⊥ ao plano da chapa: as cavilhas não o resistem ao corte; vencida a
    # folga de 2 mm do rasgo, as faces da chapa apoiam-se nas paredes do rasgo
    # (compressão ⊥ às fibras sobre a área da chapa embutida)
    A_cont = (h_mm - 60.0) * float(pe["L_ocupado_mm"] + 2.5 * d_cavilha_mm)
    sig_c90 = float(V_madeira_kN) * 1e3 / A_cont
    eta_cont = sig_c90 / (K_MOD_INST * mat.f_c90_k / 1e6 / GAMMA_M_LIG)

    # Espessura: menor comercial com compressão e T-stub dentro da margem
    t_adot, ts = None, None
    # mínimo construtivo e garganta da solda do pilarete: a ≤ 0,7·t (issue 87)
    t_min = 0.0 if pil is None else max(T_MIN_BASE_PILARETE_MM, pil["a_solda_base_mm"] / 0.7)
    for t in COMERCIAIS_MM:
        if t < t_min - 1e-9:
            continue
        if pil is not None:
            # persistente (N_t) e acidental (binário do choque), não concomitantes
            ts = max((tstub_base_tubo(N_t_kN, chumbadores_mm=geo["chumbadores_mm"],
                                      D_tubo_mm=pil["D_mm"], a_solda_mm=pil["a_solda_base_mm"],
                                      e_mm=e_mm, F_t_Rd_chu_kN=F_t_Rd_chu_kN, t_mm=t, aco=aco),
                      tstub_base_tubo(0.0, chumbadores_mm=geo["chumbadores_mm"],
                                      D_tubo_mm=pil["D_mm"], a_solda_mm=pil["a_solda_base_mm"],
                                      e_mm=e_mm, F_t_Rd_chu_kN=F_t_Rd_chu_kN, t_mm=t, aco=aco,
                                      F_extra_kN=F_extra)),
                     key=lambda r: r["eta"])
        else:
            ts = tstub_base(N_t_kN, n_y=n_y, s_mm=s_mm, e_mm=e_mm, L_mm=L,
                            t_alma_mm=t_alma, F_t_Rd_chu_kN=F_t_Rd_chu_kN,
                            t_mm=t, aco=aco)
        if ts["eta"] <= eta_alvo_chapa and N_c_pe <= eta_alvo_chapa * _compressao(t)[2]:
            t_adot = t
            break
    if t_adot is None:
        t_adot = COMERCIAIS_MM[-1]
    c_eff, A_eff, N_c_Rd = _compressao(t_adot)
    eta_comp = N_c_pe / N_c_Rd if N_c_Rd > 0 else 999.0     # por pilarete

    partes = {"chapa_tstub": ts["eta"], "chapa_compressao": eta_comp,
              "pe_tracao": pe["eta"], "pe_cortante": eta_V,
              "pe_fendilhamento": fend["eta"], "pe_secao_liquida": eta_net,
              "pe_choque_fora_do_plano": eta_cont}
    if pil is not None:
        partes["pilarete"] = pil["eta"]
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
        "fendilhamento_pe": fend,
        "secao_liquida_pe": {"A_net_mm2": round(A_net, 0), "sigma_t_MPa": round(sig_t, 3),
                             "t_rasgo_mm": t_r, "eta": round(eta_net, 4)},
        "choque_fora_plano_pe": {"A_contato_mm2": round(A_cont, 0),
                                 "sigma_c90_MPa": round(sig_c90, 3), "eta": round(eta_cont, 4)},
        "a4t_req_mm": _a4t,
        "a4t_adot_mm": round((h_mm - (nv - 1) * a2p) / 2.0, 1),
        "pilarete":     pil,
        "partes":       {k: round(v, 4) for k, v in partes.items()},
        "governa":      gov,
        "eta":          round(partes[gov], 4),
        # O pé do pilar é modo frágil (cavilhas em madeira): alvo 0,75
        "ok":           bool(geo["folga_ok"] and ts["eta"] <= 1.0 and eta_comp <= 1.0
                             and pe["ok"] and eta_V <= 0.75 + 1e-9
                             and fend["eta"] <= 0.75 + 1e-9 and eta_net <= 1.0
                             and eta_cont <= 1.0
                             and (pil is None or pil["ok"])),
        "norma":        "EN 1993-1-8 §6.2.4/§6.2.5 + EC5 §8.2.3/§8.5.1.1/An. A",
    }
