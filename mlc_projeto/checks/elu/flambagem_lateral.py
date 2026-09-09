"""
checks/elu/flambagem_lateral.py — Flambagem lateral por flexo-torção.

VERIFICAÇÃO CRÍTICA — governa vigas esbeltas sem restrição lateral contínua.

A aba comprimida de uma viga em flexão tende a deslocar-se lateralmente
(flambagem lateral), reduzindo a resistência efetiva à flexão. O EC5 §6.3.3
controla isso pelo fator k_crit, que depende da esbeltez relativa λ_rel,m.

Comprimento efetivo:
    l_ef = 0,9 · l_1  (EC5 Tab. 6.1 — carga dist. + restrição no topo)

    l_1 NÃO é livre: só pode ser o espaçamento entre terças (s) se o
    contraventamento de cobertura validar a restrição lateral
    (EC5 §9.2.5 → `l_1_efetivo_m` em contraventamento.py).
    Sem cobertura válida, l_1 deve ser o vão entre baías rígidas (ℓ).

Referência: EC5 §6.3.3 + §9.2.5
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.validacao import DominioInvalidoError, exigir_positivo
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.loads     import Carregamentos


# ── Comprimento efetivo ───────────────────────────────────────────────────────

#: Razões l_ef/l₁ da EC5 Tabela 6.1, por (restrição, tipo de carga).
_RAZAO_TAB_6_1 = {
    ("continua_topo", "distribuida"): 0.9,
    ("continua_topo", "pontual"):     0.8,
    ("so_apoios",     "distribuida"): 0.9,
    ("so_apoios",     "pontual"):     0.8,
    ("apoios_e_topo", "distribuida"): 0.9,
    ("apoios_e_topo", "pontual"):     0.8,
}

#: Correção pela POSIÇÃO da carga na altura — nota da EC5 Tabela 6.1.
#: (fator a multiplicar por h e somar a l_ef)
_AJUSTE_POSICAO_CARGA = {
    "centro_gravidade": 0.0,    # caso de referência das razões tabeladas
    "borda_comprimida": +2.0,   # "l_ef should be increased by 2h"
    "borda_tracionada": -0.5,   # "may be decreased by 0,5h"
}


def calcular_l_ef(
    l_1:           float,
    restricao:     str = "continua_topo",
    tipo_carga:    str = "distribuida",
    posicao_carga: str = "borda_comprimida",
    h_m:           float | None = None,
) -> float:
    """
    Comprimento efetivo l_ef para flambagem lateral — EC5 Tabela 6.1 + nota.

        l_ef = razão(restrição, tipo_carga) · l₁  +  Δ(posição da carga) · h

        Δ = 0      carga no centro de gravidade (caso das razões tabeladas)
        Δ = +2,0   carga na BORDA COMPRIMIDA   ("should be increased by 2h")
        Δ = −0,5   carga na borda tracionada   ("may be decreased by 0,5h")

    Achado F-07 da auditoria adversarial v2
    ---------------------------------------
    As razões estavam implementadas, a **nota da própria tabela** não. Neste
    projeto as terças apoiam no extradorso — a borda COMPRIMIDA sob gravidade —
    e com l₁ = 2,53 m e h = 2,785 m o l_ef correto é 7,85 m em vez de 2,28 m
    (3,4×): λ_rel,m sobe de 0,446 para 0,827 e a viga deixa de ser «estável».

    O default é o caso CONSERVADOR (`borda_comprimida`) e `h_m` é então
    obrigatório: nenhum chamador pode continuar a herdar em silêncio a hipótese
    mais favorável. Em peça de altura variável, `h_m` deve ser a altura da SEÇÃO
    verificada, não h0.

    Args:
        l_1           : distância entre pontos de restrição lateral (m)
        restricao     : "continua_topo" | "so_apoios" | "apoios_e_topo"
        tipo_carga    : "distribuida" | "pontual"
        posicao_carga : "borda_comprimida" | "centro_gravidade" | "borda_tracionada"
        h_m           : altura da seção (m) — obrigatória se posicao_carga ≠
                        "centro_gravidade"

    Returns:
        l_ef (m), estritamente positivo.
    """
    chave = (restricao, tipo_carga)
    if chave not in _RAZAO_TAB_6_1:
        raise ValueError(
            f"Combinação restrição='{restricao}', carga='{tipo_carga}' não "
            f"tabelada. Opções: {sorted(_RAZAO_TAB_6_1)}"
        )
    if posicao_carga not in _AJUSTE_POSICAO_CARGA:
        raise ValueError(
            f"posicao_carga='{posicao_carga}' não reconhecida. Opções: "
            f"{sorted(_AJUSTE_POSICAO_CARGA)}"
        )
    delta = _AJUSTE_POSICAO_CARGA[posicao_carga]
    if delta != 0.0:
        if h_m is None:
            raise ValueError(
                f"posicao_carga='{posicao_carga}' exige h_m: a nota da EC5 Tab. "
                f"6.1 corrige l_ef em {delta:+g}·h. Declare a altura da seção "
                f"(ou use posicao_carga='centro_gravidade' se a carga atuar "
                f"mesmo no centro de gravidade)."
            )
        h = exigir_positivo("h_m", h_m, unidade="m")
    else:
        h = 0.0

    l_ef = _RAZAO_TAB_6_1[chave] * exigir_positivo("l_1", l_1, unidade="m") + delta * h
    if l_ef <= 0.0:
        # Só possível na borda tracionada com h ≫ l₁ — a redução é um "may",
        # não pode produzir um comprimento efetivo não físico.
        raise DominioInvalidoError(
            f"l_ef = {l_ef:.4f} m ≤ 0 com l_1={l_1} m, h={h_m} m e "
            f"posicao_carga='{posicao_carga}'. A redução de 0,5h da EC5 Tab. 6.1 "
            f"é facultativa e não pode anular o comprimento efetivo."
        )
    return l_ef


# ── Funções principais EC5 §6.3.3 ────────────────────────────────────────────

def calcular_sigma_m_crit(
    E_005:  float,
    b:      float,
    h:      float,
    l_ef:   float,
    G_05:   float | None = None,
) -> float:
    """
    Tensão crítica de flambagem lateral σ_m,crit — EC5 §6.3.3.

    Seção retangular de coníferas — EC5 §6.3.3(2) Eq. (6.32):

        σ_m,crit = 0,78 · b² · E_0,05 / (h · l_ef)

    Esta expressão decorre da formulação geral (6.31) com
    G_0,05 = E_0,05/16 e I_tor ≈ h·b³/3. A relação E_0,05/16 vive AQUI, dentro
    da dedução da Eq. (6.32) — não é uma propriedade do material e não deve ser
    exposta como tal (achado [F-16]; ver `GlulamMaterial.G_g_05`, que é o valor
    tabelado da EN 14080:2013 Tab. 5, 540 MPa).

    Se G_05 for fornecido — e o valor a fornecer é `mat.G_g_05` — usa-se a
    formulação geral EC5 Eq. (6.31):
        σ_m,crit = π · √(E_0,05·I_z·G_0,05·I_tor) / (l_ef · W_y)

    Args:
        E_005  : Módulo de elasticidade característico E_0,05 (Pa)
        b      : Largura da seção (m)
        h      : Altura da seção no ponto verificado (m)
        l_ef   : Comprimento efetivo de flambagem lateral (m)
        G_05   : Opcional — G_0,05 (Pa). Se None, usa Eq. (6.32).

    Returns:
        σ_m,crit (Pa)
    """
    if G_05 is None:
        # EC5 §6.3.3(2) Eq. (6.32) — retangular, coníferas
        return 0.78 * (b ** 2) * E_005 / (h * l_ef)

    # EC5 §6.3.3 Eq. (6.31) — formulação geral
    I_z   = h * b ** 3 / 12
    I_tor = h * b ** 3 / 3
    W_y   = b * h ** 2 / 6
    return (math.pi / (W_y * l_ef)) * math.sqrt(
        E_005 * I_z * G_05 * I_tor
    )


def calcular_lambda_rel_m(
    f_m_k:       float,
    sigma_m_crit: float,
) -> float:
    """
    Esbeltez relativa λ_rel,m — EC5 §6.3.3.

        λ_rel,m = √(f_m,k / σ_m,crit)

    Args:
        f_m_k        : Resistência característica à flexão (Pa)
        sigma_m_crit : Tensão crítica de flambagem lateral (Pa)

    Returns:
        λ_rel,m (adimensional)
    """
    return math.sqrt(f_m_k / sigma_m_crit)


def calcular_k_crit(lambda_rel_m: float) -> float:
    """
    Fator de instabilidade k_crit — EC5 §6.3.3.

    Três regimes conforme a esbeltez relativa λ_rel,m:

        λ_rel,m ≤ 0,75          → k_crit = 1,0
        0,75 < λ_rel,m ≤ 1,4   → k_crit = 1,56 - 0,75·λ_rel,m
        λ_rel,m > 1,4           → k_crit = 1 / λ_rel,m²

    Args:
        lambda_rel_m: Esbeltez relativa (adimensional)

    Returns:
        k_crit (adimensional, entre 0 e 1)
    """
    if lambda_rel_m <= 0.75:
        return 1.0
    elif lambda_rel_m <= 1.4:
        return 1.56 - 0.75 * lambda_rel_m
    else:
        return 1.0 / lambda_rel_m**2


# ── Verificação principal ─────────────────────────────────────────────────────

def verifica_flambagem_lateral(
    geo:   GeometriaViga,
    mat:   GlulamMaterial,
    load:  Carregamentos,
    l_1:   float = 5.75,
    posicao_carga: str = "borda_comprimida",
) -> dict:
    """
    Verifica estabilidade lateral por flexo-torção — EC5 §6.3.3.

    Condição (flexão simples):
        σ_m,d ≤ k_crit · f_m,d

    Seção crítica: ponto de M_max da análise biarticulada.
    Altura h = h(x_Mmax).

    σ_m,crit: EC5 §6.3.3(2) Eq. (6.32) — seção retangular.

    Args:
        geo  : Geometria da viga
        mat  : Material
        load : Carregamentos
        l_1  : Distância entre restrições laterais efetivas (m).
               Usar `contraventamento['l_1_efetivo_m']` do pipeline.

    Returns:
        dict com resultados intermediários, η e ok
    """
    # ── Comprimento efetivo ───────────────────────────────────
    # l_1 já deve incorporar a validade do contraventamento (§9.2.5).
    # F-07: as terças apoiam no EXTRADORSO — borda comprimida sob gravidade —
    # logo a nota da EC5 Tab. 6.1 acrescenta 2h. Em peça de altura variável o
    # h é o da SEÇÃO verificada, pelo que l_ef entra no laço das combinações.
    b = geo.b

    # ── Envelope sobre as combinações ELU (achado F-06) ───────
    # Cada combinação traz o SEU k_mod e a SUA posição de M_max. A seção
    # crítica muda com a combinação (viga de altura variável), e uma combinação
    # de momento menor com k_mod menor pode governar.
    melhor = None
    for comb in load.combinacoes_ELU_fisicas().values():
        matc   = mat.com_duracao(comb.duracao)
        x_i    = comb.x_Mmax_m
        h_i    = float(geo.h(x_i))
        l_ef_i = calcular_l_ef(
            l_1, restricao="continua_topo", tipo_carga="distribuida",
            posicao_carga=posicao_carga, h_m=h_i,
        )
        sig_cr = calcular_sigma_m_crit(E_005=matc.E0_05, b=b, h=h_i, l_ef=l_ef_i)
        lam_i  = calcular_lambda_rel_m(matc.f_m_k, sig_cr)
        kcr_i  = calcular_k_crit(lam_i)
        W_i    = b * h_i ** 2 / 6.0
        sig_i  = abs(comb.M_max_kNm) * 1e3 / W_i
        res_i  = kcr_i * matc.f_m_d
        eta_i  = sig_i / res_i if res_i > 0 else 999.0
        if melhor is None or eta_i > melhor["eta"]:
            melhor = dict(eta=eta_i, comb=comb, mat=matc, x=x_i, h=h_i,
                          sig_crit=sig_cr, lam=lam_i, k_crit=kcr_i,
                          sigma_md=sig_i, resist=res_i, l_ef=l_ef_i)

    if melhor is None:
        raise ValueError("Não há combinações ELU para verificar a LTB.")

    comb, matc = melhor["comb"], melhor["mat"]
    x_Mmax, h_crit, l_ef = melhor["x"], melhor["h"], melhor["l_ef"]
    sigma_crit, lam_rel, k_crit = melhor["sig_crit"], melhor["lam"], melhor["k_crit"]
    sigma_md, resist, eta = melhor["sigma_md"], melhor["resist"], melhor["eta"]
    f_md = matc.f_m_d

    if lam_rel <= 0.75:
        regime = "estável — sem redução (λ ≤ 0,75)"
    elif lam_rel <= 1.4:
        regime = "instabilidade parcial (0,75 < λ ≤ 1,4)"
    else:
        regime = "instabilidade severa (λ > 1,4)"

    return {
        # Geometria
        "L_m":           geo.L,
        "x_Mmax_m":      round(x_Mmax, 3),
        "h_crit_m":      round(h_crit, 4),
        "h_ap_m":        geo.h_ap,
        "b_m":           b,
        "h_b":           round(h_crit / b, 2),
        # Combinação governante DESTA verificação (F-06)
        "comb_gov":      comb.nome,
        "duracao":       comb.duracao,
        "k_mod":         matc.k_mod,
        "n_combinacoes_varridas": len(load.combinacoes_ELU_fisicas()),
        # Comprimento efetivo (hipótese de restrição lateral)
        "l_1_m":         l_1,
        "l_ef_m":        round(l_ef, 3),
        "fator_l_ef":    0.9,           # EC5 Tab. 6.1 (dist. + restrição no topo)
        "restricao":     "continua_topo (terças fixadas ao banzo comprimido)",
        "tipo_carga":    "distribuida",
        # F-07 — nota da EC5 Tab. 6.1: carga na borda comprimida ⇒ +2h
        "posicao_carga": posicao_carga,
        "delta_posicao_h": _AJUSTE_POSICAO_CARGA[posicao_carga],
        "l_ef_formula":  (
            f"l_ef = 0,9·l_1 {_AJUSTE_POSICAO_CARGA[posicao_carga]:+g}·h "
            f"(EC5 Tab. 6.1 + nota: carga em '{posicao_carga}')"
        ),
        "l_1_origem":    ("espaçamento efetivo das terças validado pelo "
                          "contraventamento de cobertura (EC5 §9.2.5); sem "
                          "cobertura válida, l_1 = vão entre baías rígidas"),
        # Tensão crítica — EC5 §6.3.3(2) Eq. (6.32), com E_0,05
        "E0_05_MPa":        round(matc.E0_05 / 1e6, 0),
        "sigma_m_crit_MPa": round(sigma_crit / 1e6, 3),
        "sigma_m_crit_formula": "σ_m,crit = 0,78·b²·E_0,05/(h·l_ef)  (Eq. 6.32)",
        "lambda_rel_m":     round(lam_rel, 4),
        "lambda_rel_formula": "λ_rel,m = √(f_m,k/σ_m,crit)  (Eq. 6.30)",
        "k_crit":           round(k_crit,  4),
        "regime":           regime,
        # Tensões
        "sigma_md_MPa":  round(sigma_md / 1e6, 4),
        "f_md_MPa":      round(f_md     / 1e6, 4),
        "resist_MPa":    round(resist   / 1e6, 4),
        # Momento
        "M_max_ELU_kNm": round(comb.M_max_kNm, 2),
        # Resultado
        "eta":           round(eta, 4),
        "ok":            eta <= 1.0,
        # Referência
        "norma":         "EC5 §6.3.3 Eq. 6.32 + 6.33",
    }


# ── Varredura paramétrica ─────────────────────────────────────────────────────

def varrer_flambagem_lateral(
    mat:         GlulamMaterial,
    L:           float,
    g_k:         float,
    q_k:         float,
    l_1:         float = 5.75,
    h0_range:    tuple = (0.60, 1.30, 0.10),
    alpha_range: tuple = (3.0,  8.5,  0.5),
    b_range:     tuple = (0.14, 0.28, 0.02),
    eta_max:     float = 1.0,
) -> pd.DataFrame:
    """
    Varre combinações (h0, α, b) e verifica flambagem lateral para cada uma.

    Args:
        mat         : Material GlulamMaterial
        L           : Vão de cada pórtico (m)
        g_k         : Carga permanente característica (kN/m)
        q_k         : Sobrecarga característica (kN/m)
        l_1         : Espaçamento entre terças (m)
        h0_range    : (mín, máx, passo) para h0 (m)
        alpha_range : (mín, máx, passo) para α (graus)
        b_range     : (mín, máx, passo) para b (m)
        eta_max     : Taxa de utilização máxima para filtrar

    Returns:
        DataFrame com geometrias aprovadas, ordenado por η crescente
    """

    h0_vals    = np.arange(*h0_range)
    alpha_vals = np.arange(*alpha_range)
    b_vals     = np.arange(*b_range)

    resultados = []

    for h0 in h0_vals:
        for alpha in alpha_vals:
            for b in b_vals:

                geo = GeometriaViga(
                    L=L,
                    h0=round(float(h0), 3),
                    alpha_deg=round(float(alpha), 2),
                    b=round(float(b), 3),
                )

                h_crit = geo.h_ap

                # Tensão crítica de flambagem
                # F-07: +2h da nota da EC5 Tab. 6.1 (depende de h).
                l_ef = calcular_l_ef(
                    l_1, restricao="continua_topo",
                    posicao_carga="borda_comprimida", h_m=h_crit,
                )
                sigma_crit = calcular_sigma_m_crit(
                    mat.E0_05, float(b), h_crit, l_ef
                )

                lam_rel = calcular_lambda_rel_m(mat.f_m_k, sigma_crit)
                k_crit  = calcular_k_crit(lam_rel)

                # Tensão atuante — seção da cumeeira
                q_ELU    = 1.35 * g_k + 1.5 * q_k
                M_max_Nm = (q_ELU * L**2 / 8) * 1e3   # N·m
                W_y      = float(b) * h_crit**2 / 6
                sigma_md = M_max_Nm / W_y

                # Resistência
                resist = k_crit * mat.f_m_d
                eta    = sigma_md / resist

                # Regime
                if lam_rel <= 0.75:
                    regime = "estável"
                elif lam_rel <= 1.4:
                    regime = "parcial"
                else:
                    regime = "severo"

                resultados.append({
                    "h0_m":          round(float(h0),    3),
                    "alpha_deg":     round(float(alpha),  2),
                    "b_m":           round(float(b),      3),
                    "h_ap_m":        round(h_crit,        3),
                    "h_b":           round(h_crit / float(b), 2),
                    "lambda_rel_m":  round(lam_rel,       4),
                    "k_crit":        round(k_crit,        4),
                    "sigma_md_MPa":  round(sigma_md/1e6,  4),
                    "resist_MPa":    round(resist/1e6,    4),
                    "eta":           round(eta,            4),
                    "regime":        regime,
                    "ok":            eta <= eta_max,
                })

    df = pd.DataFrame(resultados)
    df_ok = df[df["ok"]].sort_values("eta").reset_index(drop=True)
    return df_ok


def relatorio_flambagem(df: pd.DataFrame, n: int = 20) -> None:
    """Imprime relatório formatado das melhores geometrias."""
    print("=" * 82)
    print("  VARREDURA — FLAMBAGEM LATERAL EC5 §6.3.3  |  Geometrias aprovadas")
    print("=" * 82)

    if df.empty:
        print("\n  Nenhuma geometria aprovada no intervalo varrido.")
        print("  Sugestões:")
        print("  - Aumentar b (largura da seção)")
        print("  - Reduzir l_1 (espaçamento entre terças)")
        print("  - Usar classe resistente superior (GL28h)")
        print("=" * 82)
        return

    print(f"\n  Total de geometrias aprovadas: {len(df)}")
    print(f"  Exibindo as {min(n, len(df))} melhores:\n")

    header = (
        f"  {'#':>3}  {'h0(m)':>6}  {'α(°)':>5}  {'b(m)':>6}  "
        f"{'h_ap(m)':>8}  {'h/b':>5}  {'λ_rel':>7}  "
        f"{'k_crit':>7}  {'σ(MPa)':>8}  {'R(MPa)':>8}  {'η':>6}  {'Regime'}"
    )
    print(header)
    print("  " + "-" * 78)

    for i, row in df.head(n).iterrows():
        linha = (
            f"  {i+1:>3}  {row['h0_m']:>6.3f}  {row['alpha_deg']:>5.1f}  "
            f"{row['b_m']:>6.3f}  {row['h_ap_m']:>8.3f}  "
            f"{row['h_b']:>5.1f}  {row['lambda_rel_m']:>7.4f}  "
            f"{row['k_crit']:>7.4f}  {row['sigma_md_MPa']:>8.4f}  "
            f"{row['resist_MPa']:>8.4f}  {row['eta']:>6.4f}  {row['regime']}"
        )
        print(linha)

    print("\n  Legenda:")
    print("  h/b    = relação altura/largura (recomendado ≤ 5 para estabilidade)")
    print("  λ_rel  = esbeltez relativa (≤ 0,75: estável | ≤ 1,4: parcial | > 1,4: severo)")
    print("  k_crit = fator de redução por instabilidade lateral (1,0 = sem redução)")
    print("  σ      = tensão de flexão de cálculo σ_m,d (MPa)")
    print("  R      = resistência efetiva k_crit·f_m,d (MPa)")
    print("  η      = taxa de utilização (aprovado se η ≤ 1,0)")
    print("=" * 82)


# ── Varredura combinada: cumeeira + flambagem lateral ────────────────────────

def varrer_combinado(
    mat:         GlulamMaterial,
    L:           float,
    g_k:         float,
    q_k:         float,
    l_1:         float = 5.75,
    h0_range:    tuple = (0.60, 1.30, 0.10),
    alpha_range: tuple = (3.0,  8.5,  0.5),
    b_range:     tuple = (0.14, 0.28, 0.02),
    eta_max:     float = 1.0,
) -> pd.DataFrame:
    """
    Varre (h0, α, b) verificando SIMULTANEAMENTE cumeeira E flambagem lateral.

    Retorna apenas geometrias aprovadas em AMBAS as verificações,
    ordenadas pelo maior η entre as duas (geometria mais restrita).

    Este é o resultado mais útil para o pré-dimensionamento — elimina
    todas as geometrias que falham em qualquer uma das duas verificações
    críticas antes de avançar para as demais verificações EC5.

    Returns:
        DataFrame com colunas de ambas as verificações + eta_gov (governante)
    """
    from mlc_projeto.checks.elu.cumeeira import (
        calcular_k_p, calcular_k_vol, calcular_sigma_t90d,
        K_DIS, V0_KVOL
    )


    h0_vals    = np.arange(*h0_range)
    alpha_vals = np.arange(*alpha_range)
    b_vals     = np.arange(*b_range)

    resultados = []

    for h0 in h0_vals:
        for alpha in alpha_vals:
            for b in b_vals:

                geo = GeometriaViga(
                    L=L,
                    h0=round(float(h0), 3),
                    alpha_deg=round(float(alpha), 2),
                    b=round(float(b), 3),
                )

                h_ap = geo.h_ap
                b_f  = float(b)

                # Carregamento ELU
                q_ELU    = 1.35 * g_k + 1.5 * q_k
                M_max_Nm = (q_ELU * L**2 / 8) * 1e3

                # ── CUMEEIRA ─────────────────────────────────
                k_p     = calcular_k_p(float(alpha))
                k_vol   = calcular_k_vol(b_f, h_ap, L, float(alpha))
                sig_t90 = calcular_sigma_t90d(k_p, M_max_Nm, b_f, h_ap)
                res_t90 = K_DIS * k_vol * mat.f_t90_d
                eta_cum = sig_t90 / res_t90

                # ── FLAMBAGEM LATERAL ─────────────────────────
                # F-07: +2h da nota da EC5 Tab. 6.1 (depende de h).
                l_ef = calcular_l_ef(
                    l_1, restricao="continua_topo",
                    posicao_carga="borda_comprimida", h_m=h_ap,
                )
                sig_crit = calcular_sigma_m_crit(
                    mat.E0_05, b_f, h_ap, l_ef
                )
                lam_rel  = calcular_lambda_rel_m(mat.f_m_k, sig_crit)
                k_crit   = calcular_k_crit(lam_rel)
                W_y      = b_f * h_ap**2 / 6
                sig_md   = M_max_Nm / W_y
                res_fl   = k_crit * mat.f_m_d
                eta_fl   = sig_md / res_fl

                # ── Ambas aprovadas? ──────────────────────────
                ok = (eta_cum <= eta_max) and (eta_fl <= eta_max)
                eta_gov = max(eta_cum, eta_fl)   # verificação governante

                if ok:
                    resultados.append({
                        "h0_m":          round(float(h0),   3),
                        "alpha_deg":     round(float(alpha), 2),
                        "b_m":           round(b_f,          3),
                        "h_ap_m":        round(h_ap,         3),
                        "h_b":           round(h_ap / b_f,   2),
                        # Cumeeira
                        "eta_cumeeira":  round(eta_cum,      4),
                        # Flambagem
                        "lambda_rel_m":  round(lam_rel,      4),
                        "k_crit":        round(k_crit,       4),
                        "eta_flambagem": round(eta_fl,       4),
                        # Governante
                        "eta_gov":       round(eta_gov,      4),
                        "verif_gov":     "cumeeira" if eta_cum >= eta_fl
                                         else "flambagem",
                    })

    df = pd.DataFrame(resultados)
    if not df.empty:
        df = df.sort_values("eta_gov").reset_index(drop=True)
    return df


def relatorio_combinado(df: pd.DataFrame, n: int = 20) -> None:
    """Imprime relatório das geometrias aprovadas nas duas verificações."""
    print("=" * 86)
    print("  VARREDURA COMBINADA — Cumeeira §6.4.3 + Flambagem Lateral §6.3.3")
    print("  Geometrias aprovadas em AMBAS as verificações críticas")
    print("=" * 86)

    if df.empty:
        print("\n  Nenhuma geometria aprovada simultaneamente nas duas verificações.")
        print("  Sugestões:")
        print("  - Ampliar os intervalos de varredura")
        print("  - Considerar GL28h ou GL32h")
        print("  - Reduzir espaçamento entre terças")
        print("=" * 86)
        return

    print(f"\n  Total de geometrias aprovadas: {len(df)}")
    print(f"  Exibindo as {min(n, len(df))} melhores (ordenadas por η governante):\n")

    header = (
        f"  {'#':>3}  {'h0(m)':>6}  {'α(°)':>5}  {'b(m)':>6}  "
        f"{'h_ap(m)':>8}  {'h/b':>5}  "
        f"{'η_cumeeira':>11}  {'η_flamb':>9}  "
        f"{'η_gov':>7}  {'Governa'}"
    )
    print(header)
    print("  " + "-" * 80)

    for i, row in df.head(n).iterrows():
        linha = (
            f"  {i+1:>3}  {row['h0_m']:>6.3f}  {row['alpha_deg']:>5.1f}  "
            f"{row['b_m']:>6.3f}  {row['h_ap_m']:>8.3f}  "
            f"{row['h_b']:>5.1f}  "
            f"{row['eta_cumeeira']:>11.4f}  {row['eta_flambagem']:>9.4f}  "
            f"{row['eta_gov']:>7.4f}  {row['verif_gov']}"
        )
        print(linha)

    melhor = df.iloc[0]
    print(f"\n  ── Geometria recomendada para prosseguir ──")
    print(f"  h0    = {melhor['h0_m']} m")
    print(f"  α     = {melhor['alpha_deg']}°")
    print(f"  b     = {melhor['b_m']} m")
    print(f"  h_ap  = {melhor['h_ap_m']} m")
    print(f"  h/b   = {melhor['h_b']}")
    print(f"  η_cumeeira  = {melhor['eta_cumeeira']:.4f}")
    print(f"  η_flambagem = {melhor['eta_flambagem']:.4f}")
    print(f"  η_governante = {melhor['eta_gov']:.4f}  ({melhor['verif_gov']})")
    print("=" * 86)


# ── Execução direta para teste ────────────────────────────────────────────────

if __name__ == "__main__":

    mat = GlulamMaterial(
        classe="GL24h",
        classe_servico=3,
        duracao="longa",
    )

    dist_porticos = 5.75
    g_k = 1.50 * dist_porticos
    q_k = 0.25 * dist_porticos

    L   = 20.25
    l_1 = 5.75

    print(f"Material : {mat.classe} | CS {mat.classe_servico} | longa duração")
    print(f"k_mod    = {mat.k_mod:.2f} | f_m,d = {mat.f_m_d/1e6:.3f} MPa")
    print(f"E_0,05   = {mat.E0_05/1e9:.2f} GPa | G_mean = {mat.G_mean/1e9:.3f} GPa")
    print(f"l_ef     = 0,9 × {l_1} = {0.9*l_1:.3f} m\n")

    # ── Varredura individual: flambagem lateral ───────────────
    print("── Varredura: Flambagem Lateral ──\n")
    df_fl = varrer_flambagem_lateral(
        mat=mat, L=L, g_k=g_k, q_k=q_k, l_1=l_1,
        h0_range=(0.60, 1.30, 0.10),
        alpha_range=(3.0, 8.5, 0.5),
        b_range=(0.14, 0.28, 0.02),
    )
    relatorio_flambagem(df_fl, n=10)

    # ── Varredura combinada ───────────────────────────────────
    print("\n── Varredura Combinada: Cumeeira + Flambagem Lateral ──\n")
    df_comb = varrer_combinado(
        mat=mat, L=L, g_k=g_k, q_k=q_k, l_1=l_1,
        h0_range=(0.60, 1.30, 0.10),
        alpha_range=(3.0, 8.5, 0.5),
        b_range=(0.14, 0.28, 0.02),
    )
    relatorio_combinado(df_comb, n=20)