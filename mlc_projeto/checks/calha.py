"""
checks/calha.py — Calha central, condutores e extravasores (issue 83).

As duas águas duplas lado a lado descarregam na calha central, sobre a linha
de pilares B, que corre por cima da terça T9 e das ligações L1c: é o ponto
mais crítico da cobertura. Concepção adotada:

  · Calha de chapa de aço galvanizada e pintada, retangular, apoiada em
    suportes sobre a T9 com folga de ventilação entre o fundo da calha e a
    madeira; as telhas do último pano apoiam-se em perfis de borda da calha.
  · Uma saída por pórtico, deslocada do eixo, para que o bocal não fique sobre
    a ligação L1c; condutor vertical ao lado do pilar central, afastado da
    madeira. Os pontos altos ficam a meio vão entre pórticos, onde ficam também
    as juntas de dilatação.
  · Extravasor: as extremidades da calha, nos oitões, abertas; junto a cada
    saída, um ladrão com descarga livre visível, que denuncia o entupimento sem
    deixar a água transbordar para dentro da cobertura.

Dimensionamento (ABNT NBR 10844):
  · área de contribuição de telhado inclinado A = (a + h/2)·b (§5.2);
  · vazão Q = I·A/60 (L/min), com I da Tabela 5 para T = 25 anos;
  · capacidade da calha pela fórmula de Manning-Strickler,
    Q = K·(S/n)·R_H^(2/3)·i^(1/2), K = 60 000, n = 0,011, lâmina de metade da altura;
  · condutor vertical pela equação de Wyly-Eaton da EN 12056-3 (Eq. 6),
    Q = 2,5·10⁻⁴·k_b^(−1/6)·d^(8/3)·f^(5/3) (L/s), enchimento f ≤ 0,33.

A água da calha cheia (extravasor no limite) entra como carga variável na
terça T9, somada à sobrecarga e ao vento (verifica_terca_flexocompressao).
"""

from __future__ import annotations

import math

#: Intensidade pluviométrica declarada — Curitiba, T = 25 anos, NBR 10844 Tab. 5.
#: TODO: confirmar com a tabela e com o local de implantação.
I_CHUVA_MM_H = 228.0
K_MANNING = 60_000.0
N_MANNING = 0.011            # aço, metais não ferrosos (NBR 10844 Tab. 2)
I_CALHA = 0.005              # declividade mínima (NBR 10844 §5.5.1)
K_B_MM = 0.25                # rugosidade do condutor (EN 12056-3)
F_ENCHIMENTO_MAX = 0.33
GAMA_AGUA = 10.0             # kN/m³
G_CALHA_KN_M = 0.10          # chapa 0,95 mm + suportes + perfis de borda
FOLGA_VENTILACAO_MM = 50.0   # entre o fundo da calha e o topo da T9
INCLINACAO_MIN_TELHA = 0.05  # telha trapezoidal sem emenda no pano (fabricante)


def area_contribuicao(*, L_vao_m: float, alpha_deg: float, comprimento_m: float) -> float:
    """Área de contribuição (m²) das duas meias-águas que descarregam na calha."""
    a = L_vao_m / 2.0
    h = a * math.tan(math.radians(alpha_deg))
    return 2.0 * (a + h / 2.0) * comprimento_m


def capacidade_calha(B_m: float, y_m: float, i: float = I_CALHA) -> float:
    """Vazão (L/min) da calha retangular de largura B com lâmina y."""
    S = B_m * y_m
    R = S / (B_m + 2.0 * y_m)
    return K_MANNING * S / N_MANNING * R ** (2.0 / 3.0) * math.sqrt(i)


def capacidade_condutor(d_mm: float, f: float = F_ENCHIMENTO_MAX) -> float:
    """Vazão (L/s) do condutor vertical de diâmetro interno d (EN 12056-3)."""
    return 2.5e-4 * K_B_MM ** (-1.0 / 6.0) * d_mm ** (8.0 / 3.0) * f ** (5.0 / 3.0)


def dimensionar_calha(*, L_vao_m: float, alpha_deg: float, L_T_m: float,
                      s_terca_m: float, B_mm: float = 300.0, H_mm: float = 150.0,
                      d_condutor_mm: float = 100.0, offset_saida_m: float = 0.40) -> dict:
    """Calha, condutor e geometria do último pano de telha."""
    A_porico = area_contribuicao(L_vao_m=L_vao_m, alpha_deg=alpha_deg, comprimento_m=L_T_m)
    Q_saida = I_CHUVA_MM_H * A_porico / 60.0                    # L/min por saída
    Q_trecho = Q_saida / 2.0                                    # cada lado chega à saída
    Q_calha = capacidade_calha(B_mm / 1e3, H_mm / 2e3)
    eta_calha = Q_trecho / Q_calha
    Q_cond = capacidade_condutor(d_condutor_mm)
    eta_cond = Q_saida / 60.0 / Q_cond
    # ponto alto a meio vão: desnível do fundo até a saída
    desnivel = I_CALHA * (L_T_m / 2.0 - offset_saida_m) * 1e3   # mm, lado mais longo
    # último pano: da T8 (topo) à borda da calha, que fica acima da T9
    tg = math.tan(math.radians(alpha_deg))
    borda = FOLGA_VENTILACAO_MM + desnivel + H_mm + 20.0        # mm acima do topo da T9
    dist = s_terca_m - B_mm / 2e3 - 0.05                        # m, da T8 à borda
    incl_pano = (s_terca_m * tg * 1e3 - borda) / (dist * 1e3)
    q_agua = GAMA_AGUA * (B_mm / 1e3) * (H_mm / 1e3)            # kN/m, calha cheia
    eta = max(eta_calha, eta_cond, INCLINACAO_MIN_TELHA / incl_pano)
    return {
        "I_mm_h": I_CHUVA_MM_H, "A_por_saida_m2": round(A_porico, 1),
        "Q_saida_L_min": round(Q_saida, 0), "Q_trecho_L_min": round(Q_trecho, 0),
        "B_mm": B_mm, "H_mm": H_mm, "Q_calha_L_min": round(Q_calha, 0),
        "eta_calha": round(eta_calha, 4),
        "d_condutor_mm": d_condutor_mm, "Q_condutor_L_s": round(Q_cond, 2),
        "eta_condutor": round(eta_cond, 4),
        "offset_saida_m": offset_saida_m, "desnivel_mm": round(desnivel, 0),
        "borda_sobre_T9_mm": round(borda, 0), "inclinacao_ultimo_pano": round(incl_pano, 4),
        "q_agua_kN_m": round(q_agua, 3), "g_calha_kN_m": G_CALHA_KN_M,
        "eta": round(eta, 4), "ok": eta <= 1.0,
        "norma": "ABNT NBR 10844 §5.2, §5.5, Tab. 2 e 5 + EN 12056-3 Eq. 6",
    }
