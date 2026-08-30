"""
checks/elu/estabilidade_global.py — Estabilidade global do pórtico.

Objetivo
---------
Verificar se efeitos de 2.ª ordem (P-Δ) e imperfeições geométricas globais
(forças horizontais nocionais) exigem análise de 2.ª ordem, ou se a
análise de 1.ª ordem adotada (Castigliano biarticulada) é suficiente.

Contexto estrutural
-------------------
  · Viga MLC biarticulada (rótulas só nos apoios) + pilares biarticulados.
  · Empuxo H de 1.ª ordem vai direto à fundação (não gera pórtico
    rígido com momentos de nó).
  · Estabilidade de **barra** já coberta por EC5 §6.3.2 (k_c) e §6.3.3
    (k_crit) na viga e nos pilares.
  · Esta verificação cobre a **escala do sistema** (global).

Referências
-----------
  EN 1995-1-1 §5.4.2 / §5.4.3  — análise estrutural (1.ª vs 2.ª ordem)
  EN 1995-1-1 §6.3.2           — imperfeições de barra (via k_c)
  EN 1993-1-1 §5.2.1           — critério α_cr (analogia de pórticos;
                                  EC5 não fixa limiar numérico global)
  EN 1993-1-1 §5.3.2           — forças nocionais (φ = φ0·α_h·α_m)
  EN 1990                      — combinações de ações

Critérios de dispensa de 2.ª ordem **global** (adotados)
---------------------------------------------------------
  0) Sistema **non-sway** no plano do pórtico: biarticulado, H de 1.ª ordem
     vai à fundação (sem pórtico rígido com momentos de nó). O P-Δ de
     «piso» (sway frame) não se aplica; a 2.ª ordem de **barra** está em
     EC5 §6.3.2 (k_c) e §6.3.3 (k_crit).
  1) w_Ed / f_c ≤ 0,05 → abaixamento do freche centroidal desprezável
     (não-linearidade geométrica do arco).
  2) H_imp / H_Ed ≤ 0,10 → força nocional coberta pelo empuxo de 1.ª ordem.
  3) α_cr,arco ≥ 10 (modo de arco, L_ef ≈ L/2 na meia-água) — informativo
     de estabilidade de sistema; se < 10, regista-se k_II e alerta.

Nota: α_cr de **barra** com L_ef = L (viga) ou H (pilar) pode ser < 10;
isso **não** obriga análise global de 2.ª ordem — obriga (e já existe)
a verificação com k_c. Reporta-se como informativo.
"""

from __future__ import annotations

import math

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.loads     import Carregamentos


# EN 1993-1-1 §5.3.2 — imperfeição global (força nocional)
PHI_0 = 1.0 / 200.0

# Limiares de projeto
ALPHA_CR_MIN = 10.0     # EN 1993-1-1 §5.2.1(3) — análise elástica
W_OVER_F_MAX = 0.05     # abaixamento relativo do freche
H_IMP_OVER_H_MAX = 0.10 # nocional face ao empuxo de cálculo


def forca_nocional(
    V_Ed_kN: float,
    h_m: float,
    m_colunas: int = 2,
) -> dict:
    """
    Força horizontal nocional — EN 1993-1-1 §5.3.2 (analogia).

        φ = φ0 · α_h · α_m
        φ0 = 1/200
        α_h = 2/√h   mas  2/3 ≤ α_h ≤ 1
        α_m = √[0,5·(1 + 1/m)]
        H_Ed,imp = φ · V_Ed

    V_Ed = soma das reações verticais do pórtico (2·R_v).
    h    = altura do piso / pé-direito (m).
    m    = número de colunas no alinhamento considerado.
    """
    if h_m <= 0:
        raise ValueError("h_m deve ser > 0")
    m = max(1, int(m_colunas))

    alpha_h = min(1.0, max(2.0 / 3.0, 2.0 / math.sqrt(h_m)))
    alpha_m = math.sqrt(0.5 * (1.0 + 1.0 / m))
    phi = PHI_0 * alpha_h * alpha_m
    H_imp = phi * abs(V_Ed_kN)

    return {
        "phi_0":     PHI_0,
        "alpha_h":   round(alpha_h, 4),
        "alpha_m":   round(alpha_m, 4),
        "phi":       round(phi, 6),
        "V_Ed_kN":   round(V_Ed_kN, 3),
        "H_imp_kN":  round(H_imp, 3),
        "h_m":       h_m,
        "m_colunas": m,
        "norma":     "EN 1993-1-1 §5.3.2 (φ global, analogia para MLC)",
    }


def alpha_cr_membro(
    mat: GlulamMaterial,
    b: float,
    h: float,
    L_ef_m: float,
    N_Ed_kN: float,
) -> dict:
    """
    Fator de carga crítica de barra comprimida (Euler, E_0,05).

        N_cr = π² · E_0,05 · I / L_ef²
        α_cr = N_cr / N_Ed

    Usa E_0,05 (fractil 5%) — coerente com flambagem EC5 §6.3.2.
    """
    I = b * h ** 3 / 12.0
    E = mat.E0_05  # Pa
    if L_ef_m <= 0 or N_Ed_kN == 0:
        return {
            "N_cr_kN": 1e99, "alpha_cr": 1e99, "I_m4": I,
            "L_ef_m": L_ef_m, "N_Ed_kN": N_Ed_kN,
        }
    N_cr_N = (math.pi ** 2) * E * I / (L_ef_m ** 2)
    N_cr_kN = N_cr_N / 1e3
    alpha = N_cr_kN / abs(N_Ed_kN)
    return {
        "N_cr_kN":  round(N_cr_kN, 1),
        "alpha_cr": round(alpha, 2),
        "I_m4":     I,
        "L_ef_m":   L_ef_m,
        "N_Ed_kN":  round(N_Ed_kN, 3),
        "E0_05_MPa": round(E / 1e6, 0),
    }


def amplificacao_segunda_ordem(alpha_cr: float) -> float:
    """
    Fator de amplificação de 1.ª → 2.ª ordem (elástico).

        k_II = 1 / (1 − 1/α_cr)   para α_cr > 1
    """
    if alpha_cr <= 1.0:
        return float("inf")
    return 1.0 / (1.0 - 1.0 / alpha_cr)


def verificar_estabilidade_global(
    geo: GeometriaViga,
    mat: GlulamMaterial,
    load: Carregamentos,
    H_pilar_m: float = 7.0,
    b_pilar: float = 0.22,
    h_pilar: float = 0.26,
    w_Ed_mm: float | None = None,
    m_colunas: int = 2,
    alpha_cr_min: float = ALPHA_CR_MIN,
    contravento_vertical_ok: bool | None = None,
    contravento_transversal_ok: bool | None = None,
) -> dict:
    """
    Verificação completa de estabilidade global do pórtico biarticulado.

    Args:
        geo, mat, load : modelo de projeto
        H_pilar_m      : pé-direito (m)
        b_pilar, h_pilar : seção do pilar lateral
        w_Ed_mm        : flecha vertical ELU no vão (mm); se None, estima
                         a partir de ELS_S1 × γ (ordem de grandeza)
        m_colunas      : colunas por pórtico (2 = biarticulado simples)
        alpha_cr_min   : limiar de dispensa (default 10)
        contravento_vertical_ok : estabilidade lateral LONGITUDINAL (issue 14).
        contravento_transversal_ok : estabilidade lateral TRANSVERSAL (issue 31).
                         Para cada direção: None → sistema não informado
                         (mecanismo, α_cr,sway → 0); True → verificado (non-sway);
                         False → não conforme (mecanismo sway). O sistema só é
                         non-sway se AMBAS as direções forem True.

    Returns:
        dict com nocionais, α_cr, critérios e ok global
    """
    gov = load.combinacao_ELU_governante()
    R_v = abs(float(gov.V_max_kN))
    H_Ed = abs(float(gov.H_kN))
    N_viga = abs(float(gov.N_viga_kN))
    V_portal = 2.0 * R_v  # dois apoios

    # ── 1) Forças nocionais ───────────────────────────────────
    noc = forca_nocional(V_portal, H_pilar_m, m_colunas=m_colunas)
    H_imp = noc["H_imp_kN"]
    ratio_imp = H_imp / H_Ed if H_Ed > 1e-9 else 0.0
    ok_imp = ratio_imp <= H_IMP_OVER_H_MAX
    # H de projeto a reter (empuxo 1.ª ordem já >> nocional)
    H_gov = max(H_Ed, H_imp)

    # ── 2) Classificação do sistema (sway vs non-sway) ────────
    # Pilares biarticulados (topo e base) + ligações viga-pilar rotuladas:
    # NÃO há ação de pórtico. A estabilidade lateral depende de sistemas de
    # contraventamento nas DUAS direções. Sem eles, o pórtico é um MECANISMO
    # (α_cr,sway → 0). O α_cr de arco (passo 4) é o modo de snap-through do arco
    # abatido — NÃO é o modo de deslocamento lateral (sway).
    #   · Longitudinal (// cumeeira): contraventamento vertical (issue 14) →
    #     contravento_vertical_ok  [checks/elu/contraventamento_vertical.py]
    #   · Transversal (⊥ cumeeira, plano do pórtico): diafragma + frontões
    #     (issue 31) → contravento_transversal_ok
    #     [checks/elu/contraventamento_transversal.py]
    # O sistema só é non-sway se AMBAS as direções tiverem sistema verificado.
    def _classifica(flag, direcao, issue):
        if flag is None:
            return False, (f"{direcao}: sistema lateral não informado → "
                           f"mecanismo sway (α_cr,sway → 0). Ver {issue}.")
        if flag:
            return True, (f"{direcao}: estabilidade lateral verificada "
                          f"(non-sway). Ver {issue}.")
        return False, (f"{direcao}: contraventamento NÃO conforme → mecanismo "
                       f"sway. Rever {issue}.")

    non_sway_long, nota_long = _classifica(
        contravento_vertical_ok, "Longitudinal (// cumeeira)", "issue 14")
    non_sway_transv, nota_direcao_transversal = _classifica(
        contravento_transversal_ok, "Transversal (⊥ cumeeira)", "issue 31")

    sistema_non_sway = non_sway_long and non_sway_transv
    alpha_cr_sway = float("inf") if sistema_non_sway else 0.0
    nota_sistema = (
        "Sistema non-sway nas duas direções (contraventamento vertical e "
        "transversal verificados)."
        if sistema_non_sway
        else "Sistema NÃO indeslocável: " + " | ".join(
            n for n, ok in [(nota_long, non_sway_long),
                            (nota_direcao_transversal, non_sway_transv)]
            if not ok
        )
    )

    # ── 3) α_cr de barra (INFORMATIVO — coberto por k_c) ───────
    h0 = geo.h0
    acr_viga = alpha_cr_membro(mat, geo.b, h0, geo.L, N_viga)
    acr_viga_ap = alpha_cr_membro(mat, geo.b, geo.h_ap, geo.L, N_viga)
    # Pilar: I mínima
    I_y = b_pilar * h_pilar ** 3 / 12.0
    I_z = h_pilar * b_pilar ** 3 / 12.0
    if I_z <= I_y:
        acr_pilar = alpha_cr_membro(mat, h_pilar, b_pilar, H_pilar_m, R_v)
    else:
        acr_pilar = alpha_cr_membro(mat, b_pilar, h_pilar, H_pilar_m, R_v)

    alpha_cr_barra = min(
        acr_viga["alpha_cr"],
        acr_viga_ap["alpha_cr"],
        acr_pilar["alpha_cr"],
    )

    # ── 4) α_cr de sistema (arco / meia-água) ──────────────────
    # Meia-água com continuidade na cumeeira: L_ef ≈ L/2 (ordem de
    # grandeza para modo de arco biarticulado no plano).
    L_ef_arco = geo.L / 2.0
    # N no arco ≈ N_viga; seção de referência h0 (conservador)
    acr_arco = alpha_cr_membro(mat, geo.b, h0, L_ef_arco, N_viga)
    alpha_cr = acr_arco["alpha_cr"]
    ok_acr = alpha_cr >= alpha_cr_min
    k_II = amplificacao_segunda_ordem(alpha_cr)

    # ── 5) Geometria do arco — abaixamento do freche ──────────
    f_c = (geo.h_ap - geo.h0) / 2.0  # m — freche do eixo centroidal
    if w_Ed_mm is None:
        try:
            from mlc_projeto.checks.els.deflection_els import verificar_ELS
            els = verificar_ELS(geo, mat, load)
            w_char = float(els.get("w_S1_mm", els.get("w_fin_mm", 5.0)))
        except Exception:
            w_char = 5.0
        w_Ed_mm = w_char * 1.5  # majoração aproximada para ELU
    w_Ed_m = w_Ed_mm / 1000.0
    w_over_f = w_Ed_m / f_c if f_c > 0 else 999.0
    ok_geom = w_over_f <= W_OVER_F_MAX
    if w_over_f < 1.0:
        k_H_geom = 1.0 / (1.0 - w_over_f)
    else:
        k_H_geom = float("inf")

    # ── 6) P-Δ no pilar (fora de prumo nocional) ──────────────
    e_0 = noc["phi"] * H_pilar_m  # m
    M_imp_pilar = R_v * e_0       # kN·m
    W_p = b_pilar * h_pilar ** 2 / 6.0
    sigma_m_imp = (M_imp_pilar * 1e3) / W_p if W_p > 0 else 0.0
    eta_M_imp = sigma_m_imp / mat.f_m_d if mat.f_m_d > 0 else 0.0

    # ── 7) Agregação ──────────────────────────────────────────
    # Pré-requisito: estabilidade LATERAL assegurada (non-sway) por um sistema
    # de contraventamento vertical. Sem ele o sistema é um mecanismo e a
    # dispensa de 2.ª ordem não se coloca (não há caminho de carga lateral).
    # Verificados então: nocional + geometria do freche + α_cr de arco
    # (snap-through). α_cr,barra é informativo (coberto por k_c no ELU).
    if not sistema_non_sway:
        ok = False
        conclusao = (
            "Estabilidade lateral NÃO demonstrada (mecanismo sway, α_cr,sway→0): "
            + nota_sistema
            + " Prover/verificar o(s) sistema(s) de contraventamento antes de "
            "dispensar a 2.ª ordem."
        )
        metodo = "instavel_lateralmente"
    else:
        ok = ok_geom and ok_imp and ok_acr
        if ok:
            conclusao = (
                "Análise de 1.ª ordem suficiente: sistema non-sway nas duas "
                "direções (contraventamento vertical §14 + transversal §31 "
                "verificados), α_cr,arco≥10, abaixamento do freche desprezável e "
                "H_imp≪H_Ed. P-Δ global dispensado. 2.ª ordem de barra coberta "
                "por k_c (EC5 §6.3.2)."
            )
            metodo = "1a_ordem"
        else:
            motivos = []
            if not ok_acr:
                motivos.append(f"α_cr,arco={alpha_cr:.1f}<{alpha_cr_min:.0f}")
            if not ok_geom:
                motivos.append(f"w/f_c={w_over_f:.4f}")
            if not ok_imp:
                motivos.append(f"H_imp/H={ratio_imp:.3f}")
            conclusao = (
                "Efeitos de 2.ª ordem NÃO dispensáveis ("
                + "; ".join(motivos)
                + "). Reanalisar com amplificação k_II ou GNL."
            )
            metodo = "2a_ordem_requerida"

    # η do critério de dispensa (não confundir com η de seção)
    eta_acr = alpha_cr_min / alpha_cr if alpha_cr > 0 else 999.0
    eta_geom = w_over_f / W_OVER_F_MAX if W_OVER_F_MAX > 0 else 999.0
    eta_imp = ratio_imp / H_IMP_OVER_H_MAX if H_IMP_OVER_H_MAX > 0 else 999.0
    eta_gov = max(eta_acr, eta_geom, eta_imp)

    return {
        "sistema": "biarticulada MLC — estabilidade global",
        "norma": (
            "EN 1995-1-1 §5.4.2+§6.3.2 | "
            "EN 1993-1-1 §5.2.1+§5.3.2 (α_cr, φ analogia)"
        ),
        # Esforços de referência
        "comb":          gov.nome,
        "R_v_kN":        round(R_v, 3),
        "V_portal_kN":   round(V_portal, 3),
        "H_Ed_kN":       round(H_Ed, 3),
        "H_gov_kN":      round(H_gov, 3),
        "N_viga_kN":     round(N_viga, 3),
        "f_c_m":         round(f_c, 4),
        "H_pilar_m":     H_pilar_m,
        # Nocionais
        "phi":           noc["phi"],
        "alpha_h":       noc["alpha_h"],
        "alpha_m":       noc["alpha_m"],
        "H_imp_kN":      H_imp,
        "H_imp_over_H":  round(ratio_imp, 5),
        "ok_nocional":   ok_imp,
        "lim_H_imp":     H_IMP_OVER_H_MAX,
        # Classificação (sway / non-sway) — issues 14 (long.) e 31 (transv.)
        "sistema_non_sway": sistema_non_sway,
        "non_sway_long": non_sway_long,
        "non_sway_transv": non_sway_transv,
        "contravento_vertical_ok": contravento_vertical_ok,
        "contravento_transversal_ok": contravento_transversal_ok,
        "alpha_cr_sway": (
            round(alpha_cr_sway, 2) if math.isfinite(alpha_cr_sway) else 1e6
        ),
        "nota_sistema":  nota_sistema,
        "nota_direcao_transversal": nota_direcao_transversal,
        # α_cr sistema (arco) e barra (informativo)
        "alpha_cr":      round(alpha_cr, 2),
        "alpha_cr_min":  alpha_cr_min,
        "alpha_cr_arco": round(alpha_cr, 2),
        "L_ef_arco_m":   L_ef_arco,
        "alpha_cr_barra": round(alpha_cr_barra, 2),
        "alpha_cr_viga_h0": acr_viga["alpha_cr"],
        "alpha_cr_viga_ap": acr_viga_ap["alpha_cr"],
        "alpha_cr_pilar":   acr_pilar["alpha_cr"],
        "N_cr_viga_kN":  acr_viga["N_cr_kN"],
        "N_cr_arco_kN":  acr_arco["N_cr_kN"],
        "N_cr_pilar_kN": acr_pilar["N_cr_kN"],
        "k_II":          round(k_II, 4) if k_II < 1e6 else 1e6,
        "ok_alpha_cr":   ok_acr,
        "nota_alpha_cr_barra": (
            "α_cr de barra (L_ef=L ou H) é informativo; "
            "valores <10 são cobertos por k_c no ELU (EC5 §6.3.2), "
            "não exigem por si análise global de 2.ª ordem."
        ),
        # Geometria arco
        "w_Ed_mm":       round(w_Ed_mm, 3),
        "w_over_f":      round(w_over_f, 5),
        "lim_w_over_f":  W_OVER_F_MAX,
        "k_H_geom":      round(k_H_geom, 4) if k_H_geom < 1e6 else 1e6,
        "ok_geometria":  ok_geom,
        # P-Δ pilar (imperfeição)
        "e_0_mm":        round(e_0 * 1000, 2),
        "M_imp_pilar_kNm": round(M_imp_pilar, 4),
        "eta_M_imp_pilar": round(eta_M_imp, 4),
        # Resultado
        "metodo_analise": metodo,
        "conclusao":     conclusao,
        "eta":           round(min(eta_gov, 9.99), 4),
        "ok":            ok,
        "nota": (
            "Empuxo H de 1.ª ordem (Castigliano) já é o esforço horizontal "
            "dominante; a força nocional e o P-Δ global são tipicamente "
            "desprezáveis em pórticos baixos biarticulados com H elevado. "
            "Estabilidade de barra: EC5 §6.3.2/§6.3.3 (pipeline ELU)."
        ),
    }


def relatorio_estabilidade_global(res: dict) -> None:
    """Imprime relatório da verificação global."""
    print("=" * 68)
    print("  ESTABILIDADE GLOBAL — P-Δ / NOCIONAIS / α_cr")
    print(f"  {res['norma']}")
    print("=" * 68)
    print(f"  Combinação : {res['comb']}")
    print(f"  H_Ed       = {res['H_Ed_kN']:.1f} kN  (empuxo 1.ª ordem)")
    print(f"  V_portal   = {res['V_portal_kN']:.1f} kN  |  "
          f"N_viga = {res['N_viga_kN']:.1f} kN")
    print(f"  f_c        = {res['f_c_m']:.3f} m  (freche centroidal)")
    print()
    print("  ── Forças nocionais (EN 1993-1-1 §5.3.2) ──")
    print(f"    φ = {res['phi']:.5f}  "
          f"(α_h={res['alpha_h']:.3f}, α_m={res['alpha_m']:.3f})")
    print(f"    H_imp = {res['H_imp_kN']:.2f} kN  |  "
          f"H_imp/H_Ed = {res['H_imp_over_H']:.4f}  "
          f"(lim {res['lim_H_imp']:.2f})  "
          f"{'✓' if res['ok_nocional'] else '✗'}")
    print()
    print("  ── Sistema ──")
    print(f"    non-sway = {res.get('sistema_non_sway', True)}")
    print(f"    {res.get('nota_sistema', '')}")
    print()
    print("  ── Fator de carga crítica α_cr ──")
    print(f"    α_cr,arco (L_ef=L/2) = {res['alpha_cr']:.1f}  "
          f"(N_cr={res.get('N_cr_arco_kN', 0):.0f} kN)  "
          f"(mín. {res['alpha_cr_min']:.0f})  "
          f"{'✓' if res['ok_alpha_cr'] else '✗'}")
    print(f"    k_II,arco = {res['k_II']:.4f}")
    print(f"    α_cr,barra (info) = {res.get('alpha_cr_barra', 0):.1f}  "
          f"[viga h0={res['alpha_cr_viga_h0']:.1f}, "
          f"ap={res['alpha_cr_viga_ap']:.1f}, "
          f"pilar={res['alpha_cr_pilar']:.1f}]")
    print(f"    → {res.get('nota_alpha_cr_barra', '')}")
    print()
    print("  ── Geometria do arco (abaixamento do freche) ──")
    print(f"    w_Ed = {res['w_Ed_mm']:.2f} mm  |  "
          f"w/f_c = {res['w_over_f']:.5f}  "
          f"(lim {res['lim_w_over_f']:.2f})  "
          f"{'✓' if res['ok_geometria'] else '✗'}")
    print(f"    k_H,geom ≈ {res['k_H_geom']:.4f}")
    print()
    print("  ── Imperfeição no pilar (P-Δ local) ──")
    print(f"    e_0 = {res['e_0_mm']:.2f} mm  |  "
          f"M_imp = {res['M_imp_pilar_kNm']:.3f} kN·m  |  "
          f"η_M ≈ {res['eta_M_imp_pilar']:.4f}")
    print()
    ok = "✓" if res["ok"] else "✗"
    print(f"  {ok} Método: {res['metodo_analise']}  |  η_critério = {res['eta']:.4f}")
    print(f"  → {res['conclusao']}")
    print("=" * 68)
