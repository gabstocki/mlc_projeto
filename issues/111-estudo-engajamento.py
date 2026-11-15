"""
Issue 111 — engajamento progressivo dos pinos da L1 sob arrancamento.

Folga acima do pino i, com a regra de montagem da issue 72 (folga ajustada pela
umidade medida), na umidade u de serviço:
    g_i(u) = tol + α⊥·(u_max − u)·y_i
Na umidade máxima as folgas são iguais (= tol); na mínima, crescem com a altura
do pino: os pinos BAIXOS encostam primeiro.

Pino: elástico-perfeitamente plástico, K_u = 2/3·K_ser (EC5 §2.2.2), K_ser de
aço–madeira = 2·ρ_m^1,5·d/23 por plano de corte (EC5 Tab. 7.1 e §7.1(3)),
dois planos; patamar em F_v,Rd (de cálculo). Rigidez alta é desfavorável à
uniformidade (o EC5 não reduz K_ser ⊥ fibras): a hipótese é conservadora.

Uso: .venv/bin/python issues/111-estudo-engajamento.py
"""
from __future__ import annotations

import math

ALPHA = 0.0025
U_MIN, U_MAX = 14.0, 19.0
TOL = 2.0
RHO_M, D = 420.0, 24.0
K_SER_PLANO = 2 * RHO_M ** 1.5 * D / 23 / 1e3          # kN/mm, aço–madeira
K_U = 2 / 3 * 2 * K_SER_PLANO                            # kN/mm por pino (2 planos)
F_RD = 25.017                                            # kN por pino (pipeline)
P_D = 100.544                                            # kN, arrancamento de cálculo
H, B = 1000.0, 320.0
F90_COEF = 0.65 / 1.3                                    # k_mod/γ_M


def forcas(delta, gaps):
    return [min(max(K_U * (delta - g), 0.0), F_RD) for g in gaps]


def resolver(gaps, P=P_D):
    lo, hi = 0.0, max(gaps) + 50
    if sum(forcas(hi, gaps)) < P:
        return None
    for _ in range(200):
        m = 0.5 * (lo + hi)
        lo, hi = (m, hi) if sum(forcas(m, gaps)) < P else (lo, m)
    return hi


def f90_rd(h_e):
    return 14 * B * math.sqrt(h_e / (1 - h_e / H)) / 1e3 * F90_COEF


def estudar(nome, ys, u, fab=0.0):
    gaps = [TOL + ALPHA * (U_MAX - u) * y for y in ys]
    # fabricação: o pino mais baixo encosta `fab` mm antes (pior caso)
    i_low = ys.index(min(ys))
    gaps[i_low] -= fab
    d = resolver(gaps)
    if d is None:
        print(f"{nome:28s} u={u:.0f}%  NÃO atinge P_d")
        return
    F = forcas(d, gaps)
    n_esc = sum(f >= F_RD - 1e-6 for f in F)
    # elástico sem patamar: força do pino mais carregado
    lo, hi = 0.0, max(gaps) + 50
    for _ in range(200):
        m = 0.5 * (lo + hi)
        s = sum(max(K_U * (m - g), 0.0) for g in gaps)
        lo, hi = (m, hi) if s < P_D else (lo, m)
    F_el_max = max(max(K_U * (hi - g), 0.0) for g in gaps)
    dy = F_RD / K_U
    mu = (d - min(gaps)) / dy
    he_eng = max(y for y, f in zip(ys, F) if f > 0.05 * F_RD)
    eta_f90 = P_D / f90_rd(he_eng)
    print(f"{nome:28s} u={u:.0f}%  Δg={max(gaps)-min(gaps):4.1f} mm | δ={d:5.1f} mm | "
          f"escoados {n_esc}/{len(ys)} | F_el,máx/F_Rd={F_el_max/F_RD:4.2f} | "
          f"μ={mu:3.1f} | h_e,ativo={he_eng:.0f} → η_90={eta_f90:.2f}")


if __name__ == "__main__":
    print(f"K_u = {K_U:.1f} kN/mm por pino | δ_y = F_Rd/K_u = {F_RD/K_U:.2f} mm | "
          f"η_90 com h_e = 818: {P_D/f90_rd(818):.2f}\n")
    atual = [818 - 72 * k for k in range(6)]
    casos = {
        "atual 1×6 (coluna)": atual,
        "2 col × 3 fil (818–674)": [818, 818, 746, 746, 674, 674],
        "3 col × 2 fil (818–746)": [818] * 3 + [746] * 3,
        "6 em fileira (y = 818)": [818] * 6,
    }
    for nome, ys in casos.items():
        for u in (U_MIN, U_MAX):
            estudar(nome, ys, u)
    print("\ncom ±0,5 mm de fabricação (pino mais baixo encosta 1,0 mm antes):")
    for nome in ("3 col × 2 fil (818–746)", "6 em fileira (y = 818)"):
        estudar(nome, casos[nome], U_MAX, fab=1.0)
