"""
checks/els/deflection_els.py — Verificações ELS completas.

Calcula flechas para todas as combinações ELS conforme EN 1990 §6.5,
usando as combinações montadas em loads.py.

Sem verificação de vibração (EC5 §7.3) — aplicável apenas a pisos,
não a coberturas industriais sem ocupação humana.

Combinações ELS (EN 1990 §6.5):
    S1: G + Q + 0,6W   — característico → w_inst ≤ L/300
    S2: G + 0,5Q        — frequente      → indicativo
    S3: G               — quase-permanente → base da fluência

Flecha final com fluência (EC5 §2.3.2.2):
    w_fin = w_G·(1+k_def) + w_Q·(1+ψ₂·k_def)
    ψ₂ = 0,0 para sobrecarga de cobertura inacessível

Limite:
    w_inst (S1) ≤ L/300   (EC5 Tab. 7.2)
    w_net,fin   ≤ L/250   (EC5 Tab. 7.2) — sem contra-flecha

Nota sobre contra-flecha:
    w_net,fin = w_fin (sem contra-flecha de fábrica)
    Se houver contra-flecha w_c: w_net,fin = w_fin - w_c

Referência: EC5 §2.3.2.2, Tab. 7.2 | EN 1990 §6.5
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.integrate import cumulative_trapezoid

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.loads     import Carregamentos


# ── Integração numérica da flecha ─────────────────────────────────────────────

def flecha_numerica(
    geo:  GeometriaViga,
    mat:  GlulamMaterial,
    q:    float,
) -> tuple[float, np.ndarray]:
    """
    Flecha máxima por integração numérica para carga uniforme q (kN/m).

    Usa E_mean para ELS conforme EC5 §2.2.3.
    Condições de contorno: w(0) = w(L) = 0 (bi-apoiada).

    Args:
        geo : Geometria da viga
        mat : Material
        q   : Carga uniforme (kN/m) — positivo = para baixo

    Returns:
        (w_max_m, w_x) — flecha máxima (m) e perfil (m)
    """
    x     = geo.x
    L     = geo.L
    E     = mat.E0_mean                  # Pa — ELS usa E_mean
    I_x   = geo.I(x)                     # m⁴
    M_x   = q * x * (L - x) / 2 * 1e3  # N·m

    kappa = M_x / (E * I_x)             # curvatura (1/m)

    theta = cumulative_trapezoid(kappa, x, initial=0.0)
    theta -= theta[-1] * x / L

    w = cumulative_trapezoid(theta, x, initial=0.0)
    w -= w[-1] * x / L

    return float(np.max(np.abs(w))), w


# ── Verificação ELS completa ──────────────────────────────────────────────────

def verificar_ELS(
    geo:        GeometriaViga,
    mat:        GlulamMaterial,
    load:       Carregamentos,
    w_camber:   float = 0.0,
) -> dict:
    """
    Verificação ELS completa com todas as combinações EN 1990.

    Usa as combinações S1, S2, S3 montadas em Carregamentos.
    Material usa k_def da classe de serviço (EC5 Tab. 3.2).

    Args:
        geo      : Geometria da viga
        mat      : Material — k_def por classe de serviço
        load     : Carregamentos com combinações ELS montadas
        w_camber : Contra-flecha de fábrica (m) — 0,0 sem contra-flecha

    Returns:
        dict com flechas por combinação, flecha final, limites e η
    """
    L     = geo.L
    k_def = mat.k_def
    psi_2 = 0.0   # sobrecarga cobertura inacessível — EN 1990 Tab. A1.1

    # Limites EC5 Tab. 7.2
    lim_inst   = L / 300
    lim_fin    = L / 250

    # ── Flechas por combinação ELS ────────────────────────────
    comb_S1 = load.combinacoes["ELS_S1"]
    comb_S2 = load.combinacoes["ELS_S2"]
    comb_S3 = load.combinacoes["ELS_S3"]

    w_S1_max, w_S1_x = flecha_numerica(geo, mat, comb_S1.q_tot)
    w_S2_max, w_S2_x = flecha_numerica(geo, mat, comb_S2.q_tot)
    w_S3_max, w_S3_x = flecha_numerica(geo, mat, comb_S3.q_tot)

    # ── Componentes separadas para fluência ───────────────────
    # Permanente: S3 = G
    # Variável dominante: Q separado
    w_G_max,  _ = flecha_numerica(geo, mat, load.g_k)
    w_Q1_max, _ = flecha_numerica(geo, mat, load.q_k)

    # ── Flecha final com fluência — EC5 §2.3.2.2 ─────────────
    # w_fin = w_G·(1+k_def) + w_Q1·(1+ψ₂·k_def)
    # ψ₂ = 0,0 → w_fin = w_G·(1+k_def) + w_Q1
    w_fin = w_G_max * (1 + k_def) + w_Q1_max * (1 + psi_2 * k_def)

    # ── Flecha líquida final — sem contra-flecha ──────────────
    w_net_fin = w_fin - w_camber

    # ── Taxas de utilização ───────────────────────────────────
    eta_S1      = w_S1_max   / lim_inst   # S1 ≤ L/300
    eta_net_fin = w_net_fin  / lim_fin    # w_fin ≤ L/250

    eta = max(eta_S1, eta_net_fin)
    verif_gov = "S1_inst" if eta_S1 >= eta_net_fin else "w_net_fin"

    return {
        # Geometria
        "L_m":          geo.L,
        "h_ap_m":       geo.h_ap,
        "b_m":          geo.b,
        # Material
        "k_def":        k_def,
        "E_mean_GPa":   round(mat.E0_mean / 1e9, 3),
        # Flechas por combinação (mm)
        "w_S1_mm":      round(w_S1_max  * 1000, 2),
        "w_S2_mm":      round(w_S2_max  * 1000, 2),
        "w_S3_mm":      round(w_S3_max  * 1000, 2),
        # Componentes para fluência
        "w_G_mm":       round(w_G_max   * 1000, 2),
        "w_Q1_mm":      round(w_Q1_max  * 1000, 2),
        # Fluência
        "w_fin_mm":     round(w_fin     * 1000, 2),
        "w_net_fin_mm": round(w_net_fin * 1000, 2),
        "w_camber_mm":  round(w_camber  * 1000, 2),
        # Limites
        "lim_inst_mm":  round(lim_inst  * 1000, 2),
        "lim_fin_mm":   round(lim_fin   * 1000, 2),
        # Verificações
        "eta_S1":       round(eta_S1,       4),
        "eta_net_fin":  round(eta_net_fin,  4),
        "eta":          round(eta,          4),
        "ok":           eta <= 1.0,
        "verif_gov":    verif_gov,
        # Combinações
        "q_S1_kNm":    round(comb_S1.q_tot, 4),
        "q_S2_kNm":    round(comb_S2.q_tot, 4),
        "q_S3_kNm":    round(comb_S3.q_tot, 4),
        # Referência
        "norma":        "EC5 §2.3.2.2, Tab. 7.2 | EN 1990 §6.5",
    }


# ── Varredura ELS integrada ao ELU ───────────────────────────────────────────

def varrer_ELS(
    mat_longa:    GlulamMaterial,
    load:         Carregamentos,
    h0_range:     tuple = (0.60, 1.60, 0.10),
    alpha_range:  tuple = (3.0,  9.0,  0.5),
    b_range:      tuple = (0.14, 0.32, 0.02),
    eta_max:      float = 1.0,
) -> pd.DataFrame:
    """
    Varre (h0, α, b) e verifica apenas as condições ELS.

    Usa mat_longa (k_mod duração longa) para E_mean e k_def.

    Returns:
        DataFrame com geometrias aprovadas no ELS, ordenado por η
    """
    geo_ref = load.geo
    L       = geo_ref.L

    h0_vals    = np.arange(*h0_range)
    alpha_vals = np.arange(*alpha_range)
    b_vals     = np.arange(*b_range)

    resultados = []

    comb_S1 = load.combinacoes["ELS_S1"]
    comb_S2 = load.combinacoes["ELS_S2"]
    k_def   = mat_longa.k_def
    lim_inst = L / 300
    lim_fin  = L / 250

    for h0 in h0_vals:
        for alpha in alpha_vals:
            for b in b_vals:

                geo = GeometriaViga(
                    L=L,
                    h0=round(float(h0), 3),
                    alpha_deg=round(float(alpha), 2),
                    b=round(float(b), 3),
                )

                w_S1, _ = flecha_numerica(geo, mat_longa, comb_S1.q_tot)
                w_G,  _ = flecha_numerica(geo, mat_longa, load.g_k)
                w_Q1, _ = flecha_numerica(geo, mat_longa, load.q_k)

                w_fin     = w_G * (1 + k_def) + w_Q1
                eta_S1    = w_S1  / lim_inst
                eta_fin   = w_fin / lim_fin
                eta       = max(eta_S1, eta_fin)

                if eta <= eta_max:
                    resultados.append({
                        "h0_m":       round(float(h0),   3),
                        "alpha_deg":  round(float(alpha), 2),
                        "b_m":        round(float(b),     3),
                        "h_ap_m":     round(geo.h_ap,     3),
                        "w_S1_mm":    round(w_S1  * 1000, 2),
                        "w_fin_mm":   round(w_fin * 1000, 2),
                        "lim_inst_mm":round(lim_inst*1000,2),
                        "lim_fin_mm": round(lim_fin *1000,2),
                        "eta_S1":     round(eta_S1,       4),
                        "eta_fin":    round(eta_fin,       4),
                        "eta":        round(eta,           4),
                        "ok":         eta <= 1.0,
                    })

    df = pd.DataFrame(resultados)
    if not df.empty:
        df = df.sort_values("eta").reset_index(drop=True)
    return df


# ── Relatório ─────────────────────────────────────────────────────────────────

def relatorio_ELS(resultado: dict) -> None:
    """Imprime relatório formatado da verificação ELS."""
    print("=" * 68)
    print("  VERIFICAÇÃO ELS — EN 1990 §6.5 + EC5 §2.3.2.2 + Tab. 7.2")
    print("=" * 68)
    print(f"\n  Geometria: L={resultado['L_m']} m | "
          f"h_ap={resultado['h_ap_m']} m | "
          f"b={resultado['b_m']} m")
    print(f"  k_def = {resultado['k_def']:.2f} | "
          f"E_mean = {resultado['E_mean_GPa']:.2f} GPa\n")

    print(f"  Combinações ELS:")
    print(f"    S1 (caracter.): q = {resultado['q_S1_kNm']:+.4f} kN/m")
    print(f"    S2 (frequente): q = {resultado['q_S2_kNm']:+.4f} kN/m")
    print(f"    S3 (q-perm.):   q = {resultado['q_S3_kNm']:+.4f} kN/m\n")

    print(f"  Flechas instantâneas:")
    print(f"    w(S1) = {resultado['w_S1_mm']:>7.2f} mm  "
          f"← comparar com L/300 = {resultado['lim_inst_mm']:.2f} mm")
    print(f"    w(S2) = {resultado['w_S2_mm']:>7.2f} mm  (frequente — indicativo)")
    print(f"    w(S3) = {resultado['w_S3_mm']:>7.2f} mm  (quase-permanente)\n")

    print(f"  Fluência — EC5 §2.3.2.2:")
    print(f"    w_G    = {resultado['w_G_mm']:>7.2f} mm")
    print(f"    w_Q1   = {resultado['w_Q1_mm']:>7.2f} mm")
    print(f"    w_fin  = w_G·(1+{resultado['k_def']:.2f}) + w_Q1")
    print(f"    w_fin  = {resultado['w_G_mm']:.2f}·"
          f"{1+resultado['k_def']:.2f} + {resultado['w_Q1_mm']:.2f}")
    print(f"    w_fin  = {resultado['w_fin_mm']:>7.2f} mm\n")

    print(f"  Sem contra-flecha → w_net,fin = w_fin = "
          f"{resultado['w_net_fin_mm']:.2f} mm\n")

    print(f"  Verificações:")
    ok_s1  = "✓" if resultado['eta_S1']     <= 1.0 else "✗"
    ok_fin = "✓" if resultado['eta_net_fin'] <= 1.0 else "✗"
    print(f"    w(S1) ≤ L/300:      "
          f"{resultado['w_S1_mm']:>7.2f} ≤ {resultado['lim_inst_mm']:.2f} mm  "
          f"η = {resultado['eta_S1']:.4f}  {ok_s1}")
    print(f"    w_net,fin ≤ L/250:  "
          f"{resultado['w_net_fin_mm']:>7.2f} ≤ {resultado['lim_fin_mm']:.2f} mm  "
          f"η = {resultado['eta_net_fin']:.4f}  {ok_fin}\n")

    status = "APROVADO" if resultado['ok'] else "REPROVADO"
    print(f"  η governante = {resultado['eta']:.4f}  "
          f"({resultado['verif_gov']})  → {status}")
    print("=" * 68)


# ── Execução direta ───────────────────────────────────────────────────────────

if __name__ == "__main__":

    from mlc_projeto.core.geometry  import GeometriaViga
    from mlc_projeto.core.wind      import ParametrosVento
    from mlc_projeto.core.loads     import carregamentos_com_vento

    # Geometria recomendada pelo predim
    geo = GeometriaViga(L=20.25, h0=0.70, alpha_deg=4.5, b=0.30)

    # Material — k_def = 0,80 para CS2
    mat = GlulamMaterial(classe="GL24h", classe_servico=2, duracao="longa")

    # Carregamentos com vento
    params_vento = ParametrosVento(
        V0=45.0, S1=1.0, categoria="IV", classe="B", S3=1.0,
        L=20.25, H1=1.0, h=7.0, dist_portico=5.75,
    )
    load = carregamentos_com_vento(
        geo=geo, mat=mat,
        g_k_m2=1.50, q_k_m2=0.25,
        dist_portico=5.75,
        params_vento=params_vento,
    )

    print(f"Geometria: h0={geo.h0} m | α={geo.alpha_deg}° | "
          f"b={geo.b} m | h_ap={geo.h_ap:.3f} m\n")
    print(f"Combinações ELS montadas:")
    for nome, c in load.combinacoes_ELS().items():
        print(f"  {nome}: q = {c.q_tot:+.4f} kN/m  —  {c.descricao}")
    print()

    resultado = verificar_ELS(geo, mat, load, w_camber=0.0)
    relatorio_ELS(resultado)

    # Nota sobre vibração
    print(f"\n  Nota: Verificação de vibração (EC5 §7.3) não aplicável.")
    print(f"  O §7.3 destina-se a pisos com ocupação humana,")
    print(f"  não a coberturas industriais sem uso de piso.")