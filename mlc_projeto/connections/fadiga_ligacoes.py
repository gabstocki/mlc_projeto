"""
connections/fadiga_ligacoes.py — Fadiga e deslizamento de ligações.

EC5 §8.1.5  — Forças alternadas
EC5 §7.1    — Deslizamento ELS (K_ser)
EC5 §2.3.2.2 — K_ser,fin com fluência
EC5 Tab. 2.3 — γ_M ligações = 1,30
EN 1990 Tab. A1.1 — ψ₂ cobertura inacessível = 0,0

Não usa valores hardcoded de esforço: lê load e resultados de dimensionamento.
"""

from __future__ import annotations

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial, GAMMA_M_LIGACAO
from mlc_projeto.core.loads     import Carregamentos


def K_ser_pino(d_mm: float, rho_m: float, aco_madeira: bool = True) -> float:
    """
    Módulo de deslizamento por plano de corte por pino (N/mm).
    EC5 §7.1 Tabela 7.1 — cavilhas/pinos: K_ser = ρ_m^1,5 · d / 23
    Aço-madeira: ×2 — EC5 §7.1(3).
    """
    K = rho_m ** 1.5 * d_mm / 23.0
    if aco_madeira:
        K *= 2.0
    return K


def K_ser_fin(K_ser: float, k_def: float, psi_2: float = 0.0) -> float:
    """
    K_ser,fin = K_ser / (1 + ψ₂ · k_def) — EC5 §2.3.2.2 Eq. (2.9).
    ψ₂ = 0,0 para sobrecarga de cobertura inacessível (EN 1990 Tab. A1.1).
    """
    return K_ser / (1.0 + psi_2 * k_def)


def deslizamento_ligacao(
    F_Ed_kN: float,
    n_pinos: int,
    K_ser: float,
    n_planos: int = 2,
) -> float:
    """u = F / (n · n_planos · K_ser)  [mm] — EC5 §7.1."""
    if n_pinos <= 0 or K_ser <= 0:
        return 0.0
    return (F_Ed_kN * 1e3) / (n_pinos * n_planos * K_ser)


def verificar_forcas_alternadas(
    F_t_Ed: float,
    F_c_Ed: float,
    F_Rd: float,
    nome: str,
) -> dict:
    """
    EC5 §8.1.5 — forças alternadas (tração ↔ compressão):
        F_t,Ed + 0,5·F_c,Ed ≤ F_Rd
        F_c,Ed + 0,5·F_t,Ed ≤ F_Rd
    """
    F_combinada_t = F_t_Ed + 0.5 * F_c_Ed
    F_combinada_c = F_c_Ed + 0.5 * F_t_Ed
    F_max = max(F_combinada_t, F_combinada_c)
    eta = F_max / F_Rd if F_Rd > 0 else 999.0

    return {
        "ligacao":     nome,
        "F_t_Ed_kN":   round(F_t_Ed, 3),
        "F_c_Ed_kN":   round(F_c_Ed, 3),
        "F_comb_t_kN": round(F_combinada_t, 3),
        "F_comb_c_kN": round(F_combinada_c, 3),
        "F_max_kN":    round(F_max, 3),
        "F_Rd_kN":     round(F_Rd, 3),
        "eta_alt":     round(eta, 4),
        "ok":          eta <= 1.0,
    }


def verificar_fadiga_deslizamento(
    mat:     GlulamMaterial,
    load:    Carregamentos,
    geo:     GeometriaViga,
    res_lig: dict,
    res_lig_c: dict | None = None,
    H_pilar: float = 7.0,
    psi_2:   float = 0.0,
) -> dict:
    """
    Fadiga (§8.1.5) e deslizamento (§7.1) a partir de esforços reais e
    capacidades já calculadas em dimensionar_ligacoes*.

    Args:
        mat       : Material (k_def, rho_mean — EN 14080)
        load      : Carregamentos com combinações ELU/ELS
        geo       : Geometria
        res_lig   : Resultado de dimensionar_ligacoes (L1, L2, L3)
        res_lig_c : Opcional — ligações do pilar central
        H_pilar   : Altura do pilar (m) — limite u = H/1000
        psi_2     : EN 1990 — cobertura inacessível = 0,0
    """
    rho_m = mat.rho_mean  # EN 14080 Tab. 1 — K_ser §7.1
    k_def = mat.k_def

    # Esforços por combinação (sem hardcode)
    comb_s1 = load.combinacoes["ELS_S1"]
    comb_s3 = load.combinacoes["ELS_S3"]
    gov     = load.combinacao_ELU_governante()

    # Resultante na base: √(N²+V²) ≈ √(R_v²+H²) — mesma definição da L1
    def F_res(comb) -> float:
        return (comb.N_viga_kN ** 2 + comb.V_viga_kN ** 2) ** 0.5

    F_ELU  = F_res(gov)
    F_S1   = F_res(comb_s1)
    F_S3   = F_res(comb_s3)

    # Sucção: empuxo pode inverter sentido → tração na ligação de base
    # (apenas se ELU_C3 existir e H mudar de sinal relativamente à gravidade)
    comb_suc = load.combinacao_ELU_succao()
    F_suc    = abs(F_res(comb_suc)) if comb_suc.q_tot < 0 else 0.0

    resultados: dict = {}

    # ── L1 base ───────────────────────────────────────────────
    L1 = res_lig["L1"]
    d_L1  = L1["d_mm"]
    n_L1  = L1["n_pinos"]
    np_L1 = 2
    F_Rd_L1 = L1["R_total_kN"]

    Kser_L1     = K_ser_pino(d_L1, rho_m, aco_madeira=True)
    Kser_fin_L1 = K_ser_fin(Kser_L1, k_def, psi_2)

    u_inst_L1 = deslizamento_ligacao(F_S1, n_L1, Kser_L1, np_L1)
    u_fin_L1  = deslizamento_ligacao(F_S3, n_L1, Kser_fin_L1, np_L1)
    u_lim_L1  = H_pilar * 1000.0 / 1000.0  # mm — H/1000
    eta_slip_L1 = max(u_inst_L1, u_fin_L1) / u_lim_L1 if u_lim_L1 > 0 else 0.0

    # §8.1.5: tração (sucção se houver) + compressão permanente
    F_t = F_suc
    F_c = F_S3
    alt_L1 = verificar_forcas_alternadas(F_t, F_c, F_Rd_L1, "L1")

    resultados["L1"] = {
        "descricao":     f"Base pilar lateral — {n_L1} pinos d={d_L1:.0f}mm",
        "d_mm":          d_L1,
        "n_pinos":       n_L1,
        "n_planos":      np_L1,
        "F_ELU_kN":      round(F_ELU, 3),
        "F_S1_kN":       round(F_S1, 3),
        "F_S3_kN":       round(F_S3, 3),
        "K_ser_Nmm":     round(Kser_L1, 2),
        "K_ser_fin_Nmm": round(Kser_fin_L1, 2),
        "u_inst_mm":     round(u_inst_L1, 4),
        "u_fin_mm":      round(u_fin_L1, 4),
        "u_lim_mm":      u_lim_L1,
        "eta_slip":      round(eta_slip_L1, 4),
        "slip_ok":       eta_slip_L1 <= 1.0,
        "alternada":     alt_L1,
        "fadiga_governa": False,
    }

    # ── L2 cumeeira ───────────────────────────────────────────
    L2 = res_lig["L2"]
    d_L2  = L2["d_pino_mm"]
    n_L2  = L2["n_pino"]
    np_L2 = 2
    F_Rd_L2 = L2["F_Rd_pino_kN"] * n_L2

    # Cortante residual de vento (mesmo critério da L2 de dimensionamento)
    V_S1_asim = abs(load.w_C1bv_k - load.w_C1st_k) * geo.L / 4.0
    V_ELU_asim = L2["V_asim_kN"]

    Kser_L2     = K_ser_pino(d_L2, rho_m, aco_madeira=True)
    Kser_fin_L2 = K_ser_fin(Kser_L2, k_def, psi_2)

    u_inst_L2 = deslizamento_ligacao(V_S1_asim, n_L2, Kser_L2, np_L2)
    u_fin_L2  = deslizamento_ligacao(V_S1_asim, n_L2, Kser_fin_L2, np_L2)
    u_lim_L2  = geo.L * 1000.0 / 500.0  # ligação interna: L/500 (ordem de grandeza ELS)
    eta_slip_L2 = max(u_inst_L2, u_fin_L2) / u_lim_L2 if u_lim_L2 > 0 else 0.0

    alt_L2 = {
        "ligacao": "L2",
        "F_t_Ed_kN": 0.0,
        "F_c_Ed_kN": round(abs(load.H_ELU()), 3),
        "F_comb_t_kN": 0.0,
        "F_comb_c_kN": round(abs(load.H_ELU()), 3),
        "F_max_kN": round(abs(load.H_ELU()), 3),
        "F_Rd_kN": round(F_Rd_L2, 3),
        "eta_alt": round(V_ELU_asim / F_Rd_L2, 4) if F_Rd_L2 > 0 else 0.0,
        "ok": (V_ELU_asim / F_Rd_L2 <= 1.0) if F_Rd_L2 > 0 else True,
        "nota": "Cumeeira isostática: M=0; pino para V residual de vento",
    }

    resultados["L2"] = {
        "descricao":     f"Cumeeira — {n_L2} pino(s) d={d_L2:.0f}mm",
        "d_mm":          d_L2,
        "n_pinos":       n_L2,
        "n_planos":      np_L2,
        "F_ELU_kN":      round(V_ELU_asim, 3),
        "F_S1_kN":       round(V_S1_asim, 3),
        "F_S3_kN":       0.0,
        "K_ser_Nmm":     round(Kser_L2, 2),
        "K_ser_fin_Nmm": round(Kser_fin_L2, 2),
        "u_inst_mm":     round(u_inst_L2, 4),
        "u_fin_mm":      round(u_fin_L2, 4),
        "u_lim_mm":      u_lim_L2,
        "eta_slip":      round(eta_slip_L2, 4),
        "slip_ok":       eta_slip_L2 <= 1.0,
        "alternada":     alt_L2,
        "fadiga_governa": False,
    }

    # ── L1c central (opcional) ────────────────────────────────
    if res_lig_c is not None and "L1c" in res_lig_c:
        L1c = res_lig_c["L1c"]
        d_c  = L1c["d_mm"]
        n_c  = L1c["n_pinos"] * 2  # 2 chapas
        F_Rd_c = L1c["R_total_kN"] * 2
        F_S1_c = 2 * F_S1  # dois pórticos
        F_S3_c = 2 * F_S3

        Kser_c     = K_ser_pino(d_c, rho_m, aco_madeira=True)
        Kser_fin_c = K_ser_fin(Kser_c, k_def, psi_2)
        u_inst_c = deslizamento_ligacao(F_S1_c, n_c, Kser_c, 2)
        u_fin_c  = deslizamento_ligacao(F_S3_c, n_c, Kser_fin_c, 2)
        eta_slip_c = max(u_inst_c, u_fin_c) / u_lim_L1

        alt_c = {
            "ligacao": "L1c",
            "F_t_Ed_kN": 0.0,
            "F_c_Ed_kN": round(F_S3_c, 3),
            "F_comb_t_kN": 0.0,
            "F_comb_c_kN": round(F_S3_c, 3),
            "F_max_kN": round(F_S3_c, 3),
            "F_Rd_kN": round(F_Rd_c, 3),
            "eta_alt": round(F_S3_c / F_Rd_c, 4) if F_Rd_c > 0 else 0.0,
            "ok": F_S3_c / F_Rd_c <= 1.0 if F_Rd_c > 0 else True,
            "nota": "Pilar central: empuxos horizontais cancelam; sem tração de vento",
        }

        resultados["L1c"] = {
            "descricao":     f"Base pilar central — 2×{L1c['n_pinos']} pinos d={d_c:.0f}mm",
            "d_mm":          d_c,
            "n_pinos":       n_c,
            "n_planos":      2,
            "F_ELU_kN":      round(2 * F_ELU, 3),
            "F_S1_kN":       round(F_S1_c, 3),
            "F_S3_kN":       round(F_S3_c, 3),
            "K_ser_Nmm":     round(Kser_c, 2),
            "K_ser_fin_Nmm": round(Kser_fin_c, 2),
            "u_inst_mm":     round(u_inst_c, 4),
            "u_fin_mm":      round(u_fin_c, 4),
            "u_lim_mm":      u_lim_L1,
            "eta_slip":      round(eta_slip_c, 4),
            "slip_ok":       eta_slip_c <= 1.0,
            "alternada":     alt_c,
            "fadiga_governa": False,
        }

    return resultados


def relatorio(res: dict, k_def: float = 0.80, psi_2: float = 0.0) -> None:
    sep = "═" * 68
    print(sep)
    print("  FADIGA E DESLIZAMENTO — EC5 §7.1 + §8.1.5")
    print(sep)

    for cod, r in res.items():
        print(f"\n  ── {cod}: {r['descricao']}")
        print(f"     d={r['d_mm']:.0f}mm | n={r['n_pinos']} | planos={r['n_planos']}")
        print(f"     K_ser={r['K_ser_Nmm']:.1f} N/mm | K_ser,fin={r['K_ser_fin_Nmm']:.1f} "
              f"(k_def={k_def}, ψ₂={psi_2})")
        print(f"     u_inst={r['u_inst_mm']:.4f} mm | u_fin={r['u_fin_mm']:.4f} mm "
              f"| lim={r['u_lim_mm']:.2f} mm | η_slip={r['eta_slip']:.4f}")
        alt = r["alternada"]
        print(f"     η_alt={alt['eta_alt']:.4f}  "
              f"{'✓' if alt['ok'] else '✗'}"
              + (f"  ({alt['nota']})" if "nota" in alt else ""))

    all_slip = all(r["slip_ok"] for r in res.values())
    all_alt  = all(r["alternada"]["ok"] for r in res.values())
    print(f"\n  Deslizamento: {'✓' if all_slip else '✗'} | "
          f"Alternadas: {'✓' if all_alt else '✗'}")
    print(sep)


if __name__ == "__main__":
    from mlc_projeto.core.geometry import GeometriaViga
    from mlc_projeto.core.materials import GlulamMaterial
    from mlc_projeto.core.wind import ParametrosVento
    from mlc_projeto.core.loads import carregamentos_com_vento
    from mlc_projeto.connections.connections import (
        dimensionar_ligacoes, dimensionar_ligacoes_central,
    )

    geo = GeometriaViga(L=20.25, h0=0.60, alpha_deg=4.5, b=0.26)
    mat = GlulamMaterial("GL24h", 2, "curta")
    pv = ParametrosVento(
        V0=45, S1=1, categoria="IV", classe="B", S3=1,
        L=20.25, H1=1, h=7, dist_portico=5.75,
    )
    load = carregamentos_com_vento(geo, mat, 1.5, 0.25, 5.75, pv)
    lig  = dimensionar_ligacoes(mat, load, geo)
    ligc = dimensionar_ligacoes_central(mat, load, geo)
    res  = verificar_fadiga_deslizamento(mat, load, geo, lig, ligc)
    relatorio(res, k_def=mat.k_def, psi_2=0.0)
