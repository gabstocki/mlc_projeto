"""
checks/els/deflection_els.py — Verificações ELS completas.

Diagramas M_g(x) e M_q(x) da análise biarticulada (continuidade na cumeeira).
Flecha total = flexão + cisalhamento (teoria de Timoshenko), com E = E_mean e
G = G_mean (EC5 §2.2.3):

    w(x) = w_flexão(x) + w_cisalhamento(x)
    w_flexão        : ∫∫ M(x)/(E·I(x)) dx²          (dupla integração de κ=M/EI)
    w_cisalhamento  : ∫ κ_s·V(x)/(G·A(x)) dx         (EC5 §2.2.3(2) e Anexo B)
                      κ_s = 1,2 (seção retangular), V = dM/dx

A parcela de cisalhamento NÃO é desprezível em vigas altas de vão médio
(h_ap/L ≈ 0,14, E/G ≈ 16): responde por parcela significativa da flecha total.

Verificações ELS (EN 1990 §6.5) — cobertura categoria H (ψ0=ψ1=ψ2=0):
    S1: G + Q  — característico (sem vento; Q e W não concomitantes) → w_inst ≤ L/300
    S2: G      — frequente (ψ1=0 ⇒ sem Q; = quase-permanente para cat. H)
    S3: G      — quase-permanente (ψ2=0; base da fluência)

Flecha final com fluência (EC5 §2.3.2.2):
    w_fin = w_G·(1+k_def) + w_Q·(1+ψ₂·k_def)
    ψ₂ = 0,0 para sobrecarga de cobertura inacessível
    w_net,fin = w_fin  (sem contra-flecha)
    w_net,fin ≤ L/250

Referência: EC5 §2.3.2.2, Tab. 7.2 | EN 1990 §6.5
"""

from __future__ import annotations

import numpy as np
from scipy.integrate import cumulative_trapezoid

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.loads     import Carregamentos, analisar_biarticulada


# ── Integração numérica da flecha ─────────────────────────────────────────────

def flecha_numerica(
    geo:   GeometriaViga,
    mat:   GlulamMaterial,
    M_x:   np.ndarray,
    x:     np.ndarray,
    *,
    incluir_cisalhamento: bool = True,
    k_s:   float = 1.2,
) -> tuple[float, np.ndarray, np.ndarray, np.ndarray]:
    """
    Flecha por integração numérica — flexão + cisalhamento (Timoshenko).

    Flexão (EC5 §2.2.3, E = E_mean):
        κ(x) = M(x)/(E·I(x)) ; w_b por dupla integração de κ.
        Condições de contorno de viga BIARTICULADA: w(0) = w(L) = 0.
        A rotação nos apoios NÃO é nula — a constante de integração da
        rotação é absorvida pelo termo linear em w. (Corrigir também θ
        imporia rotação nula nos apoios, i.e. engaste bi-engastado, e
        subestimaria a flecha em ~5× para carga uniforme.)

    Cisalhamento (EC5 §2.2.3(2) e Anexo B, G = G_mean):
        γ(x) = κ_s·V(x)/(G·A(x)) ,  V(x) = dM/dx ,  κ_s = 1,2 (retangular)
        w_s(x) = ∫ γ dx , com o sinal coerente com a convenção w'' = +M/EI
        usada na flexão, de modo que flexão e cisalhamento SOMAM no mesmo
        sentido. Usa A(x) da seção variável.

    Args:
        geo : Geometria da viga (fornece I(x), A(x) e L)
        mat : Material (E_mean, G_mean)
        M_x : Diagrama de momento (N·m) nos pontos x
        x   : Coordenadas dos pontos (m)
        incluir_cisalhamento : inclui a parcela de cortante (default True)
        k_s : fator de forma do cortante (1,2 para seção retangular)

    Returns:
        (w_max_m, w_x, w_flexao_x, w_cisalhamento_x)
        w_x = w_flexao_x + w_cisalhamento_x (perfis completos, m)
    """
    E     = mat.E0_mean
    I_x   = geo.I(x)          # m⁴ — seção variável
    kappa = M_x / (E * I_x)   # curvatura (1/m)

    # ── Parcela de flexão (BIARTICULADA: só uma correção linear, em w) ────────
    theta = cumulative_trapezoid(kappa, x, initial=0.0)
    w_b   = cumulative_trapezoid(theta, x, initial=0.0)
    w_b  -= w_b[-1] * x / geo.L

    # ── Parcela de cisalhamento (Timoshenko — EC5 §2.2.3(2)/Anexo B) ──────────
    if incluir_cisalhamento:
        G     = mat.G_mean
        A_x   = geo.A(x)                 # m² — seção variável
        V_x   = np.gradient(M_x, x)      # N — cortante = dM/dx
        gamma = -k_s * V_x / (G * A_x)   # distorção (sinal coerente c/ w''=+M/EI)
        w_s   = cumulative_trapezoid(gamma, x, initial=0.0)
        w_s  -= w_s[-1] * x / geo.L
    else:
        w_s = np.zeros_like(w_b)

    w = w_b + w_s
    return float(np.max(np.abs(w))), w, w_b, w_s


# ── Verificação ELS completa ──────────────────────────────────────────────────

def verificar_ELS(
    geo:       GeometriaViga,
    mat:       GlulamMaterial,
    load:      Carregamentos,
    w_camber:  float = 0.0,
) -> dict:
    """
    Verificação ELS completa — viga biarticulada monolítica.

    Calcula M_g(x) e M_q(x) pela análise biarticulada e integra
    numericamente para obter flechas com seção variável I(x).

    Args:
        geo      : Geometria da viga
        mat      : Material com k_def da classe de serviço
        load     : Carregamentos com combinações ELS
        w_camber : Contra-flecha de fábrica (m) — 0,0 sem contra-flecha

    Returns:
        dict com flechas por combinação, flecha final, limites e η
    """
    L         = geo.L
    k_def     = mat.k_def
    # Categoria H (EN 1990 Tab. A1.1): ψ2,Q = ψ2,W = 0. Q e vento NÃO concomitantes
    # (EN 1991-1-1 §3.3.2(1)) ⇒ ação variável dominante é Q OU vento (NBR 6123).
    psi_2_Q   = 0.0
    psi_2_W   = 0.0
    k_s_forma = 1.2                              # fator de forma do cortante (retangular)
    lim_inst  = L / 300
    lim_fin   = L / 250

    alpha_rad = geo.alpha_rad
    h0        = geo.h0
    h_ap      = geo.h_ap

    # ── Flecha assinada no ponto de máximo |w| (superposição elástica) ────────
    # Retorna (w_total, w_flexão, w_cisalhamento) no ponto de |w_total| máximo.
    def _parcelas_signed(
        q_esq: float, q_dir: float | None = None
    ) -> tuple[float, float, float]:
        r = analisar_biarticulada(
            q=0.5 * (q_esq + (q_dir if q_dir is not None else q_esq)),
            L=L, h0=h0, h_ap=h_ap, alpha_rad=alpha_rad, b=geo.b,
            q_esq=q_esq, q_dir=(q_dir if q_dir is not None else q_esq),
        )
        M_x = np.interp(geo.x, r["x"], r["M_x"]) * 1e3   # N·m
        _, w_x, w_b_x, w_s_x = flecha_numerica(geo, mat, M_x, geo.x)
        i = int(np.argmax(np.abs(w_x)))
        return float(w_x[i]), float(w_b_x[i]), float(w_s_x[i])

    def _w_signed(q_esq: float, q_dir: float | None = None) -> float:
        return _parcelas_signed(q_esq, q_dir)[0]

    # ── Parcelas isoladas (superponíveis) ─────────────────────────────────────
    w_G_s, w_G_b_s, w_G_v_s = _parcelas_signed(load.g_k)   # permanente (sentido ↓)
    w_Q_s = _w_signed(load.q_k)                 # sobrecarga
    s     = 1.0 if w_G_s >= 0 else -1.0         # sinal do sentido descendente
    w_G   = s * w_G_s                           # ↓ positiva
    w_Q   = s * w_Q_s

    # ── Vento (NBR 6123) como ação dominante do ELS característico ─────────────
    # Para cada padrão Cpe: flecha sob o vento característico (γ=1,0) isolado.
    A_trib = load.area_trib
    w_W_dn_list: list[float] = []
    wewd_list: list[tuple[float, float]] = []
    padroes = list(getattr(load, "padroes_vento", []) or [])
    for p in padroes:
        we = float(p.get("w_esq_kNm2", 0.0)) * A_trib   # kN/m (↓ +, sucção −)
        wd = float(p.get("w_dir_kNm2", 0.0)) * A_trib
        w_W_dn_list.append(s * _w_signed(we, wd))       # ↓ positiva
        wewd_list.append((we, wd))
    # Vento-pressão governante (mais descendente) e sucção governante (mais ↑)
    w_W_press = max(w_W_dn_list) if w_W_dn_list else 0.0
    w_W_suc   = min(w_W_dn_list) if w_W_dn_list else 0.0
    we_gov, wd_gov = (wewd_list[int(np.argmax(w_W_dn_list))]
                      if w_W_dn_list else (0.0, 0.0))

    # ── Característico (instantâneo) — governante descendente ──────────────────
    w_char_Q = w_G + w_Q                        # G + Q
    w_char_W = w_G + w_W_press                  # G + W (pressão, NBR 6123)
    w_S1     = max(w_char_Q, w_char_W)           # governa a flecha ↓
    gov_char = "vento" if w_char_W >= w_char_Q else "sobrecarga Q"
    # Sucção (uplift) — informativo (o EC5 limita a flecha descendente)
    w_char_up = w_G + w_W_suc                    # pode ser < 0 (↑)

    # ── Separação flexão vs cisalhamento da combinação S1 governante ──────────
    # (EC5 §2.2.3(2)/Anexo B) — analisa a combinação característica que governa
    # como um único caso de carga e mede a contribuição do cortante.
    g_k = load.g_k
    if gov_char == "vento":
        _, w_S1_b_s, w_S1_v_s = _parcelas_signed(g_k + we_gov, g_k + wd_gov)
    else:
        _, w_S1_b_s, w_S1_v_s = _parcelas_signed(g_k + load.q_k)
    w_S1_flex  = s * w_S1_b_s                    # parcela de flexão (↓ +)
    w_S1_cis   = s * w_S1_v_s                    # parcela de cisalhamento (↓ +)
    pct_cis_S1 = (abs(w_S1_cis) / abs(w_S1) * 100.0) if abs(w_S1) > 1e-12 else 0.0
    # Permanente (base da fluência) — contribuição do cortante
    w_G_flex   = s * w_G_b_s
    w_G_cis    = s * w_G_v_s
    pct_cis_G  = (abs(w_G_cis) / abs(w_G) * 100.0) if abs(w_G) > 1e-12 else 0.0

    # ── Flecha final com fluência — EC5 §2.3.2.2 ──────────────────────────────
    # Ação variável dominante (ψ2=0 para Q e vento): a de maior flecha ↓.
    w_var_fin = max(w_Q, w_W_press)
    var_gov   = "vento" if w_W_press >= w_Q else "sobrecarga Q"
    w_fin     = w_G * (1 + k_def) + w_var_fin    # ψ2·k_def = 0
    w_net_fin = w_fin - w_camber

    # ── Taxas de utilização ───────────────────────────────────
    eta_S1      = w_S1      / lim_inst
    eta_net_fin = w_net_fin / lim_fin
    eta         = max(eta_S1, eta_net_fin)
    verif_gov   = "S1_inst" if eta_S1 >= eta_net_fin else "net_fin"

    return {
        # Geometria
        "L_m":           geo.L,
        "h_ap_m":        geo.h_ap,
        "b_m":           geo.b,
        # Material / ψ
        "k_def":         k_def,
        "psi_2_Q":       psi_2_Q,
        "psi_2_W":       psi_2_W,
        "E_mean_GPa":    round(mat.E0_mean / 1e9,  3),
        # Flechas por parcela / combinação (mm, ↓ positiva)
        "w_S1_mm":       round(w_S1  * 1000,        2),   # característico ↓ governante
        # Separação flexão vs cisalhamento (EC5 §2.2.3(2)/Anexo B)
        "k_s":           k_s_forma,
        "G_mean_GPa":    round(mat.G_mean / 1e9,    3),
        "w_S1_flex_mm":  round(w_S1_flex * 1000,    2),   # S1: parcela de flexão
        "w_S1_cis_mm":   round(w_S1_cis  * 1000,    2),   # S1: parcela de cisalhamento
        "pct_cis_S1":    round(pct_cis_S1,          1),   # % do cortante em S1
        "w_G_flex_mm":   round(w_G_flex * 1000,     2),
        "w_G_cis_mm":    round(w_G_cis  * 1000,     2),
        "pct_cis_G":     round(pct_cis_G,           1),
        "w_G_mm":        round(w_G   * 1000,        2),
        "w_Q1_mm":       round(w_Q   * 1000,        2),
        "w_W_press_mm":  round(w_W_press * 1000,    2),   # vento pressão (NBR 6123)
        "w_W_suc_mm":    round(w_W_suc  * 1000,     2),   # vento sucção (↑ se <0)
        "w_char_Q_mm":   round(w_char_Q * 1000,     2),   # G+Q
        "w_char_W_mm":   round(w_char_W * 1000,     2),   # G+W
        "w_char_up_mm":  round(w_char_up * 1000,    2),   # G+W_sucção (informativo)
        "gov_caracteristico": gov_char,
        "n_padroes_vento": len(padroes),
        # Variável dominante do w_fin
        "w_var_fin_mm":  round(w_var_fin * 1000,    2),
        "var_gov_fin":   var_gov,
        # Fluência
        "w_fin_mm":      round(w_fin     * 1000,    2),
        "w_net_fin_mm":  round(w_net_fin * 1000,    2),
        "w_camber_mm":   round(w_camber  * 1000,    2),
        # Limites
        "lim_inst_mm":   round(lim_inst  * 1000,    2),
        "lim_fin_mm":    round(lim_fin   * 1000,    2),
        # Verificações
        "eta_S1":        round(eta_S1,               4),
        "eta_net_fin":   round(eta_net_fin,           4),
        "eta":           round(eta,                   4),
        "ok":            eta <= 1.0,
        "verif_gov":     verif_gov,
        # Referência
        "norma":         "EC5 §2.3.2.2, Tab. 7.2 | EN 1990 §6.5 | NBR 6123 (vento)",
        "sistema":       "biarticulada",
    }


# ── Relatório ─────────────────────────────────────────────────────────────────

def relatorio_ELS(resultado: dict) -> None:
    """Imprime relatório formatado da verificação ELS."""
    print("=" * 70)
    print("  VERIFICAÇÃO ELS — EN 1990 §6.5 + EC5 §2.3.2.2 + Tab. 7.2")
    print(f"  Sistema: {resultado['sistema']}")
    print("=" * 70)
    print(f"\n  Geometria: L={resultado['L_m']} m | "
          f"h_ap={resultado['h_ap_m']:.3f} m | b={resultado['b_m']} m")
    print(f"  k_def = {resultado['k_def']:.2f} | "
          f"E_mean = {resultado['E_mean_GPa']:.2f} GPa\n")

    print("  Flechas por parcela (↓ positiva) — cat. H, Q e vento não concomitantes:")
    print(f"    w(G)          = {resultado['w_G_mm']:>7.2f} mm")
    print(f"    w(Q)          = {resultado['w_Q1_mm']:>7.2f} mm")
    print(f"    w(vento press.)= {resultado['w_W_press_mm']:>6.2f} mm  (NBR 6123)")
    print(f"    w(vento sucção)= {resultado['w_W_suc_mm']:>6.2f} mm  (↑ se <0)\n")

    print("  Característico (instantâneo) — governante descendente:")
    print(f"    G+Q = {resultado['w_char_Q_mm']:.2f} mm | "
          f"G+W = {resultado['w_char_W_mm']:.2f} mm "
          f"→ governa {resultado['gov_caracteristico']}")
    print(f"    w(S1) = {resultado['w_S1_mm']:.2f} mm ≤ L/300 = "
          f"{resultado['lim_inst_mm']:.2f} mm")
    print(f"    (uplift G+W_sucção = {resultado['w_char_up_mm']:.2f} mm — informativo)\n")

    print("  Separação flexão vs cisalhamento (EC5 §2.2.3(2)/Anexo B, κ_s="
          f"{resultado['k_s']:.1f}, G_mean={resultado['G_mean_GPa']:.2f} GPa):")
    print(f"    S1: flexão = {resultado['w_S1_flex_mm']:.2f} mm | "
          f"cisalhamento = {resultado['w_S1_cis_mm']:.2f} mm "
          f"({resultado['pct_cis_S1']:.1f}% do total)")
    print(f"    G : flexão = {resultado['w_G_flex_mm']:.2f} mm | "
          f"cisalhamento = {resultado['w_G_cis_mm']:.2f} mm "
          f"({resultado['pct_cis_G']:.1f}% do total)\n")

    print("  Fluência — EC5 §2.3.2.2 (ψ2=0):")
    print(f"    w_fin = {resultado['w_G_mm']:.2f}·(1+{resultado['k_def']:.2f}) + "
          f"{resultado['w_var_fin_mm']:.2f} ({resultado['var_gov_fin']})")
    print(f"    w_fin = {resultado['w_fin_mm']:.2f} mm")
    print(f"    w_net,fin = {resultado['w_net_fin_mm']:.2f} mm  "
          f"(sem contra-flecha)\n")

    ok_s1  = "✓" if resultado["eta_S1"]     <= 1.0 else "✗"
    ok_fin = "✓" if resultado["eta_net_fin"] <= 1.0 else "✗"
    print("  Verificações:")
    print(f"    {ok_s1} w(S1) ≤ L/300:     "
          f"{resultado['w_S1_mm']:>7.2f} ≤ {resultado['lim_inst_mm']:.2f} mm  "
          f"η = {resultado['eta_S1']:.4f}")
    print(f"    {ok_fin} w_net,fin ≤ L/250: "
          f"{resultado['w_net_fin_mm']:>7.2f} ≤ {resultado['lim_fin_mm']:.2f} mm  "
          f"η = {resultado['eta_net_fin']:.4f}")

    status = "✓ APROVADO" if resultado["ok"] else "✗ REPROVADO"
    print(f"\n  η = {resultado['eta']:.4f}  ({resultado['verif_gov']} governa)"
          f"  → {status}")
    print("\n  Nota: vibração EC5 §7.3 não aplicável — cobertura industrial.")
    print("=" * 70)


# ── Execução direta ───────────────────────────────────────────────────────────

if __name__ == "__main__":

    from mlc_projeto.core.geometry  import GeometriaViga
    from mlc_projeto.core.materials import GlulamMaterial
    from mlc_projeto.core.wind      import ParametrosVento
    from mlc_projeto.core.loads     import carregamentos_com_vento

    geo = GeometriaViga(L=20.25, h0=0.60, alpha_deg=4.5, b=0.26)
    mat = GlulamMaterial(classe="GL24h", classe_servico=3, duracao="longa")

    params_vento = ParametrosVento(
        V0=45.0, S1=1.0, categoria="IV", classe="B", S3=1.0,
        L=20.25, H1=1.0, h=7.0, dist_portico=5.75,
    )

    load = carregamentos_com_vento(
        geo=geo, mat=mat,
        g_area=1.50, q_area=0.25,
        L_t=5.75, params_vento=params_vento,
    )

    resultado = verificar_ELS(geo, mat, load, w_camber=0.0)
    relatorio_ELS(resultado)