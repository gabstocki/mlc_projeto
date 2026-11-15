"""
connections/chapas_dim.py — Dimensionamento e ESQUADRO das chapas (issue 23).

Publica todas as dimensões das chapas das ligações — espessura, largura, altura
e furação — com a **espessura saindo do dimensionamento** (não arbitrada), e liga
às verificações metálicas da issue 21 (chapas_aco.py).

Chapas cobertas:
  · Embutida (slotted-in) de L1/L1c  — pinos em corte duplo.
  · Base (base plate) de L3/L3c      — compressão no concreto + chumbadores.

Critérios de espessura
----------------------
Chapa EMBUTIDA (central, em ranhura):
  t_p = max de:
    · t_thick  = d           → chapa central RÍGIDA/grossa: o pino desenvolve a
                               rótula plástica na face da chapa (hipótese das
                               Eq. 8.13/modos de Johansen usados em L1/L1c);
    · t_gross  = F_res·γ_M0/(f_y·h_p)                 (escoamento da seção bruta)
    · t_net    = F_res·γ_M2/(0,9·f_u·(h_p−n·d0))      (ruptura da seção líquida)
    · t_bear   = F_1,Ed·γ_M2/(k1·α_b·f_u·d)           (bearing no furo)
    · t_det    = 8 mm (mínimo construtivo)
  adotada = menor espessura comercial ≥ t_p.

Chapa de BASE (EN 1993-1-8 §6.2.5 — flexão do balanço):
  t_base = c·√(3·σ_c·γ_M0/f_y),  c = balanço da chapa além do pilar.
  Dimensões: pilar + 2c (c garante área de apoio e distância de borda do chumbador).

Referência: EN 1995-1-1 §8.2.3 (chapa em ligação aço-madeira); EN 1993-1-8 §6.2.5
            (chapa de base); EN 1993-1-1 §6.2.3 (seção líquida).
"""

from __future__ import annotations

import math

from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.connections.connections import distancias_minimas, F_U_K_PINO
from mlc_projeto.connections.chapas_aco import ACO_CHAPA, GAMMA_M0, GAMMA_M2, d0_furo


# Espessuras comerciais de chapa (mm) — laminadas a quente
COMMERCIAL_T_MM = [6.3, 8.0, 9.5, 12.5, 16.0, 19.0, 22.4, 25.0, 31.5, 38.0]

T_DET_MIN_MM = 8.0    # espessura mínima construtiva
C_ANCHOR_MM  = 40.0   # borda mínima do chumbador na chapa de base (declarado)


def _adotar_comercial(t_req_mm: float) -> float:
    for t in COMMERCIAL_T_MM:
        if t >= t_req_mm - 1e-9:
            return t
    return COMMERCIAL_T_MM[-1]


def espessura_chapa_embutida(
    res_lig:   dict,
    geo:       GeometriaViga,
    aco:       str = "S275",
    f_ub_pino: float = F_U_K_PINO,
    t_det_min: float = T_DET_MIN_MM,
) -> dict:
    """
    Espessura da chapa embutida a partir do dimensionamento (issue 23).

    Governa, em geral, t_thick = d (chapa central rígida — hipótese de Johansen).
    """
    f_y = ACO_CHAPA[aco]["f_y"]
    f_u = ACO_CHAPA[aco]["f_u"]

    d = float(res_lig["d_mm"])
    d0 = d0_furo(d)                          # furo com folga (issue 79)
    n_pinos = int(res_lig["n_pinos"])
    n_linha = int(res_lig["n_linha"])
    n_linhas = int(res_lig["n_linhas"])
    theta = float(res_lig.get("theta_deg", 0.0))
    F_res_N = float(res_lig["F_res_kN"]) * 1e3

    dist = distancias_minimas(d, theta_deg=theta)
    a1, a2, a3t, a4t = dist["a1_mm"], dist["a2_mm"], dist["a3t_mm"], dist["a4t_mm"]

    # Altura e comprimento da chapa (furação inclusa nas distâncias de borda)
    h_grupo = float(res_lig.get("h_ocupado_mm", res_lig["h_disp_mm"]))
    h_p = min(h_grupo + 2 * a4t, float(res_lig["h_disp_mm"]))
    L_grupo = float(res_lig.get("L_ocupado_mm", (n_linha - 1) * a1))
    L_p = L_grupo + 2 * a3t

    # Força por pino (redução de fila longa)
    L_j = max(0.0, (n_linha - 1)) * a1
    beta_Lf = 1.0
    if L_j > 15.0 * d:
        beta_Lf = max(0.75, 1.0 - (L_j - 15.0 * d) / (200.0 * d))
    F1_Ed_N = F_res_N / max(n_pinos, 1) / beta_Lf

    # k1, α_b do bearing (EN 1993-1-8 Tab. 3.4)
    alpha_d = min(a3t / (3 * d0), a1 / (3 * d0) - 0.25)
    alpha_b = min(alpha_d, f_ub_pino / f_u, 1.0)
    k1 = max(0.0, min(2.8 * a4t / d0 - 1.7, 1.4 * a2 / d0 - 1.7, 2.5))

    # Critérios de espessura
    t_thick = d                                                    # chapa rígida
    t_gross = F_res_N * GAMMA_M0 / (f_y * h_p)
    t_net = F_res_N * GAMMA_M2 / (0.9 * f_u * max(h_p - n_linhas * d0, 1e-6))
    t_bear = F1_Ed_N * GAMMA_M2 / (k1 * alpha_b * f_u * d) if k1 * alpha_b > 0 else 1e9

    criterios = {
        "t_thick_d_mm": round(t_thick, 2),
        "t_gross_mm":   round(t_gross, 2),
        "t_net_mm":     round(t_net, 2),
        "t_bear_mm":    round(t_bear, 2),
        "t_det_mm":     round(t_det_min, 2),
    }
    t_req = max(t_thick, t_gross, t_net, t_bear, t_det_min)
    t_gov = max(criterios, key=criterios.get)
    t_adot = _adotar_comercial(t_req)

    return {
        "tipo":        "embutida",
        "ligacao":     res_lig.get("ligacao", "—"),
        "aco":         aco,
        "d_mm":        d,
        "d0_mm":       d0,
        "n_pinos":     n_pinos,
        "n_linha":     n_linha,
        "n_linhas":    n_linhas,
        "a1_mm":       a1, "a2_mm": a2, "a3t_mm": a3t, "a4t_mm": a4t,
        "largura_mm":  round(L_p, 0),      # ao longo da viga (// fibras)
        "altura_mm":   round(h_p, 0),      # na altura da seção (⊥ fibras)
        "criterios_t": criterios,
        "t_req_mm":    round(t_req, 2),
        "t_governa":   t_gov,
        "t_adotada_mm": t_adot,
        "furacao": (
            f"{n_pinos} furos Ø{d0:.0f} mm (d + {d0 - d:.0f}); "
            f"{n_linha}×{n_linhas} @ a1={a1:.0f}/a2={a2:.0f} mm"
        ),
        "norma": "EN 1995-1-1 §8.2.3 + EN 1993-1-1 §6.2.3 + EN 1993-1-8 Tab.3.4",
    }


def espessura_chapa_base(
    res_sapata: dict,
    b_pilar_m:  float,
    h_pilar_m:  float,
    aco:        str = "S275",
    c_anchor_mm: float = C_ANCHOR_MM,
    t_det_min:  float = T_DET_MIN_MM,
    n_chu:      int = 4,
    d_chu_mm:   float = 20.0,
) -> dict:
    """
    Dimensões e espessura da chapa de base (EN 1993-1-8 §6.2.5 — flexão do balanço).

        t_base = c·√(3·σ_c·γ_M0/f_y)
    com c = balanço da chapa além do pilar (área de apoio + borda do chumbador).
    """
    f_y = ACO_CHAPA[aco]["f_y"]
    sigma_c = float(res_sapata.get("sigma_c_MPa", 0.0))
    d_chu_mm = float(res_sapata.get("d_chu_mm", d_chu_mm))  # chumbador real
    lado_equiv_mm = float(res_sapata.get("lado_chapa_cm", 0.0)) * 10.0
    b_mm = b_pilar_m * 1e3
    h_mm = h_pilar_m * 1e3

    # Lado adotado: cobre o pilar e a área de apoio, com borda p/ chumbador
    lado_mm = max(lado_equiv_mm, b_mm, h_mm) + 2 * c_anchor_mm
    largura = max(lado_mm, b_mm + 2 * c_anchor_mm)
    altura = max(lado_mm, h_mm + 2 * c_anchor_mm)

    # Maior balanço (cantilever) além do pilar
    c_mm = max((largura - b_mm) / 2.0, (altura - h_mm) / 2.0)
    t_base = c_mm * math.sqrt(3.0 * max(sigma_c, 1e-6) * GAMMA_M0 / f_y)
    t_req = max(t_base, t_det_min)
    t_gov = "flexão balanço" if t_base >= t_det_min else "mínimo construtivo"
    t_adot = _adotar_comercial(t_req)

    return {
        "tipo":        "base",
        "ligacao":     res_sapata.get("ligacao", "—"),
        "aco":         aco,
        "sigma_c_MPa": round(sigma_c, 3),
        "b_pilar_mm":  round(b_mm, 0),
        "h_pilar_mm":  round(h_mm, 0),
        "largura_mm":  round(largura, 0),
        "altura_mm":   round(altura, 0),
        "c_balanco_mm": round(c_mm, 1),
        "criterios_t": {
            "t_flexao_mm": round(t_base, 2),
            "t_det_mm":    round(t_det_min, 2),
        },
        "t_req_mm":    round(t_req, 2),
        "t_governa":   t_gov,
        "t_adotada_mm": t_adot,
        "furacao": (
            f"{n_chu} furos Ø{d_chu_mm + 2:.0f} mm p/ chumbador Ø{d_chu_mm:.0f} mm "
            f"(borda ≥ {c_anchor_mm:.0f} mm)"
        ),
        "norma": "EN 1993-1-8 §6.2.5 (chapa de base — flexão do balanço)",
    }


def esquadro_chapas(
    res_lig:    dict,
    res_lig_c:  dict,
    geo:        GeometriaViga,
    b_pilar_m:  float,
    h_pilar_m:  float,
    b_pilar_c_m: float,
    h_pilar_c_m: float,
    aco:        str = "S275",
    d_chu_mm:   float = 20.0,
) -> dict:
    """
    Consolida o ESQUADRO de todas as chapas das ligações (issue 23),
    incluindo explicitamente a base do PILAR CENTRAL (L3c).
    """
    return {
        "L1":  espessura_chapa_embutida(res_lig["L1"], geo, aco=aco),
        "L1c": espessura_chapa_embutida(res_lig_c["L1c"], geo, aco=aco),
        "L3":  espessura_chapa_base(
            res_lig["L3"], b_pilar_m, h_pilar_m, aco=aco,
            n_chu=int(res_lig["L3"].get("n_chumbadores", 4)), d_chu_mm=d_chu_mm),
        "L3c": espessura_chapa_base(
            res_lig_c["L3c"], b_pilar_c_m, h_pilar_c_m, aco=aco,
            n_chu=int(res_lig_c["L3c"].get("n_chumbadores", 4)), d_chu_mm=d_chu_mm),
        "aco": aco,
    }


def relatorio(esq: dict) -> None:
    """Imprime o esquadro de chapas."""
    print("=" * 78)
    print("  ESQUADRO DE CHAPAS DAS LIGAÇÕES — dimensões e espessuras (issue 23)")
    print(f"  Aço {esq['aco']} | espessura SAI do dimensionamento (não arbitrada)")
    print("=" * 78)
    print(f"  {'Chapa':<6} {'Tipo':<9} {'Larg×Alt (mm)':<16} {'t_req':>7} "
          f"{'t_adot':>7}  {'Governa':<16}")
    print("  " + "-" * 74)
    for k in ("L1", "L1c", "L3", "L3c"):
        c = esq[k]
        print(f"  {k:<6} {c['tipo']:<9} "
              f"{c['largura_mm']:.0f}×{c['altura_mm']:.0f}".ljust(23)
              + f"{c['t_req_mm']:>7.1f} {c['t_adotada_mm']:>7.1f}  {c['t_governa']:<16}")
        print(f"         furação: {c['furacao']}")
    print("=" * 78)


if __name__ == "__main__":
    from mlc_projeto.core.materials import GlulamMaterial
    from mlc_projeto.core.wind import ParametrosVento
    from mlc_projeto.core.loads import carregamentos_com_vento
    from mlc_projeto.connections.connections import (
        dimensionar_ligacoes, dimensionar_ligacoes_central,
    )

    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
    mat = GlulamMaterial("GL24h", 3, "curta")
    pv = ParametrosVento(V0=45, S1=1, categoria="IV", classe="B", S3=1,
                         L=20.25, H1=geo.h_ap - geo.h0, h=7, dist_portico=5.75)
    load = carregamentos_com_vento(geo=geo, mat=mat, g_area=0.823, q_area=0.40,
                                   L_t=5.75, params_vento=pv)
    gov = load.combinacao_ELU_governante()
    m = mat.com_duracao(gov.duracao)
    L = dimensionar_ligacoes(m, load, geo, d_base_mm=24, com_tirante=True, eta_alvo=0.75)
    Lc = dimensionar_ligacoes_central(m, load, geo, d_base_mm=24, eta_alvo=0.75)
    esq = esquadro_chapas(L, Lc, geo, 0.32, 0.27, 0.32, 0.27, aco="S275")
    relatorio(esq)
