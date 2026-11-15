"""
connections/oblongo_L1.py — Curso dos furos ovalizados da L1/L1c (issue 72).

Na L1/L1c a gravidade vai por contato da viga sobre a chapa de topo (ou a
sela), e o arrancamento pelos pinos, em furos ovalizados verticais da chapa
embutida, que é fixa (soldada à chapa de topo). Toda variação da altura da
viga entre a face de apoio e um pino desloca esse pino em relação à chapa:

  · PARA BAIXO — retração (secagem abaixo da umidade de montagem), fluência
    da compressão perpendicular sob a carga permanente e deformação elástica
    sob a variável. Se o curso inferior se esgotar, a gravidade volta a passar
    pelos pinos e o fendilhamento perde a reserva que o contato lhe dá.
  · PARA CIMA — inchamento. A MLC sai da fábrica seca (EN 14080) e, na classe
    de serviço 3, umedece até o equilíbrio com o ambiente: o movimento
    dominante é o inchamento, não a retração. Sem curso superior, o inchamento
    seria impedido pelo topo do furo, comprimindo a madeira ⊥ e carregando os
    pinos.

Deslocamento do pino i, à altura y_i da face de apoio:
    Δ_umidade = α⊥ · Δu · y_i      (α⊥ ≈ 0,25 % por ponto percentual)
    δ_comp    = R / (2·b·E90) · ln((l + 2·y_i) / l)   (dispersão 45° a partir
                do apoio de comprimento l), × (1 + k_def) para a permanente.

Com o curso superior, a viga sobe a folga acima do pino antes que o pino
receba o arrancamento: a folga de LEVANTAMENTO, máxima quando a madeira está na
umidade mínima de serviço, é calculada e declarada.

Os pinos são posicionados na montagem pela umidade MEDIDA da viga:
    folga acima do pino i = α⊥ · (u_max − u_medido) · y_i + tolerância.
"""

from __future__ import annotations

import math

ALPHA_PERP = 0.0025        # deformação por ponto percentual de umidade, ⊥ fibras
E90_MEAN_MPA = 300.0       # EN 14080, GL24h
TOLERANCIA_MM = 2.0        # montagem e fabricação, em cada sentido
ETA_ALVO_CURSO = 0.90      # curso exigido / adotado
#: Umidade de montagem especificada (EN 14080 admite até 15 % na produção;
#: aceita-se 15 ± 2 % na montagem, com aclimatação em obra).
U_MONTAGEM = (13.0, 17.0)
#: Umidade de equilíbrio em serviço, sob a cobertura: UR 70–85 % a 15–25 °C.
U_SERVICO = (14.0, 19.0)


def recalque_compressao_mm(R_kN: float, b_m: float, l_m: float, y_mm: float) -> float:
    """Encurtamento da altura y sob a reação R, com dispersão a 45° (mm)."""
    l = l_m * 1e3
    return (R_kN * 1e3 / (2.0 * b_m * 1e3 * E90_MEAN_MPA)) * math.log((l + 2.0 * y_mm) / l)


def curso_oblongo(*, y_pinos_mm: list[float], R_G_kN: float, R_var_kN: float,
                  b_m: float, l_apoio_m: float, k_def: float,
                  u_montagem: tuple = U_MONTAGEM, u_servico: tuple = U_SERVICO,
                  alpha: float = ALPHA_PERP, tol_mm: float = TOLERANCIA_MM) -> dict:
    """Cursos exigidos (pino mais alto governa), folga de levantamento e regra de montagem."""
    y = max(y_pinos_mm)
    y_min = min(y_pinos_mm)
    du_ret = max(u_montagem[1] - u_servico[0], 0.0)      # secagem máxima após a montagem
    du_inch = max(u_servico[1] - u_montagem[0], 0.0)     # umedecimento máximo
    ret = alpha * du_ret * y
    inch = alpha * du_inch * y
    flu = recalque_compressao_mm(R_G_kN, b_m, l_apoio_m, y) * (1.0 + k_def)
    ela = recalque_compressao_mm(R_var_kN, b_m, l_apoio_m, y)
    c_baixo = ret + flu + ela + tol_mm
    c_cima = inch + tol_mm
    # adotados: múltiplos de 5 mm (gabarito de fabricação) com taxa ≤ 0,90,
    # a margem adotada para os componentes de aço
    c_baixo_ad = 5 * math.ceil(c_baixo / ETA_ALVO_CURSO / 5)
    c_cima_ad = 5 * math.ceil(c_cima / ETA_ALVO_CURSO / 5)
    # levantamento antes de o pino mais alto pegar: madeira na umidade mínima
    lev_max = alpha * (u_servico[1] - u_servico[0]) * y + tol_mm
    lev_1o = alpha * (u_servico[1] - u_servico[0]) * y_min + tol_mm

    def folga_acima(u_medido: float, y_i: float) -> float:
        return alpha * (u_servico[1] - u_medido) * y_i + tol_mm

    regra = {f"{u:.0f}%": [round(folga_acima(u, yi), 1) for yi in sorted(y_pinos_mm, reverse=True)]
             for u in (u_montagem[0], 0.5 * sum(u_montagem), u_montagem[1])}
    eta = max(c_baixo / c_baixo_ad, c_cima / c_cima_ad)
    return {
        "y_pino_alto_mm": round(y, 1), "y_pino_baixo_mm": round(y_min, 1),
        "u_montagem": u_montagem, "u_servico": u_servico, "alpha_perp": alpha,
        "retracao_mm": round(ret, 2), "inchamento_mm": round(inch, 2),
        "fluencia_mm": round(flu, 2), "elastica_var_mm": round(ela, 2),
        "tolerancia_mm": tol_mm,
        "c_baixo_req_mm": round(c_baixo, 2), "c_cima_req_mm": round(c_cima, 2),
        "c_baixo_mm": float(c_baixo_ad), "c_cima_mm": float(c_cima_ad),
        "levantamento_max_mm": round(lev_max, 1),
        "levantamento_1o_pino_mm": round(lev_1o, 1),
        "folga_acima_montagem_mm": regra,
        "eta": round(eta, 4), "ok": eta <= 1.0,
        "norma": "EN 14080 (umidade de produção) + EC5 §2.3.1.3 (CS3) e k_def (Tab. 3.2)",
    }


#: Madeira de seção inteira exigida acima do fundo do rasgo (issue 71): 2,5
#: lamelas de 40 mm, que mantêm unidas as duas lâminas laterais do rasgo.
E_SOBRE_RASGO_MIN_MM = 100.0
#: O rasgo da L1 prolonga-se além das duas faces do pilar (issue 83): as
#: extremidades abrem-se para baixo, fora da chapa de topo, e ventilam e drenam
#: a cavidade, que de outro modo ficaria fechada pela chapa de topo.
E_RASGO_VENTILACAO_MM = 30.0


def geometria_rasgo(*, h0_mm: float, d_mm: float, d0_mm: float, a2_mm: float,
                    n_fileiras: int, R_G_kN: float, R_var_kN: float, b_m: float,
                    l_apoio_m: float, k_def: float,
                    e_sobre_min_mm: float = E_SOBRE_RASGO_MIN_MM, passo_mm: float = 10.0,
                    **kw) -> dict:
    """
    Posição do pino mais alto e altura do rasgo (issue 71).

    O rasgo é aberto a partir do intradorso; o seu fundo fica acima do topo da
    chapa embutida por uma folga que cobre a descida da madeira em relação à
    chapa (retração + fluência + elástica, à altura do topo da chapa): se a
    chapa encostasse no fundo do rasgo, a gravidade passaria pela ponta da chapa
    e não pelo contato. Sobe-se o grupo de pinos o mais possível (h_e grande no
    fendilhamento), limitado por
        fundo do rasgo = y_topo + c_cima + 1,5·d0 + folga_fundo ≤ h0 − e_sobre_min
    e por a4,c = 3d no topo (EC5 Tab. 8.5).
    """
    y = h0_mm - 3.0 * d_mm
    while y > 0:
        ys = [y - k * a2_mm for k in range(n_fileiras)]
        c = curso_oblongo(y_pinos_mm=ys, R_G_kN=R_G_kN, R_var_kN=R_var_kN, b_m=b_m,
                          l_apoio_m=l_apoio_m, k_def=k_def, **kw)
        topo_chapa = y + c["c_cima_mm"] + 1.5 * d0_mm
        cf = curso_oblongo(y_pinos_mm=[topo_chapa], R_G_kN=R_G_kN, R_var_kN=R_var_kN,
                           b_m=b_m, l_apoio_m=l_apoio_m, k_def=k_def, **kw)
        folga_fundo = cf["c_baixo_mm"]
        fundo = topo_chapa + folga_fundo
        if h0_mm - fundo >= e_sobre_min_mm - 1e-9:
            return {**c, "y_topo_mm": y, "a4c_topo_mm": h0_mm - y,
                    "topo_chapa_mm": math.ceil(topo_chapa), "folga_fundo_mm": folga_fundo,
                    "fundo_rasgo_mm": math.ceil(fundo),
                    "madeira_sobre_rasgo_mm": h0_mm - math.ceil(fundo),
                    "e_sobre_min_mm": e_sobre_min_mm}
        y -= passo_mm
    raise ValueError("não há posição de pinos que deixe a madeira mínima sobre o rasgo")


# ── Engajamento dos pinos sob arrancamento (issue 111) ────────────────────────
#
# Com a regra de montagem acima, a folga acima de um pino, na umidade u de
# serviço, é  g_i(u) = tol + α⊥·(u_max − u)·y_i : igual em todos na umidade
# máxima, crescente com a altura do pino na mínima. Pinos em alturas diferentes
# encostam em sequência — os mais BAIXOS primeiro, que são os de menor h_e no
# fendilhamento. A regra de grupo do EC5 (n_ef·F_v,Rd, §8.5.1.1) pressupõe
# engajamento simultâneo a menos da folga normal de furo (d0 − d, EN 1090-2), e
# é esse o limite adotado para o espalhamento total:
#     Δg = α⊥·(u_max − u_min)·(y_max − y_min) + tol_fab ≤ d0 − d
# tol_fab = 1,0 mm: ±0,5 mm na posição da extremidade do oblongo (corte CNC) e do
# furo na madeira, a especificar nos desenhos. Pinos numa mesma fileira (mesma
# altura) não têm espalhamento de umidade.

TOL_FAB_ENGAJ_MM = 1.0


def espalhamento_engajamento_mm(D_vert_mm: float, *, alpha: float = ALPHA_PERP,
                                u_servico: tuple = U_SERVICO,
                                tol_fab_mm: float = TOL_FAB_ENGAJ_MM) -> float:
    """Diferença máxima de folga entre pinos cujas alturas distam D_vert_mm."""
    return alpha * (u_servico[1] - u_servico[0]) * D_vert_mm + tol_fab_mm


def n_fileiras_max(a2_mm: float, folga_furo_mm: float, **kw) -> int:
    """Maior número de fileiras (na altura) com espalhamento ≤ folga do furo."""
    n = 1
    while espalhamento_engajamento_mm(n * a2_mm, **kw) <= folga_furo_mm + 1e-9:
        n += 1
    return n


def verificar_engajamento(*, y_pinos_mm: list[float], F_v_Rd_pino_kN: float,
                          K_ser_plano_Nmm: float, P_d_kN: float, d_mm: float,
                          d0_mm: float, b_mm: float, h_mm: float, k_mod: float,
                          gamma_M: float, alpha: float = ALPHA_PERP,
                          u_servico: tuple = U_SERVICO, tol_mm: float = TOLERANCIA_MM,
                          tol_fab_mm: float = TOL_FAB_ENGAJ_MM) -> dict:
    """
    Engajamento sequencial do grupo na umidade mínima de serviço (issue 111).

    Critério: Δg ≤ d0 − d (η = Δg/(d0 − d)), e a fileira mais alta em carga sob
    P_d (o fendilhamento usa h_e até ela). Informativo: distribuição elástico-
    perfeitamente plástica por pino, K_u = 2/3·K_ser (EC5 §2.2.2), K_ser aço–
    madeira = 2× o de madeira–madeira por plano (§7.1(3)), dois planos; patamar em
    F_v,Rd. A rigidez é tomada sem redução ⊥ às fibras, o que concentra mais a
    força nos primeiros pinos — hipótese conservadora para a distribuição.
    """
    K_u = 2.0 / 3.0 * 2.0 * 2.0 * K_ser_plano_Nmm / 1e3          # kN/mm por pino
    du = u_servico[1] - u_servico[0]
    gaps = [tol_mm + alpha * du * y for y in y_pinos_mm]
    i_baixo = min(range(len(y_pinos_mm)), key=lambda i: y_pinos_mm[i])
    gaps[i_baixo] -= tol_fab_mm                       # pior caso: o mais baixo adiantado
    dg = max(gaps) - min(gaps)
    folga = d0_mm - d_mm

    def forcas(delta: float, cap: bool = True) -> list[float]:
        f = [max(K_u * (delta - g), 0.0) for g in gaps]
        return [min(x, F_v_Rd_pino_kN) for x in f] if cap else f

    def resolver(cap: bool) -> float | None:
        lo, hi = 0.0, max(gaps) + 100.0
        if sum(forcas(hi, cap)) < P_d_kN:
            return None
        for _ in range(200):
            m = 0.5 * (lo + hi)
            lo, hi = (m, hi) if sum(forcas(m, cap)) < P_d_kN else (lo, m)
        return hi

    delta = resolver(True)
    delta_el = resolver(False)
    F = forcas(delta) if delta is not None else [0.0] * len(gaps)
    F_el = forcas(delta_el, cap=False)
    y_top = max(y_pinos_mm)
    ativos = [y for y, f in zip(y_pinos_mm, F) if f > 0.05 * F_v_Rd_pino_kN]
    h_e_ativo = max(ativos) if ativos else 0.0
    eta = dg / folga if folga > 0 else 999.0
    ok_topo = delta is not None and h_e_ativo >= y_top - 1e-6
    return {
        "verificacao": "Engajamento dos pinos da L1/L1c sob arrancamento",
        "y_pinos_mm": sorted(set(round(y, 1) for y in y_pinos_mm), reverse=True),
        "folgas_u_min_mm": [round(g, 2) for g in gaps],
        "delta_g_mm": round(dg, 2), "delta_g_umidade_mm": round(alpha * du * (y_top - min(y_pinos_mm)), 2),
        "tol_fab_mm": tol_fab_mm, "folga_furo_mm": round(folga, 2),
        "K_u_kNpmm": round(K_u, 2), "delta_y_mm": round(F_v_Rd_pino_kN / K_u, 2),
        "levantamento_P_d_mm": None if delta is None else round(delta, 2),
        "n_escoados": sum(f >= F_v_Rd_pino_kN - 1e-6 for f in F),
        "F_el_max_sobre_F_Rd": round(max(F_el) / F_v_Rd_pino_kN, 3),
        "mu_demanda": None if delta is None else round((delta - min(gaps)) * K_u / F_v_Rd_pino_kN, 2),
        "h_e_ativo_mm": round(h_e_ativo, 1), "fileira_alta_em_carga": ok_topo,
        "eta": round(eta, 4), "ok": bool(eta <= 1.0 + 1e-9 and ok_topo),
        "norma": "EC5 §8.5.1.1 (grupo) e §7.1 (K_ser); EN 1090-2 (folga normal d0 − d)",
    }
