"""
connections/tirante_interno.py — Tirante interno dos pilares correntes.

Concepção: a compressão passa por contato, de topo de fibra; a tração, por uma única
peça de aço. O arrancamento que a viga entrega à chapa de topo (L1, L1f) ou à sela
(L1c) não atravessa mais a madeira por cavilhas no topo e no pé do pilar: desce por
uma barra roscada que corre num furo central do pilar, do topo ao pilarete.

  · No topo, a barra rosqueia numa luva soldada sob a chapa de topo (ou sob a sela),
    diretamente abaixo da chapa embutida da viga: a força atravessa a chapa na
    espessura (aço classe Z, como antes).
  · No pé, a barra atravessa a chapa de topo do pilarete e recebe porca e arruela-
    chapa por dentro do tubo, apertadas por uma janela na parede do tubo; o tubo leva
    a tração à chapa de base e aos chumbadores.
  · O furo central do pilar é feito pelo fabricante, por ranhuras nas duas lamelas
    centrais antes da colagem, com diâmetro d + 16 mm; drena e ventila pela janela
    do pilarete.

O pilar passa a trabalhar só à compressão e ao cortante: no pé e no topo ficam duas
abas de aço, dos dois lados do tirante, com as cavilhas necessárias ao cortante do
choque e do vento e ao posicionamento.

Verificações (EN 1993-1-8):
  · tração da barra, F_t,Rd = k2·f_ub·A_s/γ_M2 (Tab. 3.4), k2 = 0,9;
  · alvo η ≤ 0,75: é a única via de tração, sem redundância;
  · solda da luva sob a chapa de topo (§4.5.3.3).
A chapa de topo do pilarete, carregada pela arruela no centro, e a seção do tubo na
janela de acesso são verificadas em connections.pilarete.
"""

from __future__ import annotations

import math

from mlc_projeto.connections.chapas_aco import ACO_CHAPA, GAMMA_M2

#: Área resistente da rosca A_s (mm²), EN ISO 898-1.
A_S_MM2 = {20: 245.0, 24: 353.0, 27: 459.0, 30: 561.0, 33: 694.0, 36: 817.0}
F_UB_MPA = 800.0            # classe 8.8, galvanizada a fogo (EN ISO 10684)
K2 = 0.9
ETA_ALVO = 0.75
FOLGA_FURO_MM = 16.0        # furo central do pilar = d + 16 mm
ARRUELA_CHAPA_MM = 80.0     # arruela-chapa sob a porca, dentro do pilarete
GARGANTAS_MM = (4.0, 5.0, 6.0, 8.0, 10.0)


L_LUVA_MM = 60.0            # luva roscada soldada sob a chapa de topo
T_ARRUELA_CHAPA_MM = 10.0   # espessura da arruela-chapa (verificar_arruela_chapa)


def comprimento_tirante(*, H_madeira_mm: float, d_mm: float, t_chapa_pilarete_mm: float) -> dict:
    """
    Comprimentos do tirante interno (issue 116), fonte única do desenho e do cálculo:
      · livre (elástico): da face inferior da chapa de topo, onde começa a luva, à
        arruela-chapa sob a chapa de topo do pilarete = madeira + chapa do pilarete;
      · de corte: livre + rosca na luva (1,5·d) + arruela-chapa + porca (0,8·d)
        + 2 passos de sobra (≈ 0,3·d), arredondado aos 10 mm.
    """
    L_livre = H_madeira_mm + t_chapa_pilarete_mm
    L_corte = L_livre + 1.5 * d_mm + T_ARRUELA_CHAPA_MM + 0.8 * d_mm + 0.3 * d_mm
    return {"L_livre_mm": round(L_livre, 0), "L_corte_mm": 10.0 * math.ceil(L_corte / 10.0)}


def dimensionar_tirante(*, rotulo: str, N_t_kN: float, aco_luva: str = "S355") -> dict:
    """Menor barra da série com η ≤ 0,75; luva e solda da luva sob a chapa de topo."""
    escolha = None
    for d, A_s in A_S_MM2.items():
        F_t = K2 * F_UB_MPA * A_s / GAMMA_M2 / 1e3
        if N_t_kN <= ETA_ALVO * F_t:
            escolha = (d, A_s, F_t)
            break
    if escolha is None:
        d = max(A_S_MM2)
        escolha = (d, A_S_MM2[d], K2 * F_UB_MPA * A_S_MM2[d] / GAMMA_M2 / 1e3)
    d, A_s, F_t = escolha
    # luva: tubo roscado de diâmetro externo ≈ 1,6d + 10, soldada em todo o contorno
    D_luva = math.ceil((1.6 * d + 10.0) / 5.0) * 5.0
    per = math.pi * D_luva
    f_w = N_t_kN * 1e3 / per                                         # N/mm
    fv = ACO_CHAPA[aco_luva]["f_u"] / math.sqrt(3.0) / (ACO_CHAPA[aco_luva]["beta_w"] * GAMMA_M2)
    a = next((g for g in GARGANTAS_MM if f_w / (fv * g) <= 0.90), GARGANTAS_MM[-1])
    eta_w = f_w / (fv * a)
    eta = N_t_kN / F_t
    return {
        "rotulo": rotulo, "N_t_kN": round(N_t_kN, 1), "d_mm": d, "A_s_mm2": A_s,
        "F_t_Rd_kN": round(F_t, 1), "furo_pilar_mm": d + FOLGA_FURO_MM,
        "D_luva_mm": D_luva, "a_solda_luva_mm": a, "eta_solda_luva": round(eta_w, 4),
        "arruela_chapa_mm": ARRUELA_CHAPA_MM,
        "partes": {"barra": round(eta, 4), "solda_luva": round(eta_w, 4)},
        "eta": round(max(eta, eta_w), 4),
        "ok": eta <= ETA_ALVO + 1e-9 and eta_w <= 0.90 + 1e-9,
        "norma": "EN 1993-1-8 Tab. 3.4 (F_t,Rd) + §4.5.3.3 (solda da luva)",
    }
