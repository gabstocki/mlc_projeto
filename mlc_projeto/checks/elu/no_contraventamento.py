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


def t_ef_bloco_mm(joh: dict, d_mm: float, t1_mm: float) -> float | None:
    """
    Profundidade efetiva t_ef do Anexo A do EC5 pelo modo de Johansen que
    governa a cavilha na madeira lateral (chapa central grossa, corte duplo —
    EN 1995-1-1:2004+A1:2008, Eq. A.3 e A.7):
      · modo (f), embutimento: None — A_net,v = L_net,v·t_1;
      · modo (g), uma rótula: t_ef = t_1·[√(2 + 4·M_y/(f_h·d·t_1²)) − 1];
      · modo (h), duas rótulas: t_ef = 2·√(M_y/(f_h·d)).
    """
    import math
    My, fh = float(joh["M_y_Nmm"]), float(joh["f_hk_MPa"])
    modo = joh.get("modo_gov", "")
    if modo.startswith("modo_f"):
        return None
    if modo.startswith("modo_g"):
        return t1_mm * (math.sqrt(2.0 + 4.0 * My / (fh * d_mm * t1_mm ** 2)) - 1.0)
    return 2.0 * math.sqrt(My / (fh * d_mm))


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
    n_vert_limite: int | None = None,
    D_perp_max_mm: float | None = None,
    a4_min_mm: float | None = None,
    n_vert_min: int = 1,
    a2_min_mm: float | None = None,
    n_chapas: int = 1,
) -> dict:
    """
    Ligação da escora (MLC) ao nó metálico: cavilhas em chapa embutida central,
    força axial PARALELA às fibras (θ = 0°), corte duplo.

        F_v,Rd,pino = 2 · k_mod · min{(f),(g),(h)} / γ_M     (EC5 §8.2.3)
        R_d = n_vert · n_ef(n_horiz) · F_v,Rd,pino           (EC5 §8.5.1.1)

    Menor malha com R_d ≥ F_Ed/η_alvo (modo frágil, alvo 0,75) E ruptura de
    bloco (Anexo A completo, issue 75) dentro do mesmo alvo. O espaçamento a2
    entre fileiras ⊥ às fibras também é variável (afastar as fileiras alarga o
    bloco), limitado por D⊥ = (n_vert − 1)·a2 ≤ D_perp_max (retração impedida,
    issue 81) e pela distância às bordas ≥ a4_min (a4,c, ou a4,t sob cortante ⊥,
    issue 76). Critério de escolha: menos cavilhas, depois grupo mais curto.

    n_chapas = 2 (chapas duplas): duas chapas embutidas em rasgos paralelos dividem a
    peça em três partes iguais de madeira, t = (b − 2·t_r)/3; cada cavilha tem quatro
    planos de corte (EN 1995-1-1 §8.1.3(1)): os dois externos pela fórmula (8.11),
    chapa central com madeira t de um lado, e os dois da parte do meio pela (8.13),
    madeira entre chapas espessas, modos (l) 0,5·f_h·t·d e (m) 2,3·√(M_y·f_h·d). A
    ruptura de bloco considera a espessura total de madeira, 3t, repartida em dois
    lados de 1,5t (aproximação do anexo A para chapas múltiplas).
    """
    t_chapa = float(d_mm)                       # chapa rígida: t ≥ d (issue 23)
    if n_chapas == 2:
        t1_mm = (b_m * 1000.0 - 2.0 * (t_chapa + 4.0)) / 3.0      # cada parte de madeira
        joh = johansen_chapa_embutida(mat.rho_k, d_mm, t1_mm, F_U_K_PINO, theta_deg=0.0)
        f_h, M_y = joh["f_hk_MPa"], joh["M_y_Nmm"]
        F_813 = min(0.5 * f_h * t1_mm * d_mm, 2.3 * math.sqrt(M_y * f_h * d_mm))
        F_v_Rd = mat.k_mod * (2.0 * joh["F_v_Rk_N"] + 2.0 * F_813) / gamma_M / 1e3
        t1_bloco = 1.5 * t1_mm
    else:
        t1_mm = (b_m * 1000.0 - t_chapa) / 2.0
        joh = johansen_chapa_embutida(mat.rho_k, d_mm, t1_mm, F_U_K_PINO, theta_deg=0.0)
        F_v_Rd = 2.0 * mat.k_mod * joh["F_v_Rk_N"] / gamma_M / 1e3      # kN/pino
        t1_bloco = t1_mm
    dist = distancias_minimas(d_mm, theta_deg=0.0)
    a1, a2_min, a3t, a4c = dist["a1_mm"], dist["a2_mm"], dist["a3t_mm"], dist["a4c_mm"]
    a4 = max(a4c, a4_min_mm or 0.0)
    h_mm = h_m * 1000.0
    t_ef = t_ef_bloco_mm(joh, d_mm, t1_mm)

    def _bloco(nh, nv, a2_):
        # Anexo A completo (issue 75): madeira de cada lado da chapa central,
        # comprimentos líquidos e t_ef do modo de Johansen governante
        return ruptura_de_bloco(
            n_par=nh, n_perp=nv, a1_m=a1 / 1000.0, a2_m=a2_ / 1000.0, a3t_m=a3t / 1000.0,
            t1_m=t1_bloco / 1000.0, f_t0_k=mat.f_t0_k, f_v_k=mat.f_v_k, k_mod=mat.k_mod,
            gamma_M=gamma_M, F_par_kN=F_Ed_kN, d_m=d_mm / 1000.0, n_lados=2,
            t_ef_m=None if t_ef is None else t_ef / 1000.0)

    candidatos = []
    # a2_min_mm: afastamento mínimo das fileiras imposto por fora (tirante interno no
    # eixo do pilar: as fileiras contornam o furo central)
    a2_0 = max(a2_min, 10.0 * math.ceil((a2_min_mm or 0.0) / 10.0))
    a2_opcoes = [a2_0 + 10.0 * k for k in range(0, 13)]
    for a2 in a2_opcoes:
        n_vert_max = max(1, int((h_mm - 2.0 * a4) // a2) + 1)
        if n_vert_limite is not None:
            n_vert_max = min(n_vert_max, int(n_vert_limite))
        for n_vert in range(max(1, n_vert_min), n_vert_max + 1):
            D = (n_vert - 1) * a2
            if n_vert > 1 and D_perp_max_mm is not None and D > D_perp_max_mm + 1e-9:
                continue
            if n_vert > 1 and (h_mm - D) / 2.0 < a4 - 1e-9:
                continue
            if n_vert == 1 and a2 > a2_0:
                continue                                         # a2 irrelevante
            for n_horiz in range(1, n_horiz_max + 1):
                R = n_vert * n_ef(n_horiz, a1, d_mm) * F_v_Rd
                if R * eta_alvo < F_Ed_kN:
                    continue
                bl = _bloco(n_horiz, n_vert, a2)
                if bl["eta"] > eta_alvo + 1e-9:
                    continue
                candidatos.append(dict(n=n_vert * n_horiz, n_vert=n_vert, n_horiz=n_horiz,
                                       R=R, a2=a2, bloco=bl))
                break                                            # menor n_horiz p/ (a2, n_vert)
    if candidatos:
        best = min(candidatos, key=lambda c: (c["n"], c["n_horiz"], -c["R"]))
    else:                                           # não cabe: maior malha, reprova
        nv = n_vert_limite or 1
        best = dict(n=nv * n_horiz_max, n_vert=nv, n_horiz=n_horiz_max, a2=a2_min,
                    R=nv * n_ef(n_horiz_max, a1, d_mm) * F_v_Rd,
                    bloco=_bloco(n_horiz_max, nv, a2_min))
    a2 = best["a2"]
    bloco = best["bloco"]
    eta_pinos = F_Ed_kN / best["R"] if best["R"] > 0 else 999.0
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
        "bloco":        bloco,
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
    b_escora_central_m: float | None = None,
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
    # chapas duplas (concepção revista): quatro planos de corte por cavilha
    lig_beiral = dimensionar_ligacao_axial_escora(
        N_beiral, mat_curta, b_terca_m, h_terca_m, d_mm=d_mm, rotulo="escora de beiral",
        n_chapas=2)
    lig_central = dimensionar_ligacao_axial_escora(
        N_central, mat_curta, b_escora_central_m or b_terca_m, h_terca_m, d_mm=d_mm,
        rotulo="escora central",
        n_chapas=2)

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
        "b_escora_central_m": b_escora_central_m or b_terca_m,
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
