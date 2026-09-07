"""
checks/elu/flexao.py — Flexo-compressão da viga — EC5 §6.3.2 + §6.3.3.

Viga biarticulada monolítica: M + N com ENVELOPE ponto a ponto ao longo do vão.
Em seção variável a seção de max|M| não é a de max|M/W(x)| — ver AUD-014.

Verificações:
    EC5 §6.3.2 Eq. (6.23) — instabilidade no plano (k_c,y)
    EC5 §6.3.2 Eq. (6.24) — instabilidade fora do plano (k_c,z)
    EC5 §6.3.3 Eq. (6.35) — compressão + flexão com flambagem lateral

Comprimentos efetivos:
    l_ef,y = L      (rótulas só nos apoios)
    l_ef,z = 0,9 · s  (terças — EC5 Tab. 6.1)
    l_ef,m = 0,9 · s  (flambagem lateral — Tab. 6.1)

Referência: EC5 §6.3.2 Eq. 6.23–6.24; §6.3.3 Eq. 6.32–6.35
"""

from __future__ import annotations

import math

import numpy as np

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.loads     import Carregamentos, analisar_biarticulada
from mlc_projeto.checks.elu.flambagem_lateral import (
    calcular_l_ef,
    calcular_sigma_m_crit,
    calcular_lambda_rel_m,
    calcular_k_crit,
)

# EC5 §6.1.6 — fator de redistribuição para seção retangular
K_M = 0.7


def verifica_flexao(
    geo:  GeometriaViga,
    mat:  GlulamMaterial,
    load: Carregamentos,
    s:    float = 1.00,
    posicao_carga: str = "borda_comprimida",
) -> dict:
    """
    Verifica flexo-compressão da viga varrendo TODAS as seções do vão.

    Eq. (6.23): σ_c,0,d/(k_c,y·f_c,0,d) + σ_m,y,d/f_m,d ≤ 1
    Eq. (6.24): σ_c,0,d/(k_c,z·f_c,0,d) + k_m·σ_m,y,d/f_m,d ≤ 1
    Eq. (6.35): (σ_m,d/(k_crit·f_m,d))² + σ_c,0,d/(k_c,z·f_c,0,d) ≤ 1

    FORMA NORMATIVA (issue 16): em §6.3.2 (colunas, instabilidade) o termo de
    COMPRESSÃO é LINEAR (÷k_c) — a forma quadrática (σ_c/(k_c·f_c0d))² é a de
    §6.2.4 (Eq. 6.19/6.20), aplicável só a peças curtas (λ_rel,y e λ_rel,z ≤ 0,3,
    por §6.3.2(2)). A viga é esbelta (l_ef,y = L → λ_rel,y » 0,3) ⇒ §6.3.2(3) ⇒
    forma linear. Em §6.3.3 (6.35) é o termo de FLEXÃO que é ao quadrado e a
    compressão LINEAR. Confirmado no texto EN 1995-1-1:2004 §6.3.2/§6.3.3.

    Args:
        geo  : Geometria da viga
        mat  : Material com k_mod da duração da combinação
        load : Carregamentos (viga biarticulada)
        s    : Espaçamento entre terças (m)

    Returns:
        dict com tensões, fatores e η governante
    """
    b = geo.b
    # ── Envelope sobre as combinações ELU (achado F-06) ───────────────────
    # A varredura de SEÇÕES (AUD-014) já existia, mas só para UMA combinação —
    # a de max|M|, cuja duração impunha o k_mod a toda a verificação. Passa a
    # varrer combinações × seções, cada combinação com o SEU k_mod.
    _melhor_comb = None
    for _c in load.combinacoes_ELU_fisicas().values():
        _r = _envelope_secoes(
            geo, mat.com_duracao(_c.duracao), load, _c, s, posicao_carga)
        if _melhor_comb is None or _r["eta_gov"] > _melhor_comb["eta_gov"]:
            _melhor_comb = _r
    if _melhor_comb is None:
        raise ValueError("Não há combinações ELU para verificar a flexão.")
    return _construir_saida(geo, load, _melhor_comb)


def _envelope_secoes(geo, mat, load, gov, s, posicao_carga) -> dict:
    """Envelope de η(x) ao longo do vão para UMA combinação (AUD-014)."""
    N_d_N    = abs(gov.N_viga_kN) * 1e3   # compressão no eixo
    x_Mmax   = gov.x_Mmax_m
    b        = geo.b

    # ── Diagrama M(x) da combinação governante — AUD-014 ──────────────────
    # A verificação passa a varrer TODAS as seções discretizadas. Em viga de
    # altura variável, max|M| e max|M/W(x)| não coincidem: W(x)=b·h(x)²/6 cai
    # com o quadrado da altura e, longe da cumeeira, essa queda domina a do
    # momento. Avaliar só a seção de M_max subestimava σ_m em ~70% no caso do
    # projeto (1,704 MPa contra 2,893 MPa).
    # O modelo de apoio vem do gerador de combinações (AUD-007), nunca de um
    # default: M(x) = M0(x) − H·y_c(x) depende dele.
    r_gov = analisar_biarticulada(
        q=0.5 * (gov.q_esq + gov.q_dir),
        L=geo.L, h0=geo.h0, h_ap=geo.h_ap, alpha_rad=geo.alpha_rad, b=b,
        q_esq=gov.q_esq, q_dir=gov.q_dir,
        desenvolve_empuxo=load.empuxo_desenvolve,
    )
    x   = geo.x
    M_x = np.interp(x, r_gov["x"], r_gov["M_x"]) * 1e3     # N·m
    h_v = geo.h(x)

    A_v = b * h_v
    W_v = b * h_v ** 2 / 6.0
    i_y_v = np.sqrt((b * h_v ** 3 / 12.0) / A_v)
    i_z_v = np.sqrt((h_v * b ** 3 / 12.0) / A_v)

    beta_c = 0.1  # glulam — EC5 §6.3.2

    def _kc(lam_rel):
        k = 0.5 * (1 + beta_c * (lam_rel - 0.3) + lam_rel ** 2)
        return np.minimum(
            1.0 / (k + np.sqrt(np.maximum(k ** 2 - lam_rel ** 2, 0.0))), 1.0
        )

    # ── Flambagem no plano (eixo y) ───────────────────────────
    # Biarticulada: rótulas apenas nos apoios → l_ef,y = L.
    # DOMÍNIO: EN 1995-1-1 §6.3.2 não formaliza k_c para peça de seção
    # variável. Adota-se a seção LOCAL, escolha explicitamente conservadora
    # (h menor → i_y menor → k_c menor → η maior) — a carga crítica real de
    # uma peça afilada não é governada pela seção mínima. A formalização do
    # domínio de viga de altura variável é item pendente da auditoria (seção O).
    l_ef_y      = geo.L
    lam_y_v     = l_ef_y / i_y_v
    lam_rel_y_v = (lam_y_v / math.pi) * math.sqrt(mat.f_c0_k / mat.E0_05)
    k_c_y_v     = _kc(lam_rel_y_v)

    # ── Flambagem fora do plano (eixo z) ──────────────────────
    # l_ef,z = 0,9·s (entre terças): comprimento CURTO, para o qual a seção
    # local é a representativa — a varredura aqui é mecanicamente própria.
    # F-07: DUAS grandezas distintas que antes partilhavam o mesmo l_ef.
    #  · l_ef,z — flambagem à COMPRESSÃO em torno de z (§6.3.2). É um
    #    comprimento de encurvadura entre travamentos: a nota da Tab. 6.1
    #    (posição da carga na altura) NÃO se aplica.
    #  · l_ef,LTB — flambagem lateral por flexo-torção (§6.3.3), que alimenta
    #    σ_m,crit. Aí a nota aplica-se: as terças carregam a borda comprimida.
    l_ef_z = calcular_l_ef(
        s, restricao="continua_topo", tipo_carga="distribuida",
        posicao_carga="centro_gravidade",
    )
    lam_z_v     = l_ef_z / i_z_v
    lam_rel_z_v = (lam_z_v / math.pi) * math.sqrt(mat.f_c0_k / mat.E0_05)
    k_c_z_v     = _kc(lam_rel_z_v)

    # ── Tensões ponto a ponto ─────────────────────────────────
    sigma_c_v = N_d_N / A_v
    sigma_m_v = np.abs(M_x) / W_v

    # ── EC5 §6.3.2 Eq. (6.23) e (6.24) — compressão LINEAR (÷k_c) ──
    # Flexão uniaxial My: σ_m,z = 0. Viga esbelta (λ_rel » 0,3) → §6.3.2(3).
    eta_623_v = sigma_c_v / (k_c_y_v * mat.f_c0_d) + sigma_m_v / mat.f_m_d
    eta_624_v = sigma_c_v / (k_c_z_v * mat.f_c0_d) + K_M * sigma_m_v / mat.f_m_d

    # ── EC5 §6.3.3 — k_crit na seção local ───────────────────
    l_ef_ltb_v = np.array([
        calcular_l_ef(
            s, restricao="continua_topo", tipo_carga="distribuida",
            posicao_carga=posicao_carga, h_m=float(hh),
        )
        for hh in h_v
    ])
    sigma_crit_v = np.array([
        calcular_sigma_m_crit(mat.E0_05, b, float(hh), float(le))
        for hh, le in zip(h_v, l_ef_ltb_v)
    ])
    lam_rel_m_v = np.array(
        [calcular_lambda_rel_m(mat.f_m_k, float(sc)) for sc in sigma_crit_v]
    )
    k_crit_v = np.array([calcular_k_crit(float(lr)) for lr in lam_rel_m_v])

    # ── EC5 §6.3.3 Eq. (6.35) — FLEXÃO ao quadrado, compressão LINEAR ──
    eta_635_v = (
        (sigma_m_v / (k_crit_v * mat.f_m_d)) ** 2
        + sigma_c_v / (k_c_z_v * mat.f_c0_d)
    )

    # ── Envelope e seção governante ───────────────────────────────────────
    # RASTREABILIDADE: a seção governante é ÚNICA — aquela que maximiza o
    # envelope η(x) = max(6.23, 6.24, 6.35). Todos os escalares devolvidos
    # (tensões, k_c, k_crit, λ_rel, η por equação) referem-se a ESSA seção, de
    # modo que o memorial possa reconstruir cada η a partir dos valores
    # publicados. Reportar quantidades colhidas em seções diferentes tornaria
    # o resultado não reconstruível — o oposto do que a auditoria exige.
    eta_env = np.maximum.reduce([eta_623_v, eta_624_v, eta_635_v])
    i_gov   = int(np.argmax(eta_env))
    eta_gov = float(eta_env[i_gov])

    eta_623 = float(eta_623_v[i_gov])
    eta_624 = float(eta_624_v[i_gov])
    eta_635 = float(eta_635_v[i_gov])
    if eta_gov == eta_635:
        verif_gov = "Eq.6.35"
    elif eta_gov == eta_623:
        verif_gov = "Eq.6.23"
    else:
        verif_gov = "Eq.6.24"

    i_sm    = int(np.argmax(sigma_m_v))
    x_gov   = float(x[i_gov])
    h_x     = float(h_v[i_gov])
    A_sec   = float(A_v[i_gov])
    sigma_c = float(sigma_c_v[i_gov])
    sigma_m = float(sigma_m_v[i_gov])
    lam_y, lam_rel_y, k_c_y = (
        float(lam_y_v[i_gov]), float(lam_rel_y_v[i_gov]), float(k_c_y_v[i_gov])
    )
    lam_z, lam_rel_z, k_c_z = (
        float(lam_z_v[i_gov]), float(lam_rel_z_v[i_gov]), float(k_c_z_v[i_gov])
    )
    lam_rel_m, k_crit = float(lam_rel_m_v[i_gov]), float(k_crit_v[i_gov])

    return dict(
        geo=geo, mat=mat, gov=gov, s=s,
        eta_gov=eta_gov, eta_623=eta_623, eta_624=eta_624, eta_635=eta_635,
        verif_gov=verif_gov, x_gov=x_gov, x_Mmax=x_Mmax, i_sm=i_sm, x=x,
        h_x=h_x, A_sec=A_sec, sigma_c=sigma_c, sigma_m=sigma_m,
        sigma_m_v=sigma_m_v, l_ef_y=l_ef_y, l_ef_z=l_ef_z,
        lam_y=lam_y, lam_rel_y=lam_rel_y, k_c_y=k_c_y,
        lam_z=lam_z, lam_rel_z=lam_rel_z, k_c_z=k_c_z,
        lam_rel_m=lam_rel_m, k_crit=k_crit,
        l_ef_ltb=float(l_ef_ltb_v[i_gov]), posicao_carga=posicao_carga,
    )


def _construir_saida(geo, load, m) -> dict:
    """Monta o dict público a partir da combinação/seção governantes."""
    mat, gov = m["mat"], m["gov"]
    eta_gov = m["eta_gov"]
    x, sigma_m_v = m["x"], m["sigma_m_v"]
    x_Mmax, i_sm = m["x_Mmax"], m["i_sm"]
    b = geo.b
    eta_623, eta_624, eta_635 = m["eta_623"], m["eta_624"], m["eta_635"]
    x_gov, h_x, A_sec = m["x_gov"], m["h_x"], m["A_sec"]
    sigma_c, sigma_m = m["sigma_c"], m["sigma_m"]
    l_ef_y, l_ef_z = m["l_ef_y"], m["l_ef_z"]
    lam_y, lam_rel_y, k_c_y = m["lam_y"], m["lam_rel_y"], m["k_c_y"]
    lam_z, lam_rel_z, k_c_z = m["lam_z"], m["lam_rel_z"], m["k_c_z"]
    lam_rel_m, k_crit, verif_gov = m["lam_rel_m"], m["k_crit"], m["verif_gov"]
    l_ef_ltb, posicao_carga = m["l_ef_ltb"], m["posicao_carga"]

    return {
        # Combinação governante DESTA verificação (F-06)
        "comb_gov":       gov.nome,
        "duracao":        gov.duracao,
        "n_combinacoes_varridas": len(load.combinacoes_ELU_fisicas()),
        "x_Mmax_m":       round(x_Mmax, 3),
        "x_gov_m":        round(x_gov, 3),
        "x_sigma_m_max_m": round(float(x[i_sm]), 3),
        "h_gov_m":        round(h_x, 4),
        "n_secoes_varridas": int(x.size),
        # Envelope de σ_m ao longo do vão e a tensão que a seção de M_max
        # produziria — o par que evidencia o achado AUD-014 no memorial.
        "sigma_m_max_MPa": round(float(sigma_m_v[i_sm]) / 1e6, 4),
        "sigma_m_x_Mmax_MPa": round(
            float(np.interp(x_Mmax, x, sigma_m_v)) / 1e6, 4
        ),
        "h_x_m":          round(h_x, 4),
        "b_m":            b,
        "A_m2":           round(A_sec, 6),
        "M_max_kNm":      round(gov.M_max_kNm, 3),
        "N_d_kN":         round(gov.N_viga_kN, 3),
        "l_ef_y_m":       round(l_ef_y, 3),
        "lambda_y":       round(lam_y, 2),
        "lambda_rel_y":   round(lam_rel_y, 4),
        "k_c_y":          round(k_c_y, 4),
        "eta_no_plano":   round(eta_623, 4),
        "l_ef_z_m":       round(l_ef_z, 3),
        "lambda_z":       round(lam_z, 2),
        "lambda_rel_z":   round(lam_rel_z, 4),
        "k_c_z":          round(k_c_z, 4),
        "eta_fora_plano": round(eta_624, 4),
        "k_crit":         round(k_crit, 4),
        # F-07 — LTB usa l_ef com o +2h da nota da Tab. 6.1; a flambagem à
        # compressão em torno de z, não.
        "l_ef_ltb_m":     round(l_ef_ltb, 3),
        "posicao_carga":  posicao_carga,
        "lambda_rel_m":   round(lam_rel_m, 4),
        "eta_635":        round(eta_635, 4),
        "sigma_c_MPa":    round(sigma_c / 1e6, 4),
        "sigma_m_MPa":    round(sigma_m / 1e6, 4),
        "f_c0d_MPa":      round(mat.f_c0_d / 1e6, 4),
        "f_md_MPa":       round(mat.f_m_d / 1e6, 4),
        "k_mod":          mat.k_mod,
        "duracao":        mat.duracao,
        "eta":            round(eta_gov, 4),
        "ok":             eta_gov <= 1.0,
        "plano_gov":      verif_gov,
        "verif_gov":      verif_gov,
        "norma":          "EC5 §6.3.2 Eq.6.23+6.24 + §6.3.3 Eq.6.35",
    }


if __name__ == "__main__":

    from mlc_projeto.core.geometry  import GeometriaViga
    from mlc_projeto.core.materials import GlulamMaterial
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

    res = verifica_flexao(geo, mat, load, s=2.53)

    print("FLEXO-COMPRESSÃO + LTB — EC5 §6.3.2 + §6.3.3")
    print(f"x={res['x_Mmax_m']} m | h={res['h_x_m']} m | b={res['b_m']} m")
    print(f"M={res['M_max_kNm']:.2f} kN·m | N={res['N_d_kN']:.2f} kN")
    print(f"η_6.23={res['eta_no_plano']:.4f} | η_6.24={res['eta_fora_plano']:.4f} "
          f"| η_6.35={res['eta_635']:.4f} | k_crit={res['k_crit']:.4f}")
    ok = "✓" if res["ok"] else "✗"
    print(f"η={res['eta']:.4f} ({res['verif_gov']}) → {ok}")
