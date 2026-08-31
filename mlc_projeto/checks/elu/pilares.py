"""
checks/elu/pilares.py — Dimensionamento dos pilares. v2

ATUALIZAÇÃO v2 — Pórtico de 3 rótulas:
    Rótulas em ambas as extremidades do pilar:
    - Base: rótula na sapata
    - Topo: rótula na ligação com a viga

    Esforços no pilar:
    - N_d = R_v = q·L/2  (compressão — reação vertical da viga)
    - M_d = 0            (rótulas em ambas as extremidades)
    - V_d = 0            (empuxo H vai para a sapata, não para o pilar)

    Verificação: compressão simples com instabilidade
    EC5 §6.3.2 Eq. 6.23 simplificada (sem momento):
        (σ_c,0,d / (k_c · f_c,0,d))² ≤ 1,0

    Comprimento efetivo — pilar com duas rótulas:
        l_ef = 1,0 · H  (EC5 §6.3.2 — articulado-articulado)

    Nota sobre o empuxo horizontal H:
        H = 621 kN vai direto para a sapata via chumbadores.
        O pilar NÃO resiste ao empuxo — ele é transferido pelo
        mecanismo de apoio articulado (pino na base).
        A sapata e os chumbadores resistem a H.

Referência: EC5 §6.3.2 Eq. 6.23
"""

from __future__ import annotations

import math
import numpy as np
import pandas as pd

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.loads     import Carregamentos


# ── Verificação pontual ───────────────────────────────────────────────────────

def _kc_ec5(lam_rel: float, beta_c: float = 0.1) -> float:
    """Fator de instabilidade k_c — EC5 §6.3.2."""
    k = 0.5 * (1 + beta_c * (lam_rel - 0.3) + lam_rel ** 2)
    return min(1.0 / (k + math.sqrt(max(k ** 2 - lam_rel ** 2, 0.0))), 1.0)


def verifica_pilar(
    mat:   GlulamMaterial,
    b:     float,
    h:     float,
    H:     float,
    N_d:   float,
    M_d_kNm: float = 0.0,
    eixo: str = "min",
) -> dict:
    """
    Verifica pilar em compressão (e flexo-compressão se M_d > 0) — EC5 §6.3.2.

    Pilar com rótulas em ambas as extremidades:
        l_ef = 1,0 · H

    Sem momento:
        (σ_c,0,d / (k_c · f_c,0,d))² ≤ 1,0
    Com momento (vento lateral no fuste):
        σ_c/(k_c·f_c0d) + σ_m/f_md ≤ 1   (Eq. 6.23 simplificada, um eixo)

    Args:
        mat     : Material do pilar
        b       : Largura da seção (m) — // cumeeira (eixo fraco tipicamente)
        h       : Altura da seção no plano do pórtico (m)
        H       : Comprimento do pilar (m)
        N_d     : Força normal de cálculo (kN) — compressão
        M_d_kNm : Momento de cálculo no fuste (kN·m) — ex. vento no fuste
        eixo    : "min" | "y" (plano pórtico, I~h) | "z" (// cumeeira, I~b)

    Returns:
        dict com k_c, λ_rel, η e ok
    """
    # ── Propriedades da seção ─────────────────────────────────
    A = b * h
    I_y = b * h ** 3 / 12.0   # plano do pórtico
    I_z = h * b ** 3 / 12.0   # fora do plano (// cumeeira)
    if eixo == "y":
        I_use = I_y
        W_use = b * h ** 2 / 6.0
    elif eixo == "z":
        I_use = I_z
        W_use = h * b ** 2 / 6.0
    else:
        I_use = min(I_y, I_z)
        W_use = b * h ** 2 / 6.0 if I_y <= I_z else h * b ** 2 / 6.0

    i_use = math.sqrt(I_use / A) if A > 0 else 1e-9

    # ── Comprimento efetivo ───────────────────────────────────
    l_ef = 1.0 * H

    # ── Esbeltez ─────────────────────────────────────────────
    lam     = l_ef / i_use
    lam_rel = (lam / math.pi) * math.sqrt(mat.f_c0_k / mat.E0_05)
    k_c     = _kc_ec5(lam_rel)

    # ── Tensões ───────────────────────────────────────────────
    sigma_c = N_d * 1e3 / A if A > 0 else 0.0          # Pa
    sigma_m = (abs(M_d_kNm) * 1e3) / W_use if W_use > 0 else 0.0  # N/m / m² = Pa? 
    # M in kN·m = 1e3 N·m; W in m³ → σ = M/W in N/m² = Pa. Yes: M*1e3/W

    # ── Verificação EC5 §6.3.2 ────────────────────────────────
    if abs(M_d_kNm) < 1e-9:
        eta = (sigma_c / (k_c * mat.f_c0_d)) ** 2
    else:
        # Eq. 6.23 (um eixo): σc/(kc fc0d) + σm/fmd ≤ 1
        eta = (
            sigma_c / (k_c * mat.f_c0_d)
            + sigma_m / mat.f_m_d
        )

    return {
        "b_m":          b,
        "h_m":          h,
        "H_m":          H,
        "l_ef_m":       round(l_ef,          3),
        "lambda":       round(lam,           2),
        "eixo":         eixo,
        "M_d_kNm":      round(M_d_kNm,       3),
        "sigma_m_MPa":  round(sigma_m / 1e6, 4),
        "lambda_rel":   round(lam_rel,       4),
        "k_c":          round(k_c,           4),
        "N_d_kN":       round(N_d,           3),
        "sigma_c_MPa":  round(sigma_c/1e6,   4),
        "f_c0d_MPa":    round(mat.f_c0_d/1e6,4),
        "eta":          round(eta,            4),
        "ok":           eta <= 1.0,
        "norma":        (
            "EC5 §6.3.2 Eq. 6.23 (flexo-compressão)"
            if abs(M_d_kNm) > 1e-9
            else "EC5 §6.3.2 Eq. 6.23 (compressão pura)"
        ),
    }


def verifica_pilar_governante(
    mat:          GlulamMaterial,
    load:         Carregamentos,
    b:            float,
    h:            float,
    H:            float,
    fator_reacao: float,
    eixo:         str = "min",
) -> dict:
    """
    Verifica o pilar (compressão + instabilidade, EC5 §6.3.2) contra TODAS as
    combinações ELU, cada uma com o seu k_mod (EC5 §3.1.3 / §2.4.1), e devolve a
    combinação GOVERNANTE (maior η) mais o detalhamento por combinação.

    Definição de N — única e rastreável — SEMPRE a reação vertical de ELU:
        N_d(comb) = fator_reacao · R_v(comb)
          fator_reacao = 1 → pilar de extremidade (uma reação de vão)
          fator_reacao = 2 → pilar central (soma das reações dos dois vãos;
                             sob carga simétrica N_central = 2·R_v; para vento
                             assimétrico adota-se 2·max(|R_A|,|R_B|) — limite
                             superior conservador, pois o padrão inter-vãos não
                             é modelado explicitamente)
        R_v(comb) = Combinacao.V_max_kN = max(|R_A|, |R_B|)

    IMPORTANTE (origem dos "dois N" — issue 13):
      · O esforço normal do PILAR é a reação vertical R_v (ex.: 209,59 kN em
        ELU_C2), NÃO o esforço normal no eixo da VIGA (Combinacao.N_viga_kN =
        H·cosθ + R_v·senθ ≈ 1,6 MN, que inclui o empuxo H — este vai ao
        tirante/sapata, não ao pilar).
      · Reações de ELS (ex.: R_v de ELS_S3 ≈ 87 kN, quase-permanente só G) são
        valores de serviço e NÃO podem ser usadas como esforço de projeto ELU.

    Por que iterar TODAS as combinações: a combinação que maximiza η pode não ser
    a de maior N, porque f_c,0,d = k_mod·f_c,0,k/γ_M depende do k_mod de cada
    combinação (uma combinação com N menor, mas k_mod menor, pode governar).

    Returns:
        dict = resultado de verifica_pilar da combinação governante, acrescido de
        comb_gov, duracao, k_mod, fator_reacao e a lista `combinacoes`
        (detalhamento por combinação, ordenado por η decrescente).
    """
    if fator_reacao <= 0:
        raise ValueError("fator_reacao deve ser > 0 (1=extremidade, 2=central)")

    combos = load.combinacoes_ELU()
    if not combos:
        raise ValueError("Nenhuma combinação ELU disponível para verificar o pilar")

    detalhes: list[dict] = []
    gov = None
    gov_nome = gov_dur = None
    gov_kmod = 0.0
    for nome, c in combos.items():
        mat_c = mat.com_duracao(c.duracao)
        R_v = abs(float(c.V_max_kN))
        N_d = fator_reacao * R_v
        r = verifica_pilar(mat_c, b, h, H, N_d, eixo=eixo)
        detalhes.append({
            "comb":        nome,
            "duracao":     c.duracao,
            "k_mod":       round(mat_c.k_mod, 3),
            "R_v_kN":      round(R_v, 3),
            "N_d_kN":      round(N_d, 3),
            "k_c":         r["k_c"],
            "sigma_c_MPa": r["sigma_c_MPa"],
            "eta":         r["eta"],
        })
        if gov is None or r["eta"] > gov["eta"]:
            gov = r
            gov_nome, gov_dur, gov_kmod = nome, c.duracao, mat_c.k_mod

    detalhes.sort(key=lambda d: d["eta"], reverse=True)
    res = dict(gov)
    res["comb_gov"] = gov_nome
    res["duracao"] = gov_dur
    res["k_mod"] = round(gov_kmod, 3)
    res["fator_reacao"] = fator_reacao
    res["combinacoes"] = detalhes
    res["nota_N"] = (
        "N_d = fator_reacao·R_v (reação vertical ELU). Não é o N do eixo da viga "
        "(inclui empuxo H) nem uma reação de ELS."
    )
    return res


def verifica_pilar_vento_lateral(
    mat: GlulamMaterial,
    b: float,
    h: float,
    H: float,
    N_d: float,
    params_vento,
    theta_deg: float = 0.0,
) -> dict:
    """
    Estabilidade lateral do pilar sob vento (estrutura aberta).

    θ = 0° (// cumeeira): arrasto na face b×H → M no eixo fraco (z)
    θ = 90° (⊥ cumeeira): arrasto na face h×H → M no plano do pórtico (y)

    Modelo: carga uniforme no fuste, biapoiado (rótulas topo/base):
        F = q · Ca · A_proj
        M_mid = F · H / 8

    Combina N_d (reação vertical ELU) + M do vento com γ_Q=1,5.
    """
    from mlc_projeto.core.wind import (
        forca_vento_pilar_90,
        CA_PILAR_RET,
    )
    from mlc_projeto.core.loads import GAMMA_Q

    q = params_vento.q
    if abs(theta_deg - 90.0) < 1e-6:
        info = forca_vento_pilar_90(params_vento, b_pilar=b, h_pilar=h)
        F_k = info["F_pilar_kN"]
        eixo = "y"
        face = "h×H (plano pórtico)"
    else:
        A = b * H
        F_k = q * CA_PILAR_RET * A
        eixo = "z"
        face = "b×H (// cumeeira)"
        info = {
            "F_pilar_kN": round(F_k, 3),
            "A_proj_m2": round(A, 4),
            "Ca": CA_PILAR_RET,
            "q_kNm2": round(q, 4),
        }

    F_d = GAMMA_Q * F_k
    M_d = F_d * H / 8.0

    res = verifica_pilar(mat, b, h, H, N_d, M_d_kNm=M_d, eixo=eixo)
    res["theta_deg"] = theta_deg
    res["face"] = face
    res["F_k_kN"] = round(F_k, 3)
    res["F_d_kN"] = round(F_d, 3)
    res["vento"] = info
    res["descricao"] = (
        f"Pilar vento θ={theta_deg:.0f}° ({face}) — "
        f"N={N_d:.1f} kN + M={M_d:.2f} kNm"
    )
    return res


# ── Varredura paramétrica ─────────────────────────────────────────────────────

def varrer_pilares(
    mat:      GlulamMaterial,
    load:     Carregamentos,
    H_pilar:  float = 7.0,
    b_range:  tuple = (0.10, 0.28, 0.02),
    h_range:  tuple = (0.10, 0.40, 0.02),
    eta_max:  float = 1.0,
) -> pd.DataFrame:
    """
    Varre seções (b × h) para o pilar em compressão simples.

    A força normal N_d é a reação vertical da viga:
        N_d = V_max_ELU = q·L/2

    Args:
        mat      : Material do pilar (GL24h duração curta)
        load     : Carregamentos — fornece N_d
        H_pilar  : Altura do pilar (m)
        b_range  : (mín, máx, passo) para largura (m)
        h_range  : (mín, máx, passo) para altura (m)
        eta_max  : Taxa máxima para aprovação

    Returns:
        DataFrame com seções aprovadas, ordenado por volume crescente
    """
    N_d = load.V_max_ELU()   # kN — reação vertical = N no pilar

    b_vals = np.arange(*b_range)
    h_vals = np.arange(*h_range)

    resultados = []

    for b in b_vals:
        for h in h_vals:
            b_f = round(float(b), 3)
            h_f = round(float(h), 3)

            res = verifica_pilar(mat, b_f, h_f, H_pilar, N_d)

            if res["ok"]:
                V_pilar = H_pilar * b_f * h_f
                resultados.append({
                    "b_m":         b_f,
                    "h_m":         h_f,
                    "h_b":         round(h_f/b_f,       2),
                    "l_ef_m":      res["l_ef_m"],
                    "lambda":      res["lambda"],
                    "lambda_rel":  res["lambda_rel"],
                    "k_c":         res["k_c"],
                    "N_d_kN":      res["N_d_kN"],
                    "sigma_c_MPa": res["sigma_c_MPa"],
                    "f_c0d_MPa":   res["f_c0d_MPa"],
                    "eta":         res["eta"],
                    "V_pilar_m3":  round(V_pilar,       4),
                })

    df = pd.DataFrame(resultados)
    if not df.empty:
        df = df.sort_values(["V_pilar_m3", "eta"]).reset_index(drop=True)
    return df


def relatorio_pilares(
    df:      pd.DataFrame,
    load:    Carregamentos,
    H_pilar: float,
    n:       int = 15,
) -> None:
    """Imprime relatório do dimensionamento dos pilares."""
    print("=" * 78)
    print("  DIMENSIONAMENTO DOS PILARES — GL24h")
    print("  Pórtico de 3 rótulas — compressão simples EC5 §6.3.2")
    print("  l_ef = 1,0·H  (articulado-articulado)")
    print("=" * 78)

    N_d = load.V_max_ELU()
    H_f = load.H_ELU()
    print(f"\n  Esforços no pilar:")
    print(f"    N_d = {N_d:.2f} kN  (compressão — reação vertical)")
    print(f"    M_d = 0 kN·m  (rótulas em ambas as extremidades)")
    print(f"    H_fund = {H_f:.2f} kN  (empuxo → sapata, não passa pelo pilar)")
    print(f"    H_pilar = {H_pilar} m")

    if df.empty:
        print("\n  Nenhuma seção aprovada. Aumentar b ou h.")
        print("=" * 78)
        return

    print(f"\n  Seções aprovadas: {len(df)}")
    print(f"  Exibindo as {min(n, len(df))} mais econômicas:\n")

    hdr = (
        f"  {'#':>3}  {'b(m)':>6}  {'h(m)':>6}  {'h/b':>5}  "
        f"{'l_ef':>6}  {'λ':>6}  {'λ_rel':>7}  "
        f"{'k_c':>6}  {'σ_c(MPa)':>9}  {'η':>7}  {'V(m³)':>7}"
    )
    print(hdr)
    print("  " + "-" * 74)

    for i, row in df.head(n).iterrows():
        print(
            f"  {i+1:>3}  {row['b_m']:>6.3f}  {row['h_m']:>6.3f}  "
            f"{row['h_b']:>5.1f}  {row['l_ef_m']:>6.2f}  "
            f"{row['lambda']:>6.1f}  {row['lambda_rel']:>7.4f}  "
            f"{row['k_c']:>6.4f}  {row['sigma_c_MPa']:>9.4f}  "
            f"{row['eta']:>7.4f}  {row['V_pilar_m3']:>7.4f}"
        )

    m = df.iloc[0]
    print(f"\n  ── Pilar recomendado ─────────────────────────────────────")
    print(f"  Seção        : {m['b_m']} × {m['h_m']} m  (b × h)")
    print(f"  l_ef         : {m['l_ef_m']} m  (= 1,0 × H)")
    print(f"  λ            : {m['lambda']:.1f}")
    print(f"  λ_rel        : {m['lambda_rel']:.4f}")
    print(f"  k_c          : {m['k_c']:.4f}")
    print(f"  σ_c,0,d      : {m['sigma_c_MPa']:.4f} MPa")
    print(f"  f_c,0,d      : {m['f_c0d_MPa']:.4f} MPa")
    print(f"  η            : {m['eta']:.4f}")
    print(f"  Volume pilar : {m['V_pilar_m3']:.4f} m³")
    print(f"  ─────────────────────────────────────────────────────────")
    print(f"  Comparação com pórtico rígido (Sistema A):")
    print(f"  Seção rígido : 0,22 × 0,80 m  (V = 1,232 m³)")
    print(f"  Economia     : "
          f"{(1-m['V_pilar_m3']/1.232)*100:.1f}% de madeira no pilar")
    print("=" * 78)


# ── Execução direta ───────────────────────────────────────────────────────────

if __name__ == "__main__":

    from mlc_projeto.core.geometry  import GeometriaViga
    from mlc_projeto.core.wind      import ParametrosVento
    from mlc_projeto.core.loads     import carregamentos_com_vento

    geo = GeometriaViga(L=20.25, h0=0.60, alpha_deg=4.5, b=0.26)
    mat = GlulamMaterial(classe="GL24h", classe_servico=3, duracao="curta")

    params_vento = ParametrosVento(
        V0=45.0, S1=1.0, categoria="IV", classe="B", S3=1.0,
        L=20.25, H1=1.0, h=7.0, dist_portico=5.75,
    )

    load = carregamentos_com_vento(
        geo=geo, mat=mat,
        g_area=1.50, q_area=0.25,
        L_t=5.75, params_vento=params_vento,
    )

    print(f"N_d = {load.V_max_ELU():.2f} kN  "
          f"| H_fund = {load.H_ELU():.2f} kN\n")

    df = varrer_pilares(
        mat=mat, load=load, H_pilar=7.0,
        b_range=(0.10, 0.28, 0.02),
        h_range=(0.10, 0.40, 0.02),
    )

    relatorio_pilares(df, load, H_pilar=7.0, n=15)