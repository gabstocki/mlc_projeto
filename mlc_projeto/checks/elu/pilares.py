"""
checks/elu/pilares.py — Dimensionamento dos pilares. v2

Sistema — pilar biarticulado (viga biarticulada + pilares rotulados):
    Rótulas em ambas as extremidades do pilar:
    - Base: rótula na sapata
    - Topo: rótula na ligação com a viga
    (Não há rótula na cumeeira — a viga é peça monolítica 1× hiperestática;
     o "pino de cumeeira" do modelo triarticulado foi removido — issue 25.)

    Esforços no pilar:
    - N_d = R_v = q·L/2  (compressão — reação vertical da viga)
    - M_d = 0            (rótulas em ambas as extremidades)
    - V_d = 0            (o pilar não recebe empuxo horizontal — ver nota abaixo)

    Verificação: compressão com instabilidade — EN 1995-1-1:2004 §6.3.2(3):
        σ_c,0,d / (k_c · f_c,0,d) ≤ 1,0        (LINEAR em k_c)
    A forma quadrática pertence a §6.2.4 (Eqs. 6.19/6.20) e só vale para
    λ_rel ≤ 0,3, quando NÃO há redução por instabilidade. Aplicá-la com k_c
    subestima a utilização (AUD-012) — corrigido na Onda 1 da auditoria.

    Comprimento efetivo — pilar com duas rótulas:
        l_ef = 1,0 · H  (EC5 §6.3.2 — articulado-articulado)

    Nota sobre o empuxo horizontal H (coerência — issues 35/38):
        No plano do pórtico o pilar biarticulado é um MECANISMO lateral: uma
        força horizontal no topo não pode ser equilibrada com rótulas nas duas
        extremidades (ΣM_base = H·H_col ⇒ H_top = 0). Logo M_d = V_d = 0 — o
        pilar NÃO transmite empuxo. Consequência (auditoria da issue 38,
        empuxo_acoplado.py): como o apoio horizontal do springing é
        ~nulo/mole (k_pilar ≈ 0 vs k_arco ~2·10⁵ kN/m), o empuxo de gravidade
        PRATICAMENTE NÃO SE DESENVOLVE (H_dev ≈ 0) e a viga tende a biapoiada.
        A reação vertical R_v (e portanto N_d do pilar) NÃO depende disso.
        A decisão de modelo A/B (fecho do empuxo no beiral × sem empuxo) está
        na issue 38; não altera o dimensionamento do pilar (compressão por R_v).

Referência: EN 1995-1-1:2004 §6.3.2 Eqs. (6.23) e (6.24); §6.1.6(2) para k_m.
"""

from __future__ import annotations

import math
import numpy as np
import pandas as pd

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.loads     import Carregamentos
from mlc_projeto.core.validacao import (
    DominioInvalidoError,
    exigir_finito,
    exigir_nao_negativo,
    exigir_positivo,
)


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

    Avalia SEMPRE as duas equações conjugadas e devolve a governante
    (EN 1995-1-1:2004 §6.3.2(3)):
        (6.23)  σc/(k_c,y·f_c0d) + σm,y/f_md + k_m·σm,z/f_md ≤ 1
        (6.24)  σc/(k_c,z·f_c0d) + k_m·σm,y/f_md + σm,z/f_md ≤ 1
    Sem momento ambas degeneram em σc/(k_c·f_c0d) ≤ 1, com k_c do eixo mais
    esbelto — utilização LINEAR, não quadrática.

    Args:
        mat     : Material do pilar
        b       : Largura da seção (m) — // cumeeira (eixo fraco tipicamente)
        h       : Altura da seção no plano do pórtico (m)
        H       : Comprimento do pilar (m)
        N_d     : Força normal de cálculo (kN) — compressão
        M_d_kNm : Momento de cálculo no fuste (kN·m) — ex. vento no fuste
        eixo    : eixo em torno do qual atua M_d_kNm —
                  "y" (plano do pórtico) | "z" (// cumeeira) | "min" (eixo de
                  menor inércia; comportamento histórico)

    Returns:
        dict com k_c/λ_rel por eixo, η_6.23, η_6.24, η governante, eixo
        governante e ok.

    Raises:
        DominioInvalidoError: dimensões não positivas/não finitas, N_d negativo
            ou eixo inválido (AUD-013).
    """
    # ── Pré-condições de domínio (AUD-013) ────────────────────
    # Sem isto, A<=0 caía num fallback (i:=1e-9, σc:=0) que devolvia η=0 e
    # ok=True para uma seção inexistente sob carga não nula.
    b = exigir_positivo("b", b, unidade="m")
    h = exigir_positivo("h", h, unidade="m")
    H = exigir_positivo("H", H, unidade="m")
    M_d_kNm = exigir_finito("M_d_kNm", M_d_kNm)
    N_d = exigir_nao_negativo("N_d", N_d, unidade="kN")
    if eixo not in ("y", "z", "min"):
        raise DominioInvalidoError(
            f"eixo = {eixo!r} inválido; use 'y' (plano do pórtico), "
            f"'z' (// cumeeira) ou 'min'."
        )

    # ── Propriedades da seção ─────────────────────────────────
    A   = b * h
    I_y = b * h ** 3 / 12.0   # flexão/flambagem no plano do pórtico
    I_z = h * b ** 3 / 12.0   # fora do plano (// cumeeira)
    W_y = b * h ** 2 / 6.0
    W_z = h * b ** 2 / 6.0

    i_y = math.sqrt(I_y / A)
    i_z = math.sqrt(I_z / A)

    # ── Comprimento efetivo ───────────────────────────────────
    l_ef = 1.0 * H

    # ── Esbeltez e k_c nos DOIS eixos ─────────────────────────
    # AUD-012: avaliar um único eixo não preserva a interação espacial — a
    # flambagem pode governar num eixo enquanto a flexão atua no outro.
    lam_y     = l_ef / i_y
    lam_z     = l_ef / i_z
    lam_rel_y = (lam_y / math.pi) * math.sqrt(mat.f_c0_k / mat.E0_05)
    lam_rel_z = (lam_z / math.pi) * math.sqrt(mat.f_c0_k / mat.E0_05)
    k_c_y     = _kc_ec5(lam_rel_y)
    k_c_z     = _kc_ec5(lam_rel_z)

    # ── Tensões ───────────────────────────────────────────────
    # `eixo` designa em torno de qual eixo atua M_d_kNm. "min" mantém o
    # comportamento histórico: o momento é atribuído ao eixo de menor inércia.
    eixo_M = eixo if eixo in ("y", "z") else ("y" if I_y <= I_z else "z")
    sigma_c  = N_d * 1e3 / A                                   # Pa
    sigma_my = abs(M_d_kNm) * 1e3 / W_y if eixo_M == "y" else 0.0
    sigma_mz = abs(M_d_kNm) * 1e3 / W_z if eixo_M == "z" else 0.0

    # ── Verificação EC5 §6.3.2 ────────────────────────────────
    # EN 1995-1-1:2004 Eqs. (6.23) e (6.24) — k_m reduz o termo de flexão do
    # eixo SECUNDÁRIO de cada equação (mesmo padrão de (6.19)/(6.20)):
    #   (6.23)  σc/(kc,y·fc0d) + σm,y/fm,d + km·σm,z/fm,d ≤ 1
    #   (6.24)  σc/(kc,z·fc0d) + km·σm,y/fm,d + σm,z/fm,d ≤ 1
    # O termo de compressão estabilizada é LINEAR (§6.3.2(3)); a forma
    # quadrática pertence a §6.2.4, válida só para λ_rel ≤ 0,3 (AUD-012).
    k_m = 0.7  # seção retangular — EC5 §6.1.6(2)
    r_c_y = sigma_c / (k_c_y * mat.f_c0_d)
    r_c_z = sigma_c / (k_c_z * mat.f_c0_d)
    eta_623 = r_c_y + sigma_my / mat.f_m_d + k_m * sigma_mz / mat.f_m_d
    eta_624 = r_c_z + k_m * sigma_my / mat.f_m_d + sigma_mz / mat.f_m_d

    if eta_623 >= eta_624:
        eta, eixo_gov = eta_623, "y"
        k_c, lam, lam_rel = k_c_y, lam_y, lam_rel_y
    else:
        eta, eixo_gov = eta_624, "z"
        k_c, lam, lam_rel = k_c_z, lam_z, lam_rel_z

    tem_M = abs(M_d_kNm) > 1e-9
    return {
        "b_m":            b,
        "h_m":            h,
        "H_m":            H,
        "l_ef_m":         round(l_ef,            3),
        "lambda":         round(lam,             2),
        "eixo":           eixo,
        "eixo_M":         eixo_M,
        "eixo_governante": eixo_gov,
        "M_d_kNm":        round(M_d_kNm,         3),
        "sigma_m_MPa":    round(max(sigma_my, sigma_mz) / 1e6, 4),
        "sigma_m_y_MPa":  round(sigma_my / 1e6,  4),
        "sigma_m_z_MPa":  round(sigma_mz / 1e6,  4),
        "lambda_rel":     round(lam_rel,         4),
        "lambda_rel_y":   round(lam_rel_y,       4),
        "lambda_rel_z":   round(lam_rel_z,       4),
        "k_c":            round(k_c,             4),
        "k_c_y":          round(k_c_y,           4),
        "k_c_z":          round(k_c_z,           4),
        "k_m":            k_m,
        "N_d_kN":         round(N_d,             3),
        "sigma_c_MPa":    round(sigma_c / 1e6,   4),
        "f_c0_d_MPa":     round(mat.f_c0_d / 1e6, 4),
        "f_m_d_MPa":      round(mat.f_m_d / 1e6,  4),
        "eta":            round(eta,             4),
        "eta_6_23":       round(eta_623,         4),
        "eta_6_24":       round(eta_624,         4),
        "ok":             eta <= 1.0,
        "norma":          (
            "EN 1995-1-1:2004 §6.3.2 Eqs. (6.23)/(6.24) — flexo-compressão, "
            "governante entre os dois eixos"
            if tem_M
            else "EN 1995-1-1:2004 §6.3.2(3) — compressão com instabilidade "
                 "(utilização linear em k_c)"
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


# ── Montante de painel de contraventamento (issue 36) ─────────────────────────

def verifica_pilar_contraventado(
    mat:              GlulamMaterial,
    b:                float,
    h:                float,
    H_pilar:          float,
    N_grav_comp_kN:   float,
    N_grav_uplift_kN: float,
    downloads_kN:     list[float] | tuple[float, ...],
    eixo:             str = "min",
    M_vento_kNm:      float = 0.0,
) -> dict:
    """
    Verifica um pilar que é MONTANTE de painel(éis) de contraventamento (cruz de
    St. André). A diagonal tracionada aplica no montante a componente vertical
    ``D = V_Ed·tan β`` — download (compressão) num montante e arrancamento
    (tração) no oposto. Este esforço EXISTE no pilar de madeira e deve ser somado
    à reação de gravidade (issue 36); hoje só ia à fundação.

    Verifica o pilar de CANTO de forma COMBINADA — todas as ações concomitantes
    do mesmo evento de vento (EN 1990 §6.4.3): axial de gravidade + download do
    contraventamento + momento de vento na face. Dois estados-limite:

      · FLEXO-COMPRESSÃO (EC5 §6.3.2, com instabilidade k_c):
            N_c = N_grav_comp + Σ D              (gravidade + download do vento)
            + M_vento na face → σ_c/(k_c·f_c0d) + σ_m/f_md ≤ 1
        N_grav_comp = reação vertical de gravidade da combinação de compressão
        (usa-se o máximo, majorante conservador de EN 1990).

      · FLEXO-TRAÇÃO sob uplift (EC5 §6.2.3 Eq. 6.17):
            N_t = Σ D − N_grav_uplift            (arrancamento − gravidade mínima)
            σ_t,0,d/f_t,0,d + σ_m,d/f_m,d ≤ 1
        Pareia o download do vento (Σ D) com a MENOR reação de gravidade
        (combinação de sucção/uplift, concomitante ao mesmo vento). Se N_t ≤ 0 não
        há tração líquida. N_t é também a DEMANDA DE ANCORAGEM à fundação
        (integrar com a verificação de arrancamento — issue 33).

    Args:
        mat              : material do pilar (k_mod da duração — vento: curta)
        b, h             : seção (m); h = dimensão no plano do pórtico
        H_pilar          : comprimento do pilar (m)
        N_grav_comp_kN   : reação vertical de gravidade p/ o caso de compressão (kN)
        N_grav_uplift_kN : reação vertical mínima (combinação de uplift) (kN)
        downloads_kN     : lista de D=V_Ed·tan β dos painéis que o montante integra
                           (ex.: [long., transv.] para o pilar de canto) (kN)
        eixo             : "min" | "y" | "z" (ver verifica_pilar)

    Returns:
        dict com η governante (max entre compressão e tração), detalhamento e a
        demanda de tração/ancoragem.

    Referência: EN 1995-1-1 §6.1.2 (tração //fibras), §6.3.2 (compressão);
                EN 1993-1-1 §5.3.3 (forças de contraventamento); EN 1990 §6.4.3.
    """
    D = float(sum(downloads_kN))
    M = abs(float(M_vento_kNm))

    # Compressão: gravidade + download + momento de vento (flexo-compressão §6.3.2)
    N_c = float(N_grav_comp_kN) + D
    r_c = verifica_pilar(mat, b, h, H_pilar, N_c, M_d_kNm=M, eixo=eixo)
    eta_comp = r_c["eta"]

    # Módulo resistente do eixo (mesma convenção de verifica_pilar)
    A = b * h
    W_use = h * b ** 2 / 6.0 if eixo == "z" else b * h ** 2 / 6.0

    # Tração líquida sob uplift + vento (flexo-tração EC5 §6.2.3 Eq. 6.17):
    #     σ_t,0,d/f_t,0,d + σ_m,d/f_m,d ≤ 1
    N_t = D - float(N_grav_uplift_kN)
    if N_t > 0.0 and A > 0.0:
        sigma_t0d = N_t * 1e3 / A                       # Pa
        sigma_m   = (M * 1e3) / W_use if W_use > 0 else 0.0
        eta_trac  = sigma_t0d / mat.f_t0_d + sigma_m / mat.f_m_d
    else:
        sigma_t0d = 0.0
        sigma_m   = 0.0
        eta_trac  = 0.0

    regime = "tracao" if eta_trac >= eta_comp else "compressao"
    eta    = max(eta_comp, eta_trac)

    return {
        "b_m":               b,
        "h_m":               h,
        "H_m":               H_pilar,
        "download_total_kN": round(D, 3),
        "M_vento_kNm":       round(M, 3),
        "N_comp_kN":         round(N_c, 3),
        "eta_comp":          round(eta_comp, 4),
        "k_c":               r_c["k_c"],
        "lambda":            r_c["lambda"],
        "N_tracao_liq_kN":   round(max(N_t, 0.0), 3),
        "sigma_t0d_MPa":     round(sigma_t0d / 1e6, 4),
        "sigma_m_MPa":       round(sigma_m / 1e6, 4),
        "f_t0d_MPa":         round(mat.f_t0_d / 1e6, 4),
        "eta_tracao":        round(eta_trac, 4),
        "regime":            regime,
        "eta":               round(eta, 4),
        "ok":                eta <= 1.0,
        "N_ancoragem_kN":    round(max(N_t, 0.0), 3),
        "norma": (
            "EC5 §6.2.3 (flexo-tração) + §6.3.2 (flexo-compressão) | "
            "EN 1993-1-1 §5.3.3 | EN 1990"
        ),
        "nota": (
            "Montante de painel de contraventamento: N = R_v ± V_Ed·tanβ "
            "(download da cruz de St. André). N_tracao_liq = demanda de "
            "ancoragem à fundação (issue 33/36)."
        ),
    }


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
                    "f_c0_d_MPa":  res["f_c0_d_MPa"],
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
    print(f"  f_c,0,d      : {m['f_c0_d_MPa']:.4f} MPa")
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