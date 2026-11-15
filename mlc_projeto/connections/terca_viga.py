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

Emenda da corda (issue 91) — as terças são biapoiadas entre pórticos, de modo que
a terça de beiral, corda do diafragma, tem uma junta sobre CADA viga intermediária
(n_eixos − 2 por linha), e não emendas a cada barra comercial. A continuidade é
dada por uma chapa embutida em rasgo SUPERIOR das duas terças, atravessando a
junta, com cavilhas Ø20 paralelas às fibras de cada lado.

Rasgo superior (issue 91) — os parafusos a 45° da junta corrente atravessam o
plano médio da terça entre as alturas z_inf e z_sup; a chapa do montante e a da
emenda ficam num rasgo aberto pelo topo, que não pode descer abaixo de z_sup mais
uma folga. Isso limita as fileiras de cavilhas na altura (n_vert e D⊥).
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
L_EF_MM = 160.0           # penetração efetiva da rosca em cada peça (≈ 340 mm de parafuso)
INCLINACAO_DEG = 45.0     # ângulo do parafuso com a vertical
GAMMA_M_LIG = 1.30        # EC5 Tab. 2.3 — ligações
GAMMA_M2 = 1.25           # tração do aço do parafuso
ETA_ALVO = 0.75           # modo frágil (arrancamento em madeira)
D_CAVILHA_JUNTA_MM = 20.0  # cavilhas do montante e da emenda da corda
FOLGA_RASGO_PARAF_MM = 10.0  # entre o fundo do rasgo e o parafuso a 45° mais alto
FUNDO_RASGO_MM = 5.0       # folga entre a borda inferior da chapa e o fundo do rasgo


def rasgo_superior(corrente: dict, *, b_terca_mm: float, h_terca_mm: float,
                   d_cav_mm: float = D_CAVILHA_JUNTA_MM) -> dict:
    """
    Profundidade máxima do rasgo superior e D⊥ admissível das cavilhas (issue 91).

    O parafuso k entra na face a z_k = a2,CG + l_ef·cos45° + k·passo e cruza o
    plano médio b_t/2 mais abaixo (45°). A chapa precisa de a4,c = 3d acima da
    fileira superior (borda carregada da madeira, topo) e de e2 = 1,2·d0 abaixo
    da inferior (borda da chapa, EN 1993-1-8 Tab. 3.3), mais a folga do fundo.
    """
    c45 = math.cos(math.radians(INCLINACAO_DEG))
    y0 = corrente["a2_CG_terca_adotado_mm"] + corrente["l_ef_mm"] * c45
    z_ent = [y0 + k * corrente["passo_vertical_mm"] for k in range(corrente["n_por_face"])]
    z_sup = max(z_ent) - b_terca_mm / 2.0 + corrente["d_mm"] / 2.0
    z_inf = min(z_ent) - b_terca_mm / 2.0 - corrente["d_mm"] / 2.0
    prof_max = h_terca_mm - z_sup - FOLGA_RASGO_PARAF_MM
    d0 = d_cav_mm + 1.0
    a4c, e2 = 3.0 * d_cav_mm, math.ceil(1.2 * d0)
    D_perp_max = prof_max - a4c - e2 - FUNDO_RASGO_MM
    return {"z_cruzamento_sup_mm": round(z_sup, 1), "z_cruzamento_inf_mm": round(z_inf, 1),
            "profundidade_max_mm": round(prof_max, 1), "a4c_mm": a4c, "e2_chapa_mm": e2,
            "D_perp_max_mm": round(max(D_perp_max, 0.0), 1),
            # a2 mínimo das cavilhas = 3d (EC5 Tab. 8.5)
            "n_vert_max": 1 + int(max(D_perp_max, 0.0) // (3.0 * d_cav_mm))}


def junta_rasgo_superior(lig: dict, rasgo: dict) -> dict:
    """Geometria da chapa no rasgo superior a partir da malha adotada."""
    D = (lig["n_vert"] - 1) * lig["a2_mm"]
    h_chapa = rasgo["a4c_mm"] + D + rasgo["e2_chapa_mm"]
    prof = h_chapa + FUNDO_RASGO_MM
    L_lado = lig["a3t_mm"] + (lig["n_horiz"] - 1) * lig["a1_mm"] + 2.0 * lig["d_mm"]
    return {"h_chapa_mm": h_chapa, "profundidade_rasgo_mm": prof,
            "L_chapa_mm": 2.0 * L_lado, "cabe": prof <= rasgo["profundidade_max_mm"] + 1e-9}


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


def fef_final(n: int) -> float:
    """n_ef/n para parafusos axiais em grupo, EC5 §8.7.2(8): n^0,9/n."""
    return n ** 0.9 / n


def verificar_garfo_terca(*, mat: GlulamMaterial, w_suc_k_kNm2: float,
                          g_k_terca_kNm2: float, s_terca_m: float, L_T_m: float,
                          b_terca_m: float, h_terca_m: float, n_face: int,
                          R_ax_d_kN: float, F_ax_kN: float, gamma_Q: float = 1.5,
                          gamma_G_inf: float = 0.9, gamma_G_sup: float = 1.35,
                          q_k_m2: float = 0.40, k_f2: float = 80.0) -> dict:
    """
    Contenção à torção da terça no apoio (apoio em garfo) — issue 77.

    A verificação da terça e a sua flambagem lateral pressupõem apoio em garfo.
    Sob gravidade o banzo comprimido (superior) é contido pela telha; sob sucção,
    o inferior fica livre entre pórticos: l_ef = 0,9·L_T (EC5 Tab. 6.1),
    σ_m,crit = 0,78·b²·E0,05/(h·l_ef) (Eq. 6.32), k_crit (Eq. 6.34).

    Força de contenção no apoio, EC5 §9.2.5.2(2)–(3): F_d = N_d/k_f,2 (MLC), com
    N_d = (1 − k_crit)·M_d/h; adota-se o limite superior k_crit = 0, que dá o
    momento de torção no garfo M_tor = F_d·h = M_d/k_f,2 (= M_d/80).

    Resistência: a terça tomba em torno da aresta inferior; os parafusos da face
    oposta, a 45°, resistem com braço b_t — tração adicional por parafuso
    ΔF = M_tor/(n_face·b_t·cos 45°), somada à do arrancamento (interação axial).
    """
    import math
    b, h = b_terca_m, h_terca_m
    M_suc = max(gamma_Q * abs(w_suc_k_kNm2) - gamma_G_inf * g_k_terca_kNm2, 0.0) \
        * s_terca_m * L_T_m ** 2 / 8.0
    M_grav = (gamma_G_sup * g_k_terca_kNm2 + gamma_Q * q_k_m2) * s_terca_m * L_T_m ** 2 / 8.0
    l_ef = 0.9 * L_T_m
    s_crit = 0.78 * b ** 2 * mat.E0_05 / (h * l_ef)
    lam = math.sqrt(mat.f_m_k / s_crit)
    k_crit = 1.0 if lam <= 0.75 else (1.56 - 0.75 * lam if lam <= 1.4 else 1.0 / lam ** 2)
    W = b * h ** 2 / 6.0
    eta_ltb = M_suc * 1e3 / W / (k_crit * mat.f_m_d)
    M_d = max(M_suc, M_grav)
    M_tor = M_d / k_f2                                           # kN·m
    dF = M_tor / (n_face * b * math.cos(math.radians(45.0)))     # kN por parafuso
    eta_ax = (F_ax_kN + dF) / R_ax_d_kN
    eta = max(eta_ax ** 2, eta_ltb)            # Eq. 8.28 (parcela axial) e flambagem
    return {
        "M_d_succao_kNm": round(M_suc, 2), "M_d_gravidade_kNm": round(M_grav, 2),
        "l_ef_m": round(l_ef, 3), "lambda_rel_m": round(lam, 3), "k_crit": round(k_crit, 3),
        "eta_ltb_succao": round(eta_ltb, 4),
        "M_tor_kNm": round(M_tor, 3), "dF_parafuso_kN": round(dF, 3),
        "eta_axial_com_torcao": round(eta_ax, 4),
        "eta": round(eta, 4), "ok": eta <= ETA_ALVO + 1e-9,
        "norma": "EC5 §6.3.3 (Tab. 6.1, Eq. 6.32–6.34) + §9.2.5.2 (k_f,2) + §8.7.2",
    }


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
    N_corda_kN:     float = 0.0,
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
    # torção do apoio em garfo (issue 77): M_tor = M_d/k_f,2, resistida pelos
    # parafusos da face oposta, a 45°, com braço b_t
    M_tor = verificar_garfo_terca(
        mat=mat, w_suc_k_kNm2=w_suc_k_kNm2, g_k_terca_kNm2=g_k_terca_kNm2,
        s_terca_m=s_terca_m, L_T_m=L_T_m, b_terca_m=b_terca_m, h_terca_m=h_terca_m,
        n_face=1, R_ax_d_kN=1.0, F_ax_kN=0.0, gamma_Q=gamma_Q, gamma_G_inf=gamma_G_inf,
    )["M_tor_kNm"]
    escolha = None
    for n_face in range(1, max(n_face_max, 1) + 1):
        n = 2 * n_face                                       # duas faces, cruzados
        fef = n ** 0.9 / n                                   # n_ef = n^0,9 (§8.7.2(8))
        # axial: arrancamento em todos; o diafragma tensiona metade (um sentido);
        # a torção do garfo traciona os da face oposta
        F_ax = (V_up / (n * math.cos(inc)) + H_viga / (n / 2 * math.sin(inc))
                + M_tor / (n_face * b_terca_m * math.cos(inc)))
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
    # ── Apoio em garfo (contenção à torção) — issue 77 ────────────────────
    # registro do garfo: F_ax do laço já inclui a torção (não somar de novo)
    garfo = verificar_garfo_terca(
        mat=mat, w_suc_k_kNm2=w_suc_k_kNm2, g_k_terca_kNm2=g_k_terca_kNm2,
        s_terca_m=s_terca_m, L_T_m=L_T_m, b_terca_m=b_terca_m, h_terca_m=h_terca_m,
        n_face=escolha["n_face"], R_ax_d_kN=R_ax_d * fef_final(escolha["n"]),
        F_ax_kN=escolha["F_ax"] - M_tor / (escolha["n_face"] * b_terca_m * math.cos(inc)),
        gamma_Q=gamma_Q, gamma_G_inf=gamma_G_inf,
    )
    corrente["garfo"] = garfo
    corrente["eta"] = round(max(corrente["eta"], garfo["eta_ltb_succao"]), 4)

    # ── Junta de montante nas baías contraventadas ────────────────────────
    # chapa em rasgo superior, acima dos parafusos a 45° (issue 91)
    rasgo = rasgo_superior(corrente, b_terca_mm=b_terca_m * 1000, h_terca_mm=h_terca_m * 1000)
    _lim = dict(n_vert_limite=rasgo["n_vert_max"], D_perp_max_mm=rasgo["D_perp_max_mm"])
    montante = dimensionar_ligacao_axial_escora(
        F_Ed_kN=float(N_montante_kN), mat=mat, b_m=b_terca_m, h_m=h_terca_m,
        d_mm=D_CAVILHA_JUNTA_MM, rotulo="terça–viga, montante da treliça", **_lim,
        n_chapas=2,
    )
    montante["chapa"] = junta_rasgo_superior(montante, rasgo)
    montante["ok"] = bool(montante["ok"] and montante["chapa"]["cabe"])
    # emenda da corda do diafragma na junta sobre a viga (issue 91)
    emenda = None
    if N_corda_kN > 0:
        emenda = dimensionar_ligacao_axial_escora(
            F_Ed_kN=float(N_corda_kN), mat=mat, b_m=b_terca_m, h_m=h_terca_m,
            d_mm=D_CAVILHA_JUNTA_MM, rotulo="emenda da corda do diafragma", **_lim,
        )
        emenda["chapa"] = junta_rasgo_superior(emenda, rasgo)
        emenda["ok"] = bool(emenda["ok"] and emenda["chapa"]["cabe"])
    partes = {"corrente": corrente["eta"], "montante": montante["eta"]}
    if emenda:
        partes["emenda_corda"] = emenda["eta"]
    gov = max(partes, key=partes.get)
    return {
        "V_up_kN": round(V_up, 2), "H_viga_kN": round(H_viga, 2),
        "H_terca_kN": round(H_terca, 2), "N_montante_kN": round(float(N_montante_kN), 2),
        "corrente": corrente, "montante": montante, "emenda_corda": emenda,
        "rasgo_superior": rasgo,
        "eta": round(max(partes.values()), 4), "governa": gov,
        "ok": bool(corrente["ok"] and montante["ok"] and (emenda is None or emenda["ok"])),
        "norma": "EC5 §8.7.2/§8.7.1/§8.7.3/§8.2.2 + Tab. 8.6; §8.2.3/§8.5.1.1 (montante)",
    }
