"""
checks/els/deslocamento_succao.py — Deslocamento vertical do apoio sob sucção (issue 112).

Sob o arrancamento, a viga sobe em relação à fundação pela soma das parcelas do
caminho de carga (combinação característica, EN 1990 §6.5.3(2)a):

  1. folga acima dos pinos da L1/L1c (issue 72): g_i(u) = tol + α⊥·(u_max − u)·y_i,
     máxima na umidade mínima de serviço;
  2. deslizamento dos pinos em carga, K_ser (EC5 §7.1, aço–madeira = 2×, dois
     planos), com engajamento sequencial das fileiras (issue 111);
  3. caminho até a base:
       · pilar corrente (L3, L3c): alongamento do tirante interno, N·L/(E·A_s),
         e dos chumbadores, mais a flexão da chapa de topo do pilarete;
       · pilar montante bipartido (pórticos 1, 2, 8 e 9): alongamento das lâminas,
         folga dos furos das cavilhas do pé (d0 − d, inversão de compressão para
         tração) e o seu deslizamento K_ser, mais os chumbadores;
  4. flecha ascendente líquida da viga (G + W, issue ELS), somada onde a peça
     ligada está ao longo do vão.

Compatibilidade (EN 1990 Anexo A1, A1.4.2: os critérios de funcionalidade são
fixados no projeto). O limite de cada peça é o curso disponível no seu detalhe:
  · escora sobre as lâminas do montante (pórticos 2 e 8): folga entre o topo da
    viga e a escora, consumida pelo inchamento de toda a altura e pela subida da
    viga em relação às lâminas (parcelas 1 e 2);
  · topo dos pilares de frontão (L1f): curso dos furos ovalizados contra a
    subida da viga do frontão no ponto do PF (parcelas 1–4, apoio bipartido);
  · condutor da calha junto ao pilar central: a junta deslizante cobre a subida
    do apoio central (parcelas 1–3, L3c).
"""

from __future__ import annotations

import math

from mlc_projeto.connections.oblongo_L1 import ALPHA_PERP, TOLERANCIA_MM, U_MONTAGEM, U_SERVICO

E_ACO_MPA = 200_000.0
NU_ACO = 0.3


def subida_grupo_mm(P_kN: float, gaps_mm: list[float], K_pino_kNpmm: float) -> float:
    """Subida δ tal que Σ K·max(δ − g_i, 0) = P (contato elástico sequencial)."""
    if P_kN <= 0:
        return 0.0
    lo, hi = 0.0, max(gaps_mm) + P_kN / K_pino_kNpmm + 1.0
    for _ in range(200):
        m = 0.5 * (lo + hi)
        f = sum(K_pino_kNpmm * max(m - g, 0.0) for g in gaps_mm)
        lo, hi = (m, hi) if f < P_kN else (lo, m)
    return hi


def flecha_chapa_circular_mm(P_kN: float, r_mm: float, t_mm: float) -> float:
    """Chapa circular simplesmente apoiada no tubo, carga central (Timoshenko)."""
    D = E_ACO_MPA * t_mm ** 3 / (12.0 * (1.0 - NU_ACO ** 2))
    return (3.0 + NU_ACO) / (1.0 + NU_ACO) * P_kN * 1e3 * r_mm ** 2 / (16.0 * math.pi * D)


def flecha_no_ponto(w_meio_mm: float, x_m: float, L_m: float) -> float:
    """Flecha de viga biapoiada sob carga uniforme em x (forma exata da elástica)."""
    xi = x_m / L_m
    return w_meio_mm * 16.0 / 5.0 * xi * (1.0 - 2.0 * xi ** 2 + xi ** 3)


def verificar_deslocamento_succao(
        *, R_up_k_kN: float, y_fileiras_mm: list[float], n_por_fileira: int,
        K_ser_plano_Nmm: float, h0_mm: float,
        tirantes: dict, chumb_corrente: dict, bipartido: dict,
        w_up_meio_mm: float, L_m: float,
        pf: dict, folga_escora_mm: float,
        alpha: float = ALPHA_PERP, u_servico: tuple = U_SERVICO,
        u_montagem: tuple = U_MONTAGEM, tol_mm: float = TOLERANCIA_MM) -> dict:
    """
    tirantes: {rótulo: {"n_vigas", "A_s_mm2", "L_mm", "r_chapa_mm", "t_chapa_mm"}}
    chumb_corrente: {"n", "A_s_mm2", "L_mm"}
    bipartido: {"n_vigas", "A_laminas_mm2", "L_mm", "E_MPa", "n_cav", "K_ser_cav_kNpmm",
                "folga_furo_mm", "chumb": {"n", "A_s_mm2", "L_mm"}}
    pf: {"x_m", "curso_mm", "y_pino_topo_mm"}
    """
    K_pino = 2.0 * 2.0 * K_ser_plano_Nmm / 1e3                 # kN/mm, aço–madeira, 2 planos
    ys = [y for y in y_fileiras_mm for _ in range(n_por_fileira)]
    u_lo, u_hi = u_servico

    def pinos(u: float, n_vigas: int = 1) -> dict:
        gaps = [tol_mm + alpha * (u_hi - u) * y for y in ys]
        d = subida_grupo_mm(R_up_k_kN, gaps, K_pino)        # cada viga tem o seu grupo
        return {"folga_mm": round(min(gaps), 2), "deslizamento_mm": round(d - min(gaps), 2),
                "subida_mm": d}

    def chumb(N_kN: float, c: dict) -> float:
        return N_kN * 1e3 * c["L_mm"] / (E_ACO_MPA * c["n"] * c["A_s_mm2"])

    caminhos = {}
    for rot, t in tirantes.items():
        N = R_up_k_kN * t["n_vigas"]
        tir = N * 1e3 * t["L_mm"] / (E_ACO_MPA * t["A_s_mm2"])
        base = chumb(N, chumb_corrente) + flecha_chapa_circular_mm(N, t["r_chapa_mm"], t["t_chapa_mm"])
        por_u = {}
        for u in (u_lo, u_hi):
            p = pinos(u)
            por_u[u] = {**{k: v for k, v in p.items() if k != "subida_mm"},
                        "tirante_mm": round(tir, 2), "base_mm": round(base, 2),
                        "total_mm": round(p["subida_mm"] + tir + base, 2)}
        caminhos[rot] = por_u
    b = bipartido
    Nb = R_up_k_kN * b["n_vigas"]
    lam = Nb * 1e3 * b["L_mm"] / (b["E_MPa"] * b["A_laminas_mm2"])
    pe = b["folga_furo_mm"] + Nb / (b["n_cav"] * b["K_ser_cav_kNpmm"])
    base_b = chumb(Nb, b["chumb"])
    bip = {}
    for u in (u_lo, u_hi):
        p = pinos(u)
        bip[u] = {**{k: v for k, v in p.items() if k != "subida_mm"},
                  "laminas_mm": round(lam, 2), "pe_mm": round(pe, 2), "base_mm": round(base_b, 2),
                  "total_mm": round(p["subida_mm"] + lam + pe + base_b, 2)}
    caminhos["montante bipartido"] = bip

    # ── Compatibilidade ──────────────────────────────────────────────────────
    # escora × topo da viga (montante): o apoio da viga e a escora estão nas
    # mesmas lâminas; contam a subida nos pinos e o inchamento de toda a altura,
    # a partir da montagem mais seca (u_mont,min).
    esc = {u: pinos(u)["subida_mm"] + alpha * (u - u_montagem[0]) * h0_mm for u in (u_lo, u_hi)}
    u_esc = max(esc, key=esc.get)
    d_esc = esc[u_esc]
    # PF: subida do apoio bipartido do frontão + flecha ascendente no ponto do PF
    # + inchamento entre o intradorso e o pino mais alto da L1f.
    w_pf = abs(flecha_no_ponto(w_up_meio_mm, pf["x_m"], L_m))
    rel_pf = {u: bip[u]["total_mm"] + w_pf + alpha * (u - u_montagem[0]) * pf["y_pino_topo_mm"]
              for u in (u_lo, u_hi)}
    u_pf = max(rel_pf, key=rel_pf.get)
    d_pf = rel_pf[u_pf]
    # condutor: subida do apoio central (L3c), na pior umidade
    rot_c = next((r for r in tirantes if "L3c" in r), next(iter(tirantes)))
    d_cond = max(caminhos[rot_c][u]["total_mm"] for u in (u_lo, u_hi))
    junta = 5.0 * math.ceil((d_cond + 10.0) / 5.0)
    d_max_corr = max(c[u]["total_mm"] for r, c in caminhos.items() for u in c)
    eta_esc = d_esc / folga_escora_mm
    eta_pf = d_pf / pf["curso_mm"]
    eta = max(eta_esc, eta_pf)
    return {
        "verificacao": "Deslocamento vertical sob sucção e compatibilidade",
        "R_up_k_kN": round(R_up_k_kN, 2), "K_ser_pino_kNpmm": round(K_pino, 1),
        "caminhos": caminhos, "subida_max_apoio_mm": round(d_max_corr, 1),
        "w_up_meio_mm": round(abs(w_up_meio_mm), 2),
        "subida_max_meio_vao_mm": round(d_max_corr + abs(w_up_meio_mm), 1),
        "escora": {"u_gov": u_esc, "delta_mm": round(d_esc, 1), "folga_mm": folga_escora_mm,
                   "eta": round(eta_esc, 4)},
        "pf": {"u_gov": u_pf, "delta_mm": round(d_pf, 1), "w_up_pf_mm": round(w_pf, 2),
               "curso_mm": pf["curso_mm"], "eta": round(eta_pf, 4)},
        "condutor": {"subida_mm": round(d_cond, 1), "junta_deslizante_mm": junta},
        "eta": round(eta, 4), "ok": eta <= 1.0,
        "norma": "EN 1990 §6.5.3 e A1.4.2 | EC5 §7.1 (K_ser) | EN 1993-1-1 (aço)",
    }
