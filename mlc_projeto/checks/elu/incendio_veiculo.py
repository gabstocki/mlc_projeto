"""
checks/elu/incendio_veiculo.py — Incêndio localizado de veículo (issue 89).

A edificação é isenta de tempo requerido de resistência ao fogo (issue 88): a
exigência regulamentar trata do incêndio generalizado. Num estacionamento
aberto, o cenário realista é outro — um veículo em chamas junto a um pilar,
eventualmente propagando-se aos vizinhos. Esta avaliação é de ROBUSTEZ, não de
conformidade, e é deliberadamente simplificada:

  · Chama e pluma pelo modelo de incêndio localizado da EN 1991-1-2 Anexo C,
    com a taxa de liberação de calor de um automóvel:
        L_f  = −1,02·D + 0,0148·Q^(2/5)                         (C.1)
        z_0  = −1,02·D + 0,00524·Q^(2/5)                        (C.3)
        Θ(z) = 20 + 0,25·Q_c^(2/3)·(z − z_0)^(−5/3) ≤ 900 °C    (C.2)
    com Q em W, Q_c = 0,8·Q, D o diâmetro equivalente da área em chamas.
    Se L_f não alcança o forro (a viga), vale (C.2) no eixo da pluma.
  · Pilar adjacente: a chama envolve as faces voltadas para o veículo. Por
    falta de um modelo de transferência de calor para a madeira sob chama
    localizada, toma-se a exposição como a do incêndio-padrão nas faces
    atingidas e procura-se o TEMPO até o colapso (η = 1) pelo método da seção
    reduzida — comparado à duração da fase intensa do incêndio de um ou mais
    veículos.
"""

from __future__ import annotations

import math

from mlc_projeto.checks.elu.fogo import verificar_fogo_pilar
from mlc_projeto.connections.chapas_aco import ACO_CHAPA

#: Automóvel de passeio grande — curva de projeto com pico de 8,3 MW aos 25 min
#: (programa europeu de ensaios em estacionamentos, CTICM/ECSC). TODO: citar.
Q_CARRO_W = 8.3e6
A_CARRO_M2 = 4.5 * 1.8
Z_FONTE_M = 0.50                     # altura da base das chamas (piso do veículo)
#: Fase intensa (Q ≥ 2 MW) de um veículo e atraso de propagação ao vizinho
#: num estacionamento aberto (mesma fonte).  TODO: citar.
DURACAO_INTENSA_MIN = 30.0
ATRASO_PROPAGACAO_MIN = 12.0


#: Proteção do pilarete: pintura intumescente para exterior, especificada pelo
#: tempo arredondado da exposição e por uma temperatura crítica de projeto
#: abaixo da calculada (margem e faixa usual dos ensaios EN 13381-8).
R_INTUMESCENTE_MIN = 60.0
THETA_CR_PROJETO_C = 750.0

_KY = ((20, 1.0), (400, 1.0), (500, 0.78), (600, 0.47), (700, 0.23), (800, 0.11),
       (900, 0.06), (1000, 0.04), (1100, 0.02), (1200, 0.0))


_KE = ((20, 1.0), (100, 1.0), (200, 0.90), (300, 0.80), (400, 0.70), (500, 0.60),
       (600, 0.31), (700, 0.13), (800, 0.09), (900, 0.0675), (1000, 0.045),
       (1100, 0.0225), (1200, 0.0))


def _interp(tab, T: float) -> float:
    for (a, ka), (b, kb) in zip(tab, tab[1:]):
        if a <= T <= b:
            return ka + (kb - ka) * (T - a) / (b - a)
    return 0.0 if T > 1200 else 1.0


def k_y_theta(T: float) -> float:
    """Fator de redução da tensão de escoamento (EN 1993-1-2 Tab. 3.1)."""
    return _interp(_KY, T)


def k_E_theta(T: float) -> float:
    """Fator de redução do módulo de elasticidade (EN 1993-1-2 Tab. 3.1)."""
    return _interp(_KE, T)


def N_b_fi_Rd(T: float, *, A: float, i: float, l_cr: float, f_y: float) -> float:
    """Resistência à flambagem em incêndio, kN (EN 1993-1-2 Eqs. 4.5–4.7, γ_M,fi = 1)."""
    ky, kE = k_y_theta(T), k_E_theta(T)
    if ky <= 0.0 or kE <= 0.0:
        return 0.0
    lam = (l_cr / i) / (math.pi * math.sqrt(210000.0 / f_y))
    lam_t = lam * math.sqrt(ky / kE)
    a = 0.65 * math.sqrt(235.0 / f_y)
    phi = 0.5 * (1.0 + a * lam_t + lam_t ** 2)
    chi = 1.0 / (phi + math.sqrt(phi ** 2 - lam_t ** 2))
    return chi * A * ky * f_y / 1e3


def _c_a(T: float) -> float:
    """Calor específico do aço (EN 1993-1-2 §3.4.1.2), J/(kg·K)."""
    if T < 600:
        return 425 + 0.773 * T - 1.69e-3 * T ** 2 + 2.22e-6 * T ** 3
    if T < 735:
        return 666 + 13002 / (738 - T)
    if T < 900:
        return 545 + 17820 / (T - 731)
    return 650.0


def temperatura_aco_sem_protecao(t_min: float, A_m_V: float, dt_s: float = 5.0) -> float:
    """Aço sem proteção sob a curva-padrão (EN 1993-1-2 Eq. 4.25)."""
    Ta, n = 20.0, int(round(t_min * 60.0 / dt_s))
    for i in range(1, n + 1):
        Tg = 20.0 + 345.0 * math.log10(8.0 * i * dt_s / 60.0 + 1.0)
        h = 25.0 * (Tg - Ta) + 0.7 * 5.67e-8 * ((Tg + 273) ** 4 - (Ta + 273) ** 4)
        Ta += A_m_V / (_c_a(Ta) * 7850.0) * h * dt_s
    return Ta


def temperatura_critica(mu0: float) -> float:
    """EN 1993-1-2 Eq. (4.22), μ0 ≥ 0,013."""
    mu0 = max(mu0, 0.013)
    return 39.19 * math.log(1.0 / (0.9674 * mu0 ** 3.833) - 1.0) + 482.0


def verificar_pilarete_fogo(*, N_fi_kN: float, D_mm: float, t_mm: float, t_exp_min: float,
                            h_m: float = 0.30, aco: str = "S355") -> dict:
    """Tubo do pilarete sob a chama: sem proteção e com a intumescente adotada."""
    d = D_mm - 2 * t_mm
    A = math.pi / 4.0 * (D_mm ** 2 - d ** 2)
    i = math.sqrt((D_mm ** 2 + d ** 2) / 16.0)
    f_y = ACO_CHAPA[aco]["f_y"]
    N_pl = A * f_y / 1e3
    kw = dict(A=A, i=i, l_cr=2.0 * h_m * 1e3, f_y=f_y)
    AV = 1.0 / (t_mm / 1e3)
    mu0 = N_fi_kN / N_pl
    # temperatura crítica com flambagem: N_b,fi,Rd(θ) = N_fi (bissecção)
    lo, hi = 20.0, 1200.0
    for _ in range(60):
        m = 0.5 * (lo + hi)
        lo, hi = (m, hi) if N_b_fi_Rd(m, **kw) >= N_fi_kN else (lo, m)
    th_cr = lo
    th_1 = temperatura_aco_sem_protecao(DURACAO_INTENSA_MIN, AV)
    th_n = temperatura_aco_sem_protecao(t_exp_min, AV)
    eta = lambda T: N_fi_kN / max(N_b_fi_Rd(T, **kw), 1e-6)
    eta_p = eta(THETA_CR_PROJETO_C)
    return {"N_fi_kN": round(N_fi_kN, 1), "N_pl_kN": round(N_pl, 0), "A_m_V_m": round(AV, 0),
            "mu0": round(mu0, 4), "theta_cr_C": round(th_cr, 0),
            "theta_cr_eq422_C": round(temperatura_critica(mu0), 0),
            "theta_1_veiculo_C": round(th_1, 0), "eta_sem_protecao_1": round(eta(th_1), 4),
            "theta_n_veiculos_C": round(th_n, 0), "eta_sem_protecao_n": round(eta(th_n), 4),
            "R_intumescente_min": R_INTUMESCENTE_MIN, "theta_cr_projeto_C": THETA_CR_PROJETO_C,
            "eta": round(eta_p, 4), "ok": eta_p <= 1.0 and R_INTUMESCENTE_MIN >= t_exp_min}


def diametro_equivalente(A_m2: float) -> float:
    return math.sqrt(4.0 * A_m2 / math.pi)


def chama_localizada(Q_W: float, D_m: float) -> dict:
    """Comprimento da chama e origem virtual (EN 1991-1-2 C.1 e C.3)."""
    q25 = Q_W ** 0.4
    return {"L_f_m": -1.02 * D_m + 0.0148 * q25, "z0_m": -1.02 * D_m + 0.00524 * q25}


def temperatura_pluma(Q_W: float, D_m: float, z_m: float) -> float:
    """Temperatura no eixo da pluma à altura z acima da fonte (EN 1991-1-2 C.2)."""
    z0 = chama_localizada(Q_W, D_m)["z0_m"]
    Qc = 0.8 * Q_W
    return min(900.0, 20.0 + 0.25 * Qc ** (2.0 / 3.0) * (z_m - z0) ** (-5.0 / 3.0))


def tempo_colapso_pilar(*, b: float, h: float, H_col_m: float, N_fi_kN: float, mat,
                        faces_b: int, faces_h: int, t_max: float = 240.0) -> float:
    """Maior tempo (min, passo 1) com η ≤ 1 sob exposição-padrão nas faces dadas."""
    t = 1.0
    while t <= t_max:
        r = verificar_fogo_pilar(b=b, h=h, H_col_m=H_col_m, N_fi_kN=N_fi_kN, mat=mat,
                                 R_req_min=t, faces_b=faces_b, faces_h=faces_h)
        if not r["ok"]:
            return t - 1.0
        t += 1.0
    return t_max


def avaliar_incendio_veiculo(*, mat, pilares: tuple[dict, ...], h_forro_m: float,
                             n_veiculos: int = 3, pilarete: tuple | None = None
                             ) -> dict:
    """
    Pluma sob a viga e tempo até o colapso dos pilares adjacentes às vagas.
    `pilares`: dicts com b, h, H_col_m, N_fi_kN, nome.
    """
    D = diametro_equivalente(A_CARRO_M2)
    ch = chama_localizada(Q_CARRO_W, D)
    H = h_forro_m - Z_FONTE_M
    alcanca = ch["L_f_m"] >= H
    theta = 900.0 if alcanca else temperatura_pluma(Q_CARRO_W, D, H)
    # exposição exigida: veículos sucessivos junto ao mesmo pilar
    t_exp = DURACAO_INTENSA_MIN + (n_veiculos - 1) * ATRASO_PROPAGACAO_MIN
    res = []
    for p in pilares:
        casos = {}
        for rot, fb, fh in (("2 faces", 1, 1), ("3 faces", 2, 1), ("4 faces", 2, 2)):
            casos[rot] = tempo_colapso_pilar(b=p["b"], h=p["h"], H_col_m=p["H_col_m"],
                                             N_fi_kN=p["N_fi_kN"], mat=mat,
                                             faces_b=fb, faces_h=fh)
        t_min = min(casos.values())
        item = {"nome": p["nome"], "N_fi_kN": round(p["N_fi_kN"], 1),
                "t_colapso_min": casos, "eta": round(t_exp / t_min, 4)}
        if pilarete:
            item["pilarete"] = verificar_pilarete_fogo(
                N_fi_kN=p["N_fi_kN"], D_mm=pilarete[0], t_mm=pilarete[1], t_exp_min=t_exp,
                h_m=pilarete[2] if len(pilarete) > 2 else 0.30)
            item["eta"] = max(item["eta"], item["pilarete"]["eta"])
        res.append(item)
    eta = max(r["eta"] for r in res)
    return {
        "Q_MW": Q_CARRO_W / 1e6, "D_m": round(D, 2), "L_f_m": round(ch["L_f_m"], 2),
        "H_forro_m": round(H, 2), "chama_alcanca_forro": alcanca,
        "theta_pluma_forro_C": round(theta, 0),
        "n_veiculos": n_veiculos, "t_exposicao_min": t_exp,
        "pilares": res, "eta": eta, "ok": eta <= 1.0,
        "norma": "EN 1991-1-2 An. C + EN 1995-1-2 §4.2.2 (avaliação de robustez)",
    }
