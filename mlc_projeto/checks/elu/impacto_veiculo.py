"""
checks/elu/impacto_veiculo.py — Choque de veículo em pilares (estacionamento).

Contexto
--------
Galpão de estacionamento coberto, laterais abertas: os pilares estão
expostos a manobras e a possíveis colisões de veículos ligeiros.

Norma
-----
  EN 1991-1-7:2006  — Ações acidentais (impacto de veículos)
  EN 1990 §6.4.3.3  — Combinação de ação acidental
  EN 1995-1-1       — Verificação da madeira (k_mod instantânea)

Forças de projeto (veículos ligeiros em parque de estacionamento)
------------------------------------------------------------------
Valores estáticos equivalentes **indicativos** de uso corrente em
parques (EN 1991-1-7 + prática europeia / NA; confirmar AN nacional):

  F_dx = 50 kN   (direção de marcha)
  F_dy = 25 kN   (transversal)
  h_imp = 0,50 m acima do pavimento (ponto de aplicação)

A AN nacional (ou o cliente) pode impor valores maiores; estes são o
mínimo de projeto adotado e documentado no memorial.

Modelo estrutural do pilar biarticulado
---------------------------------------
  · Força F horizontal a altura h_imp da base
  · R_base = F · (H − h) / H
  · R_topo = F · h / H
  · M_max  = R_base · h = F · h · (H − h) / H   (no ponto de aplicação)
  · N_d    = reação vertical da combinação acidental (essencialmente G)

Combinação acidental (EN 1990):
  A_d + G + ψ₂ Q   (ψ₂ cobertura ≈ 0 → N ≈ G_k linear × L/2)

Se η > 1: recomenda-se **proteção** (defensas / pilaretes) e/ou reforço
da seção — solução habitual em parques com pilares esbeltos de MLC.
"""

from __future__ import annotations

import math

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.loads     import Carregamentos, GAMMA_G_sup
from mlc_projeto.checks.elu.pilares import verifica_pilar


# ── Valores de projeto — impacto veículos ligeiros (parque) ─────────────────
F_DX_KN   = 50.0   # kN — marcha (EN 1991-1-7, prática parque)
F_DY_KN   = 25.0   # kN — transversal
H_IMP_M   = 0.50   # m  — altura de aplicação acima do piso
PSI_2_COB = 0.0    # cobertura — ψ₂ típico EN 1990


def forcas_impacto_veiculo(
    F_dx_kN: float = F_DX_KN,
    F_dy_kN: float = F_DY_KN,
    h_imp_m: float = H_IMP_M,
) -> dict:
    """Forças estáticas equivalentes de choque (veículo ligeiro)."""
    return {
        "F_dx_kN":  F_dx_kN,
        "F_dy_kN":  F_dy_kN,
        "F_gov_kN": max(F_dx_kN, F_dy_kN),
        "h_imp_m":  h_imp_m,
        "norma":    "EN 1991-1-7 (parque, veículos ligeiros — valores de projeto)",
        "nota": (
            f"F_dx={F_dx_kN:.0f} kN (marcha), F_dy={F_dy_kN:.0f} kN "
            f"(transversal), h={h_imp_m:.2f} m. Confirmar AN nacional."
        ),
    }


def esforcos_pilar_impacto(
    F_kN: float,
    H_m: float,
    h_imp_m: float = H_IMP_M,
) -> dict:
    """
    Esforços no pilar biarticulado sob força horizontal pontual F a h_imp.

        R_base = F · (H − h) / H
        M_max  = F · h · (H − h) / H
        V_max  = max(R_base, R_topo)
    """
    if H_m <= 0 or h_imp_m < 0 or h_imp_m > H_m:
        raise ValueError("Geometria de impacto inválida (0 ≤ h_imp ≤ H).")
    h = h_imp_m
    R_base = F_kN * (H_m - h) / H_m
    R_topo = F_kN * h / H_m
    M_max  = F_kN * h * (H_m - h) / H_m
    return {
        "F_kN":      round(F_kN, 3),
        "H_m":       H_m,
        "h_imp_m":   h,
        "R_base_kN": round(R_base, 3),
        "R_topo_kN": round(R_topo, 3),
        "V_max_kN":  round(max(abs(R_base), abs(R_topo)), 3),
        "M_max_kNm": round(M_max, 3),
    }


def N_acidental_pilar(
    load: Carregamentos,
    fator_pilar: float = 1.0,
) -> float:
    """
    Força normal na combinação acidental (EN 1990).

    N ≈ G (sem majorar γ_G na acidental clássica ΣG_k + A_d + ψ2 Q)
    — usa-se valor característico de G: g_k · L/2.

    fator_pilar: 1,0 lateral; 2,0 central (dois vãos).
    """
    R_g = load.g_k * load.geo.L / 2.0   # kN — reação de G por apoio
    # ψ2 Q ≈ 0 na cobertura
    return abs(fator_pilar) * R_g


def verifica_pilar_impacto(
    mat_inst: GlulamMaterial,
    b: float,
    h: float,
    H_m: float,
    N_d_kN: float,
    F_kN: float = F_DX_KN,
    h_imp_m: float = H_IMP_M,
    eixo: str = "z",
    rotulo: str = "pilar",
) -> dict:
    """
    Verifica pilar sob N (acidental) + M e V do impacto.

    mat_inst: material com duração «instantanea» (ação acidental).
    eixo: 'z' impacto // cumeeira (face b); 'y' no plano do pórtico (face h).
    """
    esp = esforcos_pilar_impacto(F_kN, H_m, h_imp_m)
    M_d = esp["M_max_kNm"]
    V_d = esp["V_max_kN"]

    # Flexo-compressão (já inclui M)
    res_fc = verifica_pilar(
        mat=mat_inst, b=b, h=h, H=H_m,
        N_d=N_d_kN, M_d_kNm=M_d, eixo=eixo,
    )

    # Cisalhamento — EC5 §6.1.7 (simplificado, seção retangular)
    # τ_d = 1,5 V / (k_cr b h); f_v,d com k_mod instantânea
    from mlc_projeto.core.materials import K_CR_GLULAM
    A = b * h
    b_ef = K_CR_GLULAM * b
    tau = 1.5 * (V_d * 1e3) / (b_ef * h) if b_ef * h > 0 else 0.0  # Pa
    f_vd = mat_inst.f_v_d
    eta_v = tau / f_vd if f_vd > 0 else 999.0

    eta = max(res_fc["eta"], eta_v)
    ok = eta <= 1.0 and res_fc["ok"] and eta_v <= 1.0

    return {
        "rotulo":        rotulo,
        "b_m":           b,
        "h_m":           h,
        "H_m":           H_m,
        "eixo":          eixo,
        "N_d_kN":        round(N_d_kN, 3),
        "F_kN":          F_kN,
        "h_imp_m":       h_imp_m,
        "M_d_kNm":       esp["M_max_kNm"],
        "V_d_kN":        esp["V_max_kN"],
        "R_base_kN":     esp["R_base_kN"],
        "R_topo_kN":     esp["R_topo_kN"],
        "eta_flexo":     res_fc["eta"],
        "eta_v":         round(eta_v, 4),
        "tau_MPa":       round(tau / 1e6, 4),
        "f_vd_MPa":      round(f_vd / 1e6, 4),
        "k_mod":         mat_inst.k_mod,
        "duracao":       mat_inst.duracao,
        "eta":           round(eta, 4),
        "ok":            ok,
        "norma":         "EN 1991-1-7 + EN 1990 A_d + EC5 §6.3.2+§6.1.7",
        "recomendacao": (
            "OK — seção resiste ao choque de projeto."
            if ok
            else (
                "η>1 — adotar proteção (defensas/pilaretes metálicos "
                "a ≥0,5 m do pilar) e/ou aumentar seção. Em MLC esbelto "
                "a proteção é frequentemente a solução de projeto."
            )
        ),
    }


def verificar_impacto_veiculo(
    geo: GeometriaViga,
    mat: GlulamMaterial,
    load: Carregamentos,
    b_pilar: float = 0.22,
    h_pilar: float = 0.26,
    b_pilar_c: float = 0.28,
    h_pilar_c: float = 0.28,
    H_pilar_m: float = 7.0,
    F_dx_kN: float = F_DX_KN,
    F_dy_kN: float = F_DY_KN,
    h_imp_m: float = H_IMP_M,
) -> dict:
    """
    Verificação completa — impacto de veículo em pilares do estacionamento.

    Avalia:
      · Pilar lateral (N = R_G) — impacto F_dx e F_dy
      · Pilar central (N = 2·R_G) — idem (mais exposto no corredor)

    k_mod: duração instantânea (ação acidental).
    """
    # Material com k_mod de ação acidental
    mat_inst = mat.com_duracao("instantanea")

    forcas = forcas_impacto_veiculo(F_dx_kN, F_dy_kN, h_imp_m)
    N_lat = N_acidental_pilar(load, fator_pilar=1.0)
    N_cen = N_acidental_pilar(load, fator_pilar=2.0)

    # Duas direcções × dois tipos de pilar
    casos = []
    for nome, b, h, N, fat in (
        ("lateral", b_pilar, h_pilar, N_lat, 1.0),
        ("central", b_pilar_c, h_pilar_c, N_cen, 2.0),
    ):
        # F_dx → face b (eixo z, // cumeeira) se marcha ao longo do galpão
        r_dx = verifica_pilar_impacto(
            mat_inst, b, h, H_pilar_m, N,
            F_kN=F_dx_kN, h_imp_m=h_imp_m, eixo="z",
            rotulo=f"{nome} F_dx={F_dx_kN:.0f}kN",
        )
        # F_dy → face h (eixo y, plano do pórtico)
        r_dy = verifica_pilar_impacto(
            mat_inst, b, h, H_pilar_m, N,
            F_kN=F_dy_kN, h_imp_m=h_imp_m, eixo="y",
            rotulo=f"{nome} F_dy={F_dy_kN:.0f}kN",
        )
        casos.extend([r_dx, r_dy])

    # Governante
    gov = max(casos, key=lambda c: c["eta"])
    ok_all = all(c["ok"] for c in casos)
    # Exposição: todos os pilares do piso de estacionamento
    exposicao = (
        "Sim — estacionamento coberto com pilares acessíveis a veículos "
        "(laterais abertas / sem vedação rígida). Verificação obrigatória "
        "como ação acidental (EN 1991-1-7)."
    )

    # Proteção recomendada se falhar ou como boa prática
    precisa_proteccao = not ok_all
    if ok_all:
        nota_proj = (
            "Seções resistem às forças de choque de projeto (50/25 kN). "
            "Mesmo assim, recomenda-se defensas/pilaretes junto a pilares "
            "em corredores de circulação (boa prática e limitação de dano)."
        )
    else:
        nota_proj = (
            "Seção insuficiente ao choque isolado — "
            + gov["recomendacao"]
        )

    return {
        "sistema": "Estacionamento coberto — impacto de veículo em pilares",
        "norma": (
            "EN 1991-1-7 §4.3 | EN 1990 §6.4.3.3 (A_d) | "
            "EC5 §6.3.2+§6.1.7 | k_mod=instantânea"
        ),
        "exposicao":     exposicao,
        "aplicavel":     True,
        "forcas":        forcas,
        "N_lateral_kN":  round(N_lat, 3),
        "N_central_kN":  round(N_cen, 3),
        "g_k_kNpm":      round(load.g_k, 4),
        "k_mod":         mat_inst.k_mod,
        "duracao":       "instantanea",
        "casos":         casos,
        "gov":           gov["rotulo"],
        "eta":           gov["eta"],
        "ok":            ok_all,
        "precisa_proteccao": precisa_proteccao,
        "recomendacao":  nota_proj,
        "nota": (
            "Ação acidental: não se combina com vento ELU. "
            "N = reação de G (ψ₂Q≈0). "
            "Valores F_dx/F_dy de projeto para ligeiros — "
            "confirmar com AN / especificações do cliente."
        ),
    }


def relatorio_impacto_veiculo(res: dict) -> None:
    """Imprime relatório da verificação de impacto."""
    print("=" * 68)
    print("  IMPACTO DE VEÍCULO — PILARES (ESTACIONAMENTO)")
    print(f"  {res['norma']}")
    print("=" * 68)
    print(f"  Aplicável : {res['aplicavel']}")
    print(f"  {res['exposicao']}")
    f = res["forcas"]
    print(f"\n  Forças: F_dx={f['F_dx_kN']:.0f} kN | F_dy={f['F_dy_kN']:.0f} kN | "
          f"h={f['h_imp_m']:.2f} m")
    print(f"  k_mod={res['k_mod']:.2f} ({res['duracao']}) | "
          f"N_lat={res['N_lateral_kN']:.1f} kN | N_cen={res['N_central_kN']:.1f} kN")
    print(f"\n  {'Caso':<28} {'M':>8} {'V':>7} {'η_fc':>7} {'η_v':>7} {'η':>7}  OK")
    print(f"  {'-'*72}")
    for c in res["casos"]:
        ok = "✓" if c["ok"] else "✗"
        print(
            f"  {c['rotulo']:<28} {c['M_d_kNm']:>8.2f} {c['V_d_kN']:>7.2f} "
            f"{c['eta_flexo']:>7.3f} {c['eta_v']:>7.3f} {c['eta']:>7.3f}  {ok}"
        )
    print(f"\n  Governante: {res['gov']}  η={res['eta']:.4f}  "
          f"{'✓ OK' if res['ok'] else '✗ FALHA'}")
    print(f"  → {res['recomendacao']}")
    print("=" * 68)
