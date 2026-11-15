"""
checks/elu/pilar_bipartido.py — Pilar bipartido dos montantes das baías contraventadas (issue 104).

Problema (issue 104): nas baías rígidas, a força longitudinal chega pela escora (terça sobre a
viga), h0 = 1,00 m acima do topo do pilar, e o nó do painel vertical CV-V ficava no topo do
pilar. O binário H·h0 não tinha equilíbrio, e qualquer peça que levasse força vertical entre
os dois níveis pela madeira da viga, ⊥ às fibras, ficaria sujeita ao inchamento dela.

Solução adotada: nos 14 pilares montantes (cantos P1, P3, P25, P27; laterais P4, P6, P22,
P24; centrais P2, P5, P8, P20, P23, P26), o pilar é formado por DUAS LÂMINAS de MLC, uma de
cada lado da viga, da base até a escora. É um pilar composto com espaçadores (EN 1995-1-1,
Anexo C.3).

  · A viga apoia-se numa sela de aço entre as lâminas, no nível do topo dos demais pilares;
    as abas da sela entram em rasgos das lâminas, com cavilhas paralelas às fibras.
  · A escora apoia-se no topo das lâminas. O topo da viga fica com folga sob ela, livre para
    inchar.
  · A diagonal CV-V prende-se numa chapa embutida no topo da lâmina do seu lado, no nível da
    escora. Escora e diagonal concorrem no mesmo ponto: não há binário.
  · A componente vertical D da diagonal desce pela lâmina PARALELA às fibras, até um pilarete
    próprio. Cada lâmina tem o seu pilarete, e a excentricidade de D em relação ao eixo do
    pilar vira um binário axial entre as lâminas, sem flexão.

Verificações (lâmina do lado do nó, a mais solicitada):
  · compressão com instabilidade (EC5 §6.3.2): no plano do pórtico, lâmina isolada, com
    comprimento até a sela (a viga trava); na fachada, pilar composto, com λ_ef pelas
    fórmulas (C.10)–(C.12) e η da Tab. C.1;
  · tração da lâmina sob a sucção (§6.1.2);
  · espaçadores: cortante V_d (C.5) e força no espaçador T_d = V_d·l1/a1 (C.13), em
    parafusos M16 8.8 madeira–madeira em corte duplo (§8.2.2, Johansen);
  · nó por CONTATO: a componente vertical da diagonal é sempre para baixo (com o
    vento invertido, aquela diagonal fica frouxa), e a chapa-capa do nó, apoiada no
    topo da lâmina, a leva por compressão de topo de fibra (σ_c,0 ≤ f_c,0,d); duas
    cavilhas numa aba posicionam a capa e ancoram o arrancamento das terças que nela
    se apoiam;
  · sela: cavilhas das abas na lâmina, metade da reação de cada viga, para baixo e para cima;
  · o pé de cada lâmina e o seu pilarete são verificados na base L3a, com as forças da
    lâmina e o choque de veículo.
"""

from __future__ import annotations

import math

from mlc_projeto.checks.elu.no_contraventamento import dimensionar_ligacao_axial_escora
from mlc_projeto.core.materials import GlulamMaterial

B_LAMINA_M = 0.16          # espessura da lâmina (direção da fachada)
H_LAMINA_M = 0.32          # largura da lâmina (plano do pórtico)
FOLGA_VIGA_MM = 10.0       # entre a face da viga e a lâmina, de cada lado
L_PACK_MM = 1500.0         # espaçamento dos espaçadores (≥ 3 vãos)
ETA_C1 = 3.5               # Tab. C.1: espaçadores parafusados com conectores, longa duração
D_PARAF_PACK_MM = 16.0     # parafusos dos espaçadores, classe 8.8
F_UB_8_8 = 800.0           # MPa
OFFSET_NO_MM = 50.0        # olhal além da face externa da lâmina
ETA_ALVO_FRAGIL = 0.75
GAMMA_M_LIG = 1.30


#: Folga entre o topo da viga e a escora apoiada nas lâminas (issue 104; inchamento
#: ≈ 15 mm + 10). Verificada contra a subida sob sucção em deslocamento_succao (112).
FOLGA_ESCORA_VIGA_MM = 25.0


def geometria(b_viga_m: float, b_l_m: float = B_LAMINA_M, h_l_m: float = H_LAMINA_M) -> dict:
    """Distância livre, eixo das lâminas, largura total e posição do nó (mm)."""
    a = b_viga_m * 1e3 + 2.0 * FOLGA_VIGA_MM
    bl = b_l_m * 1e3
    y_l = a / 2.0 + bl / 2.0
    return {"a_mm": a, "b_l_mm": bl, "h_l_mm": h_l_m * 1e3, "y_l_mm": y_l,
            "a1_mm": 2.0 * y_l, "largura_total_mm": a + 2.0 * bl,
            "y_no_mm": y_l + bl / 2.0 + OFFSET_NO_MM,
            "a_max_ok": a <= 3.0 * bl}            # C.3.1(2): a ≤ 3h (espaçadores)


def _k_c(lam: float, mat: GlulamMaterial) -> tuple[float, float]:
    f_c0k, E005 = mat.f_c0_k / 1e6, mat.E0_05 / 1e6
    lr = lam / math.pi * math.sqrt(f_c0k / E005)
    k = 0.5 * (1.0 + 0.1 * (lr - 0.3) + lr ** 2)          # β_c = 0,1 (MLC)
    return min(1.0, 1.0 / (k + math.sqrt(max(k * k - lr * lr, 0.0)))), lr


def F_v_Rk_parafuso_corte_duplo(d: float, t1: float, t2: float, rho_k: float, M_y: float) -> float:
    """
    EC5 Eq. (8.7), parafuso madeira–madeira em corte duplo, por plano de corte (N), sem
    efeito de corda; força paralela às fibras nas duas peças: f_h = 0,082(1 − 0,01d)ρ_k
    (Eq. 8.32), β = 1.
    """
    fh = 0.082 * (1.0 - 0.01 * d) * rho_k
    return min(fh * t1 * d,                                             # (g)
               0.5 * fh * t2 * d,                                       # (h)
               1.05 * fh * t1 * d / 3.0 * (math.sqrt(4.0 + 12.0 * M_y / (fh * d * t1 ** 2)) - 1.0),
               1.15 * math.sqrt(2.0 * M_y * fh * d))                    # (k)


def V_d_C5(F_c_kN: float, lam_ef: float, k_c: float) -> float:
    """EN 1995-1-1 (C.5): cortante de cálculo no pilar composto (kN)."""
    if lam_ef < 30.0:
        return F_c_kN / (120.0 * k_c)
    if lam_ef < 60.0:
        return F_c_kN * lam_ef / (3600.0 * k_c)
    return F_c_kN / (60.0 * k_c)


def verificar_pilar_bipartido(
    *,
    rotulo: str,
    mat: GlulamMaterial,
    b_viga_m: float,
    L_x_m: float,
    L_y_m: float,
    R_grav_kN: float,
    R_up_kN: float,
    D_kN: float,
    extra_centrado_kN: float = 0.0,
    M_vento_kNm: float = 0.0,
    V_choque_kN: float = 0.0,
    F_up_no_kN: float = 0.0,
    b_l_m: float = B_LAMINA_M,
    h_l_m: float = H_LAMINA_M,
) -> dict:
    """
    Pilar bipartido montante.

    Args:
        R_grav_kN : reação de gravidade total das vigas apoiadas (1 viga no lateral e no canto,
                    2 no central), combinação de compressão
        R_up_kN   : arrancamento total das vigas apoiadas (sucção)
        D_kN      : componente vertical da diagonal CV-V no nó (lâmina do seu lado)
        extra_centrado_kN : força vertical que chega centrada, repartida entre as lâminas
                    (download do painel de frontão no canto)
        L_x_m     : comprimento de flambagem no plano do pórtico (base → sela)
        L_y_m     : comprimento de flambagem na fachada (base → escora)
    """
    g = geometria(b_viga_m, b_l_m, h_l_m)
    bl, hl, y_l = g["b_l_mm"], g["h_l_mm"], g["y_l_mm"]
    A = bl * hl                                                     # mm² por lâmina
    f_c0d = mat.f_c0_d / 1e6
    f_t0d = mat.f_t0_d / 1e6

    # ── Lâmina do lado do nó ─────────────────────────────────────────────
    dN_vento = M_vento_kNm * 1e3 / g["a1_mm"]                      # binário do vento na fachada
    N_c = R_grav_kN / 2.0 + D_kN + extra_centrado_kN / 2.0 + dN_vento
    lam_x = L_x_m * 1e3 / (hl / math.sqrt(12.0))
    k_cx, lr_x = _k_c(lam_x, mat)
    I_tot = 2.0 * (hl * bl ** 3 / 12.0 + A * y_l ** 2)              # (C.7)
    lam = L_y_m * 1e3 / math.sqrt(I_tot / (2.0 * A))                # (C.11)
    lam1 = max(30.0, math.sqrt(12.0) * L_PACK_MM / bl)              # (C.12)
    lam_ef = math.sqrt(lam ** 2 + ETA_C1 * 2.0 / 2.0 * lam1 ** 2)   # (C.10), n = 2
    k_cy, lr_y = _k_c(lam_ef, mat)
    k_c = min(k_cx, k_cy)
    eta_comp = N_c * 1e3 / A / (k_c * f_c0d)
    # tração da lâmina sob a sucção (metade do arrancamento + binário do vento)
    N_t = R_up_kN / 2.0 + dN_vento
    eta_trac = N_t * 1e3 / A / f_t0d

    # ── Espaçadores (C.13): parafusos M16 8.8 madeira–madeira, corte duplo ──
    F_c_tot = R_grav_kN + D_kN + extra_centrado_kN
    V_d = V_d_C5(F_c_tot, lam_ef, k_cy)
    T_d = V_d * L_PACK_MM / g["a1_mm"]
    d = D_PARAF_PACK_MM
    M_y = 0.3 * F_UB_8_8 * d ** 2.6                                 # (8.30)
    F_v = 2.0 * mat.k_mod * F_v_Rk_parafuso_corte_duplo(d, bl, g["a_mm"], mat.rho_k, M_y) \
        / GAMMA_M_LIG / 1e3                                         # kN, dois planos
    n_paraf = max(2, math.ceil(T_d / (ETA_ALVO_FRAGIL * F_v)))      # C.3.1: ≥ 2 parafusos
    eta_pack = T_d / (n_paraf * F_v)

    # ── Nó por contato: chapa-capa no topo da lâmina ──────────────────────
    # a aba da capa entra num rasgo central da lâmina (t_r = 24 mm), descontado da área
    t_r = 24.0
    A_cont = A - t_r * hl
    sig_c0 = D_kN * 1e3 / A_cont
    eta_cont = sig_c0 / f_c0d
    # aba com cavilhas: posicionamento e arrancamento das terças apoiadas na capa
    no = dimensionar_ligacao_axial_escora(F_Ed_kN=max(F_up_no_kN, 1.0), mat=mat, b_m=b_l_m,
                                          h_m=h_l_m, rotulo=f"{rotulo} — aba da capa do nó",
                                          n_vert_min=2)
    no["sigma_c0_MPa"] = round(sig_c0, 3)
    no["eta_contato"] = round(eta_cont, 4)
    # ── Sela: abas embutidas nas lâminas, metade da reação por lâmina ───────
    F_sela = max(R_grav_kN, R_up_kN) / 2.0
    sela = dimensionar_ligacao_axial_escora(F_Ed_kN=F_sela, mat=mat, b_m=b_l_m, h_m=h_l_m,
                                            rotulo=f"{rotulo} — sela entre as lâminas")
    # Pé da lâmina e pilarete: verificados na base L3a (connections.base_pilar), com as
    # forças desta lâmina (N_lamina_kN, N_t_lamina_kN) e o choque de veículo.

    partes = {"lamina_compressao": eta_comp, "lamina_tracao": eta_trac,
              "espacadores": eta_pack, "no_contato": eta_cont, "no_cavilhas": no["eta"],
              "sela_cavilhas": sela["eta"]}
    gov = max(partes, key=partes.get)
    return {
        "rotulo": rotulo, "geometria": g,
        "b_lamina_m": b_l_m, "h_lamina_m": h_l_m,
        "R_grav_kN": round(R_grav_kN, 1), "R_up_kN": round(R_up_kN, 1),
        "D_kN": round(D_kN, 1), "extra_centrado_kN": round(extra_centrado_kN, 1),
        "N_lamina_kN": round(N_c, 1), "N_t_lamina_kN": round(N_t, 1),
        "lambda_x": round(lam_x, 1), "lambda_ef_y": round(lam_ef, 1), "lambda_1": round(lam1, 1),
        "k_c_x": round(k_cx, 4), "k_c_y": round(k_cy, 4), "k_c": round(k_c, 4),
        "eta_comp": round(eta_comp, 4), "eta_tracao": round(eta_trac, 4),
        "espacadores": {"V_d_kN": round(V_d, 2), "T_d_kN": round(T_d, 2), "l1_mm": L_PACK_MM,
                        "n_parafusos": n_paraf, "d_mm": d, "F_v_Rd_kN": round(F_v, 2),
                        "eta": round(eta_pack, 4)},
        "no": no, "sela": sela,
        "partes": {k: round(v, 4) for k, v in partes.items()},
        "governa": gov, "eta": round(partes[gov], 4),
        "ok": all(v <= (1.0 if k in ("lamina_compressao", "lamina_tracao", "no_contato")
                        else ETA_ALVO_FRAGIL) + 1e-9 for k, v in partes.items()),
        # compatibilidade com o consumidor antigo (bases, relatório)
        "N_comp_kN": round(N_c, 1), "download_total_kN": round(D_kN + extra_centrado_kN, 1),
        "N_tracao_liq_kN": round(N_t, 1), "M_vento_kNm": round(M_vento_kNm, 2),
        "dN_vento_kN": round(dN_vento, 2), "f_c0d_MPa": round(f_c0d, 2),
        "regime": "compressao" if eta_comp >= eta_trac else "tracao",
        "norma": "EC5 §6.3.2 + Anexo C.3 + §8.2.3/§8.5.1.1/§8.6 + EN 1993-1-1 (pilarete)",
    }


# ═══════════════════════════════════════════════════════════════════════════
# Situações acidentais da lâmina (issue 106): incêndio e choque de veículo
# ═══════════════════════════════════════════════════════════════════════════

def _k_c_composto(*, b_mm: float, h_mm: float, y_l_mm: float, L_x_m: float, L_y_m: float,
                  f_c0k: float, E005: float) -> dict:
    """k_c da lâmina no pilar composto (λ_x da lâmina; λ_ef pelo Anexo C), dados em MPa."""
    def kc(lam):
        lr = lam / math.pi * math.sqrt(f_c0k / E005)
        k = 0.5 * (1.0 + 0.1 * (lr - 0.3) + lr ** 2)
        return min(1.0, 1.0 / (k + math.sqrt(max(k * k - lr * lr, 0.0))))
    A = b_mm * h_mm
    lam_x = L_x_m * 1e3 / (h_mm / math.sqrt(12.0))
    I_tot = 2.0 * (h_mm * b_mm ** 3 / 12.0 + A * y_l_mm ** 2)
    lam = L_y_m * 1e3 / math.sqrt(I_tot / (2.0 * A))
    lam1 = max(30.0, math.sqrt(12.0) * L_PACK_MM / b_mm)
    lam_ef = math.sqrt(lam ** 2 + ETA_C1 * lam1 ** 2)
    return {"lambda_x": lam_x, "lambda_ef_y": lam_ef, "k_c": min(kc(lam_x), kc(lam_ef))}


def verificar_lamina_fogo(*, mat: GlulamMaterial, b_viga_m: float, L_x_m: float, L_y_m: float,
                          N_fi_kN: float, R_req_min: float,
                          b_l_m: float = B_LAMINA_M, h_l_m: float = H_LAMINA_M) -> dict:
    """
    Lâmina em situação de incêndio (EN 1995-1-2 §4.2.2), as QUATRO faces expostas: a face
    interna também, porque abaixo da viga o vão entre as lâminas é aberto. O pilar composto
    é refeito com a seção residual (λ_x da lâmina; λ_ef do Anexo C com b_fi).
    """
    from mlc_projeto.checks.elu.fogo import d_ef, resistencias_fogo, K_FI_MLC
    g = geometria(b_viga_m, b_l_m, h_l_m)
    d = d_ef(R_req_min) * 1e3
    b_fi, h_fi = g["b_l_mm"] - 2.0 * d, g["h_l_mm"] - 2.0 * d
    if b_fi <= 0.0 or h_fi <= 0.0:
        return {"R_req_min": R_req_min, "eta": float("inf"), "ok": False, "b_fi_mm": b_fi}
    rf = resistencias_fogo(mat)
    f_c0d = rf["f_c0_d_fi"] / 1e6
    kc = _k_c_composto(b_mm=b_fi, h_mm=h_fi, y_l_mm=g["y_l_mm"], L_x_m=L_x_m, L_y_m=L_y_m,
                       f_c0k=mat.f_c0_k * K_FI_MLC / 1e6, E005=rf["E_005_fi"] / 1e6)
    sig = N_fi_kN * 1e3 / (b_fi * h_fi)
    eta = sig / (kc["k_c"] * f_c0d)
    return {"R_req_min": R_req_min, "d_ef_mm": round(d, 1), "b_fi_mm": round(b_fi, 1),
            "h_fi_mm": round(h_fi, 1), "N_fi_kN": round(N_fi_kN, 1),
            "lambda_ef_y": round(kc["lambda_ef_y"], 1), "k_c": round(kc["k_c"], 4),
            "sigma_c_MPa": round(sig, 3), "eta": round(eta, 4), "ok": eta <= 1.0,
            "norma": "EN 1995-1-2 §4.2.2 + EN 1995-1-1 §6.3.2 e Anexo C (4 faces)"}


def tempo_colapso_lamina(t_max: float = 240.0, **kw) -> float:
    """Maior tempo (min, passo 1) de exposição-padrão nas 4 faces com η ≤ 1."""
    t = 1.0
    while t <= t_max:
        if not verificar_lamina_fogo(R_req_min=t, **kw)["ok"]:
            return t - 1.0
        t += 1.0
    return t_max


def verificar_lamina_impacto(*, mat_inst: GlulamMaterial, b_viga_m: float, L_x_m: float,
                             L_y_m: float, N_d_kN: float, F_x_kN: float, F_y_kN: float,
                             h_imp_m: float, b_l_m: float = B_LAMINA_M,
                             h_l_m: float = H_LAMINA_M, repartido: bool = True) -> dict:
    """
    Choque de veículo na lâmina (EN 1991-1-7; combinação acidental, k_mod instantâneo).

    O choque entra 0,20 m acima do pé, na altura do espaçador do pé (bloco maciço de 80 a
    530 mm acima do pé, C.3.1). O bloco leva a força às duas lâminas: por contato, na direção
    da fachada, e pelos parafusos M16 em corte duplo, no plano do pórtico. Cada lâmina recebe
    por isso metade do momento e do cortante do pilar biapoiado entre o pé e a sela, a mesma
    hipótese da base L3a (V/2 em cada pé). Com `repartido=False`, a lâmina atingida é tomada
    sozinha (limite superior, informativo).

    A compressão entra com o k_c do pilar composto; as forças frontal e lateral, não
    simultâneas, alternam entre as duas direções. Interação: EC5 (6.23)/(6.24) com o termo
    linear em σ_c.
    """
    from mlc_projeto.core.materials import K_CR_GLULAM
    g = geometria(b_viga_m, b_l_m, h_l_m)
    b, h = g["b_l_mm"], g["h_l_mm"]
    kc = _k_c_composto(b_mm=b, h_mm=h, y_l_mm=g["y_l_mm"], L_x_m=L_x_m, L_y_m=L_y_m,
                       f_c0k=mat_inst.f_c0_k / 1e6, E005=mat_inst.E0_05 / 1e6)
    f_c0d, f_md, f_vd = mat_inst.f_c0_d / 1e6, mat_inst.f_m_d / 1e6, mat_inst.f_v_d / 1e6
    sig_c = N_d_kN * 1e3 / (b * h)
    L, a = L_x_m, h_imp_m
    fr = 0.5 if repartido else 1.0
    # parafusos do espaçador do pé, plano do pórtico: metade do choque passa por eles
    d = D_PARAF_PACK_MM
    M_y = 0.3 * F_UB_8_8 * d ** 2.6
    F_v = 2.0 * mat_inst.k_mod * F_v_Rk_parafuso_corte_duplo(d, b, g["a_mm"], mat_inst.rho_k, M_y) \
        / GAMMA_M_LIG / 1e3
    n_esp = 2
    casos = []
    for F, eixo in ((F_x_kN, "fachada"), (F_y_kN, "pórtico"), (F_y_kN, "fachada"),
                    (F_x_kN, "pórtico")):
        M = fr * F * a * (L - a) / L                                  # kN·m por lâmina
        V = fr * F * (L - a) / L
        W = (h * b ** 2 if eixo == "fachada" else b * h ** 2) / 6.0   # mm³
        sig_m = M * 1e6 / W
        eta_fc = sig_c / (kc["k_c"] * f_c0d) + sig_m / f_md
        tau = 1.5 * V * 1e3 / (K_CR_GLULAM * b * h)
        eta_v = tau / f_vd
        eta_esp = (F / 2.0) / (n_esp * F_v) if (repartido and eixo == "pórtico") else 0.0
        casos.append({"F_kN": F, "direcao": eixo, "M_kNm": round(M, 2), "V_kN": round(V, 2),
                      "eta_flexo": round(eta_fc, 4), "eta_v": round(eta_v, 4),
                      "eta_espacador": round(eta_esp, 4),
                      "eta": round(max(eta_fc, eta_v, eta_esp), 4)})
    gov = max(casos, key=lambda c: c["eta"])
    return {"N_d_kN": round(N_d_kN, 1), "k_c": round(kc["k_c"], 4), "repartido": repartido,
            "espacador_pe": {"n_parafusos": n_esp, "d_mm": d, "F_v_Rd_kN": round(F_v, 2)},
            "casos": casos,
            "gov": gov, "eta": gov["eta"], "ok": gov["eta"] <= 1.0,
            "norma": "EN 1991-1-7 + EN 1990 (6.11b) + EC5 §6.3.2 e §6.1.7"}
