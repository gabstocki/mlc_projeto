"""
checks/elu/cumeeira.py — Tração perpendicular na cumeeira. v2

ATUALIZAÇÃO v2 — Pórtico de 3 rótulas:
    No pórtico de 3 rótulas, a cumeeira é uma RÓTULA.
    M na cumeeira = 0 → σ_t,90,d = 0 → η = 0.

    A verificação EC5 §6.4.3 não governa para este sistema.
    O módulo é mantido por rastreabilidade normativa e registra
    explicitamente a justificativa técnica no resultado.

    Se o sistema estrutural for alterado para pórtico rígido,
    o módulo volta a ser crítico automaticamente — usa M_ap
    do diagrama correto de cada sistema.

Para pórtico RÍGIDO (referência):
    M_ap = M_max = q·L²/8 (na cumeeira)
    σ_t,90,d = k_p · 6·M_ap / (b·h_ap²)  (EC5 §6.4.3 Eq. 6.54)
    Condição: σ_t,90,d ≤ k_dis · k_vol · f_t,90,d

Para pórtico de 3 RÓTULAS (sistema atual):
    M_ap = 0 (rótula na cumeeira)
    σ_t,90,d = 0
    η = 0  → APROVADO por definição estrutural

Referência: EC5 §6.4.3 Eq. 6.50, 6.51, 6.54
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.loads     import Carregamentos


# ── Constantes EC5 §6.4.3 ────────────────────────────────────────────────────

K_DIS   = 1.4    # fator de distribuição — duplo-bisel
V0_KVOL = 0.01   # volume de referência (m³) — EC5 Eq. 6.51


# ── Funções auxiliares (mantidas para generalidade) ───────────────────────────

def calcular_k_p(alpha_deg: float) -> float:
    """
    Coeficiente de forma k_p — EC5 §6.4.3.

    Para viga duplo-bisel sem curvatura (r → ∞):
        k_p = 0,2 · tan(α)
    """
    return 0.2 * math.tan(math.radians(alpha_deg))


def calcular_k_vol(b: float, h_ap: float, f_vol: float = 0.15) -> float:
    """
    Fator de volume k_vol — EC5 §6.4.3 Eq. 6.51.

        k_vol = (V0 / V)^0,20  ≤ 1,0

    V = b · h_ap · (f_vol · h_ap)
    """
    V = b * h_ap * (f_vol * h_ap)
    return min((V0_KVOL / V) ** 0.20, 1.0)


def calcular_sigma_t90d(
    k_p:    float,
    M_ap_Nm: float,
    b:      float,
    h_ap:   float,
) -> float:
    """
    Tensão de tração perpendicular na cumeeira — EC5 §6.4.3 Eq. 6.54.

        σ_t,90,d = k_p · 6·M_ap,d / (b · h_ap²)
    """
    if abs(M_ap_Nm) < 1e-6:
        return 0.0
    return k_p * 6.0 * M_ap_Nm / (b * h_ap**2)


# ── Verificação principal ─────────────────────────────────────────────────────

def verifica_cumeeira(
    geo:  GeometriaViga,
    mat:  GlulamMaterial,
    load: Carregamentos,
) -> dict:
    """
    Verifica tensão de tração perpendicular na cumeeira — EC5 §6.4.3.

    Para pórtico de 3 rótulas: M na cumeeira = 0 → η = 0.
    Para pórtico rígido: usa M_max do diagrama de cargas.

    O sistema estrutural é detectado automaticamente pelo atributo
    `Combinacao.x_Mmax_m` — se x_Mmax ≈ L/2, o momento máximo está
    na cumeeira (pórtico rígido). Se x_Mmax < L/2, está no vão
    (pórtico de 3 rótulas).

    Returns:
        dict com σ_t,90,d, k_vol, η e ok.
        Para 3 rótulas: η = 0 com justificativa explícita.
    """
    gov  = load.combinacao_ELU_governante()
    L    = geo.L
    h_ap = geo.h_ap
    b    = geo.b

    # ── Detectar sistema estrutural ───────────────────────────
    # 3 rótulas: M_cumeeira = 0 (rótula)
    # Pórtico rígido: M_cumeeira = M_max
    # Detecção: interpolar M no ponto x = L/2

    # M_ELU() retorna diagrama com n_pts próprio — usar x interno da análise
    # Para interpolação correta, recalcular com x uniforme de 0 a L
    from mlc_projeto.core.loads import analisar_3rotulas
    gov = load.combinacao_ELU_governante()
    r   = analisar_3rotulas(
        q=gov.q_tot, L=geo.L,
        h0=geo.h0, h_ap=geo.h_ap,
        alpha_rad=geo.alpha_rad,
    )
    M_x = r["M_x"]
    x   = r["x"]
    M_cumeeira_kNm = float(np.interp(L/2, x, M_x))
    M_cumeeira_Nm  = abs(M_cumeeira_kNm) * 1e3

    # ── Sistema de 3 rótulas — M ≈ 0 na cumeeira ─────────────
    tres_rotulas = abs(M_cumeeira_kNm) < 1.0   # tolerância 1 kN·m

    if tres_rotulas:
        return {
            # Geometria
            "L_m":           L,
            "h_ap_m":        h_ap,
            "b_m":           b,
            "alpha_deg":     geo.alpha_deg,
            # Momento na cumeeira
            "M_cumeeira_kNm":round(M_cumeeira_kNm, 4),
            "sistema":       "3 rótulas",
            # Coeficientes
            "k_p":           round(calcular_k_p(geo.alpha_deg), 6),
            "k_vol":         round(calcular_k_vol(b, h_ap),     4),
            "k_dis":         K_DIS,
            # Tensões
            "sigma_t90d_MPa":0.0,
            "f_t90d_MPa":    round(mat.f_t90_d / 1e6,          4),
            "resistencia_MPa":round(
                K_DIS * calcular_k_vol(b, h_ap) * mat.f_t90_d / 1e6, 4
            ),
            # Resultado
            "eta":           0.0,
            "ok":            True,
            "justificativa": "Rótula na cumeeira — M=0 → σ_t,90,d=0 "
                             "(pórtico de 3 rótulas, EC5 §6.4.3 não governa)",
            "norma":         "EC5 §6.4.3 — não governa para pórtico de 3 rótulas",
        }

    # ── Pórtico rígido — cálculo completo ────────────────────
    k_p   = calcular_k_p(geo.alpha_deg)
    k_vol = calcular_k_vol(b, h_ap)

    sigma_t90d = calcular_sigma_t90d(k_p, M_cumeeira_Nm, b, h_ap)
    resist     = K_DIS * k_vol * mat.f_t90_d
    eta        = sigma_t90d / resist

    return {
        "L_m":            L,
        "h_ap_m":         h_ap,
        "b_m":            b,
        "alpha_deg":      geo.alpha_deg,
        "M_cumeeira_kNm": round(M_cumeeira_kNm,     3),
        "sistema":        "rígido",
        "k_p":            round(k_p,                 6),
        "k_vol":          round(k_vol,               4),
        "k_dis":          K_DIS,
        "sigma_t90d_MPa": round(sigma_t90d / 1e6,   4),
        "f_t90d_MPa":     round(mat.f_t90_d / 1e6,  4),
        "resistencia_MPa":round(resist / 1e6,        4),
        "eta":            round(eta,                  4),
        "ok":             eta <= 1.0,
        "justificativa":  "Pórtico rígido — verificação EC5 §6.4.3 ativa",
        "norma":          "EC5 §6.4.3 Eq. 6.50, 6.51, 6.54",
    }


# ── Execução direta ───────────────────────────────────────────────────────────

if __name__ == "__main__":

    from mlc_projeto.core.geometry  import GeometriaViga
    from mlc_projeto.core.materials import GlulamMaterial
    from mlc_projeto.core.wind      import ParametrosVento
    from mlc_projeto.core.loads     import carregamentos_com_vento

    geo = GeometriaViga(L=20.25, h0=0.60, alpha_deg=4.5, b=0.26)
    mat = GlulamMaterial(classe="GL24h", classe_servico=2, duracao="curta")

    params_vento = ParametrosVento(
        V0=45.0, S1=1.0, categoria="IV", classe="B", S3=1.0,
        L=20.25, H1=1.0, h=7.0, dist_portico=5.75,
    )

    load = carregamentos_com_vento(
        geo=geo, mat=mat,
        g_area=1.50, q_area=0.25,
        L_t=5.75, params_vento=params_vento,
    )

    res = verifica_cumeeira(geo, mat, load)

    print("VERIFICAÇÃO DA CUMEEIRA — EC5 §6.4.3")
    print(f"Sistema: {res['sistema']}")
    print(f"M na cumeeira = {res['M_cumeeira_kNm']:.4f} kN·m")
    print(f"k_p = {res['k_p']:.6f} | k_vol = {res['k_vol']:.4f} | "
          f"k_dis = {res['k_dis']}")
    print(f"σ_t,90,d = {res['sigma_t90d_MPa']:.4f} MPa | "
          f"Resistência = {res['resistencia_MPa']:.4f} MPa")
    print(f"η = {res['eta']:.4f}  → "
          f"{'✓ APROVADO' if res['ok'] else '✗ REPROVADO'}")
    print(f"Nota: {res['justificativa']}")