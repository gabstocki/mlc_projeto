"""
connections/retracao.py — Retração impedida pelas chapas embutidas (issue 81).

Uma chapa rígida que liga cavilhas afastadas entre si perpendicularmente às
fibras impede a variação dimensional da madeira nessa direção e provoca
fissuras ao longo das fibras — causa frequente de dano em estruturas de MLC
(Dietsch e Winter, 2018). Em relação ao centro do grupo, a cavilha extrema
desloca-se

    δ = α⊥ · Δu · D⊥ / 2

em que D⊥ é a distância entre as cavilhas extremas perpendicularmente às fibras
e Δu a maior variação de umidade depois da montagem (a mesma faixa da issue 72:
montagem 15 ± 2 %, serviço 14–19 %, logo Δu = 6 pontos).

Critério:
  · δ ≤ (d0 − d)/2 — a folga do furo na chapa (EN 1090-2, issue 79) absorve o
    movimento: furo redondo;
  · caso contrário, se a força é paralela às fibras (escoras, montante), os
    furos da chapa são OVALIZADOS perpendicularmente às fibras, com curso ±δ
    mais 1 mm de tolerância; a força apoia-se nas faces longas do furo e a
    resistência da madeira não muda (a do aço cai a 0,6·F_b,Rd, EN 1993-1-8
    Tab. 3.4, ainda folgada com t = d);
  · no pé dos pilares o cortante do choque cruza as mesmas cavilhas
    perpendicularmente às fibras, e o furo não pode ser ovalizado: a malha é
    limitada a D⊥ que a folga do furo absorve (D⊥,max).
"""

from __future__ import annotations

import math

from mlc_projeto.connections.chapas_aco import d0_furo
from mlc_projeto.connections.oblongo_L1 import ALPHA_PERP, U_MONTAGEM, U_SERVICO

DU_MAX = max(U_SERVICO[1] - U_MONTAGEM[0], U_MONTAGEM[1] - U_SERVICO[0])   # 6 pontos
TOL_OBLONGO_MM = 1.0
ETA_ALVO = 0.90           # movimento exigido / curso adotado


def D_perp_max_mm(d_mm: float, du: float = DU_MAX, alpha: float = ALPHA_PERP) -> float:
    """Maior distância ⊥ fibras entre cavilhas extremas que a folga do furo absorve."""
    return (d0_furo(d_mm) - d_mm) / (alpha * du)


def n_perp_max(d_mm: float, a2_mm: float) -> int:
    """Número máximo de fileiras ⊥ fibras com D⊥ ≤ D⊥,max."""
    return max(1, int(D_perp_max_mm(d_mm) // a2_mm) + 1)


def avaliar_retracao(*, rotulo: str, n_perp: int, a2_mm: float, d_mm: float,
                     pode_ovalizar: bool, du: float = DU_MAX,
                     alpha: float = ALPHA_PERP, curso_existente_mm: float = 0.0) -> dict:
    """Movimento das cavilhas extremas e solução (furo redondo ou ovalizado ⊥)."""
    d0 = d0_furo(d_mm)
    D = (n_perp - 1) * a2_mm
    delta = alpha * du * D / 2.0
    folga = (d0 - d_mm) / 2.0
    if curso_existente_mm > 0.0:            # furos já ovalizados ⊥ por outro motivo
        curso = curso_existente_mm
        compr = d0 + 2.0 * curso
        lig = a2_mm - compr
        sol = f"furos já ovalizados ⊥ fibras (curso ±{curso:g} mm)"
        eta = (delta + TOL_OBLONGO_MM) / curso
    elif delta <= folga + 1e-9:
        sol, curso, eta = "furo redondo (folga do furo absorve)", 0.0, delta / folga if folga else 0.0
        compr = d0
        lig = a2_mm - d0
    elif pode_ovalizar:
        curso = math.ceil((delta + TOL_OBLONGO_MM) / ETA_ALVO)
        compr = d0 + 2.0 * curso
        lig = a2_mm - compr
        sol = f"furos ovalizados ⊥ fibras, curso ±{curso:g} mm"
        eta = (delta + TOL_OBLONGO_MM) / curso
    else:
        sol, curso, compr, lig = "malha excede D⊥,max (furo não ovalizável)", 0.0, d0, a2_mm - d0
        eta = delta / folga if folga else 999.0
    lig_min = 1.2 * d0                     # aço entre furos ⊥ (EN 1993-1-8 Tab. 3.3, e2)
    # furos já ovalizados: o aço entre eles está no quadro de espaçamentos (p1)
    eta_lig = 0.0 if curso_existente_mm > 0.0 else (lig_min / lig if lig > 0 else 999.0)
    return {
        "rotulo": rotulo, "n_perp": n_perp, "a2_mm": a2_mm, "d_mm": d_mm, "d0_mm": d0,
        "D_perp_mm": round(D, 1), "delta_mm": round(delta, 2), "folga_furo_mm": folga,
        "D_perp_max_mm": round(D_perp_max_mm(d_mm, du, alpha), 1),
        "solucao": sol, "curso_mm": curso, "comprimento_furo_mm": compr,
        "ligamento_mm": round(lig, 1), "ligamento_min_mm": round(lig_min, 1),
        "eta": round(max(eta, eta_lig), 4), "ok": max(eta, eta_lig) <= 1.0,
    }


def n_perp_max_borda_carregada(d_mm: float, a2_mm: float, h_mm: float, a4t_mm: float) -> int:
    """Fileiras ⊥ às fibras que cabem na largura h com a4,t nas duas bordas (issue 76):
    sob cortante ⊥ às fibras de sentido qualquer, as duas faces são bordas carregadas."""
    return max(1, int((h_mm - 2.0 * a4t_mm) // a2_mm) + 1)
