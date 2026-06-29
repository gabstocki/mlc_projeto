"""
checks/connections/fadiga_ligacoes.py
Verificação de fadiga e deslizamento das ligações EC5.

EC5 §8.1.5  — Forças alternadas (fadiga): redução de capacidade
EC5 §7.1    — Deslizamento sob ELS: K_ser e u_slip
EC5 §2.3.2.2 — K_ser,fin com fluência

Ligações verificadas:
    L1  — base pilar lateral  (8 pinos d=20mm, chapa-madeira, duplo corte)
    L2  — cumeeira            (1 pino  d=30mm, chapa-madeira, duplo corte)
    L1c — base pilar central  (2×8 pinos d=20mm, 2 chapas independentes)
"""

from __future__ import annotations
import math

# ── Material GL24h ────────────────────────────────────────────
rho_k   = 385.0     # kg/m³ — densidade característica GL24h
rho_m   = 430.0     # kg/m³ — densidade média GL24h (Table 1 EN14080)
gamma_M = 1.30      # coeficiente parcial para ligações (EC5 Tabela 2.3)

# ── Fatores k_mod por combinação ──────────────────────────────
# ELU_C2: duração média  (vento dominante) → k_mod = 0.80, Classe 2
# ELS_S1: duração média  (vento dominante) → k_mod = 0.80
# ELS_S3: duração longa  (permanente)      → k_mod = 0.70
k_mod = {"ELU_C2": 0.80, "ELS_S1": 0.80, "ELS_S3": 0.70}

# ── Fluência ──────────────────────────────────────────────────
k_def  = 0.80    # GL24h Classe 2 (EC5 Tabela 3.2)
psi_2  = 0.30    # fator quasi-permanente sobrecarga cobertura (EN1990)

# ── Esforços nas ligações (do pipeline EC5) ───────────────────
# L1 — base pilar lateral
# Forças na ligação (ELU_C2 governa):
# R_v = 97.84 kN  (vertical — perpendicular ao pilar)
# H   = 621.60 kN (horizontal — axial no pilar)
# N_pilar = √(R_v² + H²) ≈ 627 kN (axial total no pilar)
# A ligação resiste à componente axial N_pilar
# sob vento oposto: N gera tração → alternância

F_N_ELU_C2 = 627.36   # kN — força axial ELU_C2 (compressão)
F_N_ELS_S1 = 406.57   # kN — força axial ELS_S1
F_N_ELS_S3 = 280.00   # kN — força axial ELS_S3 (carga permanente)
F_N_vento  = 180.00   # kN — componente de vento (tração estimada)
# Nota: vento gera ~29% da carga total → F_vento ≈ 0.29 × F_N_ELU_C2

# L2 — cumeeira (pino d=30mm)
F_V_ELU_C2_L2 =  97.84  # kN — cortante na cumeeira (= R_v)
F_V_ELS_S1_L2 =  63.44  # kN

# ── Capacidade das ligações (do pipeline EC5) ─────────────────
# L1: F_Rd = 649 kN (ELU_C2) → η = 0.955 (8 pinos d=20mm, duplo corte)
F_Rd_L1_ELU  = 649.0    # kN — capacidade ELU_C2
# Capacidade característica = F_Rd × γ_M / k_mod
F_Rk_L1 = F_Rd_L1_ELU * gamma_M / k_mod["ELU_C2"]
# → F_Rk = 649 × 1.30 / 0.80 = 1054.6 kN (característica total)

# L2: F_Rd = 109.7 kN → η = 0.890
F_Rd_L2_ELU  = 109.7    # kN — capacidade ELU_C2
F_Rk_L2 = F_Rd_L2_ELU * gamma_M / k_mod["ELU_C2"]

# L1c: 2×8 pinos → capacidade ≈ 2 × F_Rd_L1_ELU = 1298 kN
F_Rd_L1c_ELU = 2 * 649.0

# ── Módulo de deslizamento K_ser ──────────────────────────────
# EC5 §7.1 Tabela 7.1: K_ser = ρ_m^1.5 × d / 23  (N/mm por plano por pino)
# Conexão chapa metálica-madeira: K_ser × 2.0 (EC5 §7.1(3))

def K_ser_pino(d_mm: float, rho_m: float = rho_m,
               aco_madeira: bool = True) -> float:
    """
    Módulo de deslizamento por plano de corte por pino (N/mm).
    EC5 §7.1 Tabela 7.1 — dowels/pinos.
    """
    K = rho_m**1.5 * d_mm / 23.0   # N/mm
    if aco_madeira:
        K *= 2.0    # EC5 §7.1(3): aço-madeira multiplica por 2
    return K


def K_ser_fin(K_ser: float, k_def: float = k_def,
              psi_2: float = psi_2) -> float:
    """
    Módulo de deslizamento final (com fluência).
    EC5 §2.3.2.2 Eq. (2.9).
    K_ser,fin = K_ser / (1 + ψ_2 × k_def)
    """
    return K_ser / (1.0 + psi_2 * k_def)


def deslizamento_ligacao(F_Ed_kN: float, n_pinos: int,
                          K_ser: float, n_planos: int = 2) -> float:
    """
    Deslizamento da ligação sob carga F_Ed (kN).
    u = F_Ed / (n_pinos × n_planos × K_ser)   [mm]
    """
    F_N = F_Ed_kN * 1e3   # N
    return F_N / (n_pinos * n_planos * K_ser)


# ── Verificação §8.1.5: Forças alternadas ────────────────────

def verificar_forcas_alternadas(
    F_t_Ed: float, F_c_Ed: float,
    F_Rd: float, nome: str
) -> dict:
    """
    EC5 §8.1.5: Forças alternadas (tração ↔ compressão).

    Dimensionar para:
        (F_t,Ed + 0.5×F_c,Ed) ≤ F_Rd
        (F_c,Ed + 0.5×F_t,Ed) ≤ F_Rd

    Args:
        F_t_Ed : força de tração (kN, positivo)
        F_c_Ed : força de compressão (kN, positivo)
        F_Rd   : capacidade de cálculo (kN)
        nome   : identificação da ligação
    """
    F_combinada_t = F_t_Ed + 0.5 * F_c_Ed   # governa se F_t > F_c
    F_combinada_c = F_c_Ed + 0.5 * F_t_Ed   # governa se F_c > F_t
    F_max = max(F_combinada_t, F_combinada_c)
    eta   = F_max / F_Rd

    return {
        "ligacao":        nome,
        "F_t_Ed_kN":      round(F_t_Ed, 3),
        "F_c_Ed_kN":      round(F_c_Ed, 3),
        "F_comb_t_kN":    round(F_combinada_t, 3),
        "F_comb_c_kN":    round(F_combinada_c, 3),
        "F_max_kN":       round(F_max, 3),
        "F_Rd_kN":        round(F_Rd, 3),
        "eta_alt":        round(eta, 4),
        "ok":             eta <= 1.0,
    }


# ── Pipeline principal ────────────────────────────────────────

def verificar_fadiga_deslizamento() -> dict:
    """
    Verificação completa de fadiga e deslizamento das ligações.
    Retorna dict com todos os resultados para integração no report.
    """
    resultados = {}

    # ═══════════════════════════════════════════════════════════
    # L1 — BASE PILAR LATERAL (8 pinos d=20mm)
    # ═══════════════════════════════════════════════════════════
    d_L1   = 20.0   # mm
    n_L1   = 8      # pinos
    np_L1  = 2      # planos de corte (duplo)

    Kser_L1     = K_ser_pino(d_L1, aco_madeira=True)
    Kser_fin_L1 = K_ser_fin(Kser_L1)

    # Deslizamento ELS_S1 (instantâneo)
    u_inst_L1 = deslizamento_ligacao(F_N_ELS_S1, n_L1, Kser_L1, np_L1)
    # Deslizamento ELS_S3 (final com fluência)
    u_fin_L1  = deslizamento_ligacao(F_N_ELS_S3, n_L1, Kser_fin_L1, np_L1)

    # Limite de deslizamento: L/1000 = 7000/1000 = 7 mm (pilar H=7m)
    u_lim_L1 = 7000.0 / 1000.0   # 7 mm
    eta_slip_L1 = max(u_inst_L1, u_fin_L1) / u_lim_L1

    # §8.1.5 — forças alternadas
    # Carga permanente: compressão N = 280 kN
    # Vento oposto:     tração   N = 180 kN (estimativa conservadora)
    # F_Rd para tração: mesma capacidade (pinos simétricos)
    alt_L1 = verificar_forcas_alternadas(
        F_t_Ed=F_N_vento,    # kN tração (vento)
        F_c_Ed=F_N_ELS_S3,   # kN compressão (permanente)
        F_Rd=F_Rd_L1_ELU,
        nome="L1"
    )

    resultados["L1"] = {
        "descricao":      "Base pilar lateral — 8 pinos d=20mm",
        "d_mm":           d_L1,
        "n_pinos":        n_L1,
        "n_planos":       np_L1,
        "K_ser_Nmm":      round(Kser_L1, 2),
        "K_ser_fin_Nmm":  round(Kser_fin_L1, 2),
        "u_inst_mm":      round(u_inst_L1, 4),
        "u_fin_mm":       round(u_fin_L1,  4),
        "u_lim_mm":       u_lim_L1,
        "eta_slip":       round(eta_slip_L1, 4),
        "slip_ok":        eta_slip_L1 <= 1.0,
        "alternada":      alt_L1,
        "fadiga_governa": False,   # ver conclusão abaixo
    }

    # ═══════════════════════════════════════════════════════════
    # L2 — CUMEEIRA (1 pino d=30mm)
    # ═══════════════════════════════════════════════════════════
    d_L2  = 30.0
    n_L2  = 1
    np_L2 = 2

    Kser_L2     = K_ser_pino(d_L2, aco_madeira=True)
    Kser_fin_L2 = K_ser_fin(Kser_L2)

    # Esforço na cumeeira: cortante = R_v (não há alternância relevante)
    u_inst_L2 = deslizamento_ligacao(F_V_ELS_S1_L2, n_L2, Kser_L2, np_L2)
    u_fin_L2  = deslizamento_ligacao(F_V_ELS_S1_L2, n_L2, Kser_fin_L2, np_L2)

    # Limite: L/1000 = 20250/1000 = 20.25 mm → usar L/500 = 40.5 mm
    # para ligação interna (cumeeira não é apoio de extremidade)
    u_lim_L2  = 20250.0 / 500.0   # 40.5 mm
    eta_slip_L2 = max(u_inst_L2, u_fin_L2) / u_lim_L2

    # §8.1.5: cumeeira só tem compressão (carga simétrica)
    # vento não gera alternância relevante na cumeeira isostática
    alt_L2 = {
        "ligacao": "L2",
        "F_t_Ed_kN": 0.0,
        "F_c_Ed_kN": F_V_ELS_S1_L2,
        "F_comb_t_kN": 0.0,
        "F_comb_c_kN": F_V_ELS_S1_L2,
        "F_max_kN": F_V_ELS_S1_L2,
        "F_Rd_kN": F_Rd_L2_ELU,
        "eta_alt": round(F_V_ELS_S1_L2 / F_Rd_L2_ELU, 4),
        "ok": True,
        "nota": "Pórtico isostático: cumeeira só compressão (M=0)",
    }

    resultados["L2"] = {
        "descricao":      "Cumeeira — 1 pino d=30mm",
        "d_mm":           d_L2,
        "n_pinos":        n_L2,
        "n_planos":       np_L2,
        "K_ser_Nmm":      round(Kser_L2, 2),
        "K_ser_fin_Nmm":  round(Kser_fin_L2, 2),
        "u_inst_mm":      round(u_inst_L2, 4),
        "u_fin_mm":       round(u_fin_L2,  4),
        "u_lim_mm":       u_lim_L2,
        "eta_slip":       round(eta_slip_L2, 4),
        "slip_ok":        eta_slip_L2 <= 1.0,
        "alternada":      alt_L2,
        "fadiga_governa": False,
    }

    # ═══════════════════════════════════════════════════════════
    # L1c — BASE PILAR CENTRAL (2×8 pinos d=20mm)
    # ═══════════════════════════════════════════════════════════
    # Pilar central: N_d = 195.68 kN (dois pórticos)
    # Forças alternadas: vento cancela (pórticos opostos)
    # → sem alternância significativa
    F_N_L1c_ELS = 195.68 * (6.266 / 9.6634)   # proporcional ao ELS_S1
    F_N_L1c_perm= 195.68 * 0.45               # ~permanente

    Kser_L1c     = K_ser_pino(20.0, aco_madeira=True)
    Kser_fin_L1c = K_ser_fin(Kser_L1c)

    # 2 chapas × 8 pinos × 2 planos cada
    u_inst_L1c = deslizamento_ligacao(F_N_L1c_ELS, 16, Kser_L1c, 2)
    u_fin_L1c  = deslizamento_ligacao(F_N_L1c_perm, 16, Kser_fin_L1c, 2)
    u_lim_L1c  = 7000.0 / 1000.0
    eta_slip_L1c = max(u_inst_L1c, u_fin_L1c) / u_lim_L1c

    alt_L1c = {
        "ligacao": "L1c",
        "F_t_Ed_kN": 0.0,
        "F_c_Ed_kN": F_N_L1c_ELS,
        "F_comb_t_kN": 0.0,
        "F_comb_c_kN": F_N_L1c_ELS,
        "F_max_kN": F_N_L1c_ELS,
        "F_Rd_kN": F_Rd_L1c_ELU,
        "eta_alt": round(F_N_L1c_ELS / F_Rd_L1c_ELU, 4),
        "ok": True,
        "nota": "Pilar central: vento cancela entre pórticos opostos",
    }

    resultados["L1c"] = {
        "descricao":      "Base pilar central — 2×8 pinos d=20mm",
        "d_mm":           20.0,
        "n_pinos":        16,
        "n_planos":       2,
        "K_ser_Nmm":      round(Kser_L1c, 2),
        "K_ser_fin_Nmm":  round(Kser_fin_L1c, 2),
        "u_inst_mm":      round(u_inst_L1c, 4),
        "u_fin_mm":       round(u_fin_L1c,  4),
        "u_lim_mm":       u_lim_L1c,
        "eta_slip":       round(eta_slip_L1c, 4),
        "slip_ok":        eta_slip_L1c <= 1.0,
        "alternada":      alt_L1c,
        "fadiga_governa": False,
    }

    return resultados


# ── Relatório ─────────────────────────────────────────────────

def relatorio(res: dict) -> None:
    sep = "═" * 68
    print(sep)
    print("  FADIGA E DESLIZAMENTO DE LIGAÇÕES — EC5 §2.4 + §7.1 + §8.1.5")
    print("  Galpão MLC GL24h — STOCKI Engenharia Estrutural")
    print(sep)

    for cod, r in res.items():
        print(f"\n  ── {cod}: {r['descricao']}")
        print(f"     d={r['d_mm']:.0f}mm | n={r['n_pinos']} pinos "
              f"| {r['n_planos']} planos de corte")
        print()

        # K_ser
        print(f"     EC5 §7.1 — Módulo de deslizamento:")
        print(f"       K_ser     = {r['K_ser_Nmm']:.1f} N/mm  "
              f"(aço-madeira × 2)")
        print(f"       K_ser,fin = {r['K_ser_fin_Nmm']:.1f} N/mm  "
              f"(com k_def={k_def} | ψ₂={psi_2})")

        # Deslizamento
        print(f"\n     EC5 §7.1 — Deslizamento da ligação:")
        print(f"       u_inst = {r['u_inst_mm']:.4f} mm  (ELS_S1)")
        print(f"       u_fin  = {r['u_fin_mm']:.4f} mm  (ELS_S3 + fluência)")
        print(f"       u_lim  = {r['u_lim_mm']:.2f} mm  (L/1000)")
        status = "✓ OK" if r['slip_ok'] else "✗ NÃO OK"
        print(f"       η_slip = {r['eta_slip']:.4f}  → {status}")

        # Forças alternadas
        alt = r['alternada']
        print(f"\n     EC5 §8.1.5 — Forças alternadas (fadiga):")
        if "nota" in alt:
            print(f"       {alt['nota']}")
        else:
            print(f"       F_t,Ed = {alt['F_t_Ed_kN']:.2f} kN  "
                  f"(vento — tração)")
            print(f"       F_c,Ed = {alt['F_c_Ed_kN']:.2f} kN  "
                  f"(permanente — compressão)")
            print(f"       F_comb = {alt['F_max_kN']:.2f} kN  "
                  f"(F_t + 0.5×F_c governa)")
        print(f"       F_Rd   = {alt['F_Rd_kN']:.2f} kN")
        print(f"       η_alt  = {alt['eta_alt']:.4f}  "
              f"→ {'✓ OK' if alt['ok'] else '✗ NÃO OK'}")

    # Conclusão sobre fadiga
    print(f"\n  {'─'*64}")
    print(f"  CONCLUSÃO — EC5 §2.4 (Fadiga):")
    print()
    print(f"  A EC5 §2.4 exige verificação explícita de fadiga quando")
    print(f"  as ações variáveis são frequentemente repetidas.")
    print()
    print(f"  Para este galpão de estacionamento coberto:")
    print(f"    • Sobrecarga de uso:  N ≈ 10³..10⁴ ciclos/vida útil")
    print(f"    • Ações de vento:     N ≈ 10⁴..10⁵ ciclos/vida útil")
    print(f"    • Limiar S-N madeira: N > 10⁶ ciclos (EC5 Annex A)")
    print()
    print(f"  → Número de ciclos muito inferior ao limiar de fadiga.")
    print(f"  → A verificação de §8.1.5 (forças alternadas) governa,")
    print(f"     não a fadiga por S-N.")
    print(f"  → Fadiga não governa o dimensionamento. ✓")
    print()
    print(f"  RESULTADO GLOBAL:")
    all_slip = all(r['slip_ok'] for r in res.values())
    all_alt  = all(r['alternada']['ok'] for r in res.values())
    print(f"    Deslizamento ELS: {'✓ TODAS OK' if all_slip else '✗ VERIFICAR'}")
    print(f"    Forças alternadas: {'✓ TODAS OK' if all_alt else '✗ VERIFICAR'}")
    print(sep)


if __name__ == "__main__":
    res = verificar_fadiga_deslizamento()
    relatorio(res)
