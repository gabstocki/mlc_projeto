"""
checks/elu/beiral.py — Balanços do beiral e do oitão (issue 82).

A cobertura projeta-se 1,00 m além da face dos pilares de perímetro:

  · BEIRAL (alinhamentos A e C) — a viga de duplo-bisel prolonga-se em balanço
    além do apoio, de a = projeção + meia dimensão do pilar, com o extradorso
    continuando a água (altura decrescente até h_ponta = h0 − a·tg α). Os
    efeitos do balanço sobre o VÃO (momento de extremidade, reações) entram na
    própria análise da viga (core.loads.analisar_biarticulada); aqui verifica-se
    o balanço como peça: flexão na raiz com k_m,α da borda inclinada (EC5
    §6.4.2), cisalhamento (§6.1.7), flambagem lateral (§6.3.3, Tab. 6.1) e a
    flecha da ponta (EC5 §7.2, Tab. 7.2, linha dos balanços), que soma a do
    próprio balanço à rotação do apoio causada pelo vão.

  · OITÃO (eixos 1 e 9) — as terças prolongam-se em balanço além do pórtico de
    frontão. Terça contínua sobre o apoio de extremidade com balanço a_t: a
    flexão e o cisalhamento da raiz e a flecha da ponta (viga com balanço sob
    carga uniforme em todo o comprimento).

Os momentos dos balanços são pequenos frente aos do vão (≈ 1 % na viga); a
verificação existe para que a peça projetada tenha a sua própria taxa e para
documentar a flecha da ponta, que a análise do vão não fornece.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.integrate import trapezoid

from mlc_projeto.checks.els.deflection_els import flecha_numerica
from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.loads import Carregamentos, analisar_biarticulada
from mlc_projeto.core.materials import GlulamMaterial

#: EC5 Tab. 7.2, balanços — limites menos restritivos da faixa, coerentes com os
#: adotados para as vigas (ℓ/300 e ℓ/250, também os menos restritivos).
LIM_INST_BALANCO = 150.0     # w_inst ≤ a/150
LIM_FIN_BALANCO = 125.0      # w_net,fin ≤ a/125


def k_m_alpha(mat: GlulamMaterial, alpha_rad: float, borda_tracionada: bool) -> float:
    """EC5 Eq. 6.39 (borda inclinada tracionada) e 6.40 (comprimida)."""
    t = math.tan(alpha_rad)
    fm, fv = mat.f_m_d, mat.f_v_d
    if borda_tracionada:
        return 1.0 / math.sqrt(1.0 + (fm / (0.75 * fv) * t) ** 2
                               + (fm / mat.f_t90_d * t ** 2) ** 2)
    return 1.0 / math.sqrt(1.0 + (fm / (1.5 * fv) * t) ** 2
                           + (fm / mat.f_c90_d * t ** 2) ** 2)


def flecha_ponta_viga(geo: GeometriaViga, mat: GlulamMaterial, q_esq: float,
                      q_dir: float, *, desenvolve_empuxo: bool,
                      n: int = 201) -> float:
    """Flecha da ponta do balanço ESQUERDO (m, ↓ positiva) sob q_esq/q_dir (kN/m).

    Linha elástica do vão (com os momentos dos balanços) prolongada no balanço:
    w(−u) = w(0) − θ_A·u + ∫₀ᵘ (u − s)·κ(s) ds, com a convenção de
    `flecha_numerica` (w'' = M/EI); a flecha descendente é −w(−a). Seção
    variável h(u) = h0 − u·tg α; deformação por cortante desprezada no balanço.
    """
    a = float(geo.a_bal)
    if a <= 0.0:
        return 0.0
    r = analisar_biarticulada(
        q=0.5 * (q_esq + q_dir), L=geo.L, h0=geo.h0, h_ap=geo.h_ap,
        alpha_rad=geo.alpha_rad, b=geo.b, q_esq=q_esq, q_dir=q_dir,
        desenvolve_empuxo=desenvolve_empuxo, a_bal=a,
    )
    M_x = np.interp(geo.x, r["x"], r["M_x"]) * 1e3
    _, w_x, _, _ = flecha_numerica(geo, mat, M_x, geo.x, incluir_cisalhamento=False)
    theta_A = (w_x[1] - w_x[0]) / (geo.x[1] - geo.x[0])
    u = np.linspace(0.0, a, n)
    M_c = -q_esq * 1e3 * (a - u) ** 2 / 2.0                  # N·m (hogging < 0)
    kappa = M_c / (mat.E0_mean * geo.b * geo.h_balanco(u) ** 3 / 12.0)
    integ = float(trapezoid(kappa * (a - u), u))
    w_tip = -theta_A * a + integ
    return -w_tip


def _flecha_ponta_terca(q_Nm: float, L: float, a: float, E: float, I: float) -> float:
    """Ponta do balanço de viga com balanço, carga uniforme em todo o comprimento
    (Roark): δ = q·a·(4a²L − L³ + 3a³)/(24EI), ↓ positiva (m)."""
    return q_Nm * a * (4 * a ** 2 * L - L ** 3 + 3 * a ** 3) / (24.0 * E * I)


def modulo_secao_com_rasgo(b: float, h: float, t_r: float, h_r: float) -> float:
    """
    Menor módulo resistente (m³) da seção b × h com rasgo central de largura t_r
    aberto a partir do intradorso até a altura h_r (issue 83): a raiz do balanço
    fica sobre o apoio L1, onde a chapa embutida ocupa o rasgo.
    """
    h_r = min(max(h_r, 0.0), h)
    A = b * h - t_r * h_r
    y = (b * h ** 2 / 2.0 - t_r * h_r ** 2 / 2.0) / A          # centroide, do intradorso
    I = (b * h ** 3 / 12.0 + b * h * (h / 2.0 - y) ** 2
         - t_r * h_r ** 3 / 12.0 - t_r * h_r * (h_r / 2.0 - y) ** 2)
    return I / max(y, h - y)


def verificar_balanco_viga(geo: GeometriaViga, load: Carregamentos,
                           mat: GlulamMaterial, t_rasgo_m: float = 0.0,
                           h_rasgo_m: float | None = None) -> dict:
    """
    Balanço da viga no beiral: ELU (envelope das combinações) e ELS da ponta.
    A raiz fica sobre o apoio L1: seção líquida do rasgo da chapa embutida
    (largura t_rasgo_m até h_rasgo_m; sem h_rasgo_m, rasgo em toda a altura).
    """
    a, h0, b = float(geo.a_bal), float(geo.h0), float(geo.b)
    h_r = h0 if h_rasgo_m is None else float(h_rasgo_m)
    W0 = modulo_secao_com_rasgo(b, h0, float(t_rasgo_m), h_r) if t_rasgo_m else b * h0 ** 2 / 6.0
    melhor = None
    for nome, c in load.combinacoes_ELU().items():
        m = mat.com_duracao(c.duracao)
        for q in (c.q_esq, c.q_dir):
            M = abs(q) * a ** 2 / 2.0                      # kN·m na raiz
            V = abs(q) * a                                 # kN
            km = k_m_alpha(m, geo.alpha_rad, borda_tracionada=q > 0)
            sigma = M * 1e3 / W0                           # Pa
            eta_m = sigma / (km * m.f_m_d)
            tau = 1.5 * V * 1e3 / (m.k_cr * (b - t_rasgo_m) * h0)
            eta_v = tau / m.f_v_d
            # Flambagem lateral — EC5 Tab. 6.1 (balanço, carga uniforme):
            # l_ef = 0,5·a; σ_m,crit = 0,78·b²·E0,05/(h·l_ef) (Eq. 6.32)
            l_ef = 0.5 * a + (2.0 * h0 if q < 0 else 0.0)  # carga na borda comprimida
            s_crit = 0.78 * b ** 2 * m.E0_05 / (h0 * l_ef)
            lam = math.sqrt(m.f_m_k / s_crit)
            k_crit = 1.0 if lam <= 0.75 else (1.56 - 0.75 * lam if lam <= 1.4 else 1 / lam ** 2)
            eta_ltb = sigma / (k_crit * km * m.f_m_d)
            eta = max(eta_m, eta_v, eta_ltb)
            if melhor is None or eta > melhor["eta"]:
                melhor = dict(comb=nome, q_kNm=q, M_raiz_kNm=M, V_raiz_kN=V,
                              k_m_alpha=km, sigma_MPa=sigma / 1e6, eta_flexao=eta_m,
                              tau_MPa=tau / 1e6, eta_cisalhamento=eta_v,
                              l_ef_m=l_ef, lambda_rel_m=lam, k_crit=k_crit,
                              eta_ltb=eta_ltb, eta=eta)

    # ── ELS — flecha da ponta (mesmas parcelas do ELS da viga) ────────────
    mat_l = mat.com_duracao("longa")
    emp = load.empuxo_desenvolve

    def _w(qe, qd):
        return flecha_ponta_viga(geo, mat_l, qe, qd, desenvolve_empuxo=emp)

    w_G = _w(load.g_k, load.g_k)
    w_Q = _w(load.q_k, load.q_k)
    w_W = [_w(p["w_esq_kNm2"] * load.area_trib, p["w_dir_kNm2"] * load.area_trib)
           for p in load.padroes_vento]
    w_var = max([w_Q] + w_W)                                 # ↓ governante
    w_inst = w_G + w_var
    w_fin = w_G * (1.0 + mat_l.k_def) + w_var                # ψ2 = 0 (cat. H)
    lim_inst, lim_fin = a / LIM_INST_BALANCO, a / LIM_FIN_BALANCO
    eta_els = max(abs(w_inst) / lim_inst, abs(w_fin) / lim_fin)
    eta = max(melhor["eta"], eta_els)
    return {
        "a_m": round(a, 4), "h0_m": h0, "h_ponta_m": round(geo.h_ponta, 4),
        "W_raiz_m3": round(W0, 6), "W_bruto_m3": round(b * h0 ** 2 / 6.0, 6),
        "t_rasgo_m": t_rasgo_m, "h_rasgo_m": h_r if t_rasgo_m else 0.0,
        **{k: (round(v, 4) if isinstance(v, float) else v) for k, v in melhor.items()
           if k != "eta"},
        "eta_ELU": round(melhor["eta"], 4),
        "w_inst_mm": round(w_inst * 1e3, 3), "w_fin_mm": round(w_fin * 1e3, 3),
        "lim_inst_mm": round(lim_inst * 1e3, 2), "lim_fin_mm": round(lim_fin * 1e3, 2),
        "eta_ELS": round(eta_els, 4),
        "eta": round(eta, 4), "ok": eta <= 1.0,
        "norma": "EC5 §6.4.2 (k_m,α) + §6.1.7 + §6.3.3 Tab. 6.1 + §7.2 Tab. 7.2",
    }


def verificar_balanco_terca(mat: GlulamMaterial, *, a_m: float, L_t: float, s: float,
                            b: float, h: float, alpha_deg: float, g_k_m2: float,
                            q_k_m2: float, w_kNm2: float, k_m: float = 0.7) -> dict:
    """Balanço da terça no oitão (contínua sobre o pórtico de frontão)."""
    g, q, w = g_k_m2 * s, q_k_m2 * s, w_kNm2 * s           # kN/m
    W_y, W_z = b * h ** 2 / 6.0, h * b ** 2 / 6.0
    M_z = 1.35 * g * math.sin(math.radians(alpha_deg)) * a_m ** 2 / 2.0
    casos = (("1,35G+1,5W", 1.35 * g + 1.5 * w, "curta"),
             ("1,35G+1,5Q", 1.35 * g + 1.5 * q, "media"))
    melhor = None
    for nome, qd, dur in casos:
        m = mat.com_duracao(dur)
        M_y = qd * a_m ** 2 / 2.0
        s_y, s_z = M_y * 1e3 / W_y, M_z * 1e3 / W_z
        eta_m = max(s_y / m.f_m_d + k_m * s_z / m.f_m_d, k_m * s_y / m.f_m_d + s_z / m.f_m_d)
        tau = 1.5 * qd * a_m * 1e3 / (m.k_cr * b * h)
        eta_v = tau / m.f_v_d
        eta = max(eta_m, eta_v)
        if melhor is None or eta > melhor["eta"]:
            melhor = dict(comb=nome, q_d_kNm=qd, M_y_kNm=M_y, M_z_kNm=M_z,
                          eta_flexao=eta_m, eta_cisalhamento=eta_v, eta=eta)
    m_l = mat.com_duracao("longa")
    E, I = m_l.E0_mean, b * h ** 3 / 12.0
    w_G = _flecha_ponta_terca(g * 1e3, L_t, a_m, E, I)
    w_var = max(_flecha_ponta_terca(q * 1e3, L_t, a_m, E, I),
                _flecha_ponta_terca(w * 1e3, L_t, a_m, E, I))
    w_inst = w_G + w_var
    w_fin = w_G * (1.0 + m_l.k_def) + w_var
    lim_inst, lim_fin = a_m / LIM_INST_BALANCO, a_m / LIM_FIN_BALANCO
    eta_els = max(abs(w_inst) / lim_inst, abs(w_fin) / lim_fin)
    eta = max(melhor["eta"], eta_els)
    return {
        "a_m": round(a_m, 4),
        **{k: (round(v, 4) if isinstance(v, float) else v) for k, v in melhor.items()
           if k != "eta"},
        "eta_ELU": round(melhor["eta"], 4),
        "w_inst_mm": round(w_inst * 1e3, 3), "w_fin_mm": round(w_fin * 1e3, 3),
        "lim_inst_mm": round(lim_inst * 1e3, 2), "lim_fin_mm": round(lim_fin * 1e3, 2),
        "eta_ELS": round(eta_els, 4),
        "eta": round(eta, 4), "ok": eta <= 1.0,
        "norma": "EC5 §6.1.6 + §6.1.7 + §7.2 Tab. 7.2",
    }
