"""
checks/elu/diafragma_cobertura.py — Alma do diafragma da cobertura (issue 110).

Os pórticos intermediários são rotulados (viga–pilar, pilar–base) e não têm rigidez
lateral própria: a força transversal no topo de cada pórtico precisa chegar aos
frontões (painéis CV-T) por um diafragma horizontal de 46 m. Vigas e terças rotuladas
formam retângulos sem rigidez ao cisalhamento; a alma é dada por cruzes de St. André
em todos os painéis das baías intermediárias (CV-D), além das cruzes CV-H das baías
1–2 e 8–9, que já existem para o vento longitudinal e trabalham também aqui.

A verificação usa o modelo em planta (`opensees.diafragma_espacial`):
  · diagonais das baías intermediárias: menor diâmetro da série (≥ D_MIN_MM) com
    η = F_diag / N_t,Rd ≤ 0,90 (aço, rosca recalcada, como as demais diagonais);
  · deslocamento do topo do pórtico mais deslocado ≤ H/300, o mesmo limite dos
    painéis de contraventamento, agora somando a flexibilidade do diafragma à dos
    painéis dos frontões;
  · rigidez equivalente K = H_tr/δ_max, que substitui, no α_cr transversal, a
    rigidez só dos painéis dos frontões (que supunha diafragma rígido).
Registra também o caso sem alma (mecanismo) e o de uma força no pórtico central.
"""

from __future__ import annotations

from mlc_projeto.checks.elu.contraventamento_vertical import D_COMERCIAL_MM, _n_t_rd_kN
from mlc_projeto.opensees.diafragma_espacial import analisar_diafragma

D_MIN_MM = 12.0
ETA_ALVO = 0.90


def verificar_diafragma_cobertura(*, L_T: float, n_eixos: int, s: float, n_faixas: int,
                                  A_terca_m2: float, A_viga_m2: float, E_mlc_kPa: float,
                                  d_cvh_mm: float, C_h_frontao_kNpm: float,
                                  C_h_long_kNpm: float, H_tr_kN: float, H_pilar_m: float,
                                  aco: str = "S235", drift_lim: float = 300.0) -> dict:
    n_baias = n_eixos - 1
    base = dict(L_T=L_T, n_eixos=n_eixos, s=s, n_faixas=n_faixas, A_terca_m2=A_terca_m2,
                A_viga_m2=A_viga_m2, E_mlc_kPa=E_mlc_kPa, C_h_frontao_kNpm=C_h_frontao_kNpm,
                C_h_long_kNpm=C_h_long_kNpm, H_tr_kN=H_tr_kN)
    extremas = (0, n_baias - 1)
    sem_alma = analisar_diafragma(
        d_diag_mm_por_baia=[d_cvh_mm if i in extremas else None for i in range(n_baias)], **base)
    r = None
    for d in [x for x in D_COMERCIAL_MM if x >= D_MIN_MM]:
        diams = [d_cvh_mm if i in extremas else float(d) for i in range(n_baias)]
        r = analisar_diafragma(d_diag_mm_por_baia=diams, **base)
        F_int = max(f for b, f in r["F_diag_max_kN_por_baia"].items() if (b - 1) not in extremas)
        if F_int <= ETA_ALVO * _n_t_rd_kN(d, aco):
            break
    d_int = float(d)
    N_t_Rd = _n_t_rd_kN(d_int, aco)
    F_ext = max(r["F_diag_max_kN_por_baia"][b + 1] for b in extremas)
    eta_diag = F_int / N_t_Rd
    eta_ext = F_ext / _n_t_rd_kN(d_cvh_mm, aco)          # CV-H, com o vento transversal
    delta_lim = H_pilar_m * 1000.0 / drift_lim
    eta_delta = r["delta_max_mm"] / delta_lim
    centro = analisar_diafragma(d_diag_mm_por_baia=diams, F_portico_kN=100.0,
                                portico_carregado=n_eixos // 2, **base)
    eta = max(eta_diag, eta_ext, eta_delta)
    return {
        "sistema": "Diafragma da cobertura — alma em cruzes (CV-D) nas baías 2 a 8",
        "d_diafragma_mm": d_int, "d_cvh_mm": d_cvh_mm,
        "n_barras_novas": 2 * n_faixas * (n_baias - 2),
        "L_diag_m": round((L_T ** 2 + s ** 2) ** 0.5, 3),
        "F_diag_max_kN": round(F_int, 2), "N_t_Rd_kN": round(N_t_Rd, 2),
        "eta_diag": round(eta_diag, 4), "eta_cvh_transversal": round(eta_ext, 4),
        "delta_max_mm": r["delta_max_mm"], "delta_lim_mm": round(delta_lim, 2),
        "eta_delta": round(eta_delta, 4), "K_eq_kNpm": r["K_eq_kNpm"],
        "R_frontoes_kN": r["R_frontoes_kN"], "N_corda_max_kN": r["N_corda_max_kN"],
        "F_diag_por_baia_kN": r["F_diag_max_kN_por_baia"],
        "uy_portico_mm": r["uy_portico_mm"],
        "portico_central_100kN": centro,
        "sem_alma_mecanismo": bool(sem_alma.get("mecanismo")),
        "eta": round(eta, 4), "ok": eta <= 1.0 and eta_diag <= ETA_ALVO + 1e-9,
        "norma": "EN 1995-1-1 §5.4 e §9.2.5 | EN 1993-1-1 §6.2.3 | modelo em planta OpenSeesPy",
    }
