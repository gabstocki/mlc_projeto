"""
checks/elu/corda_beiral.py — Elemento de beiral como CORDA do diafragma (issue 32).

O contraventamento transversal (issue 31) modela a cobertura como uma viga-diafragma
horizontal entre frontões. As CORDAS (banzos) desse diafragma são os elementos de
BEIRAL, que recebem a força axial N_corda = M_diaf/B_cob (calculada em
contraventamento_transversal.py) e que NÃO era verificada num membro.

Solução adotada: a **terça de beiral** (perímetro da cobertura, MLC GL24h) atua como
corda — é contínua ao longo dos 46 m (emendas transferindo N_corda). Ela é um
elemento de FLEXO-AXIAL:
  · carrega a flexão local da cobertura (terça de borda — área tributária s/2);
  · carrega a força de corda N_corda, que **inverte de sinal** com o sentido do
    vento (tração num sentido, compressão no outro).

Verificações (ambos os sinais):
  · Flexo-COMPRESSÃO — EC5 §6.3.2 Eq. (6.23)/(6.24) (com flambagem k_c);
  · Flexo-TRAÇÃO    — EC5 §6.2.3 Eq. (6.17)/(6.18);
  · Continuidade das emendas — cada emenda transfere N_corda (§8, à parte).

Referência: EN 1995-1-1 §6.2.3 + §6.3.2; força de corda de EN 1993-1-1 §5.3/§6.2.3.
"""

from __future__ import annotations

import math

from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.checks.elu.tercas import verifica_terca


def verificar_corda_beiral(
    mat:         GlulamMaterial,
    N_corda_kN:  float,
    L_t:         float,
    s_eave:      float,
    b:           float,
    h:           float,
    alpha_deg:   float,
    g_k_m2:      float,
    q_k_m2:      float,
    w_kNm2:      float,
    L_comp:      float,
    L_barra_m:   float = 11.75,
    k_m:         float = 0.7,
    beta_c:      float = 0.10,
) -> dict:
    """
    Verifica a terça de beiral como corda do diafragma de cobertura (issue 32).

    Args:
        mat        : Material GL24h (usado na duração curta — vento)
        N_corda_kN : força axial de corda (|valor|; inverte de sinal com o vento)
        L_t        : vão da terça de beiral entre pórticos (m)
        s_eave     : área tributária da terça de BORDA (≈ s/2) para a flexão (m)
        b, h       : seção da terça de beiral (m)
        alpha_deg  : inclinação da cobertura (graus)
        g_k_m2, q_k_m2, w_kNm2 : cargas por área (kN/m²) — flexão concomitante
        L_comp     : comprimento total do beiral / diafragma (m)
        L_barra_m  : comprimento comercial da barra de MLC (define nº de emendas)
        k_m, beta_c: fatores EC5

    Returns:
        dict com η de flexo-compressão, flexo-tração, η governante e emendas.
    """
    # ── Flexão local da cobertura (terça de borda, tributária s_eave) ──
    rf = verifica_terca(
        mat=mat, L_t=L_t, s=s_eave, b=b, h=h, alpha_deg=alpha_deg,
        g_k_m2=g_k_m2, q_k_m2=q_k_m2, w_kNm2=w_kNm2, k_m=k_m,
    )
    sigma_my = rf["sigma_my_MPa"] * 1e6
    sigma_mz = rf["sigma_mz_MPa"] * 1e6
    f_md     = rf["f_md_MPa"]    * 1e6

    A = b * h
    sigma_N = abs(N_corda_kN) * 1e3 / A                 # Pa

    mat_c = GlulamMaterial(mat.classe, mat.classe_servico, "curta")
    f_c0d, f_t0d = mat_c.f_c0_d, mat_c.f_t0_d
    f_c0k, E005 = mat_c.f_c0_k, mat_c.E0_05

    # ── k_c,y e k_c,z (flambagem entre pórticos, l_ef = L_t) ──
    def _k_c(i: float) -> float:
        lam = L_t / i if i > 0 else 1e9
        lam_rel = (lam / math.pi) * math.sqrt(f_c0k / E005)
        k = 0.5 * (1 + beta_c * (lam_rel - 0.3) + lam_rel ** 2)
        return min(1.0 / (k + math.sqrt(max(k ** 2 - lam_rel ** 2, 0.0))), 1.0)

    k_c_y = _k_c(h / math.sqrt(12.0))
    k_c_z = _k_c(b / math.sqrt(12.0))

    # ── Flexo-COMPRESSÃO — EC5 §6.3.2 Eq. (6.23)/(6.24) ──
    eta_c_623 = sigma_N / (k_c_y * f_c0d) + sigma_my / f_md + k_m * sigma_mz / f_md
    eta_c_624 = sigma_N / (k_c_z * f_c0d) + k_m * sigma_my / f_md + sigma_mz / f_md
    eta_compr = max(eta_c_623, eta_c_624)

    # ── Flexo-TRAÇÃO — EC5 §6.2.3 Eq. (6.17)/(6.18) ──
    eta_t_617 = sigma_N / f_t0d + sigma_my / f_md + k_m * sigma_mz / f_md
    eta_t_618 = sigma_N / f_t0d + k_m * sigma_my / f_md + sigma_mz / f_md
    eta_tract = max(eta_t_617, eta_t_618)

    eta = max(eta_compr, eta_tract)
    caso_gov = "flexo-compressão (§6.3.2)" if eta_compr >= eta_tract \
        else "flexo-tração (§6.2.3)"

    # ── Continuidade das emendas ao longo do beiral ──
    n_emendas = max(0, math.ceil(L_comp / L_barra_m) - 1)

    return {
        "elemento":     "Terça de beiral = corda do diafragma (MLC GL24h)",
        "N_corda_kN":   round(abs(N_corda_kN), 3),
        "b_m":          b, "h_m": h, "A_m2": round(A, 5),
        "s_eave_m":     s_eave,
        "sigma_N_MPa":  round(sigma_N / 1e6, 4),
        "sigma_my_MPa": rf["sigma_my_MPa"],
        "sigma_mz_MPa": rf["sigma_mz_MPa"],
        "f_md_MPa":     rf["f_md_MPa"],
        "f_c0d_MPa":    round(f_c0d / 1e6, 3),
        "f_t0d_MPa":    round(f_t0d / 1e6, 3),
        "k_c_y":        round(k_c_y, 4),
        "k_c_z":        round(k_c_z, 4),
        # Flexo-compressão
        "eta_compr_623": round(eta_c_623, 4),
        "eta_compr_624": round(eta_c_624, 4),
        "eta_compressao": round(eta_compr, 4),
        # Flexo-tração
        "eta_tract_617": round(eta_t_617, 4),
        "eta_tract_618": round(eta_t_618, 4),
        "eta_tracao":   round(eta_tract, 4),
        # Governante
        "caso_gov":     caso_gov,
        "eta":          round(eta, 4),
        "ok":           eta <= 1.0,
        # Emendas / continuidade
        "L_comp_m":     L_comp,
        "L_barra_m":    L_barra_m,
        "n_emendas":    n_emendas,
        "F_emenda_kN":  round(abs(N_corda_kN), 3),
        "nota_emenda": (
            f"A corda deve ser CONTÍNUA ao longo de {L_comp:.0f} m: "
            f"{n_emendas} emenda(s) (barras ~{L_barra_m:.1f} m), cada uma "
            f"transferindo N_corda={abs(N_corda_kN):.1f} kN (tração e compressão, "
            "por chapa/parafusos — EC5 §8). Sem continuidade o diafragma não funciona."
        ),
        "norma": "EC5 §6.3.2 (Eq.6.23/6.24) + §6.2.3 (Eq.6.17/6.18)",
    }


def relatorio(res: dict) -> None:
    """Relatório legível da corda de beiral."""
    print("=" * 70)
    print("  CORDA DO DIAFRAGMA — ELEMENTO DE BEIRAL (issue 32)")
    print("=" * 70)
    print(f"  {res['elemento']}")
    print(f"  N_corda = {res['N_corda_kN']:.2f} kN (±, inverte c/ vento) | "
          f"seção {res['b_m']}×{res['h_m']} m | s_beiral={res['s_eave_m']:.2f} m")
    print(f"  σ_N={res['sigma_N_MPa']:.3f} | σ_m,y={res['sigma_my_MPa']:.3f} MPa "
          f"(f_md={res['f_md_MPa']:.2f}, f_t0d={res['f_t0d_MPa']:.2f})")
    print(f"  {'-'*66}")
    print(f"  Flexo-compressão §6.3.2: η={res['eta_compressao']:.4f} "
          f"(6.23={res['eta_compr_623']:.3f}, 6.24={res['eta_compr_624']:.3f})")
    print(f"  Flexo-tração   §6.2.3: η={res['eta_tracao']:.4f} "
          f"(6.17={res['eta_tract_617']:.3f}, 6.18={res['eta_tract_618']:.3f})")
    print(f"  {'-'*66}")
    ok = "APROVADO" if res["ok"] else "REPROVADO"
    print(f"  η governante = {res['eta']:.4f} ({res['caso_gov']}) → {ok}")
    print(f"  Emendas: {res['n_emendas']} × N_corda={res['F_emenda_kN']:.1f} kN "
          f"(continuidade obrigatória)")
    print("=" * 70)


if __name__ == "__main__":
    mat = GlulamMaterial("GL24h", 3, "curta")
    res = verificar_corda_beiral(
        mat, N_corda_kN=7.6, L_t=5.75, s_eave=2.53 / 2, b=0.20, h=0.58,
        alpha_deg=10.0, g_k_m2=0.389, q_k_m2=0.40, w_kNm2=0.7158, L_comp=46.0,
    )
    relatorio(res)
