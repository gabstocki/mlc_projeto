"""
checks/elu/estabilidade_global.py — Estabilidade global do pórtico.

Objetivo
---------
Verificar se efeitos de 2.ª ordem (P-Δ) e imperfeições geométricas globais
(forças horizontais nocionais) exigem análise de 2.ª ordem, ou se a
análise de 1.ª ordem adotada (Castigliano biarticulada) é suficiente.

Contexto estrutural
-------------------
  · Viga MLC biarticulada (rótulas só nos apoios) + pilares biarticulados.
  · Empuxo H de 1.ª ordem vai direto à fundação (não gera pórtico
    rígido com momentos de nó).
  · Estabilidade de **barra** já coberta por EC5 §6.3.2 (k_c) e §6.3.3
    (k_crit) na viga e nos pilares.
  · Esta verificação cobre a **escala do sistema** (global).

Referências
-----------
  EN 1995-1-1 §5.4.2 / §5.4.3  — análise estrutural (1.ª vs 2.ª ordem)
  EN 1995-1-1 §6.3.2           — imperfeições de barra (via k_c)
  EN 1993-1-1 §5.2.1           — critério α_cr (analogia de pórticos;
                                  EC5 não fixa limiar numérico global)
  EN 1993-1-1 §5.3.2           — forças nocionais (φ = φ0·α_h·α_m)
  EN 1990                      — combinações de ações

Critérios de dispensa de 2.ª ordem **global** (adotados)
---------------------------------------------------------
  0) Sistema **non-sway** no plano do pórtico: biarticulado, H de 1.ª ordem
     vai à fundação (sem pórtico rígido com momentos de nó). O P-Δ de
     «piso» (sway frame) não se aplica; a 2.ª ordem de **barra** está em
     EC5 §6.3.2 (k_c) e §6.3.3 (k_crit).
  1) w_Ed / f_c ≤ 0,05 → abaixamento do freche centroidal desprezável
     (não-linearidade geométrica do arco).
  2) H_imp / H_Ed ≤ 0,10 → força nocional coberta pelo empuxo de 1.ª ordem.
  3) α_cr,arco ≥ 10 (modo de arco, L_ef ≈ L/2 na meia-água) — informativo
     de estabilidade de sistema; se < 10, regista-se k_II e alerta.

Nota: α_cr de **barra** com L_ef = L (viga) ou H (pilar) pode ser < 10;
isso **não** obriga análise global de 2.ª ordem — obriga (e já existe)
a verificação com k_c. Reporta-se como informativo.
"""

from __future__ import annotations

import math

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.loads     import Carregamentos
from mlc_projeto.core.validacao import DominioInvalidoError


# EN 1993-1-1 §5.3.2 — imperfeição global (força nocional)
PHI_0 = 1.0 / 200.0

# Limiares de projeto
ALPHA_CR_MIN = 10.0     # EN 1993-1-1 §5.2.1(3) — análise elástica
# EN 1993-1-1 §5.2.2(5)B — o método da amplificação de sway (k_II) só é
# admissível para α_cr ≥ 3,0; abaixo disso exige-se análise de 2.ª ordem
# rigorosa (GNL), fora do escopo deste pipeline.
ALPHA_CR_AMPLIF_MIN = 3.0
W_OVER_F_MAX = 0.05     # abaixamento relativo do freche
H_IMP_OVER_H_MAX = 0.10 # nocional face ao empuxo de cálculo


def forca_nocional(
    V_Ed_kN: float,
    h_m: float,
    m_colunas: int = 2,
) -> dict:
    """
    Força horizontal nocional — EN 1993-1-1 §5.3.2 (analogia).

        φ = φ0 · α_h · α_m
        φ0 = 1/200
        α_h = 2/√h   mas  2/3 ≤ α_h ≤ 1
        α_m = √[0,5·(1 + 1/m)]
        H_Ed,imp = φ · V_Ed

    V_Ed = soma das reações verticais do pórtico (2·R_v).
    h    = altura do piso / pé-direito (m).
    m    = número de colunas no alinhamento considerado.
    """
    if h_m <= 0:
        raise ValueError("h_m deve ser > 0")
    m = max(1, int(m_colunas))

    alpha_h = min(1.0, max(2.0 / 3.0, 2.0 / math.sqrt(h_m)))
    alpha_m = math.sqrt(0.5 * (1.0 + 1.0 / m))
    phi = PHI_0 * alpha_h * alpha_m
    H_imp = phi * abs(V_Ed_kN)

    return {
        "phi_0":     PHI_0,
        "alpha_h":   round(alpha_h, 4),
        "alpha_m":   round(alpha_m, 4),
        "phi":       round(phi, 6),
        "V_Ed_kN":   round(V_Ed_kN, 3),
        "H_imp_kN":  round(H_imp, 3),
        "h_m":       h_m,
        "m_colunas": m,
        "norma":     "EN 1993-1-1 §5.3.2 (φ global, analogia para MLC)",
    }


def alpha_cr_membro(
    mat: GlulamMaterial,
    b: float,
    h: float,
    L_ef_m: float,
    N_Ed_kN: float,
) -> dict:
    """
    Fator de carga crítica de barra comprimida (Euler, E_0,05).

        N_cr = π² · E_0,05 · I / L_ef²
        α_cr = N_cr / N_Ed

    Usa E_0,05 (fractil 5%) — coerente com flambagem EC5 §6.3.2.
    """
    I = b * h ** 3 / 12.0
    E = mat.E0_05  # Pa
    # F-02: NÃO devolver 1e99 ("infinitamente estável"). Com N_Ed = 0 a razão
    # F_cr/F_Ed é INDETERMINADA, não infinita-favorável; o chamador tem de saber
    # distinguir os dois casos e nunca converter isto em aprovação.
    if L_ef_m <= 0 or N_Ed_kN == 0:
        return {
            "N_cr_kN": math.inf, "alpha_cr": math.inf, "I_m4": I,
            "L_ef_m": L_ef_m, "N_Ed_kN": N_Ed_kN,
            "indeterminado": True,
        }
    N_cr_N = (math.pi ** 2) * E * I / (L_ef_m ** 2)
    N_cr_kN = N_cr_N / 1e3
    alpha = N_cr_kN / abs(N_Ed_kN)
    return {
        "N_cr_kN":  round(N_cr_kN, 1),
        "alpha_cr": round(alpha, 2),
        "I_m4":     I,
        "L_ef_m":   L_ef_m,
        "N_Ed_kN":  round(N_Ed_kN, 3),
        "E0_05_MPa": round(E / 1e6, 0),
        "indeterminado": False,
    }


def alpha_cr_sistema(
    K_lat_kNpm: float,
    h_m: float,
    V_Ed_kN: float,
) -> dict:
    """
    Fator de carga crítica do SISTEMA numa direção — EN 1993-1-1 §5.2.1(4)B.

    Achado F-02 da auditoria adversarial v2
    ---------------------------------------
    O α_cr que era comparado com o limiar 10 era a carga de Euler de UMA BARRA
    (L_ef = L/2, seção h0) dividida pelo esforço normal da VIGA — normal que o
    modelo adotado (Opção B, H = 0) força a ~zero. A métrica crescia quando a
    hipótese que devia testar era adotada, e passava sempre.

    O α_cr que a norma define é o do modo de DESLOCAMENTO LATERAL do sistema:

        Eq. (5.2):   α_cr = (H_Ed / V_Ed) · (h / δ_H,Ed)

    Num sistema elástico de rigidez lateral K (δ_H,Ed = H_Ed / K), o quociente
    H_Ed/δ_H,Ed é a própria rigidez, e a expressão reduz-se a

        α_cr = K · h / V_Ed

    independente do nível de carga horizontal — como tem de ser.

    Aqui K é a soma das rigidezes horizontais dos painéis de contraventamento
    ATIVOS na direção considerada (`verifica_painel_vertical → C_h_kNpm`), h o
    pé-direito e V_Ed a carga vertical de cálculo TOTAL suportada pelos pilares
    estabilizados por esses painéis.

    Regimes (EN 1993-1-1 §5.2.1(3) e §5.2.2(5)B):
        α_cr ≥ 10          → "1a_ordem"          (2.ª ordem dispensável)
        3 ≤ α_cr < 10      → "amplificar"        (k_II = 1/(1 − 1/α_cr))
        0 < α_cr < 3       → "2a_ordem_rigorosa" (amplificação não admissível)
        K ≤ 0              → "mecanismo"         (α_cr = 0, k_II = ∞)

    Args:
        K_lat_kNpm : rigidez lateral total da direção (kN/m)
        h_m        : altura sobre a qual o deslocamento se desenvolve (m)
        V_Ed_kN    : carga vertical de cálculo total estabilizada (kN)

    Returns:
        dict com α_cr, k_II, regime e os dados de entrada.
    """
    if h_m <= 0:
        raise ValueError("h_m deve ser > 0")
    if V_Ed_kN <= 0:
        raise ValueError("V_Ed_kN deve ser > 0 (não há sway sem carga vertical)")
    K = float(K_lat_kNpm)
    if K <= 0.0:
        return {
            "alpha_cr": 0.0, "k_II": math.inf, "regime": "mecanismo",
            "K_lat_kNpm": K, "h_m": h_m, "V_Ed_kN": V_Ed_kN,
            "norma": "EN 1993-1-1 §5.2.1(4)B Eq. (5.2)",
        }

    alpha = K * h_m / abs(V_Ed_kN)
    if alpha >= ALPHA_CR_MIN:
        regime = "1a_ordem"
    elif alpha >= ALPHA_CR_AMPLIF_MIN:
        regime = "amplificar"
    else:
        regime = "2a_ordem_rigorosa"

    return {
        "alpha_cr":   alpha,
        "k_II":       amplificacao_segunda_ordem(alpha),
        "regime":     regime,
        "K_lat_kNpm": round(K, 1),
        "h_m":        h_m,
        "V_Ed_kN":    round(abs(V_Ed_kN), 1),
        "norma":      "EN 1993-1-1 §5.2.1(4)B Eq. (5.2) | §5.2.2(5)B (k_II)",
    }


def amplificacao_segunda_ordem(alpha_cr: float) -> float:
    """
    Fator de amplificação de 1.ª → 2.ª ordem (elástico).

        k_II = 1 / (1 − 1/α_cr)   para α_cr > 1
    """
    if alpha_cr <= 1.0:
        return float("inf")
    return 1.0 / (1.0 - 1.0 / alpha_cr)


def verificar_estabilidade_global(
    geo: GeometriaViga,
    mat: GlulamMaterial,
    load: Carregamentos,
    H_pilar_m: float = 7.0,
    b_pilar: float = 0.22,
    h_pilar: float = 0.26,
    w_Ed_mm: float | None = None,
    m_colunas: int = 2,
    alpha_cr_min: float = ALPHA_CR_MIN,
    contravento_vertical_ok: bool | None = None,
    contravento_transversal_ok: bool | None = None,
    nocional_no_contraventamento: bool = False,
    K_lat_long_kNpm: float | None = None,
    K_lat_transv_kNpm: float | None = None,
    V_Ed_total_kN: float | None = None,
    amplificacao_aplicada: bool = False,
) -> dict:
    """
    Verificação completa de estabilidade global do pórtico biarticulado.

    Args:
        geo, mat, load : modelo de projeto
        H_pilar_m      : pé-direito (m)
        b_pilar, h_pilar : seção do pilar lateral
        w_Ed_mm        : flecha vertical ELU no vão (mm); se None, estima
                         a partir de ELS_S1 × γ (ordem de grandeza)
        m_colunas      : colunas por pórtico (2 = biarticulado simples)
        alpha_cr_min   : limiar de dispensa (default 10)
        contravento_vertical_ok : estabilidade lateral LONGITUDINAL (issue 14).
        contravento_transversal_ok : estabilidade lateral TRANSVERSAL (issue 31).
                         Para cada direção: None → sistema não informado
                         (mecanismo, α_cr,sway → 0); True → verificado (non-sway);
                         False → não conforme (mecanismo sway). O sistema só é
                         non-sway se AMBAS as direções forem True.

    Returns:
        dict com nocionais, α_cr, critérios e ok global
    """
    # Resíduo do [F-06]. Esta verificação usa TRÊS medidas com envelopes
    # diferentes e é preciso separá-las, senão uma delas fica refém do seletor
    # de outra:
    #   · V_portal = 2·R_v alimenta a nocional  → maximiza-se a carga vertical;
    #   · H_Ed é o denominador da razão de dispensa H_imp/H_Ed → o caso adverso
    #     é uma RAZÃO entre duas grandezas da MESMA combinação — avalia-se
    #     combinação a combinação e retém-se a razão máxima;
    #   · N_viga entra em α_cr como ΣN_Ed → maximiza-se.
    # Lia-se tudo da combinação de max|M|, que não é o envelope de nenhuma das
    # três (EN 1990 §6.4.3.2).
    #
    # A razão MERECE o cuidado extra: tomar o H mínimo de uma combinação e o
    # H_imp de outra seria misturar estados — exatamente o vício que o envelope
    # existe para evitar. Cada combinação é um estado coerente; a razão calcula-se
    # dentro dele.
    gov, R_v = load.envelope_ELU(lambda c: abs(float(c.V_max_kN)))
    _, N_viga = load.envelope_ELU(lambda c: abs(float(c.N_viga_kN)))
    V_portal = 2.0 * R_v  # dois apoios

    # ── 1) Forças nocionais ───────────────────────────────────
    noc = forca_nocional(V_portal, H_pilar_m, m_colunas=m_colunas)
    H_imp = noc["H_imp_kN"]

    def _razao_imp(comb) -> float:
        """H_imp/H_Ed DENTRO de uma combinação — ambos do mesmo estado."""
        h_i = forca_nocional(2.0 * abs(float(comb.V_max_kN)), H_pilar_m,
                             m_colunas=m_colunas)["H_imp_kN"]
        h_e = abs(float(comb.H_kN))
        if h_e > 1e-9:
            return h_i / h_e
        return math.inf if h_i > 1e-9 else 0.0

    comb_imp, ratio_por_combinacao = load.envelope_ELU(_razao_imp)
    # H_Ed continua a ser o empuxo MÁXIMO — é o que alimenta H_gov e o que o
    # memorial publica como empuxo de projeto. O H da combinação que governa a
    # RAZÃO vai à parte, para rastreabilidade: são perguntas diferentes.
    _, H_Ed = load.envelope_ELU(lambda c: abs(float(c.H_kN)))
    H_Ed_ratio = abs(float(comb_imp.H_kN))
    # AUD-008 / AUD-006: com H_Ed = 0 a razão H_imp/H_Ed é indefinida, NÃO nula.
    # O fallback original (`else 0.0`) convertia a pior condição possível em
    # aprovação automática.
    #
    # Mas a razão nunca foi o critério certo: ela é apenas um teste de DISPENSA
    # ("a nocional é coberta pelo empuxo de 1.ª ordem"). O critério correto,
    # que a própria auditoria pede em AUD-008, é verificar a força nocional
    # como CASO DE CARGA EXPLÍCITO no sistema resistente lateral — que é o que
    # checks/elu/contraventamento_transversal.py faz (arrasto θ=90° + H_imp).
    #
    # `nocional_no_contraventamento` declara que a nocional entrou, verificada,
    # no caminho lateral. O default é False para preservar a proteção de
    # AUD-008 quando o chamador não o declara.
    ratio_imp = ratio_por_combinacao

    ok_imp = (
        ratio_imp <= H_IMP_OVER_H_MAX          # dispensa pelo empuxo de 1.ª ordem
        or bool(nocional_no_contraventamento)  # ou caminho lateral verificado
    )
    # H de projeto a reter (empuxo 1.ª ordem já >> nocional)
    H_gov = max(H_Ed, H_imp)

    # ── 2) Classificação do sistema (sway vs non-sway) ────────
    # Pilares biarticulados (topo e base) + ligações viga-pilar rotuladas:
    # NÃO há ação de pórtico. A estabilidade lateral depende de sistemas de
    # contraventamento nas DUAS direções. Sem eles, o pórtico é um MECANISMO
    # (α_cr,sway → 0). O α_cr de arco (passo 4) é o modo de snap-through do arco
    # abatido — NÃO é o modo de deslocamento lateral (sway).
    #   · Longitudinal (// cumeeira): contraventamento vertical (issue 14) →
    #     contravento_vertical_ok  [checks/elu/contraventamento_vertical.py]
    #   · Transversal (⊥ cumeeira, plano do pórtico): diafragma + frontões
    #     (issue 31) → contravento_transversal_ok
    #     [checks/elu/contraventamento_transversal.py]
    # O sistema só é non-sway se AMBAS as direções tiverem sistema verificado.
    def _classifica(flag, direcao, issue):
        if flag is None:
            return False, (f"{direcao}: sistema lateral não informado → "
                           f"mecanismo sway (α_cr,sway → 0). Ver {issue}.")
        if flag:
            return True, (f"{direcao}: estabilidade lateral verificada "
                          f"(non-sway). Ver {issue}.")
        return False, (f"{direcao}: contraventamento NÃO conforme → mecanismo "
                       f"sway. Rever {issue}.")

    non_sway_long, nota_long = _classifica(
        contravento_vertical_ok, "Longitudinal (// cumeeira)", "issue 14")
    non_sway_transv, nota_direcao_transversal = _classifica(
        contravento_transversal_ok, "Transversal (⊥ cumeeira)", "issue 31")

    sistema_non_sway = non_sway_long and non_sway_transv
    alpha_cr_sway = float("inf") if sistema_non_sway else 0.0
    nota_sistema = (
        "Sistema non-sway nas duas direções (contraventamento vertical e "
        "transversal verificados)."
        if sistema_non_sway
        else "Sistema NÃO indeslocável: " + " | ".join(
            n for n, ok in [(nota_long, non_sway_long),
                            (nota_direcao_transversal, non_sway_transv)]
            if not ok
        )
    )

    # ── 3) α_cr de barra (INFORMATIVO — coberto por k_c) ───────
    h0 = geo.h0
    acr_viga = alpha_cr_membro(mat, geo.b, h0, geo.L, N_viga)
    acr_viga_ap = alpha_cr_membro(mat, geo.b, geo.h_ap, geo.L, N_viga)
    # Pilar: I mínima
    I_y = b_pilar * h_pilar ** 3 / 12.0
    I_z = h_pilar * b_pilar ** 3 / 12.0
    if I_z <= I_y:
        acr_pilar = alpha_cr_membro(mat, h_pilar, b_pilar, H_pilar_m, R_v)
    else:
        acr_pilar = alpha_cr_membro(mat, b_pilar, h_pilar, H_pilar_m, R_v)

    alpha_cr_barra = min(
        acr_viga["alpha_cr"],
        acr_viga_ap["alpha_cr"],
        acr_pilar["alpha_cr"],
    )

    # ── 4a) α_cr do modo de ARCO (snap-through) — INFORMATIVO ──
    # NÃO é o modo de deslocamento lateral e, com H = 0 (Opção B), o seu
    # denominador N_viga tende a zero — F-02: nunca pode ser o critério de
    # dispensa de 2.ª ordem.
    L_ef_arco = geo.L / 2.0
    acr_arco = alpha_cr_membro(mat, geo.b, h0, L_ef_arco, N_viga)
    alpha_cr_arco = acr_arco["alpha_cr"]

    # ── 4b) α_cr de SISTEMA por direção — EN 1993-1-1 Eq. (5.2) ─
    V_Ed_sist = float(V_Ed_total_kN) if V_Ed_total_kN is not None else None
    acr_long = acr_transv = None
    if V_Ed_sist is not None and V_Ed_sist > 0:
        if K_lat_long_kNpm is not None:
            acr_long = alpha_cr_sistema(K_lat_long_kNpm, H_pilar_m, V_Ed_sist)
        if K_lat_transv_kNpm is not None:
            acr_transv = alpha_cr_sistema(K_lat_transv_kNpm, H_pilar_m, V_Ed_sist)

    if acr_long is not None and acr_transv is not None:
        if acr_long["alpha_cr"] <= acr_transv["alpha_cr"]:
            acr_gov, direcao_critica = acr_long, "longitudinal"
        else:
            acr_gov, direcao_critica = acr_transv, "transversal"
    elif acr_long is not None:
        acr_gov, direcao_critica = acr_long, "longitudinal"
    elif acr_transv is not None:
        acr_gov, direcao_critica = acr_transv, "transversal"
    else:
        acr_gov, direcao_critica = None, None

    if acr_gov is None:
        # Dado ausente NÃO é aprovação (F-02).
        alpha_cr_sist = None
        alpha_cr = 0.0
        regime_acr = "nao_determinado"
        ok_acr = False
        k_II = float("inf")
    else:
        alpha_cr_sist = acr_gov["alpha_cr"]
        alpha_cr = alpha_cr_sist
        regime_acr = acr_gov["regime"]
        ok_acr = alpha_cr >= alpha_cr_min
        k_II = acr_gov["k_II"]

    # ── 5) Geometria do arco — abaixamento do freche ──────────
    f_c = (geo.h_ap - geo.h0) / 2.0  # m — freche do eixo centroidal
    if w_Ed_mm is None:
        # Achado [S-4]. Estava aqui um `except Exception: w_char = 5.0` — um
        # número inventado que entrava no critério de abaixamento do freche
        # como se fosse resultado. Se o ELS falhar, a estabilidade geométrica
        # não é verificável, e não-verificável nunca é aprovado. O 5,0 mm nem
        # sequer era conservador: era arbitrário.
        from mlc_projeto.checks.els.deflection_els import verificar_ELS
        els = verificar_ELS(geo, mat, load)
        w_char = els.get("w_S1_mm", els.get("w_fin_mm"))
        if w_char is None or not math.isfinite(float(w_char)):
            raise DominioInvalidoError(
                "verificar_ELS não devolveu flecha característica (w_S1_mm nem "
                "w_fin_mm): sem ela o abaixamento do freche não é verificável. "
                "Passe `w_Ed_mm` explicitamente ou corrija o ELS — não há "
                "valor por omissão que possa substituir um cálculo em falta."
            )
        w_Ed_mm = float(w_char) * 1.5  # majoração aproximada para ELU
    w_Ed_m = w_Ed_mm / 1000.0
    w_over_f = w_Ed_m / f_c if f_c > 0 else 999.0
    ok_geom = w_over_f <= W_OVER_F_MAX
    if w_over_f < 1.0:
        k_H_geom = 1.0 / (1.0 - w_over_f)
    else:
        k_H_geom = float("inf")

    # ── 6) P-Δ no pilar (fora de prumo nocional) ──────────────
    e_0 = noc["phi"] * H_pilar_m  # m
    M_imp_pilar = R_v * e_0       # kN·m
    W_p = b_pilar * h_pilar ** 2 / 6.0
    sigma_m_imp = (M_imp_pilar * 1e3) / W_p if W_p > 0 else 0.0
    eta_M_imp = sigma_m_imp / mat.f_m_d if mat.f_m_d > 0 else 0.0

    # ── 7) Agregação ──────────────────────────────────────────
    # Pré-requisito: estabilidade LATERAL assegurada (non-sway) por um sistema
    # de contraventamento vertical. Sem ele o sistema é um mecanismo e a
    # dispensa de 2.ª ordem não se coloca (não há caminho de carga lateral).
    # Verificados então: nocional + geometria do freche + α_cr de arco
    # (snap-through). α_cr,barra é informativo (coberto por k_c no ELU).
    if not sistema_non_sway:
        ok = False
        conclusao = (
            "Estabilidade lateral NÃO demonstrada (mecanismo sway, α_cr,sway→0): "
            + nota_sistema
            + " Prover/verificar o(s) sistema(s) de contraventamento antes de "
            "dispensar a 2.ª ordem."
        )
        metodo = "instavel_lateralmente"
    elif regime_acr == "nao_determinado":
        # F-02: sem rigidez lateral declarada não há α_cr de sistema; a ausência
        # de dado nunca é aprovação.
        ok = False
        conclusao = (
            "α_cr de SISTEMA não determinado: a rigidez lateral dos painéis "
            "(K_lat_long_kNpm / K_lat_transv_kNpm) e a carga vertical total "
            "(V_Ed_total_kN) não foram informadas. Sem elas o modo de sway não "
            "é quantificável e a 2.ª ordem não pode ser dispensada "
            "(EN 1993-1-1 §5.2.1(4)B)."
        )
        metodo = "alpha_cr_nao_determinado"
    else:
        ok_2a_ordem = (
            regime_acr == "1a_ordem"
            or (regime_acr == "amplificar" and amplificacao_aplicada)
        )
        ok = ok_geom and ok_imp and ok_2a_ordem
        if ok and regime_acr == "1a_ordem":
            conclusao = (
                f"Análise de 1.ª ordem suficiente: sistema non-sway nas duas "
                f"direções (contraventamento vertical §14 + transversal §31 "
                f"verificados), α_cr,sistema={alpha_cr:.1f} ≥ {alpha_cr_min:.0f} "
                f"(direção crítica: {direcao_critica}), abaixamento do freche "
                f"desprezável e H_imp≪H_Ed. P-Δ global dispensado. 2.ª ordem de "
                f"barra coberta por k_c (EC5 §6.3.2)."
            )
            metodo = "1a_ordem"
        elif ok:
            conclusao = (
                f"α_cr,sistema={alpha_cr:.2f} < {alpha_cr_min:.0f} na direção "
                f"{direcao_critica}: a 2.ª ordem NÃO é dispensável, mas os "
                f"efeitos laterais foram amplificados por k_II={k_II:.3f} "
                f"(EN 1993-1-1 §5.2.2(5)B, admissível para α_cr ≥ "
                f"{ALPHA_CR_AMPLIF_MIN:.0f}). Análise de 1.ª ordem AMPLIFICADA."
            )
            metodo = "1a_ordem_amplificada"
        else:
            motivos = []
            if regime_acr == "2a_ordem_rigorosa":
                motivos.append(
                    f"α_cr,sistema={alpha_cr:.2f}<{ALPHA_CR_AMPLIF_MIN:.0f} "
                    f"({direcao_critica}) — amplificação k_II NÃO admissível"
                )
            elif regime_acr == "amplificar":
                motivos.append(
                    f"α_cr,sistema={alpha_cr:.2f}<{alpha_cr_min:.0f} "
                    f"({direcao_critica}) e a amplificação k_II={k_II:.3f} NÃO "
                    f"foi declarada aplicada no contraventamento"
                )
            if not ok_geom:
                motivos.append(f"w/f_c={w_over_f:.4f}")
            if not ok_imp:
                motivos.append(
                    "H_Ed=0 com H_imp>0 e a força nocional NÃO foi declarada "
                    "verificada no caminho lateral (AUD-008)"
                    if math.isinf(ratio_imp)
                    else f"H_imp/H={ratio_imp:.3f}"
                )
            conclusao = (
                "Efeitos de 2.ª ordem NÃO dispensáveis ("
                + "; ".join(motivos)
                + "). Reanalisar com amplificação k_II ou GNL."
            )
            metodo = "2a_ordem_requerida"

    # η do critério de dispensa (não confundir com η de seção)
    eta_acr = alpha_cr_min / alpha_cr if alpha_cr > 0 else 999.0
    if metodo == "1a_ordem_amplificada":
        # Amplificação aplicada: o critério deixa de reprovar por α_cr — a
        # utilização passa a ser a do contraventamento já amplificado.
        eta_acr = 0.0
    eta_geom = w_over_f / W_OVER_F_MAX if W_OVER_F_MAX > 0 else 999.0
    if nocional_no_contraventamento:
        # A nocional é resistida no contraventamento; a razão face a H_Ed deixa
        # de ser um critério de reprovação (η do contraventamento é que manda).
        eta_imp = 0.0
    elif H_IMP_OVER_H_MAX > 0:
        eta_imp = ratio_imp / H_IMP_OVER_H_MAX
    else:
        eta_imp = 999.0
    eta_gov = max(eta_acr, eta_geom, eta_imp)

    return {
        "sistema": "biarticulada MLC — estabilidade global",
        "norma": (
            "EN 1995-1-1 §5.4.2+§6.3.2 | "
            "EN 1993-1-1 §5.2.1+§5.3.2 (α_cr, φ analogia)"
        ),
        # Esforços de referência
        "comb":          gov.nome,
        "R_v_kN":        round(R_v, 3),
        "V_portal_kN":   round(V_portal, 3),
        "H_Ed_kN":       round(H_Ed, 3),
        "H_gov_kN":      round(H_gov, 3),
        "N_viga_kN":     round(N_viga, 3),
        "f_c_m":         round(f_c, 4),
        "H_pilar_m":     H_pilar_m,
        # Nocionais
        "phi":           noc["phi"],
        "alpha_h":       noc["alpha_h"],
        "alpha_m":       noc["alpha_m"],
        "H_imp_kN":      H_imp,
        "H_imp_over_H":  round(ratio_imp, 5),
        # Rastreabilidade do envelope da razão (resíduo do F-06): qual combinação
        # a governa e com que empuxo — que NÃO é o empuxo máximo de projeto.
        "comb_H_imp_over_H": comb_imp.nome,
        "H_Ed_da_razao_kN":  round(H_Ed_ratio, 3),
        "ok_nocional":   ok_imp,
        "nocional_no_contraventamento": bool(nocional_no_contraventamento),
        "criterio_nocional": (
            "caso de carga explícito no contraventamento lateral"
            if nocional_no_contraventamento and not (ratio_imp <= H_IMP_OVER_H_MAX)
            else "dispensa por H_imp/H_Ed ≤ %.2f" % H_IMP_OVER_H_MAX
        ),
        "lim_H_imp":     H_IMP_OVER_H_MAX,
        # Classificação (sway / non-sway) — issues 14 (long.) e 31 (transv.)
        "sistema_non_sway": sistema_non_sway,
        "non_sway_long": non_sway_long,
        "non_sway_transv": non_sway_transv,
        "contravento_vertical_ok": contravento_vertical_ok,
        "contravento_transversal_ok": contravento_transversal_ok,
        "alpha_cr_sway": (
            round(alpha_cr_sway, 2) if math.isfinite(alpha_cr_sway) else 1e6
        ),
        "nota_sistema":  nota_sistema,
        "nota_direcao_transversal": nota_direcao_transversal,
        # α_cr de SISTEMA (gate) — EN 1993-1-1 Eq. (5.2), achado F-02
        "alpha_cr":      round(alpha_cr, 2),
        "alpha_cr_min":  alpha_cr_min,
        "alpha_cr_amplif_min": ALPHA_CR_AMPLIF_MIN,
        "alpha_cr_sistema": (
            None if alpha_cr_sist is None else round(alpha_cr_sist, 2)
        ),
        "alpha_cr_long": (
            None if acr_long is None else round(acr_long["alpha_cr"], 2)
        ),
        "alpha_cr_transv": (
            None if acr_transv is None else round(acr_transv["alpha_cr"], 2)
        ),
        "K_lat_long_kNpm":   K_lat_long_kNpm,
        "K_lat_transv_kNpm": K_lat_transv_kNpm,
        "V_Ed_total_kN":     V_Ed_sist,
        "direcao_critica":   direcao_critica,
        "regime_alpha_cr":   regime_acr,
        "amplificacao_aplicada": bool(amplificacao_aplicada),
        # α_cr do modo de arco e de barra — INFORMATIVOS
        "alpha_cr_arco": round(alpha_cr_arco, 2),
        "L_ef_arco_m":   L_ef_arco,
        "alpha_cr_barra": round(alpha_cr_barra, 2),
        "alpha_cr_viga_h0": acr_viga["alpha_cr"],
        "alpha_cr_viga_ap": acr_viga_ap["alpha_cr"],
        "alpha_cr_pilar":   acr_pilar["alpha_cr"],
        "N_cr_viga_kN":  acr_viga["N_cr_kN"],
        "N_cr_arco_kN":  acr_arco["N_cr_kN"],
        "N_cr_pilar_kN": acr_pilar["N_cr_kN"],
        "k_II":          round(k_II, 4) if math.isfinite(k_II) else 1e6,
        # k_II BRUTO (acima) vs k_II EFETIVAMENTE APLICADO: com α_cr ≥ 10 a
        # norma permite desprezar a amplificação, e nada é amplificado.
        "k_II_aplicado": (
            round(k_II, 4)
            if (regime_acr == "amplificar" and amplificacao_aplicada
                and math.isfinite(k_II))
            else 1.0
        ),
        "ok_alpha_cr":   ok_acr,
        "nota_alpha_cr_barra": (
            "α_cr de barra (L_ef=L ou H) é informativo; "
            "valores <10 são cobertos por k_c no ELU (EC5 §6.3.2), "
            "não exigem por si análise global de 2.ª ordem."
        ),
        # Geometria arco
        "w_Ed_mm":       round(w_Ed_mm, 3),
        "w_over_f":      round(w_over_f, 5),
        "lim_w_over_f":  W_OVER_F_MAX,
        "k_H_geom":      round(k_H_geom, 4) if k_H_geom < 1e6 else 1e6,
        "ok_geometria":  ok_geom,
        # P-Δ pilar (imperfeição)
        "e_0_mm":        round(e_0 * 1000, 2),
        "M_imp_pilar_kNm": round(M_imp_pilar, 4),
        "eta_M_imp_pilar": round(eta_M_imp, 4),
        # Resultado
        "metodo_analise": metodo,
        "conclusao":     conclusao,
        "eta":           round(min(eta_gov, 9.99), 4),
        "ok":            ok,
        "nota": (
            "Empuxo H de 1.ª ordem (Castigliano) já é o esforço horizontal "
            "dominante; a força nocional e o P-Δ global são tipicamente "
            "desprezáveis em pórticos baixos biarticulados com H elevado. "
            "Estabilidade de barra: EC5 §6.3.2/§6.3.3 (pipeline ELU)."
        ),
    }


def relatorio_estabilidade_global(res: dict) -> None:
    """Imprime relatório da verificação global."""
    print("=" * 68)
    print("  ESTABILIDADE GLOBAL — P-Δ / NOCIONAIS / α_cr")
    print(f"  {res['norma']}")
    print("=" * 68)
    print(f"  Combinação : {res['comb']}")
    print(f"  H_Ed       = {res['H_Ed_kN']:.1f} kN  (empuxo 1.ª ordem)")
    print(f"  V_portal   = {res['V_portal_kN']:.1f} kN  |  "
          f"N_viga = {res['N_viga_kN']:.1f} kN")
    print(f"  f_c        = {res['f_c_m']:.3f} m  (freche centroidal)")
    print()
    print("  ── Forças nocionais (EN 1993-1-1 §5.3.2) ──")
    print(f"    φ = {res['phi']:.5f}  "
          f"(α_h={res['alpha_h']:.3f}, α_m={res['alpha_m']:.3f})")
    print(f"    H_imp = {res['H_imp_kN']:.2f} kN  |  "
          f"H_imp/H_Ed = {res['H_imp_over_H']:.4f}  "
          f"(lim {res['lim_H_imp']:.2f})  "
          f"{'✓' if res['ok_nocional'] else '✗'}")
    print()
    print("  ── Sistema ──")
    print(f"    non-sway = {res.get('sistema_non_sway', True)}")
    print(f"    {res.get('nota_sistema', '')}")
    print()
    print("  ── Fator de carga crítica α_cr ──")
    print(f"    α_cr,arco (L_ef=L/2) = {res['alpha_cr']:.1f}  "
          f"(N_cr={res.get('N_cr_arco_kN', 0):.0f} kN)  "
          f"(mín. {res['alpha_cr_min']:.0f})  "
          f"{'✓' if res['ok_alpha_cr'] else '✗'}")
    print(f"    k_II,arco = {res['k_II']:.4f}")
    print(f"    α_cr,barra (info) = {res.get('alpha_cr_barra', 0):.1f}  "
          f"[viga h0={res['alpha_cr_viga_h0']:.1f}, "
          f"ap={res['alpha_cr_viga_ap']:.1f}, "
          f"pilar={res['alpha_cr_pilar']:.1f}]")
    print(f"    → {res.get('nota_alpha_cr_barra', '')}")
    print()
    print("  ── Geometria do arco (abaixamento do freche) ──")
    print(f"    w_Ed = {res['w_Ed_mm']:.2f} mm  |  "
          f"w/f_c = {res['w_over_f']:.5f}  "
          f"(lim {res['lim_w_over_f']:.2f})  "
          f"{'✓' if res['ok_geometria'] else '✗'}")
    print(f"    k_H,geom ≈ {res['k_H_geom']:.4f}")
    print()
    print("  ── Imperfeição no pilar (P-Δ local) ──")
    print(f"    e_0 = {res['e_0_mm']:.2f} mm  |  "
          f"M_imp = {res['M_imp_pilar_kNm']:.3f} kN·m  |  "
          f"η_M ≈ {res['eta_M_imp_pilar']:.4f}")
    print()
    ok = "✓" if res["ok"] else "✗"
    print(f"  {ok} Método: {res['metodo_analise']}  |  η_critério = {res['eta']:.4f}")
    print(f"  → {res['conclusao']}")
    print("=" * 68)
