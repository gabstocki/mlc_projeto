"""
connections/chapas_aco.py — Componente METÁLICO das ligações (issue 21).

Verifica o lado do AÇO das ligações de cavilha em chapa embutida (L1/L1c/L3),
conforme EN 1993-1-8 (ligações) e EN 1993-1-1 (seção bruta/líquida):

  1. Cisalhamento do pino (cavilha de aço)      — EN 1993-1-8 Tab. 3.4
  2. Pressão de contato / rasgamento no furo     — EN 1993-1-8 Tab. 3.4
  3. Seção líquida da chapa em tração            — EN 1993-1-1 §6.2.3
  4. Solda chapa embutida ↔ chapa de base        — EN 1993-1-8 §4.5.3.3

O lado da MADEIRA (Johansen, n_ef, distâncias, fendilhamento, ruptura de bloco)
está em connections.py. Aqui só o aço.

Decisões de projeto (DECLARADAS — confirmar no detalhamento, issue 23):
  · Aço da chapa: S275 (f_y=275, f_u=430 MPa; t ≤ 40 mm) — escolha da usuária.
  · Espessura da chapa embutida t_p e garganta da solda a: parametrizados.
  · Furo na chapa com folga normal (issue 79): d_0 = d + Δ, Δ da EN 1090-2
    Tab. 11 — ver d0_furo(). Na madeira o furo continua ajustado (EC5 §10.4.4).

Fatores parciais (EN 1993-1-1/1-8):
  γ_M0 = 1,00 (resistência de seção)   γ_M2 = 1,25 (parafusos, seção líquida, solda)

Referência: EN 1993-1-8:2005 Tab. 3.4 + §4.5.3.3; EN 1993-1-1 §6.2.3 + Tab. 3.1.
"""

from __future__ import annotations

import math

from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.connections.connections import distancias_minimas, F_U_K_PINO


# ── Aços estruturais EN 1993-1-1 Tab. 3.1 (t ≤ 40 mm) ─────────────────────────
ACO_CHAPA: dict[str, dict] = {
    "S235": {"f_y": 235.0, "f_u": 360.0, "beta_w": 0.80},
    "S275": {"f_y": 275.0, "f_u": 430.0, "beta_w": 0.85},
    "S355": {"f_y": 355.0, "f_u": 490.0, "beta_w": 0.90},
}


def folga_furo_mm(d_mm: float) -> float:
    """Folga nominal de furo redondo normal na chapa (EN 1090-2:2018 Tab. 11):
    1 mm até Ø14, 2 mm de Ø16 a Ø24, 3 mm a partir de Ø27. Atende também o
    limite do EC5 §10.4.3 para furos em chapas de aço, max(2 mm; 0,1·d)."""
    d = float(d_mm)
    return 1.0 if d <= 14.0 else (2.0 if d <= 24.0 else 3.0)


def d0_furo(d_mm: float) -> float:
    """Diâmetro do furo na chapa, d_0 = d + folga (issue 79). Nos furos
    ovalizados, d_0 é a largura do rasgo; as distâncias e_3, e_4 da EN 1993-1-8
    Tab. 3.3 e os termos em d_0 da Tab. 3.4 usam este valor."""
    return float(d_mm) + folga_furo_mm(d_mm)

GAMMA_M0 = 1.00   # EN 1993-1-1 §6.1 — resistência de seção bruta
GAMMA_M2 = 1.25   # EN 1993-1-8 — parafusos/pinos, seção líquida e solda
ALPHA_V  = 0.6    # EN 1993-1-8 Tab. 3.4 — cortante do pino (classe genérica)


def verificar_chapas_aco(
    F_res_kN:   float,
    N_ax_kN:    float,
    d_mm:       float,
    n_pinos:    int,
    n_linha:    int,
    n_linhas:   int,
    h_grupo_mm: float,
    h_disp_mm:  float,
    theta_deg:  float,
    t_p_mm:     float = 16.0,
    a_solda_mm: float = 6.0,
    aco:        str = "S275",
    f_ub_pino:  float = F_U_K_PINO,
    n_planos:   int = 2,
    l_solda_fator: float = 2.0,
) -> dict:
    """
    Verifica os componentes de aço de uma ligação de cavilha em chapa embutida.

    Args:
        F_res_kN   : resultante de projeto na ligação (kN)
        N_ax_kN    : componente axial // fibras (kN) — usada na seção líquida
        d_mm       : diâmetro da cavilha (mm)
        n_pinos    : nº total de cavilhas
        n_linha    : cavilhas por fileira (// fibras)
        n_linhas   : nº de fileiras (⊥ fibras, na altura)
        h_grupo_mm : altura ocupada pelo grupo de cavilhas (mm)
        h_disp_mm  : altura disponível da peça na ligação (mm) — limita a chapa
        theta_deg  : ângulo da resultante com as fibras (graus)
        t_p_mm     : espessura da chapa embutida (mm) — DECLARADA
        a_solda_mm : garganta da solda de filete (mm) — DECLARADA
        aco        : classe do aço da chapa
        f_ub_pino  : f_u do aço da cavilha (MPa)
        n_planos   : planos de corte por cavilha (chapa central = 2)
        l_solda_fator : nº de cordões de solda ao longo da altura da chapa (2 = duplo filete)

    Returns:
        dict com as 4 sub-verificações, η governante e ok.
    """
    if aco not in ACO_CHAPA:
        raise ValueError(f"Aço '{aco}' não reconhecido: {list(ACO_CHAPA)}")
    if t_p_mm <= 0 or a_solda_mm <= 0:
        raise ValueError("t_p e a_solda devem ser > 0")

    f_y = ACO_CHAPA[aco]["f_y"]
    f_u = ACO_CHAPA[aco]["f_u"]
    beta_w = ACO_CHAPA[aco]["beta_w"]

    F_res_N = abs(F_res_kN) * 1e3
    d0 = d0_furo(d_mm)                          # furo com folga (issue 79)
    A_dowel = math.pi * d_mm ** 2 / 4.0         # mm² — área do fuste

    # Força de projeto por cavilha (aço dúctil → todas efetivas).
    # Redução de fila longa EN 1993-1-8 §3.8: L_j = (n_linha−1)·a1.
    dist = distancias_minimas(d_mm, theta_deg=theta_deg)
    a1, a2 = dist["a1_mm"], dist["a2_mm"]
    a3t, a4t = dist["a3t_mm"], dist["a4t_mm"]
    L_j = max(0.0, (n_linha - 1)) * a1
    beta_Lf = 1.0
    if L_j > 15.0 * d_mm:
        beta_Lf = max(0.75, 1.0 - (L_j - 15.0 * d_mm) / (200.0 * d_mm))
    F1_Ed_N = F_res_N / max(n_pinos, 1) / beta_Lf

    # ── 1) Cisalhamento do pino — EN 1993-1-8 Tab. 3.4 ────────────────────
    F_v_Rd_1 = ALPHA_V * f_ub_pino * A_dowel / GAMMA_M2      # N por plano
    F_v_Rd = n_planos * F_v_Rd_1                             # N por cavilha
    eta_shear = F1_Ed_N / F_v_Rd if F_v_Rd > 0 else 999.0

    # ── 2) Pressão de contato / rasgamento — EN 1993-1-8 Tab. 3.4 ─────────
    #   α_b = min( e1/(3d0), p1/(3d0)−1/4, f_ub/f_u, 1 )
    #   k1  = min( 2,8·e2/d0−1,7, 1,4·p2/d0−1,7, 2,5 )
    alpha_d = min(a3t / (3 * d0), a1 / (3 * d0) - 0.25)
    alpha_b = min(alpha_d, f_ub_pino / f_u, 1.0)
    k1 = min(2.8 * a4t / d0 - 1.7, 1.4 * a2 / d0 - 1.7, 2.5)
    k1 = max(k1, 0.0)
    F_b_Rd = k1 * alpha_b * f_u * d_mm * t_p_mm / GAMMA_M2   # N (uma chapa)
    eta_bearing = F1_Ed_N / F_b_Rd if F_b_Rd > 0 else 999.0

    # ── 3) Seção líquida da chapa em tração — EN 1993-1-1 §6.2.3 ──────────
    #   A seção crítica atravessa as n_linhas fileiras (furos na altura).
    h_p = min(h_grupo_mm + 2 * a4t, h_disp_mm)              # altura da chapa
    A_gross = t_p_mm * h_p                                  # mm²
    A_net = t_p_mm * (h_p - n_linhas * d0)                  # mm²
    A_net = max(A_net, 0.0)
    N_pl_Rd = A_gross * f_y / GAMMA_M0                      # N — escoamento bruto
    N_u_Rd = 0.9 * A_net * f_u / GAMMA_M2                   # N — ruptura líquida
    N_t_Rd = min(N_pl_Rd, N_u_Rd)
    # Envelope conservador: chapa avaliada à tração com a resultante F_res
    # (mesmo quando a combinação governante é de compressão — a tração ocorre
    #  nas combinações de sucção/uplift). N_ax reportado para transparência.
    eta_net = F_res_N / N_t_Rd if N_t_Rd > 0 else 999.0
    net_gov = "escoamento" if N_pl_Rd <= N_u_Rd else "ruptura líquida"

    # ── 4) Solda chapa embutida ↔ chapa de base — EN 1993-1-8 §4.5.3.3 ────
    #   f_vw,d = (f_u/√3)/(β_w·γ_M2);  resistência por comprimento = f_vw,d·a
    l_w = l_solda_fator * h_p                              # mm — comprimento total
    f_vw_d = (f_u / math.sqrt(3.0)) / (beta_w * GAMMA_M2)  # MPa
    Fw_Rd_lin = f_vw_d * a_solda_mm                        # N/mm
    Fw_Ed_lin = F_res_N / l_w if l_w > 0 else 1e9          # N/mm
    eta_weld = Fw_Ed_lin / Fw_Rd_lin if Fw_Rd_lin > 0 else 999.0

    # A solda da chapa embutida à chapa de topo / sela é verificada no quadro de
    # soldas (issue 78), com a geometria real (cordões na borda inferior da
    # chapa); o valor aqui, de garganta declarada, fica só informativo.
    etas = {
        "pino_cisalh": eta_shear,
        "furo_bearing": eta_bearing,
        "chapa_liquida": eta_net,
    }
    gov_key = max(etas, key=etas.get)
    eta_gov = etas[gov_key]

    return {
        "aco":          aco,
        "f_y_MPa":      f_y,
        "f_u_MPa":      f_u,
        "t_p_mm":       t_p_mm,
        "a_solda_mm":   a_solda_mm,
        "d_mm":         d_mm,
        "d0_mm":        d0,
        "n_pinos":      n_pinos,
        "F_res_kN":     round(F_res_kN, 2),
        "N_ax_kN":      round(N_ax_kN, 2),
        "beta_Lf":      round(beta_Lf, 4),
        "F1_Ed_kN":     round(F1_Ed_N / 1e3, 3),
        # 1) cisalhamento do pino
        "F_v_Rd_kN":    round(F_v_Rd / 1e3, 3),
        "n_planos":     n_planos,
        "eta_pino_cisalh": round(eta_shear, 4),
        # 2) bearing
        "alpha_b":      round(alpha_b, 4),
        "k1":           round(k1, 4),
        "F_b_Rd_kN":    round(F_b_Rd / 1e3, 3),
        "eta_furo_bearing": round(eta_bearing, 4),
        # 3) seção líquida
        "h_p_mm":       round(h_p, 1),
        "A_gross_cm2":  round(A_gross / 100.0, 2),
        "A_net_cm2":    round(A_net / 100.0, 2),
        "N_pl_Rd_kN":   round(N_pl_Rd / 1e3, 1),
        "N_u_Rd_kN":    round(N_u_Rd / 1e3, 1),
        "N_t_Rd_kN":    round(N_t_Rd / 1e3, 1),
        "net_gov":      net_gov,
        "eta_chapa_liquida": round(eta_net, 4),
        # 4) solda
        "l_solda_mm":   round(l_w, 1),
        "f_vw_d_MPa":   round(f_vw_d, 2),
        "Fw_Rd_kNpm":   round(Fw_Rd_lin / 1e3, 4),   # kN/mm
        "Fw_Ed_kNpm":   round(Fw_Ed_lin / 1e3, 4),   # kN/mm
        "eta_solda":    round(eta_weld, 4),
        # governante
        "etas":         {k: round(v, 4) for k, v in etas.items()},
        "eta_gov_key":  gov_key,
        "eta":          round(eta_gov, 4),
        "ok":           eta_gov <= 1.0,
        "gamma_M0":     GAMMA_M0,
        "gamma_M2":     GAMMA_M2,
        "norma":        "EN 1993-1-8 Tab.3.4+§4.5.3.3 | EN 1993-1-1 §6.2.3",
        "nota_declarado": (
            f"Aço {aco}, t_p={t_p_mm:.0f} mm e solda a={a_solda_mm:.0f} mm "
            "DECLARADOS — confirmar no detalhamento (issue 23)."
        ),
    }


def chapas_aco_ligacao(
    res_lig:    dict,
    geo:        GeometriaViga,
    t_p_mm:     float = 16.0,
    a_solda_mm: float = 6.0,
    aco:        str = "S275",
) -> dict:
    """
    Aplica as verificações de aço (EN 1993-1-8/1-1) a uma ligação de cavilha já
    dimensionada (L1/L1c), lendo o layout real do dict de resultado.
    """
    res = verificar_chapas_aco(
        F_res_kN=float(res_lig["F_res_kN"]),
        N_ax_kN=abs(float(res_lig["N_d_kN"])),
        d_mm=float(res_lig["d_mm"]),
        n_pinos=int(res_lig["n_pinos"]),
        n_linha=int(res_lig["n_linha"]),
        n_linhas=int(res_lig["n_linhas"]),
        h_grupo_mm=float(res_lig.get("h_ocupado_mm", res_lig["h_disp_mm"])),
        h_disp_mm=float(res_lig["h_disp_mm"]),
        theta_deg=float(res_lig.get("theta_deg", 0.0)),
        t_p_mm=t_p_mm, a_solda_mm=a_solda_mm, aco=aco,
        n_planos=2,
    )
    res["ligacao"] = res_lig.get("ligacao", "—")
    return res


def relatorio(res: dict) -> None:
    """Relatório legível das verificações de aço."""
    print("=" * 72)
    print("  CHAPAS DE AÇO / FUROS / SOLDAS — EN 1993-1-8 + EN 1993-1-1")
    print(f"  {res.get('ligacao', '—')} | Aço {res['aco']} "
          f"(f_y={res['f_y_MPa']:.0f}, f_u={res['f_u_MPa']:.0f} MPa)")
    print("=" * 72)
    print(f"  F_res={res['F_res_kN']:.1f} kN | {res['n_pinos']} pinos Ø{res['d_mm']:.0f} | "
          f"F_1,Ed={res['F1_Ed_kN']:.2f} kN/pino (β_Lf={res['beta_Lf']:.2f})")
    print(f"  t_chapa={res['t_p_mm']:.0f} mm | solda a={res['a_solda_mm']:.0f} mm")
    print(f"  {'-'*68}")
    print(f"  1) Cisalh. pino ({res['n_planos']} planos): "
          f"F_v,Rd={res['F_v_Rd_kN']:.1f} kN | η={res['eta_pino_cisalh']:.4f}")
    print(f"  2) Bearing furo: α_b={res['alpha_b']:.2f} k1={res['k1']:.2f} | "
          f"F_b,Rd={res['F_b_Rd_kN']:.1f} kN | η={res['eta_furo_bearing']:.4f}")
    print(f"  3) Seção líquida chapa (h_p={res['h_p_mm']:.0f} mm): "
          f"N_t,Rd={res['N_t_Rd_kN']:.0f} kN ({res['net_gov']}) | "
          f"η={res['eta_chapa_liquida']:.4f}")
    print(f"  4) Solda (l={res['l_solda_mm']:.0f} mm): "
          f"F_w,Rd={res['Fw_Rd_kNpm']:.2f} kN/mm ≥ F_w,Ed={res['Fw_Ed_kNpm']:.2f} | "
          f"η={res['eta_solda']:.4f}")
    print(f"  {'-'*68}")
    print(f"  η governante ({res['eta_gov_key']}) = {res['eta']:.4f} → "
          f"{'APROVADO' if res['ok'] else 'REPROVADO'}")
    print(f"  ⚠ {res['nota_declarado']}")
    print("=" * 72)


if __name__ == "__main__":
    from mlc_projeto.core.materials import GlulamMaterial
    from mlc_projeto.core.wind import ParametrosVento
    from mlc_projeto.core.loads import carregamentos_com_vento
    from mlc_projeto.connections.connections import dimensionar_ligacao_base

    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
    mat = GlulamMaterial("GL24h", 3, "curta")
    pv = ParametrosVento(V0=45, S1=1, categoria="IV", classe="B", S3=1,
                         L=20.25, H1=geo.h_ap - geo.h0, h=7, dist_portico=5.75)
    load = carregamentos_com_vento(geo=geo, mat=mat, g_area=0.823, q_area=0.40,
                                   L_t=5.75, params_vento=pv)
    gov = load.combinacao_ELU_governante()
    L1 = dimensionar_ligacao_base(mat.com_duracao(gov.duracao), load, geo, d_mm=24)
    relatorio(chapas_aco_ligacao(L1, geo))
