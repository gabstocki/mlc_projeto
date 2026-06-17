"""
checks/els/deflection_els.py — Verificações ELS completas. v2

ATUALIZAÇÃO v2 — Pórtico de 3 rótulas:
    Os diagramas M_g(x) e M_q(x) agora são calculados pela análise
    estrutural correta de 3 rótulas via analisar_3rotulas().

    A integração numérica w = ∫∫M/(EI)dx² permanece idêntica.
    O que muda é APENAS o M(x) de entrada — não a mecânica do cálculo.

    Consequência: flechas menores que no pórtico rígido porque
    M_max é ~75% menor. A flecha raramente governa neste sistema.

Verificações ELS (EN 1990 §6.5):
    S1: G + Q + 0,6W  — característico → w_inst ≤ L/300
    S2: G + 0,5Q      — frequente (informativo)
    S3: G             — quase-permanente (base da fluência)

Flecha final com fluência (EC5 §2.3.2.2):
    w_fin = w_G·(1+k_def) + w_Q·(1+ψ₂·k_def)
    ψ₂ = 0,0 para sobrecarga de cobertura inacessível
    w_net,fin = w_fin  (sem contra-flecha)
    w_net,fin ≤ L/250

Referência: EC5 §2.3.2.2, Tab. 7.2 | EN 1990 §6.5
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.integrate import cumulative_trapezoid

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.loads     import Carregamentos, analisar_3rotulas


# ── Integração numérica da flecha ─────────────────────────────────────────────

def flecha_numerica(
    geo:   GeometriaViga,
    mat:   GlulamMaterial,
    M_x:   np.ndarray,
    x:     np.ndarray,
) -> tuple[float, np.ndarray]:
    """
    Flecha por integração numérica de κ(x) = M(x)/(E·I(x)).

    Usa E_mean para ELS conforme EC5 §2.2.3.
    Condições de contorno: w(0) = w(L) = 0.

    Args:
        geo : Geometria da viga (fornece I(x) e L)
        mat : Material (E_mean)
        M_x : Diagrama de momento (N·m) nos pontos x
        x   : Coordenadas dos pontos (m)

    Returns:
        (w_max_m, w_x) — flecha máxima e perfil completo
    """
    E     = mat.E0_mean
    I_x   = geo.I(x)          # m⁴ — seção variável
    kappa = M_x / (E * I_x)   # curvatura (1/m)

    theta = cumulative_trapezoid(kappa, x, initial=0.0)
    theta -= theta[-1] * x / geo.L

    w = cumulative_trapezoid(theta, x, initial=0.0)
    w -= w[-1] * x / geo.L

    return float(np.max(np.abs(w))), w


# ── Verificação ELS completa ──────────────────────────────────────────────────

def verificar_ELS(
    geo:       GeometriaViga,
    mat:       GlulamMaterial,
    load:      Carregamentos,
    w_camber:  float = 0.0,
) -> dict:
    """
    Verificação ELS completa — pórtico de 3 rótulas.

    Calcula M_g(x) e M_q(x) pela análise de 3 rótulas e integra
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
    psi_2     = 0.0   # cobertura inacessível — EN 1990 Tab. A1.1
    lim_inst  = L / 300
    lim_fin   = L / 250

    alpha_rad = geo.alpha_rad
    h0        = geo.h0
    h_ap      = geo.h_ap

    # ── Combinações ELS ───────────────────────────────────────
    comb_S1 = load.combinacoes["ELS_S1"]
    comb_S2 = load.combinacoes["ELS_S2"]

    # ── Diagramas M(x) pela análise de 3 rótulas ─────────────
    def _M_interp(q: float) -> tuple[np.ndarray, np.ndarray]:
        """Retorna (x, M_Nm) interpolados nos pontos de geo."""
        r = analisar_3rotulas(q, L, h0, h_ap, alpha_rad)
        # Interpolar nos pontos de geo.x para manter coerência com I(x)
        M_interp = np.interp(geo.x, r["x"], r["M_x"]) * 1e3  # N·m
        return geo.x, M_interp

    x_S1, M_S1_Nm = _M_interp(comb_S1.q_tot)
    x_S2, M_S2_Nm = _M_interp(comb_S2.q_tot)
    x_g,  M_g_Nm  = _M_interp(load.g_k)
    x_q,  M_q_Nm  = _M_interp(load.q_k)

    # ── Flechas instantâneas ──────────────────────────────────
    w_S1, w_S1_x = flecha_numerica(geo, mat, M_S1_Nm, x_S1)
    w_S2, _      = flecha_numerica(geo, mat, M_S2_Nm, x_S2)
    w_G,  _      = flecha_numerica(geo, mat, M_g_Nm,  x_g)
    w_Q1, _      = flecha_numerica(geo, mat, M_q_Nm,  x_q)

    # ── Flecha final com fluência — EC5 §2.3.2.2 ─────────────
    w_fin     = w_G * (1 + k_def) + w_Q1 * (1 + psi_2 * k_def)
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
        # Material
        "k_def":         k_def,
        "E_mean_GPa":    round(mat.E0_mean / 1e9,  3),
        # Flechas por combinação (mm)
        "w_S1_mm":       round(w_S1  * 1000,        2),
        "w_S2_mm":       round(w_S2  * 1000,        2),
        "w_G_mm":        round(w_G   * 1000,        2),
        "w_Q1_mm":       round(w_Q1  * 1000,        2),
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
        # Combinações
        "q_S1_kNm":      round(comb_S1.q_tot,        4),
        "q_S2_kNm":      round(comb_S2.q_tot,        4),
        "q_g_kNm":       round(load.g_k,             4),
        "q_q_kNm":       round(load.q_k,             4),
        # Referência
        "norma":         "EC5 §2.3.2.2, Tab. 7.2 | EN 1990 §6.5",
        "sistema":       "3 rótulas",
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

    print(f"  Combinações ELS (3 rótulas — M_max ≈ 75% menor que pórtico rígido):")
    print(f"    S1 (caracter.): q = {resultado['q_S1_kNm']:+.4f} kN/m")
    print(f"    S2 (frequente): q = {resultado['q_S2_kNm']:+.4f} kN/m")
    print(f"    G (permanente): q = {resultado['q_g_kNm']:+.4f} kN/m")
    print(f"    Q (variável):   q = {resultado['q_q_kNm']:+.4f} kN/m\n")

    print(f"  Flechas instantâneas:")
    print(f"    w(S1) = {resultado['w_S1_mm']:>7.2f} mm  "
          f"← limite L/300 = {resultado['lim_inst_mm']:.2f} mm")
    print(f"    w(S2) = {resultado['w_S2_mm']:>7.2f} mm  (frequente — informativo)")
    print(f"    w(G)  = {resultado['w_G_mm']:>7.2f} mm")
    print(f"    w(Q)  = {resultado['w_Q1_mm']:>7.2f} mm\n")

    print(f"  Fluência — EC5 §2.3.2.2:")
    print(f"    w_fin = {resultado['w_G_mm']:.2f}·"
          f"(1+{resultado['k_def']:.2f}) + {resultado['w_Q1_mm']:.2f}")
    print(f"    w_fin = {resultado['w_fin_mm']:.2f} mm")
    print(f"    w_net,fin = {resultado['w_net_fin_mm']:.2f} mm  "
          f"(sem contra-flecha)\n")

    ok_s1  = "✓" if resultado["eta_S1"]     <= 1.0 else "✗"
    ok_fin = "✓" if resultado["eta_net_fin"] <= 1.0 else "✗"
    print(f"  Verificações:")
    print(f"    {ok_s1} w(S1) ≤ L/300:     "
          f"{resultado['w_S1_mm']:>7.2f} ≤ {resultado['lim_inst_mm']:.2f} mm  "
          f"η = {resultado['eta_S1']:.4f}")
    print(f"    {ok_fin} w_net,fin ≤ L/250: "
          f"{resultado['w_net_fin_mm']:>7.2f} ≤ {resultado['lim_fin_mm']:.2f} mm  "
          f"η = {resultado['eta_net_fin']:.4f}")

    status = "✓ APROVADO" if resultado["ok"] else "✗ REPROVADO"
    print(f"\n  η = {resultado['eta']:.4f}  ({resultado['verif_gov']} governa)"
          f"  → {status}")
    print(f"\n  Nota: vibração EC5 §7.3 não aplicável — cobertura industrial.")
    print("=" * 70)


# ── Execução direta ───────────────────────────────────────────────────────────

if __name__ == "__main__":

    from mlc_projeto.core.geometry  import GeometriaViga
    from mlc_projeto.core.materials import GlulamMaterial
    from mlc_projeto.core.wind      import ParametrosVento
    from mlc_projeto.core.loads     import carregamentos_com_vento

    geo = GeometriaViga(L=20.25, h0=0.60, alpha_deg=4.5, b=0.26)
    mat = GlulamMaterial(classe="GL24h", classe_servico=2, duracao="longa")

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