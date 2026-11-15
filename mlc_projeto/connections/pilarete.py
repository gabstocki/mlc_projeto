"""
connections/pilarete.py — Pilarete metálico das bases (issue 87).

O pé do pilar de madeira deixa de apoiar-se na chapa de base, no nível do
bloco: a chapa, maior que a seção, formaria uma bandeja que retém água junto ao
topo da madeira. Entre a chapa de base e o pé do pilar entra um PILARETE —
tubo circular de aço com chapa de topo — que eleva a madeira acima da zona de
respingo:

    chumbadores → chapa de base → pilarete (tubo) → chapa de topo
               → chapa vertical embutida no pé do pilar → cavilhas → madeira

  · Chapa de topo com dimensões MENORES que a seção do pilar (10 mm de recuo em
    cada face), para não formar bandeja; a chapa vertical do pé solda-se nela.
  · Seção circular: o choque de veículo pode vir de qualquer direção, e o tubo
    resiste igualmente em todas.
  · O cortante na base do pilar de madeira (choque, vento) flete o pilarete
    como balanço engastado na chapa de base: M = V·h. O momento chega à chapa
    de base e aos chumbadores.
  · As diagonais de contraventamento continuam ligadas à chapa de base, ABAIXO
    do pilarete: o cortante dos painéis vai à chaveta sem fletir o pilarete; só
    o esforço normal do montante (o pilar) o atravessa.

Verificações (EN 1993-1-1 e EN 1993-1-8): classe da seção (Tab. 5.2), tração e
compressão com flambagem (§6.2.3, §6.3.1, curva a, l_cr = 2h), flexão com
esforço normal (§6.2.9.1, M_N,Rd = M_pl,Rd·(1 − n^1,7) para tubo circular),
cortante (§6.2.6, A_v = 2A/π), chapa de topo à flexão sob o arrancamento e
soldas de filete tubo–chapas (§4.5.3.3, método simplificado) e seção líquida
nos furos de respiro da galvanização (issue 86).
"""

from __future__ import annotations

import math

from mlc_projeto.connections.chapas_aco import ACO_CHAPA, GAMMA_M0, GAMMA_M2

GAMMA_M1 = 1.00
#: Tubos circulares laminados a quente (EN 10210-2): (D, t) em mm.
#: Tubos menores, para as lâminas do pilar bipartido (issue 104), de 160 mm.
TUBOS_CHS_LAMINA = ((114.3, 8.0), (114.3, 10.0))
#: Janela de acesso à porca do tirante interno, na parede do tubo (largura, mm).
JANELA_MM = 60.0
TUBOS_CHS = ((139.7, 8.0), (139.7, 10.0), (168.3, 8.0), (168.3, 10.0), (168.3, 12.5),
             (193.7, 10.0), (193.7, 12.5), (219.1, 10.0), (219.1, 12.5), (219.1, 16.0))
CHAPAS_TOPO_MM = (16.0, 19.0, 22.4, 25.0, 31.5, 38.0)
GARGANTAS_MM = (5.0, 6.0, 8.0, 10.0, 12.0)
ETA_ALVO = 0.90           # componente de aço, dúctil (como as diagonais e a chapa de base)
RECUO_TOPO_MM = 10.0      # recuo da chapa de topo em relação a cada face do pilar
ACO_PILARETE = "S355"
#: Furos de respiro e drenagem da galvanização a fogo (issue 86, EN ISO 14713-2):
#: o tubo, fechado pelas duas chapas, explodiria no banho de zinco. Dois furos
#: diametralmente opostos junto a cada chapa; os de baixo ficam abertos como dreno.
D_FURO_RESPIRO_MM = 16.0
N_FUROS_RESPIRO_SECAO = 2


def propriedades_chs(D: float, t: float) -> dict:
    """Área, módulos e raio de giração de tubo circular (mm)."""
    d = D - 2.0 * t
    A = math.pi / 4.0 * (D ** 2 - d ** 2)
    I = math.pi / 64.0 * (D ** 4 - d ** 4)
    return {"A": A, "I": I, "W_el": I / (D / 2.0),
            "W_pl": (D ** 3 - d ** 3) / 6.0, "i": math.sqrt(I / A)}


def _soldas(F_n_lin: float, F_v_lin: float, aco: str) -> tuple[float, float]:
    """Menor garganta (mm) com η ≤ alvo e o seu η, para forças por comprimento N/mm."""
    f_u, beta = ACO_CHAPA[aco]["f_u"], ACO_CHAPA[aco]["beta_w"]
    f_vwd = f_u / math.sqrt(3.0) / (beta * GAMMA_M2)
    F = math.hypot(F_n_lin, F_v_lin)
    for a in GARGANTAS_MM:
        eta = F / (f_vwd * a)
        if eta <= ETA_ALVO:
            return a, eta
    a = GARGANTAS_MM[-1]
    return a, F / (f_vwd * a)


def verificar_pilarete(*, rotulo: str, N_c_kN: float, N_t_kN: float, V_kN: float,
                       h_m: float, b_pilar_mm: float, h_pilar_mm: float,
                       aco: str = ACO_PILARETE, tubos: tuple | None = None,
                       tirante: dict | None = None) -> dict:
    """
    Escolhe o menor tubo (em área) e a chapa de topo que atendem ao alvo, e
    verifica as soldas. V é o maior cortante na base do pilar de madeira
    (choque de veículo, acidental, ou vento); M = V·h no engaste.
    """
    f_y, eps = ACO_CHAPA[aco]["f_y"], math.sqrt(235.0 / ACO_CHAPA[aco]["f_y"])
    h = h_m * 1e3
    M = V_kN * h / 1e3                                          # kN·m na base
    D_max = min(b_pilar_mm, h_pilar_mm) - 2.0 * RECUO_TOPO_MM - 20.0
    escolha = None
    for D, t in sorted(tubos or TUBOS_CHS, key=lambda dt: propriedades_chs(*dt)["A"]):
        if D > D_max or D / t > 50.0 * eps ** 2:                # cabe sob a chapa; classe 1
            continue
        p = propriedades_chs(D, t)
        N_pl = p["A"] * f_y / GAMMA_M0 / 1e3
        lam = (2.0 * h / p["i"]) / (math.pi * math.sqrt(210000.0 / f_y))
        phi = 0.5 * (1 + 0.21 * (lam - 0.2) + lam ** 2)
        chi = min(1.0, 1.0 / (phi + math.sqrt(phi ** 2 - lam ** 2)))
        M_pl = p["W_pl"] * f_y / GAMMA_M0 / 1e6
        V_pl = 2.0 * p["A"] / math.pi * f_y / math.sqrt(3.0) / GAMMA_M0 / 1e3
        rho = max(0.0, (2.0 * V_kN / V_pl - 1.0) ** 2) if V_kN > 0.5 * V_pl else 0.0
        etas = {}
        for caso, N in (("compressao", N_c_kN), ("tracao", N_t_kN)):
            n = N / N_pl
            M_N = M_pl * (1.0 - rho) * max(0.0, 1.0 - n ** 1.7)
            etas[caso] = max(n / (chi if caso == "compressao" else 1.0),
                             M / M_N if M_N > 0 else 999.0)
        etas["cortante"] = V_kN / V_pl
        # seção líquida nos furos de respiro, junto ao engaste (M ≈ V·h):
        # N_u,Rd = 0,9·A_net·f_u/γM2 (§6.2.3) e M_pl reduzido na proporção da área
        r_net = 1.0 - N_FUROS_RESPIRO_SECAO * D_FURO_RESPIRO_MM * t / p["A"]
        N_u_net = 0.9 * r_net * p["A"] * ACO_CHAPA[aco]["f_u"] / GAMMA_M2 / 1e3
        etas["secao_liquida_respiro"] = (max(N_t_kN, 0.0) / N_u_net
                                         + M / (r_net * M_pl * (1.0 - rho)))
        if tirante:
            # janela de acesso à porca do tirante, logo abaixo da chapa de topo: uma
            # abertura de largura JANELA_MM na parede; M ≈ V·(t_topo + 70 mm)
            r_w = 1.0 - JANELA_MM * t / p["A"]
            N_u_w = 0.9 * r_w * p["A"] * ACO_CHAPA[aco]["f_u"] / GAMMA_M2 / 1e3
            etas["secao_janela"] = (max(N_t_kN, 0.0) / N_u_w
                                    + V_kN * 0.10 / (r_w * M_pl * (1.0 - rho)))
        eta = max(etas.values())
        if eta <= ETA_ALVO:
            escolha = dict(D_mm=D, t_mm=t, A_mm2=round(p["A"], 0), N_pl_Rd_kN=round(N_pl, 1),
                           chi=round(chi, 3), M_pl_Rd_kNm=round(M_pl, 2),
                           V_pl_Rd_kN=round(V_pl, 1), A_net_mm2=round(r_net * p["A"], 0),
                           etas={k: round(v, 4) for k, v in etas.items()},
                           eta_tubo=eta)
            break
    if escolha is None:
        raise ValueError(f"{rotulo}: nenhum tubo da série atende (N_c={N_c_kN:.0f}, "
                         f"N_t={N_t_kN:.0f}, M={M:.1f})")
    D = escolha["D_mm"]

    # Chapa de topo — a chapa vertical do pé (linha central) entrega N_t ao tubo:
    # faixa de largura D bi-engastada na parede, carga em linha no meio:
    # M = N_t·D/8, W = D·t²/6  →  σ = 0,75·N_t/t²
    # Com tirante interno, a porca e a arruela-chapa (raio b) carregam a chapa no
    # centro: placa circular engastada na parede do tubo (raio a), carga
    # distribuída em r ≤ b (Timoshenko & Woinowsky-Krieger, ν = 0,3), majorante
    # m = W/(4π)·[(1 + ν)·ln(a/b) + 1]  →  σ = 6m/t²
    if tirante:
        a_pl = (D - escolha["t_mm"]) / 2.0
        b_pl = min(tirante.get("arruela_chapa_mm", 80.0) / 2.0, 0.9 * a_pl)
        k_pl = 6.0 / (4.0 * math.pi) * (1.3 * math.log(a_pl / b_pl) + 1.0)
    else:
        k_pl = 0.75
    t_topo, eta_topo = None, None
    for tt in CHAPAS_TOPO_MM:
        eta_topo = k_pl * N_t_kN * 1e3 / tt ** 2 / (ACO_CHAPA["S275"]["f_y"] / GAMMA_M0)
        if eta_topo <= ETA_ALVO:
            t_topo = tt
            break
    if t_topo is None:
        t_topo = CHAPAS_TOPO_MM[-1]
    B_topo = b_pilar_mm - 2.0 * RECUO_TOPO_MM
    L_topo = h_pilar_mm - 2.0 * RECUO_TOPO_MM

    # Soldas de filete em todo o perímetro do tubo (método simplificado §4.5.3.3)
    per = math.pi * D
    f_n_base = (max(N_t_kN, 0.0) * 1e3 / per) + 4.0 * M * 1e6 / (math.pi * D ** 2)
    f_v = 2.0 * V_kN * 1e3 / per
    a_base, eta_sb = _soldas(f_n_base, f_v, "S275")
    a_topo, eta_st = _soldas(max(N_t_kN, 0.0) * 1e3 / per, f_v, "S275")

    partes = {"tubo": escolha["eta_tubo"], "chapa_topo": eta_topo,
              "solda_base": eta_sb, "solda_topo": eta_st}
    gov = max(partes, key=partes.get)
    return {
        "rotulo": rotulo, "aco": aco, "h_m": h_m,
        "N_c_kN": round(N_c_kN, 1), "N_t_kN": round(N_t_kN, 1), "V_kN": round(V_kN, 1),
        "M_base_kNm": round(M, 2),
        **{k: v for k, v in escolha.items() if k != "eta_tubo"},
        "chapa_topo_mm": (B_topo, L_topo, t_topo),
        "furos_respiro": f"{2 * N_FUROS_RESPIRO_SECAO}×Ø{D_FURO_RESPIRO_MM:.0f} mm",
        "a_solda_base_mm": a_base, "a_solda_topo_mm": a_topo,
        "partes": {k: round(v, 4) for k, v in partes.items()},
        "governa": gov, "eta": round(partes[gov], 4),
        "ok": partes[gov] <= 1.0,
        "norma": "EN 1993-1-1 §6.2.3/§6.2.6/§6.2.9.1/§6.3.1 + EN 1993-1-8 §4.5.3.3",
    }


def tracao_equivalente_momento(M_kNm: float, layout: tuple[int, int], s_mm: float) -> float:
    """
    Tração equivalente no grupo de chumbadores (kN) para um momento M na base,
    na pior direção: binário com braço z = (n − 1)·s na direção considerada e a
    tração dividida pela fileira mais afastada. Devolve n_total × F do chumbador
    mais tracionado, para uso nas verificações que distribuem N igualmente.
    """
    n_x, n_y = layout
    piores = []
    for n_dir, n_fila in ((n_x, n_y), (n_y, n_x)):
        if n_dir < 2:
            continue
        z = (n_dir - 1) * s_mm / 1e3
        piores.append(M_kNm / z / n_fila)
    return (max(piores) if piores else 0.0) * n_x * n_y
