"""
checks/elu/icamento.py — Situação transitória de IÇAMENTO da viga (issue 26).

Fase de montagem: a viga maciça de MLC é içada em DOIS pontos de suspensão,
gerando esforços com sinais/posições distintos dos de serviço:
  · momento NEGATIVO (hogging) nos pontos de içamento (balanços);
  · momento POSITIVO (sagging) no vão entre pontos;
  · compressão axial se as lingas forem inclinadas;
  · flambagem lateral (LTB) sobre o vão entre pontos — a viga está SEM
    contraventamento (terças ainda não montadas). Costuma GOVERNAR.

Esquema adotado (confirmado com o projetista):
  · 2 pontos simétricos a a = 0,207·L (posição que equilibra |M⁻| e |M⁺|);
  · lingas INCLINADAS direto ao gancho (introduzem compressão axial N_c);
  · viga NÃO contraventada → l_ef,LTB = vão entre pontos (L − 2a).

Combinação (EN 1991-1-6 — ações durante a execução):
  w_d(x) = γ_G · φ_dyn · w(x)
    γ_G   = 1,35 (permanente desfavorável — peso próprio da peça)
    φ_dyn = 1,1  (amplificação dinâmica do içamento; declarado, EN 1991-1-6)
  w(x) = γ_glulam · A(x)   (peso próprio distribuído, seção variável)
  Duração INSTANTÂNEA (k_mod,inst) — evento momentâneo de montagem.

Verificações: flexão (M⁻ e M⁺), cortante, e flexo-compressão + LTB (§6.3.3).

Referência: EN 1991-1-6 §4 (execução); EN 1995-1-1 §6.1.6/§6.1.7/§6.3.3.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.integrate import cumulative_trapezoid

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.checks.elu.flambagem_lateral import (
    calcular_sigma_m_crit, calcular_lambda_rel_m, calcular_k_crit,
)

G_GRAV = 9.81   # m/s²


def verificar_icamento(
    geo:           GeometriaViga,
    mat:           GlulamMaterial,
    a_rel:         float = 0.207,
    gamma_G:       float = 1.35,
    phi_dyn:       float = 1.10,
    psi_sling_deg: float = 30.0,
    spreader:      bool = False,
    n_pts:         int = 2001,
) -> dict:
    """
    Verifica a viga na situação de içamento em 2 pontos (EN 1991-1-6 + EC5).

    Args:
        geo   : Geometria da viga (seção variável A(x), h(x))
        mat   : Material GL — usado na duração INSTANTÂNEA internamente
        a_rel : posição dos pontos de içamento (fração de L a partir de cada ponta)
        gamma_G : coef. do peso próprio (desfavorável)
        phi_dyn : amplificação dinâmica do içamento (EN 1991-1-6)
        psi_sling_deg : ângulo da linga com a VERTICAL (compressão axial se >0)
        spreader : True = balancim (lingas verticais, N_c=0)
        n_pts : pontos de integração

    Returns:
        dict com M⁻/M⁺/V, tensões, k_crit, η por verificação e η governante.
    """
    mat_i = GlulamMaterial(mat.classe, mat.classe_servico, "instantanea")
    f_m_d = mat_i.f_m_d
    f_v_d = mat_i.f_v_d
    f_c0d = mat_i.f_c0_d
    f_c0k = mat_i.f_c0_k
    E005  = mat_i.E0_05
    f_m_k = mat_i.f_m_k

    L = float(geo.L)
    b = float(geo.b)
    h_ap = float(geo.h_ap)
    gamma_gl = mat.rho_mean * G_GRAV / 1e3          # kN/m³

    # ── Peso próprio distribuído (seção variável) ─────────────
    x = np.linspace(0.0, L, n_pts)
    h_x = np.array([geo.h(float(xi)) for xi in x])
    A_x = b * h_x                                   # m²
    w = gamma_gl * A_x                              # kN/m (peso próprio)
    w_d = gamma_G * phi_dyn * w                     # kN/m (cálculo)

    # ── Estática do içamento em 2 pontos (a·L e (1−a)·L) ──────
    x1 = a_rel * L
    x2 = (1.0 - a_rel) * L
    W_tot = float(np.trapezoid(w_d, x))             # kN
    R = W_tot / 2.0                                 # reação por ponto (kN)

    # Cortante e momento por integração (extremos livres → M(0)=M(L)=0)
    carga_acum = cumulative_trapezoid(w_d, x, initial=0.0)   # ∫w dx
    V = R * (x >= x1).astype(float) + R * (x >= x2).astype(float) - carga_acum
    M = cumulative_trapezoid(V, x, initial=0.0)     # kN·m

    M_neg = float(np.min(M))                        # hogging (nos pontos)
    M_pos = float(np.max(M))                        # sagging (vão central)
    i_Vmax = int(np.argmax(np.abs(V)))
    V_max = float(abs(V[i_Vmax]))
    h_Vmax = float(h_x[i_Vmax])

    # ── Seções e tensões de flexão ────────────────────────────
    h_pick = float(geo.h(x1))
    W_pick = b * h_pick ** 2 / 6.0                  # módulo no ponto de içamento
    W_mid  = b * h_ap ** 2 / 6.0                    # módulo no ápice (vão central)
    sig_m_neg = abs(M_neg) * 1e3 / W_pick           # Pa (topo tracionado no balanço)
    sig_m_pos = M_pos * 1e3 / W_mid                 # Pa (fibra inf. comprimida)
    eta_flex = max(sig_m_neg, sig_m_pos) / f_m_d

    # ── Cortante (na seção do V máx, ⊥ ao apoio de içamento) ──
    A_Vmax = b * h_Vmax
    tau = 1.5 * V_max * 1e3 / (mat_i.k_cr * A_Vmax)  # Pa
    eta_cis = tau / f_v_d

    # ── Compressão axial das lingas inclinadas ────────────────
    psi = math.radians(psi_sling_deg)
    N_c = 0.0 if spreader else R * math.tan(psi)     # kN (entre os pontos)
    A_mid = b * h_ap
    sig_c = N_c * 1e3 / A_mid if A_mid > 0 else 0.0

    # ── Flambagem lateral (LTB) no vão entre pontos ───────────
    l_ef = L - 2.0 * a_rel * L                       # sem contraventamento
    sig_crit = calcular_sigma_m_crit(E005, b, h_ap, l_ef)
    lam_rel_m = calcular_lambda_rel_m(f_m_k, sig_crit)
    k_crit = calcular_k_crit(lam_rel_m)

    # k_c,z para o comprimento entre pontos (flambagem no plano fraco)
    i_z = b / math.sqrt(12.0)
    lam_z = l_ef / i_z
    lam_rel_z = (lam_z / math.pi) * math.sqrt(f_c0k / E005)
    beta_c = 0.10
    k_z = 0.5 * (1 + beta_c * (lam_rel_z - 0.3) + lam_rel_z ** 2)
    k_c_z = min(1.0 / (k_z + math.sqrt(max(k_z ** 2 - lam_rel_z ** 2, 0.0))), 1.0)

    # EC5 §6.3.3 Eq. (6.35): σ_m/(k_crit·f_m_d) + (σ_c/(k_c,z·f_c0d))² ≤ 1
    eta_ltb = sig_m_pos / (k_crit * f_m_d) + (sig_c / (k_c_z * f_c0d)) ** 2

    etas = {"flexao": eta_flex, "cisalhamento": eta_cis, "LTB_6.35": eta_ltb}
    gov = max(etas, key=etas.get)
    eta_gov = etas[gov]

    return {
        "sistema":     "Içamento em 2 pontos (montagem)",
        "esquema":     f"2 pontos a {a_rel:.3f}·L | "
                       + ("balancim (lingas verticais)" if spreader
                          else f"lingas a {psi_sling_deg:.0f}° da vertical"),
        "gamma_glulam_kNm3": round(gamma_gl, 3),
        "gamma_G":     gamma_G,
        "phi_dyn":     phi_dyn,
        "duracao":     "instantanea",
        "k_mod":       mat_i.k_mod,
        "W_total_kN":  round(W_tot, 2),
        "R_ponto_kN":  round(R, 2),
        "x1_m":        round(x1, 3),
        "x2_m":        round(x2, 3),
        # Esforços
        "M_neg_kNm":   round(M_neg, 2),
        "M_pos_kNm":   round(M_pos, 2),
        "V_max_kN":    round(V_max, 2),
        "h_pick_m":    round(h_pick, 3),
        # Tensões
        "sigma_m_neg_MPa": round(sig_m_neg / 1e6, 3),
        "sigma_m_pos_MPa": round(sig_m_pos / 1e6, 3),
        "tau_MPa":     round(tau / 1e6, 3),
        "N_c_kN":      round(N_c, 2),
        "sigma_c_MPa": round(sig_c / 1e6, 3),
        "f_m_d_MPa":   round(f_m_d / 1e6, 3),
        "f_v_d_MPa":   round(f_v_d / 1e6, 3),
        # LTB
        "l_ef_LTB_m":  round(l_ef, 3),
        "sigma_crit_MPa": round(sig_crit / 1e6, 3),
        "lambda_rel_m": round(lam_rel_m, 4),
        "k_crit":      round(k_crit, 4),
        "k_c_z":       round(k_c_z, 4),
        # η
        "eta_flexao":  round(eta_flex, 4),
        "eta_cisalhamento": round(eta_cis, 4),
        "eta_LTB":     round(eta_ltb, 4),
        "etas":        {k: round(v, 4) for k, v in etas.items()},
        "eta_gov_key": gov,
        "eta":         round(eta_gov, 4),
        "ok":          eta_gov <= 1.0,
        "norma":       "EN 1991-1-6 §4 | EN 1995-1-1 §6.1.6/§6.1.7/§6.3.3",
    }


def relatorio(res: dict) -> None:
    """Relatório legível da verificação de içamento."""
    print("=" * 70)
    print("  IÇAMENTO DA VIGA (montagem) — EN 1991-1-6 + EC5")
    print("=" * 70)
    print(f"  Esquema : {res['esquema']}")
    print(f"  Comb.   : γ_G={res['gamma_G']} · φ_dyn={res['phi_dyn']} · g "
          f"(γ_glulam={res['gamma_glulam_kNm3']:.2f} kN/m³) | "
          f"k_mod={res['k_mod']:.2f} (instantânea)")
    print(f"  Peso    : W={res['W_total_kN']:.1f} kN | R/ponto={res['R_ponto_kN']:.1f} kN "
          f"@ x={res['x1_m']:.2f} e {res['x2_m']:.2f} m")
    print(f"  {'-'*66}")
    print(f"  M⁻ (içar) = {res['M_neg_kNm']:.1f} kN·m | "
          f"M⁺ (vão) = {res['M_pos_kNm']:.1f} kN·m | V = {res['V_max_kN']:.1f} kN")
    print(f"  σ_m⁻={res['sigma_m_neg_MPa']:.2f} | σ_m⁺={res['sigma_m_pos_MPa']:.2f} MPa "
          f"(f_m,d={res['f_m_d_MPa']:.2f}) → η_flex={res['eta_flexao']:.4f}")
    print(f"  τ={res['tau_MPa']:.3f} MPa (f_v,d={res['f_v_d_MPa']:.2f}) → "
          f"η_cis={res['eta_cisalhamento']:.4f}")
    print(f"  N_c (lingas)={res['N_c_kN']:.1f} kN → σ_c={res['sigma_c_MPa']:.3f} MPa")
    print(f"  LTB: l_ef={res['l_ef_LTB_m']:.2f} m | σ_crit={res['sigma_crit_MPa']:.2f} MPa "
          f"| λ_rel,m={res['lambda_rel_m']:.3f} | k_crit={res['k_crit']:.3f}")
    print(f"       Eq.6.35 → η_LTB={res['eta_LTB']:.4f}")
    print(f"  {'-'*66}")
    ok = "APROVADO" if res["ok"] else "REPROVADO"
    print(f"  η governante ({res['eta_gov_key']}) = {res['eta']:.4f} → {ok}")
    print("=" * 70)


if __name__ == "__main__":
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
    mat = GlulamMaterial("GL24h", 3, "curta")
    relatorio(verificar_icamento(geo, mat))
