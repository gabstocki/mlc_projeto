"""
checks/elu/empuxo_sistema.py — Rigidez ao afastamento dos apoios no sistema espacial (issue 113).

A justificativa original do empuxo nulo considerava só o pilar isolado (rotulado:
rigidez nula; engastado: ~53 kN/m). Mas os topos dos pilares estão ligados pelo
diafragma da cobertura, e, com as cruzes CV-D em todas as baías (issue 110), esse
diafragma é rígido no próprio plano: o afastamento das duas linhas de apoio de uma viga
deforma as cruzes e as terças vizinhas.

Método: no modelo em planta (`opensees.diafragma_espacial`), retira-se a viga de um
pórtico (só o vão A–B; o B–C é simétrico) e aplica-se um par de forças opostas ±P nos
seus dois apoios. A rigidez ao afastamento oferecida pelo resto do sistema é
k_ap = P/Δ. O empuxo que se desenvolve segue as duas molas em série (o arco da própria
viga, k_arco, e o sistema, k_ap), como na auditoria do empuxo acoplado:

    H_dev = H_rígido · k_ap / (k_ap + k_arco)

Efeitos de H_dev na viga: o momento na cumeeira diminui H·y_c(L/2) (favorável à
flexão, desprezado) e o normal cresce H·cos θ (desfavorável, verificado como acréscimo).
H_dev passa pelos pinos da L1 como força horizontal: verificado contra R_d da ligação.
"""

from __future__ import annotations

import math

from mlc_projeto.checks.elu.empuxo_acoplado import empuxo_desenvolvido
from mlc_projeto.opensees.diafragma_espacial import analisar_diafragma

P_TESTE_KN = 10.0


def empuxo_no_sistema(*, base_modelo: dict, n_eixos: int, n_faixas: int,
                      H_rigido_kN: float, k_arco_kNm: float, L_m: float,
                      alpha_rad: float, R_d_L1_kN: float) -> dict:
    j_B = n_faixas // 2
    linhas = []
    for i in range(n_eixos):
        r = analisar_diafragma(sem_viga=(i, 0, j_B), H_tr_kN=0.0,
                               cargas=[(i, 0, 0.0, -P_TESTE_KN), (i, j_B, 0.0, P_TESTE_KN)],
                               **base_modelo)
        if r.get("mecanismo"):
            k_ap = 0.0
        else:
            u = r["u_y_no_m"]
            d = u[(i, j_B)] - u[(i, 0)]
            k_ap = P_TESTE_KN / d if d > 0 else math.inf
        H = empuxo_desenvolvido(H_rigido_kN, k_arco_kNm=k_arco_kNm, k_support_kNm=k_ap)
        linhas.append({"portico": i + 1, "k_ap_kNpm": round(k_ap, 1), "H_dev_kN": round(H, 2),
                       "fracao": round(H / H_rigido_kN, 4) if H_rigido_kN else 0.0})
    gov = max(linhas, key=lambda x: x["H_dev_kN"])
    H = gov["H_dev_kN"]
    theta = math.atan(math.tan(alpha_rad) / 2.0)
    y_c = (L_m / 2.0) * math.tan(alpha_rad) / 2.0
    eta_L1 = H / R_d_L1_kN if R_d_L1_kN > 0 else 0.0
    return {
        "verificacao": "Empuxo no sistema espacial (rigidez ao afastamento pelo diafragma)",
        "k_arco_kNm": round(k_arco_kNm, 1), "H_rigido_kN": round(H_rigido_kN, 2),
        "porticos": linhas, "portico_gov": gov["portico"],
        "k_ap_min_kNpm": min(x["k_ap_kNpm"] for x in linhas),
        "k_ap_max_kNpm": max(x["k_ap_kNpm"] for x in linhas),
        "H_dev_max_kN": H, "fracao_max": gov["fracao"],
        "dM_cumeeira_kNm": round(-H * y_c, 2),              # favorável à flexão
        "dN_viga_kN": round(H * math.cos(theta), 2),        # acréscimo de compressão
        "eta_L1_horizontal": round(eta_L1, 4),
        "eta": round(eta_L1, 4), "ok": eta_L1 <= 0.75,
        "norma": "EN 1995-1-1 §5.4 | compatibilidade arco × sistema (molas em série)",
    }
