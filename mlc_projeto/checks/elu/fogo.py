"""
checks/elu/fogo.py — Resistência ao fogo da MLC (EN 1995-1-2), seção reduzida.

Achado A5 da auditoria de conformidade ao Eurocódigo
----------------------------------------------------
O fogo estava **ausente e não declarado**: nem verificação, nem declaração de
escopo. Num estacionamento coberto isso não é uma omissão conservadora — é uma
lacuna. Este módulo fecha-a pelo lado da verificação.

O que o Eurocódigo fixa e o que NÃO fixa
---------------------------------------
A EN 1995-1-2 dá o MÉTODO (taxa de carbonização, seção reduzida, propriedades
em situação de incêndio). **Não fixa o tempo requerido de resistência** `R`:
esse é dado do regulamento nacional de segurança contra incêndio (no Brasil,
ABNT NBR 14432 / Instruções Técnicas do corpo de bombeiros estadual), não do
Eurocódigo. Por isso `R_req_min` entra aqui como PARÂMETRO DECLARADO, registado
em `core/normativo.py` com origem `"PROJETO"` — e o memorial verifica a
estrutura para o valor declarado e publica a margem também no patamar acima.

Método — seção reduzida (EN 1995-1-2 §4.2.2)
--------------------------------------------
    d_char,n = β_n · t                          §3.4.2 Eq. (3.2)
    d_ef     = d_char,n + k_0 · d_0             §4.2.2 Eq. (4.1)
    k_0      = t/20 para t < 20 min, 1,0 para t ≥ 20 min   Tab. 4.1
    d_0      = 7 mm                             §4.2.2(2)

    β_n = 0,70 mm/min — MLC de coníferas com ρ_k ≥ 290 kg/m³ (Tab. 3.1).
    A taxa NOCIONAL (β_n) e não a unidimensional (β_0 = 0,65) porque a seção
    reduzida embute o arredondamento das arestas.

Propriedades em situação de incêndio (EN 1995-1-2 §2.3)
------------------------------------------------------
    f_d,fi = k_mod,fi · k_fi · f_k / γ_M,fi
    S_d,fi = k_fi · S_05 / γ_M,fi     (rigidez, para verificações de estabilidade)

    γ_M,fi  = 1,00   §2.3(1)
    k_fi    = 1,15   Tab. 2.1 — MLC
    k_mod,fi= 1,00   §4.2.2(5) — no método da seção reduzida o efeito da
                     temperatura já está na perda de seção; NÃO se acumula com
                     a redução de k_mod do método da seção efetiva (§4.2.3).

Ações — combinação acidental (EN 1990 Eq. 6.11b)
------------------------------------------------
    E_fi,d = Σ G_k + ψ_1,1·Q_k,1 + Σ ψ_2,i·Q_k,i

Neste projeto, categoria H: ψ_1,Q = 0 e, para o vento, ψ_2,W = 0 (EN 1990
Tab. A1.1) — logo `E_fi,d` reduz-se ao PERMANENTE, sem coeficiente parcial. Os
ψ NÃO estão escritos aqui: são lidos de `core/normativo.py`, de modo que
reclassificar a edificação propaga automaticamente para o incêndio.

O vento de sucção é omitido (ψ_2,W = 0). Em situação de incêndio isso é
conservador para os esforços de gravidade — que são os que governam a seção
reduzida — e a norma não pede a concomitância inversa.

Referência: EN 1995-1-2:2004 §2.3, §3.4.2, §4.2.2, Tab. 2.1, Tab. 3.1, Tab. 4.1
            EN 1990:2002 §6.4.3.3 Eq. (6.11b)
"""

from __future__ import annotations

import math

import numpy as np

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.loads     import Carregamentos, analisar_biarticulada
from mlc_projeto.core.normativo import NDP_SOURCE
from mlc_projeto.core.validacao import exigir_positivo
from mlc_projeto.checks.elu.flambagem_lateral import (
    calcular_l_ef,
    calcular_sigma_m_crit,
    calcular_lambda_rel_m,
    calcular_k_crit,
)

# ── Constantes normativas EN 1995-1-2 ────────────────────────────────────────

#: β_n — taxa de carbonização NOCIONAL, MLC de coníferas ρ_k ≥ 290 kg/m³
#: (EN 1995-1-2:2004 Tab. 3.1, linha "glued laminated timber, softwood").
BETA_N_MLC_CONIFERA = 0.70e-3      # m/min

#: d_0 — espessura da camada de resistência nula (§4.2.2(2)).
D_0 = 7.0e-3                        # m

#: k_fi — MLC (Tab. 2.1). Converte o 5 % fractil no 20 % fractil.
K_FI_MLC = 1.15

#: γ_M,fi — §2.3(1). É 1,00: a situação de incêndio é acidental.
GAMMA_M_FI = 1.00

#: k_mod,fi no método da SEÇÃO REDUZIDA (§4.2.2(5)).
K_MOD_FI = 1.00

#: ρ_k mínimo para que β_n = 0,70 seja aplicável (Tab. 3.1).
RHO_K_MIN_BETA_N = 290.0            # kg/m³

#: EC5 §6.3.2(1) — MLC. Mesmo β_c da situação normal: a EN 1995-1-2 não o altera.
BETA_C = 0.10


def k_0(t_min: float) -> float:
    """
    k_0 do termo de resistência nula — EN 1995-1-2 §4.2.2 Tab. 4.1.

    Superfície não protegida: k_0 = t/20 para t < 20 min; 1,0 para t ≥ 20 min.
    """
    t = float(t_min)
    if t < 0.0:
        raise ValueError(f"t_min = {t} min: o tempo de exposição não é negativo.")
    return min(t / 20.0, 1.0)


def d_char_n(t_min: float, beta_n: float = BETA_N_MLC_CONIFERA) -> float:
    """
    Profundidade de carbonização nocional — EN 1995-1-2 §3.4.2 Eq. (3.2).

        d_char,n = β_n · t

    Args:
        t_min  : tempo de exposição (min)
        beta_n : taxa nocional (m/min)

    Returns:
        d_char,n (m)
    """
    return float(beta_n) * float(t_min)


def d_ef(t_min: float, beta_n: float = BETA_N_MLC_CONIFERA, d0: float = D_0) -> float:
    """
    Profundidade efetiva de carbonização — EN 1995-1-2 §4.2.2 Eq. (4.1).

        d_ef = d_char,n + k_0 · d_0

    Returns:
        d_ef (m)
    """
    return d_char_n(t_min, beta_n) + k_0(t_min) * float(d0)


def secao_reduzida(
    b: float,
    h: float,
    d_ef_m: float,
    *,
    faces_b: int = 2,
    faces_h: int = 2,
) -> tuple[float, float]:
    """
    Seção residual após `d_ef` — EN 1995-1-2 §4.2.2.

    Args:
        b, h    : dimensões iniciais (m)
        d_ef_m  : profundidade efetiva (m)
        faces_b : faces expostas na direção da LARGURA (0, 1 ou 2)
        faces_h : faces expostas na direção da ALTURA (0, 1 ou 2)

    Returns:
        (b_fi, h_fi) em m. Zero (não negativo) quando a seção é consumida — a
        verificação a jusante trata isso como η indeterminado, não como η = 0.
    """
    b_fi = float(b) - faces_b * float(d_ef_m)
    h_fi = float(h) - faces_h * float(d_ef_m)
    return max(b_fi, 0.0), max(h_fi, 0.0)


def resistencias_fogo(mat: GlulamMaterial) -> dict:
    """
    Propriedades de cálculo em situação de incêndio — EN 1995-1-2 §2.3.

        f_d,fi = k_mod,fi · k_fi · f_k / γ_M,fi
        E_0,05,fi = k_fi · E_0,05 / γ_M,fi

    Note que f_d,fi > f_d da situação normal: γ_M cai de 1,25 para 1,00, k_mod
    de 0,50–0,70 para 1,00 e k_fi eleva o fractil de 5 % para 20 %. É o método;
    a segurança vem da seção perdida e da combinação acidental.
    """
    if mat.rho_k < RHO_K_MIN_BETA_N:
        raise ValueError(
            f"ρ_k = {mat.rho_k} kg/m³ < {RHO_K_MIN_BETA_N:.0f}: a taxa "
            f"β_n = 0,70 mm/min da EN 1995-1-2 Tab. 3.1 não cobre esta MLC."
        )
    fator = K_MOD_FI * K_FI_MLC / GAMMA_M_FI
    return {
        "f_m_d_fi":   mat.f_m_k * fator,
        "f_v_d_fi":   mat.f_v_k * fator,
        "f_c0_d_fi":  mat.f_c0_k * fator,
        "f_c90_d_fi": mat.f_c90_k * fator,
        "E_005_fi":   mat.E0_05 * K_FI_MLC / GAMMA_M_FI,
        "k_fi":       K_FI_MLC,
        "k_mod_fi":   K_MOD_FI,
        "gamma_M_fi": GAMMA_M_FI,
    }


def carga_acidental_incendio(load: Carregamentos) -> dict:
    """
    Carga linear da combinação acidental de incêndio — EN 1990 Eq. (6.11b).

        q_fi = g_k + ψ_1,1·q_k   (o vento entra com ψ_2,W, aqui nulo)

    Os ψ vêm de `NDP_SOURCE`: se a classificação da edificação mudar, o incêndio
    acompanha sem edição deste módulo.
    """
    psi_1_Q = float(NDP_SOURCE["psi_1_Q"].valor)
    psi_2_W = float(NDP_SOURCE["psi_2_W"].valor)
    q_fi = load.g_k + psi_1_Q * load.q_k
    return {
        "q_fi_kNm": q_fi,
        "g_k_kNm":  load.g_k,
        "q_k_kNm":  load.q_k,
        "psi_1_Q":  psi_1_Q,
        "psi_2_W":  psi_2_W,
        "norma":    "EN 1990 §6.4.3.3 Eq. (6.11b)",
    }


def reacao_vertical_incendio(geo: GeometriaViga, load: Carregamentos) -> float:
    """
    Reação vertical por apoio na combinação acidental de incêndio (kN).

    É o esforço normal que desce ao pilar lateral; o central recebe 2×. Sai da
    MESMA análise da viga, não de uma fração arbitrada de `R_v` da situação
    normal — a razão E_fi/E_d não é constante entre combinações.
    """
    q_fi = carga_acidental_incendio(load)["q_fi_kNm"]
    r = analisar_biarticulada(
        q=q_fi, L=geo.L, h0=geo.h0, h_ap=geo.h_ap,
        alpha_rad=geo.alpha_rad, b=geo.b,
        q_esq=q_fi, q_dir=q_fi,
        desenvolve_empuxo=load.empuxo_desenvolve,
        a_bal=geo.a_bal,
    )
    return abs(float(r["R_v_gov_kN"]))


def _k_c(lambda_rel: float) -> float:
    """k_c — EC5 §6.3.2 Eq. (6.25)/(6.27). Inalterado em incêndio."""
    k = 0.5 * (1.0 + BETA_C * (lambda_rel - 0.3) + lambda_rel ** 2)
    raiz = k ** 2 - lambda_rel ** 2
    return min(1.0 / (k + math.sqrt(max(raiz, 0.0))), 1.0)


def verificar_fogo_viga(
    geo:  GeometriaViga,
    mat:  GlulamMaterial,
    load: Carregamentos,
    R_req_min: float,
    s: float = 1.00,
    *,
    faces_b: int = 2,
    faces_h: int = 2,
    posicao_carga: str = "borda_comprimida",
) -> dict:
    """
    Viga MLC em situação de incêndio — flexão, flambagem lateral e corte.

    Varre TODAS as seções do vão com a seção residual: em peça de altura
    variável a perda de `d_ef` pesa muito mais junto ao apoio (h₀ = 1,39 m
    perde 4 % da altura; a largura b = 0,32 m perde 17,5 % aos 30 min), e é a
    LARGURA que governa a flambagem lateral, com b³ em σ_m,crit.

    Args:
        geo, mat, load : modelo de projeto
        R_req_min      : tempo requerido de resistência ao fogo (min) — dado do
                         regulamento nacional, NÃO do Eurocódigo
        s              : espaçamento entre terças (m) — l₁ da Tab. 6.1
        faces_b/faces_h: faces expostas (4 lados = 2/2)

    Returns:
        dict com seção residual, tensões, η por modo e η governante.
    """
    exigir_positivo("R_req_min", R_req_min, unidade="min")
    d = d_ef(R_req_min)
    b_fi, _ = secao_reduzida(geo.b, geo.h0, d, faces_b=faces_b, faces_h=faces_h)

    res_f = resistencias_fogo(mat)
    carga = carga_acidental_incendio(load)
    q_fi  = carga["q_fi_kNm"]

    if b_fi <= 0.0:
        return {
            "eta": float("nan"), "ok": False,
            "R_req_min": R_req_min, "d_ef_mm": d * 1e3,
            "b_fi_m": 0.0,
            "motivo": (
                f"A largura residual é nula para R{R_req_min:.0f}: "
                f"b = {geo.b*1e3:.0f} mm perde 2·{d*1e3:.1f} mm."
            ),
            "norma": "EN 1995-1-2 §4.2.2",
            **carga, **res_f,
        }

    r = analisar_biarticulada(
        q=q_fi, L=geo.L, h0=geo.h0, h_ap=geo.h_ap,
        alpha_rad=geo.alpha_rad, b=geo.b,
        q_esq=q_fi, q_dir=q_fi,
        desenvolve_empuxo=load.empuxo_desenvolve,
        a_bal=geo.a_bal,
    )

    x    = geo.x
    M_x  = np.interp(x, r["x"], r["M_x"]) * 1e3          # N·m
    h_x  = np.asarray(geo.h(x), dtype=float)
    h_fi = np.maximum(h_x - faces_h * d, 0.0)

    ok_secao = h_fi > 0.0
    if not np.any(ok_secao):
        return {
            "eta": float("nan"), "ok": False,
            "R_req_min": R_req_min, "d_ef_mm": d * 1e3,
            "motivo": "Altura residual nula em todo o vão.",
            "norma": "EN 1995-1-2 §4.2.2", **carga, **res_f,
        }

    W_fi = np.where(ok_secao, b_fi * h_fi ** 2 / 6.0, np.inf)
    sigma_m = np.abs(M_x) / W_fi                          # Pa

    # ── Flambagem lateral com a seção residual (EC5 §6.3.3 + §2.3 da 1-2) ────
    # σ_m,crit ∝ b², e b é a dimensão que a carbonização mais castiga em termos
    # relativos. O E_0,05 usado é o de incêndio (20 % fractil, §2.3(2)).
    k_crit = np.ones_like(h_fi)
    lambda_rel = np.zeros_like(h_fi)
    for i, hi in enumerate(h_fi):
        if not ok_secao[i]:
            continue
        l_ef = calcular_l_ef(
            l_1=s, restricao="continua_topo", tipo_carga="distribuida",
            posicao_carga=posicao_carga, h_m=float(hi),
        )
        s_crit = calcular_sigma_m_crit(
            E_005=res_f["E_005_fi"], b=b_fi, h=float(hi), l_ef=l_ef,
        )
        # f_m,k em incêndio = k_fi·f_m,k (mesmo fractil que σ_m,crit — §2.3(2))
        lam = calcular_lambda_rel_m(mat.f_m_k * K_FI_MLC, s_crit)
        lambda_rel[i] = lam
        k_crit[i] = calcular_k_crit(lam)

    eta_m   = sigma_m / res_f["f_m_d_fi"]
    eta_ltb = sigma_m / (k_crit * res_f["f_m_d_fi"])

    i_m   = int(np.argmax(np.where(ok_secao, eta_m, -np.inf)))
    i_ltb = int(np.argmax(np.where(ok_secao, eta_ltb, -np.inf)))

    # ── Corte no apoio (EC5 §6.1.7 com b_ef = k_cr·b_fi) ─────────────────────
    V_fi_N = abs(float(r["V_apoio_kN"])) * 1e3
    h_ap_fi = float(h_fi[0])
    tau = 1.5 * V_fi_N / (mat.k_cr * b_fi * h_ap_fi) if h_ap_fi > 0 else float("inf")
    eta_v = tau / res_f["f_v_d_fi"]

    modos = {
        "flexao":            float(eta_m[i_m]),
        "flambagem_lateral": float(eta_ltb[i_ltb]),
        "cisalhamento":      float(eta_v),
    }
    modo_gov = max(modos, key=modos.get)
    eta = modos[modo_gov]

    return {
        "R_req_min":       float(R_req_min),
        "d_char_n_mm":     round(d_char_n(R_req_min) * 1e3, 2),
        "k_0":             round(k_0(R_req_min), 4),
        "d_ef_mm":         round(d * 1e3, 2),
        "faces_expostas":  faces_b + faces_h,
        "b_inicial_mm":    round(geo.b * 1e3, 1),
        "b_fi_mm":         round(b_fi * 1e3, 1),
        "perda_b_pct":     round(100.0 * (1.0 - b_fi / geo.b), 2),
        "h0_fi_mm":        round(h_ap_fi * 1e3, 1),
        "q_fi_kNm":        round(q_fi, 4),
        "M_max_fi_kNm":    round(float(np.max(np.abs(M_x))) / 1e3, 3),
        "V_apoio_fi_kN":   round(V_fi_N / 1e3, 3),
        "sigma_m_MPa":     round(float(sigma_m[i_ltb]) / 1e6, 4),
        "f_m_d_fi_MPa":    round(res_f["f_m_d_fi"] / 1e6, 4),
        "f_v_d_fi_MPa":    round(res_f["f_v_d_fi"] / 1e6, 4),
        "tau_MPa":         round(tau / 1e6, 4),
        "x_gov_m":         round(float(x[i_ltb]), 3),
        "lambda_rel_m":    round(float(lambda_rel[i_ltb]), 4),
        "k_crit":          round(float(k_crit[i_ltb]), 4),
        "eta_flexao":      round(modos["flexao"], 4),
        "eta_ltb":         round(modos["flambagem_lateral"], 4),
        "eta_cisalhamento": round(modos["cisalhamento"], 4),
        "modo_gov":        modo_gov,
        "eta":             round(eta, 4),
        "ok":              eta <= 1.0,
        "k_fi":            K_FI_MLC,
        "beta_n_mm_min":   BETA_N_MLC_CONIFERA * 1e3,
        "psi_1_Q":         carga["psi_1_Q"],
        "psi_2_W":         carga["psi_2_W"],
        "norma": ("EN 1995-1-2 §3.4.2+§4.2.2+§2.3 | EC5 §6.1.7+§6.3.3 | "
                  "EN 1990 Eq. (6.11b)"),
    }


def verificar_fogo_pilar(
    b: float,
    h: float,
    H_col_m: float,
    N_fi_kN: float,
    mat: GlulamMaterial,
    R_req_min: float,
    *,
    faces_b: int = 2,
    faces_h: int = 2,
    beta_l: float = 1.0,
    nome: str = "pilar",
) -> dict:
    """
    Pilar MLC em situação de incêndio — compressão com flambagem (EC5 §6.3.2)
    sobre a seção residual da EN 1995-1-2 §4.2.2.

    Args:
        b, h      : seção inicial (m)
        H_col_m   : altura do pilar (m)
        N_fi_kN   : esforço normal da combinação acidental (kN, compressão > 0)
        beta_l    : coeficiente de comprimento de flambagem (1,0 = biarticulado)

    Returns:
        dict com seção residual, λ_rel, k_c, η e ok.
    """
    exigir_positivo("R_req_min", R_req_min, unidade="min")
    d = d_ef(R_req_min)
    b_fi, h_fi = secao_reduzida(b, h, d, faces_b=faces_b, faces_h=faces_h)
    res_f = resistencias_fogo(mat)

    if b_fi <= 0.0 or h_fi <= 0.0:
        return {
            "nome": nome, "eta": float("nan"), "ok": False,
            "R_req_min": float(R_req_min), "d_ef_mm": round(d * 1e3, 2),
            "b_fi_mm": round(b_fi * 1e3, 1), "h_fi_mm": round(h_fi * 1e3, 1),
            "motivo": "Seção residual nula.",
            "norma": "EN 1995-1-2 §4.2.2",
        }

    A_fi = b_fi * h_fi
    sigma_c = abs(float(N_fi_kN)) * 1e3 / A_fi

    l_ef = beta_l * float(H_col_m)
    pior = None
    for lado, dim in (("z", b_fi), ("y", h_fi)):
        i = dim / math.sqrt(12.0)
        lam = l_ef / i
        lam_rel = (lam / math.pi) * math.sqrt(mat.f_c0_k * K_FI_MLC
                                              / res_f["E_005_fi"])
        kc = _k_c(lam_rel)
        eta = sigma_c / (kc * res_f["f_c0_d_fi"])
        if pior is None or eta > pior["eta"]:
            pior = dict(eixo=lado, lam=lam, lam_rel=lam_rel, kc=kc, eta=eta)

    return {
        "nome":          nome,
        "R_req_min":     float(R_req_min),
        "d_ef_mm":       round(d * 1e3, 2),
        "b_mm":          round(b * 1e3, 1),
        "h_mm":          round(h * 1e3, 1),
        "b_fi_mm":       round(b_fi * 1e3, 1),
        "h_fi_mm":       round(h_fi * 1e3, 1),
        "perda_A_pct":   round(100.0 * (1.0 - A_fi / (b * h)), 2),
        "N_fi_kN":       round(float(N_fi_kN), 3),
        "sigma_c_MPa":   round(sigma_c / 1e6, 4),
        "f_c0_d_fi_MPa": round(res_f["f_c0_d_fi"] / 1e6, 4),
        "eixo_gov":      pior["eixo"],
        "lambda":        round(pior["lam"], 2),
        "lambda_rel_c":  round(pior["lam_rel"], 4),
        "k_c":           round(pior["kc"], 4),
        "eta":           round(pior["eta"], 4),
        "ok":            pior["eta"] <= 1.0,
        "norma":         "EN 1995-1-2 §4.2.2+§2.3 | EC5 §6.3.2",
    }


def verificar_fogo(
    geo:  GeometriaViga,
    mat:  GlulamMaterial,
    load: Carregamentos,
    R_req_min: float,
    s: float = 1.00,
    *,
    pilares: tuple[dict, ...] = (),
    R_comparacao: tuple[float, ...] = (30.0, 60.0),
) -> dict:
    """
    Verificação consolidada de resistência ao fogo — viga + pilares.

    `R_req_min` é o tempo REQUERIDO, dado do regulamento nacional de segurança
    contra incêndio e declarado em `NDP_SOURCE["R_fogo_req_min"]` com origem
    `"PROJETO"`. `R_comparacao` produz, além da verificação, a margem nos
    patamares usuais — o memorial publica até onde a seção aguenta, não só se
    passa no valor adotado.

    Args:
        pilares : tuplos de kwargs para `verificar_fogo_pilar` (sem R_req_min).

    Returns:
        dict com η governante do conjunto e o detalhe por elemento.
    """
    viga = verificar_fogo_viga(geo, mat, load, R_req_min, s)
    res_pilares = [
        verificar_fogo_pilar(mat=mat, R_req_min=R_req_min, **p) for p in pilares
    ]

    etas = {"viga": viga["eta"]}
    for p in res_pilares:
        etas[p["nome"]] = p["eta"]

    finitos = {k: v for k, v in etas.items() if isinstance(v, float)
               and math.isfinite(v)}
    if len(finitos) != len(etas):
        eta_gov, elem_gov = float("nan"), "indeterminado"
        ok = False
    else:
        elem_gov = max(finitos, key=finitos.get)
        eta_gov = finitos[elem_gov]
        ok = eta_gov <= 1.0

    # Margem: até que R a estrutura ainda passa (varredura sobre R_comparacao)
    margem = {}
    for R in R_comparacao:
        v = verificar_fogo_viga(geo, mat, load, R, s)
        ps = [verificar_fogo_pilar(mat=mat, R_req_min=R, **p) for p in pilares]
        cand = [v["eta"], *[q["eta"] for q in ps]]
        finit = [c for c in cand if isinstance(c, float) and math.isfinite(c)]
        margem[f"R{int(R)}"] = (round(max(finit), 4)
                                if len(finit) == len(cand) else None)

    return {
        "R_req_min":  float(R_req_min),
        "viga":       viga,
        "pilares":    res_pilares,
        "eta_por_elemento": {k: (round(v, 4) if math.isfinite(v) else None)
                             for k, v in etas.items()},
        "elemento_gov": elem_gov,
        "margem_por_R": margem,
        "eta":        eta_gov,
        "ok":         ok,
        "norma":      "EN 1995-1-2:2004 §4.2.2 (seção reduzida) + EN 1990 Eq. (6.11b)",
        "nota_R": (
            "O tempo requerido R NÃO é fixado pelo Eurocódigo: vem do "
            "regulamento nacional de segurança contra incêndio (ABNT NBR 14432 "
            "/ IT do CBM estadual). O valor aqui verificado é uma DECLARAÇÃO de "
            "projeto, registada em NDP_SOURCE com origem 'PROJETO'."
        ),
    }
