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
    EC5 §8.2     — teoria de Johansen
    EC5 §8.5.1.1 — número efetivo de pernos/pinos (fileira // fibras)
    EC5 §8.3.1.2 — distâncias mínimas (Tab. 8.2; pinos via §8.6)
    EC5 §8.6     — pinos lisos (remete a §8.5)
    EC5 §6.1.4   — compressão paralela às fibras
    EC5 §6.1.5   — compressão perpendicular às fibras
    EN 14592     — especificação dos pinos de aço
    EN 1993-1-8  — chapa metálica e chumbadores
"""

from __future__ import annotations

import math
import numpy as np
import pandas as pd

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial, GAMMA_M, GAMMA_M_LIGACAO
from mlc_projeto.core.loads     import Carregamentos

# Pinos de aço — EN 14592 (grau típico de cavilha; f_u a confirmar na ficha)
F_U_K_PINO = 400.0   # MPa — f_u,k do pino (não confundir com f_y do S355)

# EC5 §8.6(2) — faixa de diâmetro admissível para CAVILHAS (dowels).
# As fórmulas de embutimento (Eq. 8.32) e o escopo de §8.5/§8.6 são calibrados
# nesta faixa; diâmetros fora dela (ex.: Ø36 mm) estão fora do escopo normativo.
D_CAVILHA_MIN_MM = 6.0
D_CAVILHA_MAX_MM = 30.0


# ── Critério η-alvo das ligações (issue 22) ──────────────────────────────────
# O alvo 0,75 é uma MARGEM DE PROJETO (uso público), justificada pela ausência de
# redistribuição plástica — falha FRÁGIL. Aplica-se aos modos FRÁGEIS:
#   · ruptura frágil da MADEIRA: embutimento do grupo de cavilhas (Johansen+n_ef),
#     corte de bloco (Anexo A), fendilhamento (§8.1.4);
#   · ancoragem FRÁGIL no concreto (cone/arrancamento dos chumbadores, EN 1992-4).
# NÃO se aplica a modos DÚCTEIS ou de COMPRESSÃO, que usam o limite normativo η≤1,0
# (exceções justificadas):
#   · compressão localizada no CONCRETO sob a chapa de base (L3/L3c — esmagamento);
#   · compressão da MADEIRA na cumeeira (verificação de SEÇÃO §6.1.4/§6.1.5/§6.4.3);
#   · componentes de AÇO dúcteis (chapa, furo/bearing, solda, pino — EN 1993).
ETA_ALVO_LIGACAO = 0.75


def classificar_criterio_eta(modo_fragil: bool, eta_alvo: float = ETA_ALVO_LIGACAO) -> dict:
    """
    Classifica uma verificação de ligação quanto ao critério η (issue 22).

    Args:
        modo_fragil : True se a falha governante é FRÁGIL (madeira: embutimento/
                      bloco/fendilhamento; ou ancoragem frágil no concreto) →
                      aplica-se o alvo. False para modos dúcteis/compressão → η≤1,0.
        eta_alvo    : margem de projeto para modos frágeis (default 0,75).

    Returns:
        dict com eta_limite, alvo_aplica e criterio_eta (texto para o memorial).
    """
    if modo_fragil:
        return {
            "eta_limite":   eta_alvo,
            "alvo_aplica":  True,
            "criterio_eta": f"alvo {eta_alvo:.2f} — modo FRÁGIL (sem redistribuição)",
        }
    return {
        "eta_limite":   1.0,
        "alvo_aplica":  False,
        "criterio_eta": "η≤1,0 — modo dúctil/compressão (exceção justificada)",
    }


def aplicar_criterio_eta(
    res: dict,
    modo_fragil: bool,
    eta_alvo: float = ETA_ALVO_LIGACAO,
) -> dict:
    """
    Injeta a classificação do critério η numa verificação de ligação e recalcula
    `ok` de forma CONSISTENTE com o limite aplicável (issue 22).

        ok = (η ≤ η_limite)  [e ok_geometria, se existir]

    Modo frágil → η_limite = eta_alvo (0,75); senão → η_limite = 1,0.
    Preserva `ok_alvo` (η ≤ 0,75) para transparência mesmo nas exceções.

    O critério de η só pode ACRESCENTAR motivo de reprovação, nunca remover um
    existente: `ok` é conjugado com o valor que a verificação já tinha. Antes,
    esta função recalculava `ok` exclusivamente a partir de η e apagava
    qualquer outro bloqueio — foi assim que o `status_ancoragem="NOT VALIDATED"`
    de `dimensionar_sapata` (AUD-017) chegava ao memorial como aprovado, com
    η = 0 a "passar" no limite. É exatamente o mecanismo de falsa aprovação que
    AUD-016 descreve; qualquer verificação com η baixo e bloqueio não numérico
    estava sujeita a ele.
    """
    cls = classificar_criterio_eta(modo_fragil, eta_alvo)
    res.update(cls)
    eta = float(res.get("eta", res.get("eta_gov", 0.0)))
    ok = eta <= cls["eta_limite"] + 1e-9
    if "ok_geometria" in res:
        ok = ok and bool(res["ok_geometria"])
    # Nunca promover um `ok` que já era False.
    ok = ok and bool(res.get("ok", True))
    res["ok"] = ok
    res["ok_alvo"] = eta <= eta_alvo + 1e-9
    return res


def _validar_diametro_cavilha(d_mm: float) -> None:
    """
    Guarda de escopo EC5 §8.6(2): 6 mm ≤ d ≤ 30 mm para cavilhas (issue 18).

    Rejeita (ValueError) diâmetros fora do escopo — evita usar silenciosamente
    fórmulas não calibradas. Para forças elevadas, reduzir d e aumentar o número
    de pinos/planos de corte, ou usar conector com regras próprias (parafusos
    autoperfurantes inclinados).
    """
    if not (D_CAVILHA_MIN_MM <= float(d_mm) <= D_CAVILHA_MAX_MM):
        raise ValueError(
            f"Diâmetro de cavilha d={d_mm:.0f} mm fora do escopo EC5 §8.6(2) "
            f"({D_CAVILHA_MIN_MM:.0f}–{D_CAVILHA_MAX_MM:.0f} mm). Reduza d "
            f"(mais pinos/planos de corte) ou use conector com regras próprias."
        )


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


# ── Ruptura de bloco — EC5 Anexo A (informativo) ─────────────────────────────

def ruptura_de_bloco(
    n_par:      int,
    n_perp:     int,
    a1_m:       float,
    a2_m:       float,
    a3t_m:      float,
    t1_m:       float,
    f_t0_k:     float,
    f_v_k:      float,
    k_mod:      float,
    gamma_M:    float,
    F_par_kN:   float,
) -> dict:
    """
    Ruptura de bloco (block shear) — EN 1995-1-1 Anexo A, Eq. (A.1)–(A.3).

    Falha frágil do bloco de madeira delimitado por um grupo de conectores sob
    força PARALELA às fibras, próximo ao extremo da peça (Figura A.1).

        F_bs,Rk = max{ 1,5·A_net,t·f_t,0,k ; 0,7·A_net,v·f_v,k }      (A.1)
        A_net,t = L_net,t · t_1                                        (A.2)
        A_net,v = L_net,v · t_1   (block shear, Fig. A.1)             (A.3)

    Geometria do bloco (grupo retangular, força // fibras):
        L_net,t = (n_perp − 1)·a2         largura líquida ⊥ fibras (plano de tração)
        L_net,v = 2·[(n_par − 1)·a1 + a3,t]   comprimento total das duas faces de
                  cisalhamento // fibras (do extremo carregado ao plano de tração)
        t_1     = espessura de madeira mobilizada (chapa embutida central:
                  ≈ largura b da peça; descontar a fenda da chapa — ver issue 21)

    NOTA sobre a Eq. (A.1): a norma usa `max{}` (não `min{}`) — a resistência é
    governada pelo MAIOR dos dois mecanismos idealizados (tração da face de
    extremidade OU cisalhamento das faces laterais). Reportam-se AMBOS os termos
    para transparência (o termo de cisalhamento costuma ser o crítico se o `max`
    não o selecionar).

    Args (SI): distâncias e t_1 em m; f_t0_k, f_v_k em Pa; F_par_kN em kN.

    Returns:
        dict com áreas líquidas, os dois termos, F_bs,Rk, F_bs,Rd, η e ok.
    """
    L_net_t = max(0.0, (n_perp - 1)) * a2_m
    L_net_v = 2.0 * (max(0.0, (n_par - 1)) * a1_m + a3t_m)
    A_net_t = L_net_t * t1_m                    # m²
    A_net_v = L_net_v * t1_m                    # m²

    F_t = 1.5 * A_net_t * f_t0_k                # N (tração // fibras)
    F_v = 0.7 * A_net_v * f_v_k                 # N (cisalhamento // fibras)
    F_bs_Rk = max(F_t, F_v)                     # N — Eq. (A.1)
    F_bs_Rd = k_mod * F_bs_Rk / gamma_M         # N
    F_bs_Rd_v = k_mod * F_v / gamma_M           # N — só cisalhamento (transparência)

    eta = (F_par_kN * 1e3) / F_bs_Rd if F_bs_Rd > 0 else 999.0
    eta_v = (F_par_kN * 1e3) / F_bs_Rd_v if F_bs_Rd_v > 0 else 999.0
    governa = "tração" if F_t >= F_v else "cisalhamento"

    return {
        "n_par":          n_par,
        "n_perp":         n_perp,
        "L_net_t_mm":     round(L_net_t * 1e3, 1),
        "L_net_v_mm":     round(L_net_v * 1e3, 1),
        "t1_mm":          round(t1_m * 1e3, 1),
        "A_net_t_cm2":    round(A_net_t * 1e4, 1),
        "A_net_v_cm2":    round(A_net_v * 1e4, 1),
        "term_tracao_kN": round(F_t / 1e3, 1),
        "term_cisalh_kN": round(F_v / 1e3, 1),
        "governa":        governa,
        "F_bs_Rk_kN":     round(F_bs_Rk / 1e3, 1),
        "F_bs_Rd_kN":     round(F_bs_Rd / 1e3, 1),
        "F_par_kN":       round(F_par_kN, 1),
        "eta":            round(eta, 4),
        "eta_so_cisalh":  round(eta_v, 4),
        "ok":             eta <= 1.0,
        "norma":          "EN 1995-1-1 Anexo A Eq. (A.1)–(A.3)",
        "nota": (
            "Eq. (A.1) usa max{} — governado por "
            f"{governa}. η só-cisalhamento={eta_v:.2f} (transparência). "
            "t_1 = b (fenda da chapa a descontar — issue 21)."
        ),
    }


def ruptura_de_bloco_ligacao(
    res_lig:  dict,
    geo:      GeometriaViga,
    mat:      GlulamMaterial,
    k_mod:    float | None = None,
    gamma_M:  float = GAMMA_M,
) -> dict:
    """
    Aplica a ruptura de bloco (Anexo A) a uma ligação de cavilhas já dimensionada
    (resultado de dimensionar_ligacao_base / _central), lendo o layout real.

    Força // fibras = |N_d| (componente axial). t_1 = b (largura da peça).
    γ_M = GAMMA_M (glulam, material — a ruptura de bloco é falha do material da
    peça, EC5 §2.4.1); k_mod da combinação (padrão = mat.k_mod).
    """
    if k_mod is None:
        k_mod = mat.k_mod
    n_par = int(res_lig["n_linha"])       # pinos // fibras por fileira
    n_perp = int(res_lig["n_linhas"])     # fileiras ⊥ fibras (altura)
    d_mm = float(res_lig["d_mm"])
    a1_m = float(res_lig["a1_mm"]) / 1e3
    a2_m = float(res_lig["a2_mm"]) / 1e3
    # distância de extremidade carregada a3,t — EC5 Tab. 8.4 (cavilha): max(7d, 80 mm)
    a3t_m = max(7.0 * d_mm, 80.0) / 1e3
    t1_m = geo.b                          # largura da peça (fenda da chapa desprezada)
    F_par_kN = abs(float(res_lig["N_d_kN"]))
    return ruptura_de_bloco(
        n_par=n_par, n_perp=n_perp, a1_m=a1_m, a2_m=a2_m, a3t_m=a3t_m,
        t1_m=t1_m, f_t0_k=mat.f_t0_k, f_v_k=mat.f_v_k,
        k_mod=k_mod, gamma_M=gamma_M, F_par_kN=F_par_kN,
    )


# ── Fendilhamento (splitting) — EC5 §8.1.4 Eq. (8.4)/(8.5) (issue 20) ─────────

def verificar_fendilhamento(
    F_90_Ed_kN: float,
    b_mm:       float,
    h_mm:       float,
    h_e_mm:     float,
    k_mod:      float,
    gamma_M:    float,
    w:          float = 1.0,
) -> dict:
    """
    Capacidade ao fendilhamento de uma ligação carregada com componente de
    força PERPENDICULAR às fibras — EN 1995-1-1 §8.1.4, Eq. (8.4)/(8.5).

        F_90,Rk = 14·b·w·√( h_e / (1 − h_e/h) )         (8.4)   [N; mm]
        w = 1                para cavilhas/parafusos e todos os conectores
            (w_pl/100)^0,35  APENAS para chapas metálicas puncionadas   (8.5)

        F_90,Rd = k_mod · F_90,Rk / γ_M
        Verificação:  F_90,Ed ≤ F_90,Rd

    onde (Fig. 8.1):
        b    = espessura da peça (mm)
        h    = altura total da peça na ligação (mm)
        h_e  = distância da BORDA CARREGADA ao conector mais distante (mm)
        F_90,Ed = componente da força da ligação ⊥ às fibras
                  (= max{F_v,Ed,1; F_v,Ed,2} dos cortantes de cada lado; aqui a
                   ligação está no apoio → o cortante de um lado é o V_d da viga).

    Falha FRÁGIL: sem redistribuição plástica → verificação obrigatória sempre
    que houver componente ⊥ às fibras (apontamento do orientador, issue 20).

    Args:
        F_90_Ed_kN : força de cálculo ⊥ às fibras (kN)
        b_mm, h_mm, h_e_mm : geometria (mm)
        k_mod, gamma_M     : da combinação / ligação (γ_M=1,30)
        w          : fator Eq. (8.5) — 1,0 para cavilhas

    Returns:
        dict com F_90,Rk, F_90,Rd, η e ok.
    """
    if not (0.0 < h_e_mm < h_mm):
        raise ValueError(f"h_e ({h_e_mm}) deve estar em (0, h={h_mm}) mm")
    if b_mm <= 0:
        raise ValueError("b deve ser > 0")

    F_90_Rk = 14.0 * b_mm * w * math.sqrt(h_e_mm / (1.0 - h_e_mm / h_mm))  # N
    F_90_Rd = k_mod * F_90_Rk / gamma_M                                    # N
    eta = (abs(F_90_Ed_kN) * 1e3) / F_90_Rd if F_90_Rd > 0 else 999.0

    return {
        "F_90_Ed_kN":  round(abs(F_90_Ed_kN), 3),
        "b_mm":        round(b_mm, 1),
        "h_mm":        round(h_mm, 1),
        "h_e_mm":      round(h_e_mm, 1),
        "h_e_h":       round(h_e_mm / h_mm, 4),
        "w":           w,
        "F_90_Rk_kN":  round(F_90_Rk / 1e3, 3),
        "F_90_Rd_kN":  round(F_90_Rd / 1e3, 3),
        "k_mod":       k_mod,
        "gamma_M":     gamma_M,
        "eta":         round(eta, 4),
        "ok":          eta <= 1.0,
        "norma":       "EN 1995-1-1 §8.1.4 Eq. (8.4)/(8.5)",
    }


def fendilhamento_ligacao(
    res_lig:  dict,
    geo:      GeometriaViga,
    mat:      GlulamMaterial,
    k_mod:    float | None = None,
    gamma_M:  float = GAMMA_M_LIGACAO,
    reforcar: bool = False,
    eta_reforco_alvo: float = 0.75,
    d_reforco_mm: float = 10.0,
    l_ef_reforco_mm: float = 400.0,
) -> dict:
    """
    Aplica o fendilhamento (§8.1.4) a uma ligação de cavilhas já dimensionada
    (resultado de dimensionar_ligacao_base / _central), lendo o layout real.

    Componente ⊥ às fibras: F_90,Ed = |V_d| (cortante no eixo, componente vertical
    da resultante inclinada). h_e (borda carregada → fileira mais distante) para o
    grupo de n_linhas fileiras centrado na altura h0:

        h_e = h0/2 + (n_linhas − 1)·a2 / 2

    γ_M = 1,30 (ligação, EC5 Tab. 2.3); k_mod da combinação.
    """
    if k_mod is None:
        k_mod = mat.k_mod

    n_vert = int(res_lig["n_linhas"])          # fileiras ⊥ fibras (na altura)
    a2_mm  = float(res_lig["a2_mm"])           # espaçamento ⊥ fibras
    h_mm   = float(res_lig["h_disp_mm"])       # altura da peça na ligação (h0)
    b_mm   = float(geo.b) * 1e3                 # espessura da peça
    F_90_Ed_kN = abs(float(res_lig["V_d_kN"])) # componente ⊥ fibras

    h_e_mm = h_mm / 2.0 + (n_vert - 1) * a2_mm / 2.0

    res = verificar_fendilhamento(
        F_90_Ed_kN=F_90_Ed_kN, b_mm=b_mm, h_mm=h_mm, h_e_mm=h_e_mm,
        k_mod=k_mod, gamma_M=gamma_M, w=1.0,
    )
    res["ligacao"] = res_lig.get("ligacao", "—")
    res["n_linhas"] = n_vert
    res["a2_mm"] = round(a2_mm, 1)
    res["reforcado"] = False

    # Reforço ⊥ às fibras (EC5 §8.1.4 + §8.7.2): quando o fendilhamento (modo
    # FRÁGIL) ultrapassa o alvo, parafusos autoatarraxantes absorvem F_90,Ed e o
    # modo deixa de governar. O η reportado passa a ser o do reforço (arrancamento).
    if reforcar and res["eta"] > eta_reforco_alvo:
        reforco = dimensionar_reforco_fendilhamento(
            F_90_Ed_kN=F_90_Ed_kN, rho_k=mat.rho_k, k_mod=k_mod,
            d_mm=d_reforco_mm, l_ef_mm=l_ef_reforco_mm, gamma_M=gamma_M,
            eta_alvo=eta_reforco_alvo,
        )
        res["reforcado"] = True
        res["eta_fendilhamento_nu"] = res["eta"]
        res["ok_fendilhamento_nu"] = res["eta"] <= 1.0
        res["reforco"] = reforco
        res["eta"] = reforco["eta"]              # η governante = reforço
        res["ok"] = reforco["ok"]
        res["norma"] = (
            "EN 1995-1-1 §8.1.4 (reforçado por parafusos ⊥ fibras §8.7.2)"
        )
    return res


# ── Reforço ao fendilhamento — parafusos autoatarraxantes ⊥ às fibras ─────────
# EC5 §8.1.4 (força ⊥ às fibras) resolvido por reforço AXIAL (§8.7.2): parafusos
# totalmente rosqueados, inseridos ⊥ às fibras cruzando o plano de fendilhamento,
# absorvem a tração F_90,Ed. O modo FRÁGIL de fendilhamento deixa de governar.

def arrancamento_parafuso_perp(
    d_mm:    float,
    l_ef_mm: float,
    rho_k:   float,
    k_mod:   float,
    gamma_M: float = GAMMA_M_LIGACAO,
) -> dict:
    """
    Arrancamento de UM parafuso autoatarraxante inserido ⊥ às fibras (α=90°) —
    EN 1995-1-1 §8.7.2 Eq. (8.38)/(8.39):

        f_ax,k  = 0,52·d^-0,5·l_ef^-0,1·ρ_k^0,8    (N/mm²; válida 6 ≤ d ≤ 12 mm)
        F_ax,Rk = f_ax,k·d·l_ef·k_d                 (α=90° ⇒ denom.=1; k_d=min(d/8,1))
        F_ax,Rd = k_mod·F_ax,Rk/γ_M
    """
    if not (6.0 <= d_mm <= 12.0):
        raise ValueError("Eq. (8.39) válida para 6 ≤ d ≤ 12 mm")
    if l_ef_mm <= 0 or rho_k <= 0:
        raise ValueError("l_ef e ρ_k devem ser > 0")
    k_d = min(d_mm / 8.0, 1.0)
    f_ax_k = 0.52 * d_mm ** -0.5 * l_ef_mm ** -0.1 * rho_k ** 0.8   # N/mm²
    F_ax_Rk = f_ax_k * d_mm * l_ef_mm * k_d                          # N
    F_ax_Rd = k_mod * F_ax_Rk / gamma_M                             # N
    return {
        "d_mm":        d_mm,
        "l_ef_mm":     l_ef_mm,
        "k_d":         round(k_d, 3),
        "f_ax_k_MPa":  round(f_ax_k, 3),
        "F_ax_Rk_kN":  round(F_ax_Rk / 1e3, 3),
        "F_ax_Rd_kN":  round(F_ax_Rd / 1e3, 3),
    }


def dimensionar_reforco_fendilhamento(
    F_90_Ed_kN: float,
    rho_k:      float,
    k_mod:      float,
    d_mm:       float = 10.0,
    l_ef_mm:    float = 400.0,
    gamma_M:    float = GAMMA_M_LIGACAO,
    eta_alvo:   float = 0.75,
    f_u_MPa:    float = 800.0,
    gamma_M2:   float = 1.25,
    n_max:      int = 80,
) -> dict:
    """
    Dimensiona o nº de parafusos ⊥ às fibras para absorver F_90,Ed:
      · arrancamento em GRUPO: n_ef = n^0,9 (EC5 §8.7.2(8));
      · tração do AÇO do fuste (raiz ≈ 0,7·d; f_u, γ_M2=1,25 — EN 1993-1-8).
    Escolhe o menor n com η = max(η_arrancamento, η_aço) ≤ eta_alvo.
    """
    single = arrancamento_parafuso_perp(d_mm, l_ef_mm, rho_k, k_mod, gamma_M)
    F_ax_Rd1 = single["F_ax_Rd_kN"]
    A_s = math.pi * (0.7 * d_mm) ** 2 / 4.0                # mm² (área do fuste)
    F_t_Rd1 = f_u_MPa * A_s / gamma_M2 / 1e3               # kN (tração do aço)
    F = abs(float(F_90_Ed_kN))

    n_sel = n_max
    for n in range(2, n_max + 1):
        F_ax_grp = n ** 0.9 * F_ax_Rd1
        F_t_grp = n * F_t_Rd1
        if max(F / F_ax_grp, F / F_t_grp) <= eta_alvo:
            n_sel = n
            break

    F_ax_grp = n_sel ** 0.9 * F_ax_Rd1
    F_t_grp = n_sel * F_t_Rd1
    eta_ax = F / F_ax_grp if F_ax_grp > 0 else 999.0
    eta_st = F / F_t_grp if F_t_grp > 0 else 999.0
    eta = max(eta_ax, eta_st)
    return {
        "sistema":          "Reforço ao fendilhamento — parafusos ⊥ às fibras",
        "F_90_Ed_kN":       round(F, 3),
        "d_mm":             d_mm,
        "l_ef_mm":          l_ef_mm,
        "n_parafusos":      n_sel,
        "f_ax_k_MPa":       single["f_ax_k_MPa"],
        "F_ax_Rd_unit_kN":  round(F_ax_Rd1, 3),
        "F_ax_Rd_grupo_kN": round(F_ax_grp, 3),
        "F_t_Rd_unit_kN":   round(F_t_Rd1, 3),
        "F_t_Rd_grupo_kN":  round(F_t_grp, 3),
        "eta_arrancamento": round(eta_ax, 4),
        "eta_aco":          round(eta_st, 4),
        "eta":              round(eta, 4),
        "eta_alvo":         eta_alvo,
        "ok":               eta <= 1.0 + 1e-9,
        "norma":            "EN 1995-1-1 §8.1.4 (reforço) + §8.7.2 Eq.(8.38)/(8.39)",
        "nota": (
            f"F_90,Ed={F:.0f} kN absorvido por {n_sel}×∅{d_mm:.0f} mm "
            f"(l_ef={l_ef_mm:.0f} mm): arrancamento η={eta_ax:.2f}, aço η={eta_st:.2f}. "
            "Confirmar f_ax e f_u,parafuso com a ETA do produto."
        ),
    }


# ── Número efetivo — EC5 §8.5.1.1 (pernos; pinos via §8.6) ───────────────────

def n_ef(n: int, a1_mm: float, d_mm: float) -> float:
    """
    Número efetivo de pinos/pernos em fileira // fibras — EC5 §8.5.1.1.

        n_ef = min( n , n^0,9 · (a₁ / (13·d))^(1/4) )

    Redução de grupo: a resistência da fileira não é n·F_v,Rd (não-conservador),
    mas n_ef·F_v,Rd.  Para pinos lisos, EC5 §8.6 remete às regras de §8.5.1.

    Args:
        n     : Número de pinos na fileira (// fibras)
        a1_mm : Espaçamento entre pinos na direção das fibras (mm)
        d_mm  : Diâmetro do pino (mm)

    Returns:
        n_ef (adimensional, ≤ n)
    """
    if n <= 0:
        return 0.0
    if n == 1:
        return 1.0  # sem grupo — redução §8.5.1.1 só para fileira
    if a1_mm <= 0 or d_mm <= 0:
        raise ValueError("a1_mm e d_mm devem ser positivos")
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
    L_max_mm: float = 1800.0,
) -> dict:
    """
    Verifica o grupo de pinos na chapa embutida no extremo da viga.

    Orientação EC5 Tab. 8.2 (fibras ≈ eixo longitudinal da viga):
        - Horizontal (// fibras, no plano da chapa): espaçamento a1, extremos a3t/a3c
        - Vertical   (⊥ fibras, altura da seção):   espaçamento a2, bordas a4t/a4c

    A chapa fica no plano longitudinal-vertical (fenda central em b).
    Os pinos atravessam a largura b (espessura de madeira t = b/2 por lado).

    Args:
        n_horiz  : pinos por fileira // fibras
        n_vert   : número de fileiras na altura
        d_mm     : diâmetro do pino (mm)
        h0_mm    : altura disponível na seção do apoio (mm)
        theta_deg: ângulo força–fibras (para distâncias mínimas)
        L_max_mm : comprimento máximo da ligação ao longo da viga (mm)
                   — critério de detalhamento (não EC5); default 1,8 m
                   (η_alvo≤0,75 com d=36 exige ~1,62 m em layout 8×8)

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
    eta_alvo: float = 0.75,
    L_max_mm: float = 1800.0,
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
    eta_alvo: margem de projeto (uso público) — R ≥ F_res / eta_alvo.
              EC5 exige η ≤ 1,0; o alvo 0,75 é critério de projeto.
    L_max_mm: comprimento máximo da chapa ao longo da viga (detalhamento).
    """
    _validar_diametro_cavilha(d_mm)   # EC5 §8.6(2): 6–30 mm (issue 18)
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
    # Capacidade mínima de projeto (margem)
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

    # Módulo de deslizamento K_ser — EC5 §7.1 Tab. 7.1 (cavilha): ρ_m^1,5·d/23
    K_ser_pino = mat.rho_mean ** 1.5 * d_mm / 23.0   # N/mm (por pino, por plano)

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
                h0_mm=h0_mm, theta_deg=theta_deg, L_max_mm=L_max_mm,
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
                    h0_mm=h0_mm, theta_deg=theta_deg, L_max_mm=L_max_mm,
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
                h0_mm=h0_mm, theta_deg=theta_deg, L_max_mm=L_max_mm,
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
        # ── Memória de Johansen (issue 29) ──────────────────────
        "f_h0k_MPa":     joh["f_hk_MPa"],                # EC5 §8.5.1.1 Eq. 8.32
        "M_y_Rk_Nmm":    joh["M_y_Nmm"],                 # EC5 §8.5.1.1 Eq. 8.30
        "modo_I_kN":     round(joh["modo_I_N"]/1e3,   3),  # esmagamento madeira
        "modo_IIIb_kN":  round(joh["modo_IIIb_N"]/1e3, 3), # 1 rótula plástica
        "modo_IV_kN":    round(joh["modo_IV_N"]/1e3,  3),  # 2 rótulas plásticas
        "F_v_Rk_plano_kN": round(joh["F_v_Rk_N"]/1e3, 3),  # min dos modos (1 plano)
        "n_planos_corte": 2,
        # Espessuras e distâncias (EC5 §8.3 Tab. 8.4)
        "t1_madeira_mm": round(t_mm,           1),       # t₁ = b/2 (cada lado)
        "a3t_mm":        dist["a3t_mm"],                 # extremo carregado
        "a4t_mm":        dist["a4t_mm"],                 # borda lateral
        # Módulo de deslizamento (EC5 §7.1 Tab. 7.1)
        "K_ser_Nmm":     round(K_ser_pino, 1),           # por pino, por plano
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
        "d_norma_ok":    D_CAVILHA_MIN_MM <= d_mm <= D_CAVILHA_MAX_MM,
        "d_faixa_mm":    (D_CAVILHA_MIN_MM, D_CAVILHA_MAX_MM),
        "norma":         "EC5 §8.2+§8.5.1.1+§8.6(2) 6–30 mm | γ_M=1,30 | η_alvo projeto",
    }


# ── LIGAÇÃO 3 — Sapata na fundação ───────────────────────────────────────────

# ── Apoio da chapa de base no concreto — EN 1992-1-1 ─────────────────────────

# f_ck (MPa) por classe de resistência — EN 1992-1-1 Tab. 3.1.
F_CK_CLASSE = {
    "C12/15": 12.0, "C16/20": 16.0, "C20/25": 20.0, "C25/30": 25.0,
    "C30/37": 30.0, "C35/45": 35.0, "C40/50": 40.0, "C45/55": 45.0,
    "C50/60": 50.0,
}
ALPHA_CC = 1.0    # EN 1992-1-1 §3.1.6(1) — valor recomendado (NDP)
GAMMA_C  = 1.5    # EN 1992-1-1 Tab. 2.1N — valor recomendado (NDP)


def resistencia_apoio_concreto(
    classe_concreto: str,
    k_confinamento: float = 1.0,
) -> dict:
    """
    Resistência de apoio sob a chapa de base — EN 1992-1-1 §3.1.6 e §6.7.

        f_cd  = α_cc · f_ck / γ_C
        f_Rdu = k_conf · f_cd,    com k_conf = √(A_c1/A_c0) ≤ 3,0   (§6.7)

    `k_confinamento` traduz o ganho por área parcialmente carregada: a difusão
    da carga no bloco de concreto permite tensão de apoio superior a f_cd. Esse
    ganho depende das dimensões da SAPATA (A_c1), que este módulo não conhece —
    por isso o default é 1,0, sem ganho. Elevá-lo exige geometria da fundação e
    o cumprimento das regras de difusão de §6.7.
    """
    if classe_concreto not in F_CK_CLASSE:
        raise ValueError(
            f"classe_concreto={classe_concreto!r} desconhecida. "
            f"Opções: {', '.join(sorted(F_CK_CLASSE))}."
        )
    if not (1.0 <= k_confinamento <= 3.0):
        raise ValueError("k_confinamento deve estar em [1,0; 3,0] — §6.7.")
    f_ck = F_CK_CLASSE[classe_concreto]
    f_cd = ALPHA_CC * f_ck / GAMMA_C
    return {
        "classe_concreto": classe_concreto,
        "f_ck_MPa": f_ck,
        "f_cd_MPa": round(f_cd, 3),
        "k_confinamento": k_confinamento,
        "f_Rdu_MPa": round(k_confinamento * f_cd, 3),
        "norma": "EN 1992-1-1 §3.1.6 (f_cd) + §6.7 (área parcialmente carregada)",
    }


def _dimensionar_chapa_base(
    N_d_kN: float,
    b_pilar_m: float,
    h_pilar_m: float,
    f_Rd_MPa: float,
    passo_cm: float = 5.0,
) -> dict:
    """
    Dimensiona a chapa de base e DEPOIS a verifica — sem circularidade.

    A versão anterior fazia `A = N/f_c`, o que forçava σ_c = f_c e portanto
    η ≡ 1,0000 qualquer que fosse a carga ou a resistência: uma tautologia que
    aparecia no memorial como "no limite" e nunca podia reprovar. Pior, no ramo
    sem tirante faltava o piso na área do pilar — com f_cd realista a chapa
    resultava MENOR que o próprio pilar (7,7 cm contra 32×27 cm).

    Agora: área requerida → piso na área do pilar → arredondamento para
    dimensão construtiva → e só então σ_c e η, que passam a ter margem real.
    """
    A_pilar = max(b_pilar_m * h_pilar_m, 1e-6)
    A_req = N_d_kN * 1e3 / (f_Rd_MPa * 1e6) if f_Rd_MPa > 0 else A_pilar
    lado_min_cm = math.sqrt(max(A_req, A_pilar)) * 100.0
    # Dimensão construtiva: múltiplo de `passo_cm` para cima.
    lado_cm = math.ceil(lado_min_cm / passo_cm) * passo_cm
    A_chapa = (lado_cm / 100.0) ** 2
    sigma_c = N_d_kN * 1e3 / (A_chapa * 1e6)
    return {
        "A_pilar_m2": round(A_pilar, 6),
        "A_req_m2": round(A_req, 6),
        "A_chapa_m2": A_chapa,
        "A_chapa_cm2": A_chapa * 1e4,
        "lado_chapa_cm": lado_cm,
        "sigma_c_MPa": sigma_c,
        "eta_N": sigma_c / f_Rd_MPa if f_Rd_MPa > 0 else 999.0,
        "governa_chapa": "area_pilar" if A_pilar >= A_req else "resistencia_concreto",
    }


# ── Contrato de verificação de ancoragem — AUD-017 ───────────────────────────

CAMPOS_ANCORAGEM_OBRIGATORIOS = (
    "eta_produto",           # referência do ETA / laudo do chumbador
    "h_ef_mm",               # profundidade efetiva de embutimento
    "c_borda_mm",            # menor distância à borda
    "s_grupo_mm",            # menor espaçamento do grupo
    "classe_concreto",       # p.ex. "C25/30"
    "concreto_fissurado",    # bool — governa k_cr em EN 1992-4
    "verificacao_en1992_4",  # referência do cálculo/relatório que a cumpriu
)


def _ancoragem_completa(dados: dict | None) -> bool:
    """True só quando TODOS os dados exigidos por EN 1992-4/ETA foram dados."""
    if not dados:
        return False
    return all(
        campo in dados and dados[campo] not in (None, "")
        for campo in CAMPOS_ANCORAGEM_OBRIGATORIOS
    )


def _estado_ancoragem(dados: dict | None) -> dict:
    """
    Campos de rastreabilidade da ancoragem.

    A soma linear de capacidades isoladas de chumbador NÃO é a capacidade do
    grupo: cone, pull-out, pry-out, borda, grupo, interação e fissuração do
    concreto governam (EN 1992-4). Sem os dados, o estado é NOT VALIDATED e
    nenhuma aprovação pode ser emitida a partir daqui.
    """
    completo = _ancoragem_completa(dados)
    faltando = [] if completo else [
        c for c in CAMPOS_ANCORAGEM_OBRIGATORIOS
        if not dados or c not in dados or dados[c] in (None, "")
    ]
    return {
        "en_1992_4_verificado":         completo,
        "produto_chumbador_verificado": completo,
        "status_ancoragem":             "VERIFICADO" if completo else "NOT VALIDATED",
        "dados_ancoragem_faltando":     faltando,
        "modos_en_1992_4_pendentes": [] if completo else [
            "cone de arrancamento (concrete cone)",
            "pull-out do chumbador",
            "pry-out sob corte",
            "rotura de borda sob corte (edge breakage)",
            "efeito de grupo e espaçamentos",
            "interação tração-corte",
            "concreto fissurado / não fissurado",
        ],
    }


def dimensionar_sapata(
    load:     Carregamentos,
    geo:      GeometriaViga,
    F_chu_kN: float = 80.0,
    d_chu_mm: float = 20.0,
    eta_alvo: float = 0.75,
    com_tirante: bool = False,
    b_pilar_m: float = 0.32,
    h_pilar_m: float = 0.27,
    f_c_conc_MPa: float | None = None,
    classe_concreto: str = "C25/30",
    k_confinamento: float = 1.0,
    dados_ancoragem: dict | None = None,
) -> dict:
    """
    PRÉ-SELECIONA a quantidade de chumbadores da sapata articulada.

    AUD-017 — ESTA FUNÇÃO NÃO VERIFICA A ANCORAGEM. Ela escolhe uma quantidade
    por `n = ceil(H_d / (F_chu · η_alvo))`, tratando a capacidade como a soma
    linear de capacidades isoladas. A capacidade real de uma ancoragem no
    concreto NÃO é essa soma: é governada por modos de rotura que dependem de
    geometria e substrato — cone de arrancamento, pull-out, pry-out, efeito de
    grupo, distância às bordas, interação tração/corte e fissuração do concreto
    (EN 1992-4), além dos dados certificados do produto (ETA).

    Enquanto `dados_ancoragem` não for fornecido, o resultado sai com
    `en_1992_4_verificado=False`, `produto_chumbador_verificado=False` e
    `status="NOT VALIDATED"`, e `ok` é forçado a False — a pré-seleção não pode
    valer como aprovação. Para declarar a verificação cumprida, forneça:

        dados_ancoragem = {
            "eta_produto": "<referência do ETA/laudo do chumbador>",
            "h_ef_mm": ..., "c_borda_mm": ..., "s_grupo_mm": ...,
            "classe_concreto": "C25/30", "concreto_fissurado": True/False,
            "verificacao_en1992_4": "<referência do cálculo/relatório externo>",
        }

    Todos esses campos são obrigatórios: faltando qualquer um, o estado
    permanece NOT VALIDATED.

    Esforços (biarticulada):
        N_d = V_max_ELU  (compressão vertical do pilar)
        H_arco = H_ELU   (empuxo Castigliano do pórtico)
        M_d = 0          (rótula)

    Sem tirante (com_tirante=False):
        H_d = H_arco → chumbadores ao cisalhamento
        η = η_H (com margem eta_alvo)

    Com tirante ao nível do piso (com_tirante=True):
        H_d ≈ 0 na sapata (H absorvido pelo tirante)
        chumbadores: mínimo construtivo (4×)
        η = η_N compressão no concreto sob a chapa (como L3c)

    Args:
        load, geo, F_chu_kN, d_chu_mm, eta_alvo
        com_tirante : se True, H_sapata≈0
        b_pilar_m, h_pilar_m, f_c_conc_MPa : para η_N com tirante

    Returns:
        dict com H_arco, H_d, n_chu, η e ok
    """
    if eta_alvo <= 0 or eta_alvo > 1.0:
        raise ValueError("eta_alvo deve estar em (0, 1]")

    N_d = load.V_max_ELU()   # kN
    H_arco = load.H_ELU()    # kN — empuxo estrutural do pórtico
    H_d = 0.0 if com_tirante else H_arco

    # ── Chapa de base — compressão N_d sobre o concreto ──────────────────
    # f_c_conc_MPa (legado) mantido apenas para compatibilidade; quando dado,
    # sobrepõe-se a f_Rdu. O valor default antigo era 1,5 MPa, que NÃO é
    # resistência de concreto (C25/30 ⇒ f_cd = 16,7 MPa) — ver nota do módulo.
    _apoio = resistencia_apoio_concreto(classe_concreto, k_confinamento)
    f_Rd_MPa = float(f_c_conc_MPa) if f_c_conc_MPa else _apoio["f_Rdu_MPa"]
    _chapa = _dimensionar_chapa_base(N_d, b_pilar_m, h_pilar_m, f_Rd_MPa)
    A_pilar_m2  = _chapa["A_pilar_m2"]
    A_chapa_m2  = _chapa["A_chapa_m2"]
    A_chapa_cm2 = _chapa["A_chapa_cm2"]
    lado_chapa  = _chapa["lado_chapa_cm"]
    sigma_c_MPa = _chapa["sigma_c_MPa"]
    eta_N       = _chapa["eta_N"]

    if com_tirante:
        n_chu = 4
        n_chu_eta1 = 4
        n_chu_x4 = 4
        R_chu_kN = n_chu * F_chu_kN
        eta_H = 0.0
        eta_H_x4 = 0.0
        eta = eta_N
        ok_norma = eta_N <= 1.0 + 1e-9
        ok_alvo = ok_norma  # margem eta_alvo aplica-se ao tirante, não a H
        nota = (
            f"Com tirante de base: H_arco={H_arco:.1f} kN absorvido pelo tirante; "
            f"H_sapata≈0. Chumbadores n={n_chu} construtivos. "
            f"η=η_N compressão no concreto (N={N_d:.1f} kN, "
            f"σ={sigma_c_MPa:.2f} MPa)."
        )
        ligacao = "L3 — Sapata (com tirante de base, H≈0)"
    else:
        # Mínimo construtivo de 4 chumbadores (um por canto da chapa de base) —
        # garante a ancoragem ao UPLIFT mesmo quando H_d≈0 (Opção B: sem empuxo).
        # Sem esse piso, H_d=0 daria n=1 e a verificação de sucção (que consome
        # este n_chu) ficaria sem ancoragem (issue 35/38).
        n_chu = max(4, math.ceil(H_d / (F_chu_kN * eta_alvo))) if F_chu_kN > 0 else 4
        n_chu_eta1 = max(1, math.ceil(H_d / F_chu_kN)) if F_chu_kN > 0 else 1
        R_chu_kN = n_chu * F_chu_kN
        eta_H = H_d / R_chu_kN if R_chu_kN > 0 else 0.0
        n_chu_x4 = n_chu if n_chu % 4 == 0 else n_chu + (4 - n_chu % 4)
        eta_H_x4 = H_d / (n_chu_x4 * F_chu_kN) if F_chu_kN > 0 else 0.0
        eta = eta_H
        ok_norma = eta_H <= 1.0
        ok_alvo = eta_H <= eta_alvo + 1e-9
        nota = (
            f"Sem tirante: H_sapata=H_arco={H_d:.1f} kN. "
            f"Chumbadores n={n_chu} (mín. construtivo 4; mín η≤1: {n_chu_eta1}; "
            f"grade ×4: {n_chu_x4}). Ancoragem ao uplift verificada à parte "
            f"(sucção/issue 33). Verificação final EN 1992-4."
        )
        ligacao = "L3 — Sapata na fundação"

    return {
        "ligacao":        ligacao,
        "com_tirante":    com_tirante,
        "N_d_kN":         round(N_d,          3),
        "H_arco_kN":      round(H_arco,       3),
        "H_d_kN":         round(H_d,          3),
        "d_chu_mm":       d_chu_mm,
        "F_chu_kN":       F_chu_kN,
        "n_chumbadores":  n_chu,
        "n_chu_eta1":     n_chu_eta1,
        "n_chu_x4":       n_chu_x4,
        "R_chu_kN":       round(R_chu_kN,     1),
        "eta_alvo":       eta_alvo,
        "eta_H":          round(eta_H,         4),
        "eta_H_x4":       round(eta_H_x4,      4),
        "eta_N":          round(eta_N,         4),
        "sigma_c_MPa":    round(sigma_c_MPa,   4),
        "A_chapa_cm2":    round(A_chapa_cm2,  2),
        "lado_chapa_cm":  round(lado_chapa,   1),
        "eta":            round(eta,           4),
        "ok_alvo":        ok_alvo,
        # ── Contrato de ancoragem — AUD-017 ──────────────────────────────
        **_estado_ancoragem(dados_ancoragem),
        "classe_concreto": _apoio["classe_concreto"],
        "f_cd_MPa":        _apoio["f_cd_MPa"],
        "f_Rdu_MPa":       round(f_Rd_MPa, 3),
        "k_confinamento":  k_confinamento,
        "governa_chapa":   _chapa["governa_chapa"],
        "ok":             (ok_norma and ok_alvo
                           and _ancoragem_completa(dados_ancoragem)),
        "ok_pre_selecao": ok_norma and ok_alvo,
        "norma":          "EN 1993-1-8 | pré-seleção; verificação por EN 1992-4",
        "nota":           nota,
    }


# ── Dimensionamento completo ──────────────────────────────────────────────────

def dimensionar_ligacoes(
    mat:   GlulamMaterial,
    load:  Carregamentos,
    geo:   GeometriaViga,
    d_base_mm:    float = 20.0,
    F_chu_kN:     float = 80.0,
    eta_alvo:     float = 0.75,
    com_tirante:  bool = False,
    b_pilar_m:    float = 0.32,
    h_pilar_m:    float = 0.27,
) -> dict:
    """
    Dimensiona as ligações do pórtico (biarticulada): L1 (base) e L3 (sapata).

    Não há ligação na CUMEEIRA: a viga é peça única de duplo-bisel, contínua
    no ápice (sem junta). O antigo L2 (pino passante) era resquício do modelo
    triarticulado e foi removido (issue 25). A cumeeira é verificada como
    SEÇÃO (t90/ápice §6.4.3 — checks/elu/cumeeira.py).

    eta_alvo: margem de projeto para L1 e L3 (uso público).
    com_tirante: se True, L3 com H_sapata≈0 (empuxo no tirante de base).
    """
    L1 = dimensionar_ligacao_base(
        mat, load, geo, d_mm=d_base_mm, eta_alvo=eta_alvo,
    )
    L3 = dimensionar_sapata(
        load, geo, F_chu_kN=F_chu_kN, eta_alvo=eta_alvo,
        com_tirante=com_tirante,
        b_pilar_m=b_pilar_m, h_pilar_m=h_pilar_m,
    )

    eta_gov = max(L1["eta"], L3["eta"])
    lig_gov = "L1 base" if L1["eta"] >= L3["eta"] else "L3 sapata"

    return {
        "L1": L1,
        "L3": L3,
        "eta":     round(eta_gov, 4),
        "ok":      L1["ok"] and L3["ok"],
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
    eta_alvo:  float = 0.75,
) -> dict:
    """
    Ligação viga-pilar central — duas chapas independentes.

    Cada chapa recebe a força de uma viga (mesmos N_d, V_d da lateral).
    Espessura de madeira por lado = b_pilar_c/2 (chapa embutida no pilar).
    """
    _validar_diametro_cavilha(d_mm)   # EC5 §8.6(2): 6–30 mm (issue 18)
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
                h0_mm=h0_mm, theta_deg=theta_deg, L_max_mm=1800.0,
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
    classe_concreto: str = "C25/30",
    k_confinamento: float = 1.0,
    b_pilar_m: float = 0.32,
    h_pilar_m: float = 0.27,
    f_c_conc_MPa: float | None = None,
) -> dict:
    """
    Sapata do pilar central — empuxo horizontal nulo por simetria.

    Esforços:
        N_d = 2 × R_v   (dois pórticos compartilham o pilar central)
        H_d ≈ 0         (empuxos dos dois vãos cancelam-se)

    Verificações:
        1) Compressão no concreto sob a chapa (EN 1992-4 / apoio localizado
           simplificado): σ = N / A_contato ≤ f_c,conc
           A_contato = área do topo do pilar (ou chapa ≥ pilar).
        2) Chumbadores: só mínimo construtivo (4×M20) — sem H de cálculo.
           eta_H = 0 porque H_d = 0 (não significa “sem carga na sapata”).

    η reportado = η_N (compressão) — o valor relevante; eta_H fica
    documentado à parte para não confundir com η=0 “vazio”.
    """
    import math
    N_d = 2 * load.V_max_ELU()   # kN
    H_d = 0.0                     # kN — cancelamento simétrico

    # Chapa de base — mesmo critério de L3 (EN 1992-1-1 §3.1.6 + §6.7)
    _apoio = resistencia_apoio_concreto(classe_concreto, k_confinamento)
    f_Rd_MPa = float(f_c_conc_MPa) if f_c_conc_MPa else _apoio["f_Rdu_MPa"]
    _chapa = _dimensionar_chapa_base(N_d, b_pilar_m, h_pilar_m, f_Rd_MPa)
    A_pilar_m2  = _chapa["A_pilar_m2"]
    A_chapa_m2  = _chapa["A_chapa_m2"]
    lado_cm     = _chapa["lado_chapa_cm"]
    chapa_alargada = _chapa["governa_chapa"] == "resistencia_concreto"
    sigma_c_MPa = _chapa["sigma_c_MPa"]
    eta_N       = _chapa["eta_N"]

    n_chu_min = 4   # construtivo — sem esforço horizontal de projeto
    eta_H = 0.0     # H_d = 0 (não confundir com “sapata sem carga”)

    eta = eta_N
    ok = eta_N <= 1.0 + 1e-9

    return {
        "ligacao":         "L3c — Sapata central (H≈0, N=2·R_v)",
        "N_d_kN":          round(N_d, 3),
        "H_d_kN":          0.0,
        "d_chu_mm":        d_chu_mm,
        "n_chumbadores":   n_chu_min,
        "nota_chu":        "Mínimo construtivo 4× — H_d≈0 (empuxos cancelam)",
        "b_pilar_m":       b_pilar_m,
        "h_pilar_m":       h_pilar_m,
        "A_pilar_cm2":     round(A_pilar_m2 * 1e4, 1),
        "A_chapa_cm2":     round(A_chapa_m2 * 1e4, 1),
        "lado_chapa_cm":   round(lado_cm, 1),
        "chapa_alargada":  chapa_alargada,
        "f_c_conc_MPa":    f_c_conc_MPa,
        "sigma_c_MPa":     round(sigma_c_MPa, 4),
        "eta_N":           round(eta_N, 4),
        "eta_H":           eta_H,
        "eta":             round(eta, 4),
        "ok":              ok,
        "norma":           "EN 1993-1-8 + EN 1992-4 (apoio localizado simplificado)",
        "nota": (
            "H_d≈0: empuxos dos dois vãos cancelam no pilar central "
            "(eta_H=0 não significa sapata sem carga). "
            f"η=η_N compressão no concreto sob a chapa "
            f"(N={N_d:.1f} kN, σ={sigma_c_MPa:.2f} MPa, "
            f"A_chapa={A_chapa_m2*1e4:.0f} cm²"
            + (", chapa alargada face ao pilar" if chapa_alargada else "")
            + ")."
        ),
    }


def dimensionar_ligacoes_central(
    mat:   GlulamMaterial,
    load:  Carregamentos,
    geo:   GeometriaViga,
    b_pilar_c: float = 0.26,
    h_pilar_c: float = 0.26,
    d_base_mm: float = 20.0,
    eta_alvo:  float = 0.75,
) -> dict:
    """
    Dimensiona as ligações do pilar central compartilhado: L1c e L3c.

    Sem ligação na cumeeira (peça monolítica contínua no ápice — issue 25);
    o antigo L2c (pino) foi removido. Cumeeira verificada como SEÇÃO (t90/ápice).

    L1c: viga-pilar — 2 chapas independentes, mesma força que lateral
    L3c: sapata — H≈0; η = compressão N no concreto (não eta_H=0)
    """
    L1c = dimensionar_ligacao_base_central(
        mat, load, geo, b_pilar_c, d_base_mm, eta_alvo=eta_alvo,
    )
    L3c = dimensionar_sapata_central(
        load, geo, d_chu_mm=20.0,
        b_pilar_m=b_pilar_c, h_pilar_m=h_pilar_c,
    )

    eta_gov = max(L1c["eta"], L3c["eta"])
    lig_gov = "L1c base" if L1c["eta"] >= L3c["eta"] else "L3c sapata"

    return {
        "L1c": L1c,
        "L3c": L3c,
        "eta":     round(eta_gov, 4),
        "ok":      L1c["ok"] and L3c["ok"],
        "lig_gov": lig_gov,
    }


# ── Relatório ─────────────────────────────────────────────────────────────────

def relatorio_ligacoes(res: dict) -> None:
    """Imprime relatório completo das três ligações."""
    print("=" * 70)
    print("  LIGAÇÕES DO PÓRTICO DE 3 RÓTULAS")
    print("  EC5 §8.2+§8.3+§8.6 | EC5 §6.1.4+§6.1.5 | EN 1993-1-8")
    print("=" * 70)

    for key in ["L1", "L3"]:
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