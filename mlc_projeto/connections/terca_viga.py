"""
connections/terca_viga.py — Ligação terça–viga (issue 43).

A terça apoia-se por contato sobre o extradorso da viga; a gravidade vai por
contato. A ligação recebe o que o contato não transmite:

  · o ARRANCAMENTO de sucção da cobertura (reação de cada extremidade da terça
    biapoiada entre pórticos);
  · a força de CONTENÇÃO lateral da viga, EC5 §9.2.5.2 (ao longo da terça);
  · o cisalhamento do DIAFRAGMA, que leva o vento perpendicular às cumeeiras aos
    frontões (ao longo da viga);
  · nas baías contraventadas, a força de MONTANTE da treliça da cobertura, que
    chega pela terça ao nó das diagonais.

Junta corrente — parafusos autoatarraxantes de rosca total, inseridos pelas
faces laterais da terça a 45° e cruzados em pares, ancorados no extradorso da
viga. Resistência axial pelo EC5 §8.7.2 (EN 1995-1-1:2004+A1:2008, Eq. 8.38 e
8.40a), lateral pelo §8.7.1 com Johansen (§8.2.2, Eq. 8.6, sem efeito de corda)
e interação pelo §8.7.3 (Eq. 8.28). A resistência à tração do aço, o diâmetro
de núcleo e o momento de plastificação são DADOS DE CATÁLOGO — declarados aqui e
a confirmar com a avaliação técnica do produto, como o fixador da telha.

Junta de montante (baías rígidas) — chapa metálica no nó, embutida na terça
com cavilhas paralelas às fibras, mesmo detalhe das escoras (issue 66).
"""

from __future__ import annotations

import math

from mlc_projeto.checks.elu.no_contraventamento import dimensionar_ligacao_axial_escora
from mlc_projeto.core.materials import GlulamMaterial

# Parafuso autoatarraxante de rosca total — dados de CATÁLOGO declarados
D_PARAF_MM = 8.0          # diâmetro nominal (diâmetro externo da rosca)
D_NUCLEO_MM = 5.4         # diâmetro de núcleo
F_TENS_K_KN = 20.0        # resistência característica à tração do aço
M_Y_RK_NMM = 20_000.0     # momento de plastificação característico
L_EF_MM = 120.0           # penetração efetiva da rosca em cada peça
INCLINACAO_DEG = 45.0     # ângulo do parafuso com a vertical
GAMMA_M_LIG = 1.30        # EC5 Tab. 2.3 — ligações
GAMMA_M2 = 1.25           # tração do aço do parafuso
ETA_ALVO = 0.75           # modo frágil (arrancamento em madeira)


def f_ax_k(d: float, l_ef: float, rho_k: float) -> float:
    """EC5 Eq. 8.39 (A1:2008): resistência ao arrancamento, N/mm²."""
    return 0.52 * d ** -0.5 * l_ef ** -0.1 * rho_k ** 0.8


def F_ax_Rk(d: float, l_ef: float, rho_k: float, alpha_fibras_deg: float) -> float:
    """EC5 Eq. 8.38 (A1:2008), um parafuso, kN: n_ef·f_ax·d·l_ef·k_d/(1,2cos²α+sen²α)."""
    a = math.radians(alpha_fibras_deg)
    k_d = min(d / 8.0, 1.0)
    return (f_ax_k(d, l_ef, rho_k) * d * l_ef * k_d
            / (1.2 * math.cos(a) ** 2 + math.sin(a) ** 2) / 1e3)


def F_v_Rk_madeira_madeira(d_ef: float, t1: float, t2: float, rho_k: float,
                           M_y: float) -> float:
    """EC5 Eq. 8.6, corte simples madeira–madeira, sem efeito de corda, kN.
    f_h para pinos d ≤ 6 mm sem pré-furação (§8.3.1): 0,082·ρ_k·d^−0,3."""
    fh = 0.082 * rho_k * d_ef ** -0.3
    b = 1.0                                             # f_h,2/f_h,1 (mesmo material)
    modos = (
        fh * t1 * d_ef,
        fh * t2 * d_ef,
        fh * t1 * d_ef / (1 + b) * (math.sqrt(b + 2 * b ** 2 * (1 + t2 / t1 + (t2 / t1) ** 2)
                                              + b ** 3 * (t2 / t1) ** 2) - b * (1 + t2 / t1)),
        1.05 * fh * t1 * d_ef / (2 + b) * (math.sqrt(2 * b * (1 + b)
                                                     + 4 * b * (2 + b) * M_y / (fh * d_ef * t1 ** 2)) - b),
        1.05 * fh * t2 * d_ef / (1 + 2 * b) * (math.sqrt(2 * b ** 2 * (1 + b)
                                                         + 4 * b * (1 + 2 * b) * M_y / (fh * d_ef * t2 ** 2)) - b),
        1.15 * math.sqrt(2 * b / (1 + b)) * math.sqrt(2 * M_y * fh * d_ef),
    )
    return min(modos) / 1e3


def espacamentos_parafusos(d: float) -> dict:
    """EC5 Tab. 8.6 (A1:2008) — parafusos solicitados axialmente."""
    return {"a1_mm": 7.0 * d, "a2_mm": 5.0 * d, "a1_CG_mm": 10.0 * d,
            "a2_CG_mm": 4.0 * d}


def verificar_ligacao_terca_viga(
    *,
    mat:            GlulamMaterial,
    w_suc_k_kNm2:   float,
    g_k_terca_kNm2: float,
    s_terca_m:      float,
    L_T_m:          float,
    b_terca_m:      float,
    b_viga_m:       float,
    F_contencao_kN: float,
    H_diafragma_kN: float,
    N_montante_kN:  float,
    h_terca_m:      float,
    gamma_Q:        float = 1.5,
    gamma_G_inf:    float = 0.9,
    d_mm:           float = D_PARAF_MM,
    d_nucleo_mm:    float = D_NUCLEO_MM,
    l_ef_mm:        float = L_EF_MM,
    f_tens_k_kN:    float = F_TENS_K_KN,
    M_y_Rk_Nmm:     float = M_Y_RK_NMM,
) -> dict:
    """Dimensiona a junta corrente (parafusos) e a de montante (cavilhas)."""
    # ── Esforços na extremidade de uma terça biapoiada entre pórticos ─────
    V_up = max((gamma_Q * abs(w_suc_k_kNm2) - gamma_G_inf * g_k_terca_kNm2)
               * s_terca_m * L_T_m / 2.0, 0.0)              # arrancamento
    H_viga = float(H_diafragma_kN)                           # ao longo da viga
    H_terca = float(F_contencao_kN)                          # ao longo da terça

    # ── Resistências de um parafuso ───────────────────────────────────────
    inc = math.radians(INCLINACAO_DEG)
    rho = mat.rho_k
    # parafuso no plano vertical que contém o eixo da VIGA: 45° com as fibras da
    # viga e 90° com as da terça
    R_ax_k = min(F_ax_Rk(d_mm, l_ef_mm, rho, 45.0), F_ax_Rk(d_mm, l_ef_mm, rho, 90.0))
    R_ax_d = min(mat.k_mod * R_ax_k / GAMMA_M_LIG, f_tens_k_kN / GAMMA_M2)
    d_ef = 1.1 * d_nucleo_mm                                 # §8.7.1(3)
    R_v_d = mat.k_mod * F_v_Rk_madeira_madeira(d_ef, l_ef_mm, l_ef_mm, rho,
                                               M_y_Rk_Nmm) / GAMMA_M_LIG

    # ── Geometria: as terças são biapoiadas e se encontram sobre a viga; cada
    # extremidade dispõe de meia largura da viga. Os parafusos de uma face ficam
    # numa única posição ao longo da terça, empilhados na vertical: na terça o
    # passo é ⊥ às fibras (a2) e, na viga, vira passo // às fibras (a1) a 45°.
    esp = espacamentos_parafusos(d_mm)
    meia = b_viga_m * 1000 / 2.0
    # posição ao longo da terça: ≥ a1,CG da extremidade da terça (topo) e
    # ≥ a2,CG da face lateral da viga → centro do intervalo admissível
    # as duas faces ficam deslocadas de ±2d ao longo da terça, para que os
    # parafusos cruzados não se encontrem
    desloc = 2.0 * d_mm
    x_min, x_max = esp["a1_CG_mm"] + desloc, meia - esp["a2_CG_mm"] - desloc
    x_p = (x_min + x_max) / 2.0
    passo_v = max(esp["a1_mm"], esp["a2_mm"])               # vertical, na face
    n_face_max = int((h_terca_m * 1000 - 2 * esp["a2_CG_mm"] - l_ef_mm) // passo_v) + 1
    escolha = None
    for n_face in range(1, max(n_face_max, 1) + 1):
        n = 2 * n_face                                       # duas faces, cruzados
        fef = n ** 0.9 / n                                   # n_ef = n^0,9 (§8.7.2(8))
        # axial: arrancamento em todos; o diafragma tensiona metade (um sentido)
        F_ax = V_up / (n * math.cos(inc)) + H_viga / (n / 2 * math.sin(inc))
        eta_ax = F_ax / (R_ax_d * fef)
        # lateral: contenção ao longo da terça, ⊥ ao plano dos parafusos
        F_v = H_terca / n
        eta_v = F_v / R_v_d if R_v_d > 0 else 999.0
        eta = eta_ax ** 2 + eta_v ** 2                       # §8.7.3 Eq. 8.28
        escolha = dict(n=n, n_face=n_face, F_ax=F_ax, eta_ax=eta_ax, F_v=F_v,
                       eta_v=eta_v, eta=eta)
        if eta <= ETA_ALVO:
            break
    corrente = {
        "d_mm": d_mm, "d_nucleo_mm": d_nucleo_mm, "l_ef_mm": l_ef_mm,
        "inclinacao_deg": INCLINACAO_DEG, "n_parafusos": escolha["n"],
        "n_por_face": escolha["n_face"],
        "R_ax_d_kN": round(R_ax_d, 2), "R_v_d_kN": round(R_v_d, 2),
        "F_ax_kN": round(escolha["F_ax"], 2), "F_v_kN": round(escolha["F_v"], 2),
        "eta_axial": round(escolha["eta_ax"], 4), "eta_lateral": round(escolha["eta_v"], 4),
        "eta": round(escolha["eta"], 4),
        "ok": escolha["eta"] <= ETA_ALVO + 1e-9 and x_min <= x_max,
        "espacamentos_req": esp,
        "geometria_ok": x_min <= x_max and escolha["n_face"] <= n_face_max,
        # adotados (issue 43): passo vertical na face, distâncias do centróide
        "passo_vertical_mm": round(passo_v, 1),
        "deslocamento_faces_mm": round(desloc, 1),
        "x_p_mm": round(x_p, 1),
        "a1_CG_adotado_mm": round(x_p - desloc, 1),          # à extremidade da terça
        "a2_CG_viga_adotado_mm": round(meia - x_p - desloc, 1),  # à face lateral da viga
        "a2_CG_terca_adotado_mm": round(esp["a2_CG_mm"], 1),  # às faces sup./inf.
        "declarados": {"f_tens_k_kN": f_tens_k_kN, "M_y_Rk_Nmm": M_y_Rk_Nmm,
                       "d_nucleo_mm": d_nucleo_mm},
    }
    # ── Junta de montante nas baías contraventadas ────────────────────────
    montante = dimensionar_ligacao_axial_escora(
        F_Ed_kN=float(N_montante_kN), mat=mat, b_m=b_terca_m, h_m=h_terca_m,
        d_mm=20.0, rotulo="terça–viga, montante da treliça",
    )
    gov = "corrente" if corrente["eta"] >= montante["eta"] else "montante"
    return {
        "V_up_kN": round(V_up, 2), "H_viga_kN": round(H_viga, 2),
        "H_terca_kN": round(H_terca, 2), "N_montante_kN": round(float(N_montante_kN), 2),
        "corrente": corrente, "montante": montante,
        "eta": round(max(corrente["eta"], montante["eta"]), 4), "governa": gov,
        "ok": bool(corrente["ok"] and montante["ok"]),
        "norma": "EC5 §8.7.2/§8.7.1/§8.7.3/§8.2.2 + Tab. 8.6; §8.2.3/§8.5.1.1 (montante)",
    }
