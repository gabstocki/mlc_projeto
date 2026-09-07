"""
checks/elu/contraventamento_vertical.py — Contraventamento vertical e de frontões.

Objetivo (issue 14)
-------------------
O contraventamento da COBERTURA (checks/elu/contraventamento.py, EC5 §9.2.5)
estabiliza as vigas e coleta a força lateral no plano do telhado, entregando-a
como reação R_ext às baías de extremidade. Falta, porém, o sistema que leva essa
reação do nível da cobertura **até a fundação**: o contraventamento VERTICAL
(nas paredes) e o dos FRONTÕES.

Com pilares biarticulados no topo e na base e ligações viga-pilar rotuladas, o
pórtico não tem ação de pórtico (frame action): para carga lateral ele é um
mecanismo. A estabilidade lateral tem de vir de um sistema de contraventamento
com caminho de carga completo até a fundação — é isso que este módulo verifica
na direção LONGITUDINAL (θ=0°, // cumeeira), onde atua a força de vento
longitudinal (estrutura aberta).

Cadeia de forças (direção longitudinal, // cumeeira)
----------------------------------------------------
  Vento θ=0° na estrutura (pilares + fricção)   [core/wind.py]
       ↓  coletado pelo contraventamento da cobertura
  Reação R nas baías de extremidade             [checks/elu/contraventamento.py]
       ↓  contraventamento VERTICAL da parede (cruz de St. André)
  Diagonal tracionada (aço) + montante/pilar
       ↓
  FUNDAÇÃO  (reação horizontal H_base + arrancamento N_uplift)

Modelo de cálculo
-----------------
  · Painel de cruz de St. André: só a diagonal TRACIONADA é ativa (a
    comprimida flamba e é desprezada — hipótese usual para tirantes esbeltos).
  · Painel de altura H_col e largura b_baia; ângulo β com a horizontal,
    tan β = H_col / b_baia.
  · Para o cortante horizontal de projeto V_Ed no painel:
        N_diag = V_Ed / cos β                (tração na diagonal)
        H_base = V_Ed                        (→ fundação, cortante)
        N_uplift = V_Ed · tan β              (→ fundação/ancoragem, tração)
  · Resistência da diagonal — EN 1993-1-1 §6.2.3:
        N_t,Rd = A · f_y / γ_M0
  · Rigidez horizontal do painel (uma diagonal ativa):
        C_h = (E·A / L_diag) · cos²β
        δ = V_Ed / C_h ≤ H_col / drift_lim   (ELS do contraventamento)
  · Imperfeições globais — EN 1993-1-1 §5.3.2:
        φ = φ0·α_h·α_m ;  H_imp = φ · V_Ed,vertical  (somada à ação lateral)

Referências
-----------
  EN 1995-1-1 §5.4 (análise estrutural / estabilidade do sistema)
  EN 1993-1-1 §5.3.2 (imperfeições globais, φ) e §6.2.3 (tração da diagonal)
  NBR 6123 (força de vento θ=0°, via core/wind.py)
"""

from __future__ import annotations

import math

# Exceção checks→checks deliberada e documentada (análoga a creep.py →
# deflection.py e a contraventamento_transversal.py → este módulo): o α_cr de
# sistema desta direção depende da rigidez dos painéis aqui dimensionados, e a
# sua definição normativa (EN 1993-1-1 Eq. 5.2) vive em estabilidade_global.py.
from mlc_projeto.checks.elu.estabilidade_global import alpha_cr_sistema
from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.loads     import Carregamentos


# ── Constantes de aço (EN 1993-1-1) ───────────────────────────────────────────
E_ACO_MPA = 210_000.0    # MPa
GAMMA_M0  = 1.00         # EN 1993-1-1 §6.1

ACO = {
    "S235": {"f_y": 235.0, "f_u": 360.0},
    "S355": {"f_y": 355.0, "f_u": 510.0},
}

# Diâmetros comerciais de barra redonda (mm) — mesma sequência do tirante de base
D_COMERCIAL_MM = (
    12, 16, 20, 24, 27, 30, 33, 36, 39, 42, 45, 48, 52, 56, 60, 64,
)

# EN 1993-1-1 §5.3.2 — imperfeição global
PHI_0 = 1.0 / 200.0


# ── Geometria do painel de cruz ───────────────────────────────────────────────

def geometria_painel(H_col_m: float, b_baia_m: float) -> dict:
    """
    Geometria de um painel de cruz de St. André (parede vertical).

    β é o ângulo da diagonal com a HORIZONTAL: tan β = H_col / b_baia.
    """
    if H_col_m <= 0 or b_baia_m <= 0:
        raise ValueError("H_col_m e b_baia_m devem ser positivos")
    L = math.hypot(H_col_m, b_baia_m)
    return {
        "H_col_m":   H_col_m,
        "b_baia_m":  b_baia_m,
        "L_diag_m":  L,
        "beta_deg":  round(math.degrees(math.atan2(H_col_m, b_baia_m)), 2),
        "cos_beta":  b_baia_m / L,
        "sin_beta":  H_col_m / L,
        "tan_beta":  H_col_m / b_baia_m,
    }


# ── Força nocional (imperfeição global) — EN 1993-1-1 §5.3.2 ──────────────────

def forca_nocional(V_vertical_kN: float, h_m: float, m_colunas: int) -> dict:
    """
    Força horizontal nocional H_imp = φ·V — EN 1993-1-1 §5.3.2.

        φ = φ0 · α_h · α_m
        φ0 = 1/200 ;  α_h = 2/√h  (2/3 ≤ α_h ≤ 1) ;  α_m = √[0,5·(1 + 1/m)]
    """
    if h_m <= 0:
        raise ValueError("h_m deve ser > 0")
    m = max(1, int(m_colunas))
    alpha_h = min(1.0, max(2.0 / 3.0, 2.0 / math.sqrt(h_m)))
    alpha_m = math.sqrt(0.5 * (1.0 + 1.0 / m))
    phi = PHI_0 * alpha_h * alpha_m
    return {
        "phi":      round(phi, 6),
        "alpha_h":  round(alpha_h, 4),
        "alpha_m":  round(alpha_m, 4),
        "H_imp_kN": round(phi * abs(V_vertical_kN), 3),
    }


# ── Resistência da diagonal à tração — EN 1993-1-1 §6.2.3 ─────────────────────

def _n_t_rd_kN(d_mm: float, aco: str) -> float:
    if aco not in ACO:
        raise ValueError(f"Aço '{aco}' não reconhecido. Use {list(ACO)}")
    A_mm2 = math.pi * d_mm ** 2 / 4.0
    return A_mm2 * ACO[aco]["f_y"] / GAMMA_M0 / 1e3   # kN


def escolher_diametro(
    N_diag_kN: float,
    aco: str = "S235",
    eta_alvo: float = 0.90,
    d_lista: tuple[float, ...] = D_COMERCIAL_MM,
) -> float:
    """Menor diâmetro comercial com η = N_diag / N_t,Rd ≤ eta_alvo."""
    if N_diag_kN < 0:
        raise ValueError("N_diag_kN deve ser ≥ 0")
    if not 0 < eta_alvo <= 1.0:
        raise ValueError("eta_alvo deve estar em (0, 1]")
    N_req = N_diag_kN / eta_alvo
    for d in d_lista:
        if _n_t_rd_kN(d, aco) >= N_req - 1e-9:
            return float(d)
    return float(d_lista[-1])   # nenhum comercial serve → maior disponível (η>alvo)


# ── Verificação de um painel de contraventamento vertical ─────────────────────

def verifica_painel_vertical(
    V_Ed_kN:     float,
    H_col_m:     float,
    b_baia_m:    float,
    d_mm:        float,
    aco:         str = "S235",
    drift_lim:   float = 300.0,
) -> dict:
    """
    Verifica UM painel de cruz de St. André sob o cortante horizontal V_Ed.

    Só a diagonal tracionada é considerada ativa.

    Args:
        V_Ed_kN   : cortante horizontal de projeto no painel (kN)
        H_col_m   : altura do painel = pé-direito (m)
        b_baia_m  : largura da baía contraventada (m)
        d_mm      : diâmetro da diagonal (mm)
        aco       : "S235" | "S355"
        drift_lim : denominador do limite de deslocamento δ ≤ H_col/drift_lim

    Returns:
        dict com N_diag, resistência, caminho de carga à fundação, drift, η, ok
    """
    g = geometria_painel(H_col_m, b_baia_m)
    cos_b, tan_b = g["cos_beta"], g["tan_beta"]

    # Esforços
    N_diag = V_Ed_kN / cos_b                 # kN — tração na diagonal
    H_base = V_Ed_kN                         # kN — → fundação (cortante)
    N_uplift = V_Ed_kN * tan_b               # kN — → fundação (arrancamento)

    # Resistência (EN 1993-1-1 §6.2.3)
    A_mm2 = math.pi * d_mm ** 2 / 4.0
    N_t_Rd = _n_t_rd_kN(d_mm, aco)
    eta_N = N_diag / N_t_Rd if N_t_Rd > 0 else 999.0

    # Rigidez / drift (uma diagonal ativa)
    C_h = (E_ACO_MPA * A_mm2 / (g["L_diag_m"] * 1e3)) * cos_b ** 2   # kN/m
    delta_m = V_Ed_kN / C_h if C_h > 0 else 1e9
    delta_lim_m = H_col_m / drift_lim
    eta_delta = delta_m / delta_lim_m if delta_lim_m > 0 else 999.0

    eta = max(eta_N, eta_delta)

    return {
        "V_Ed_kN":       round(V_Ed_kN, 3),
        "beta_deg":      g["beta_deg"],
        "L_diag_m":      round(g["L_diag_m"], 4),
        "d_mm":          d_mm,
        "aco":           aco,
        "A_mm2":         round(A_mm2, 1),
        "N_diag_kN":     round(N_diag, 3),
        "N_t_Rd_kN":     round(N_t_Rd, 3),
        "eta_N":         round(eta_N, 4),
        "ok_N":          eta_N <= 1.0,
        # Caminho de carga até a fundação
        "H_base_kN":     round(H_base, 3),
        "N_uplift_kN":   round(N_uplift, 3),
        # Rigidez / ELS
        "C_h_kNpm":      round(C_h, 1),
        "delta_mm":      round(delta_m * 1000, 3),
        "delta_lim_mm":  round(delta_lim_m * 1000, 2),
        "eta_delta":     round(eta_delta, 4),
        "ok_delta":      eta_delta <= 1.0,
        "eta":           round(eta, 4),
        "ok":            eta <= 1.0,
        "norma":         "EN 1993-1-1 §6.2.3 (tração) + §5.4 (rigidez do sistema)",
    }


# ── Verificação completa do contraventamento vertical ─────────────────────────

def verificar_contraventamento_vertical(
    geo:            GeometriaViga,
    load:           Carregamentos,
    H_pilar_m:      float = 7.0,
    dist_portico:   float = 5.75,
    L_comp:         float = 46.0,
    n_porticos:     int   = 2,
    n_paineis_long: int   = 2,
    b_baia_long_m:  float | None = None,
    aco:            str   = "S235",
    d_mm:           float | None = None,
    eta_alvo:       float = 0.90,
    drift_lim:      float = 300.0,
    R_ext_cobertura_kN: float | None = None,
    V_Ed_total_kN: float | None = None,
) -> dict:
    """
    Verifica o contraventamento vertical LONGITUDINAL (paredes // cumeeira) que
    conduz a força de vento θ=0° do nível da cobertura até a fundação.

    Demanda lateral (longitudinal):
        V_lat = F_vento0 (θ=0°, estrutura aberta) + H_imp (nocional §5.3.2)
        distribuída por n_paineis_long painéis de cruz nas paredes de extremidade.

    O contraventamento da COBERTURA (§9.2.5) já coleta F_vento0 e o entrega às
    baías de extremidade; este módulo dimensiona/verifica a descida vertical
    dessa reação. R_ext_cobertura_kN (opcional) permite conferir a coerência
    entre os dois sistemas (a demanda adotada é a maior).

    Args:
        geo, load          : modelo de projeto (load.vento_0 traz F_total θ=0°)
        H_pilar_m          : pé-direito (m) = altura do painel
        dist_portico       : espaçamento entre pórticos (m) = largura da baía
        L_comp, n_porticos : geometria do galpão (para nocional e quantitativo)
        n_paineis_long     : nº de painéis de cruz que resistem à força longitudinal
        b_baia_long_m      : largura da baía contraventada (default = dist_portico)
        aco, d_mm          : aço e diâmetro da diagonal (d_mm=None → auto)
        eta_alvo           : margem de projeto na escolha automática do diâmetro
        drift_lim          : limite de drift δ ≤ H_col/drift_lim
        R_ext_cobertura_kN : reação entregue pelo contraventamento da cobertura (kN)
        V_Ed_total_kN : carga vertical de cálculo TOTAL estabilizada por estes
                        painéis (kN). Quando informada, calcula-se o α_cr de
                        SISTEMA desta direção (EN 1993-1-1 Eq. 5.2) a partir da
                        rigidez dos próprios painéis e, se α_cr < 10, AMPLIFICA-SE
                        a demanda lateral por k_II = 1/(1−1/α_cr) (§5.2.2(5)B)
                        antes de dimensionar a diagonal — achado F-02.

    Returns:
        dict com demanda, painel verificado, caminho de carga, η, ok e o flag
        `lateral_estavel_long` para alimentar a classificação de estabilidade.
    """
    if b_baia_long_m is None:
        b_baia_long_m = dist_portico
    n_pan = max(1, int(n_paineis_long))

    # ── 1) Demanda de vento longitudinal θ=0° ─────────────────────────────────
    vento_0 = getattr(load, "vento_0", None) or {}
    F_vento0_kN = float(vento_0.get("F_total_kN", 0.0))

    # ── 2) Força nocional (imperfeição global) — EN 1993-1-1 §5.3.2 ───────────
    gov = load.combinacao_ELU_governante()
    R_v = abs(float(gov.V_max_kN))                       # reação vertical por apoio
    n_frames = max(2, round(L_comp / dist_portico) + 1)  # pórticos ao longo do comp.
    # Carga vertical total ≈ 2·n_porticos·R_v por pórtico × n_frames
    V_vert_total = 2.0 * n_porticos * R_v * n_frames
    noc = forca_nocional(V_vert_total, H_pilar_m, m_colunas=n_frames)
    H_imp_kN = noc["H_imp_kN"]

    # ── 3) Cortante lateral de projeto por painel ─────────────────────────────
    V_lat_total = F_vento0_kN + H_imp_kN
    if R_ext_cobertura_kN is not None:
        # coerência: a demanda por extremidade não pode ser menor que a reação
        # entregue pelo contraventamento da cobertura (soma nas duas extremidades)
        V_lat_total = max(V_lat_total, 2.0 * float(R_ext_cobertura_kN))
    # ── 4) Ponto fixo demanda ↔ rigidez ↔ 2.ª ordem (achado F-02) ─────────────
    #      Sem V_Ed_total_kN mantém-se k_II = 1,0, mas então o α_cr de sistema
    #      fica indeterminado e estabilidade_global.py recusa dispensar a 2.ª
    #      ordem (a ausência de dado nunca é aprovação).
    g = geometria_painel(H_pilar_m, b_baia_long_m)
    d_auto = d_mm is None
    d_fixo = None if d_auto else float(d_mm)

    k_II = 1.0
    acr = None
    for _ in range(12):
        V_painel = V_lat_total * k_II / n_pan

        if d_auto:
            N_diag_req = V_painel / g["cos_beta"]
            d_mm = float(escolher_diametro(N_diag_req, aco=aco, eta_alvo=eta_alvo))
        else:
            d_mm = d_fixo

        painel = verifica_painel_vertical(
            V_Ed_kN=V_painel, H_col_m=H_pilar_m, b_baia_m=b_baia_long_m,
            d_mm=d_mm, aco=aco, drift_lim=drift_lim,
        )

        if V_Ed_total_kN is None or float(V_Ed_total_kN) <= 0.0:
            break

        K_lat = painel["C_h_kNpm"] * n_pan
        acr = alpha_cr_sistema(K_lat, H_pilar_m, float(V_Ed_total_kN))
        k_novo = 1.0 if acr["regime"] == "1a_ordem" else acr["k_II"]
        if not math.isfinite(k_novo):
            break                      # mecanismo: reprova a jusante, não itera
        if abs(k_novo - k_II) <= 1e-4:
            k_II = k_novo
            break
        k_II = k_novo

    K_lat_kNpm = painel["C_h_kNpm"] * n_pan
    regime_acr = acr["regime"] if acr is not None else "nao_determinado"
    amplificacao_aplicada = k_II > 1.0 + 1e-9
    # Um painel que só "passa" sob amplificação inadmissível (α_cr < 3) ou num
    # mecanismo não é um sistema de contraventamento válido.
    regime_ok = regime_acr not in ("2a_ordem_rigorosa", "mecanismo")

    # ── 5) Quantitativo (2 diagonais por cruz) ────────────────────────────────
    n_diagonais = 2 * n_pan
    L_tot = n_diagonais * g["L_diag_m"]
    peso = L_tot * (math.pi * (d_mm / 1000) ** 2 / 4) * 7850.0

    lateral_estavel_long = painel["ok"] and regime_ok

    return {
        "sistema": "Contraventamento vertical longitudinal (cruzes de St. André)",
        "norma":   "EN 1993-1-1 §5.3.2+§6.2.3 | EN 1995-1-1 §5.4 | NBR 6123 (θ=0°)",
        "direcao": "longitudinal (// cumeeira, θ=0°)",

        # Demanda
        "F_vento0_kN":   round(F_vento0_kN, 3),
        "phi":           noc["phi"],
        "H_imp_kN":      H_imp_kN,
        "V_vert_total_kN": round(V_vert_total, 1),
        "V_lat_total_kN": round(V_lat_total, 3),
        "n_paineis":     n_pan,
        "V_painel_kN":   round(V_painel, 3),
        "R_ext_cobertura_kN": (
            None if R_ext_cobertura_kN is None else round(R_ext_cobertura_kN, 3)
        ),

        # Painel / diagonal
        "H_col_m":       H_pilar_m,
        "b_baia_m":      b_baia_long_m,
        "beta_deg":      painel["beta_deg"],
        "d_mm":          d_mm,
        "d_auto":        d_auto,
        "aco":           aco,
        "N_diag_kN":     painel["N_diag_kN"],
        "N_t_Rd_kN":     painel["N_t_Rd_kN"],
        "eta_diag_N":    painel["eta_N"],
        "ok_diag":       painel["ok_N"],

        # Caminho de carga até a fundação
        "H_base_kN":     painel["H_base_kN"],
        "N_uplift_kN":   painel["N_uplift_kN"],

        # Rigidez / ELS
        "delta_mm":      painel["delta_mm"],
        "delta_lim_mm":  painel["delta_lim_mm"],
        "eta_delta":     painel["eta_delta"],
        "ok_delta":      painel["ok_delta"],

        # α_cr de sistema desta direção e 2.ª ordem (F-02)
        "C_h_kNpm":      painel["C_h_kNpm"],
        "K_lat_kNpm":    round(K_lat_kNpm, 1),
        "alpha_cr":      None if acr is None else round(acr["alpha_cr"], 2),
        "k_II":          round(k_II, 4),
        "regime_alpha_cr": regime_acr,
        "amplificacao_aplicada": amplificacao_aplicada,
        "V_lat_amplificado_kN": round(V_lat_total * k_II, 3),

        # Resultado
        "eta":           painel["eta"],
        "ok":            painel["ok"] and regime_ok,
        "lateral_estavel_long": lateral_estavel_long,

        # Nota sobre a direção transversal (tratada em módulo próprio)
        "nota_transversal": (
            "Direção transversal (⊥ cumeeira, no plano do pórtico): resolvida no "
            "módulo checks/elu/contraventamento_transversal.py (issue 31, Opção 2 "
            "— diafragma de cobertura + frontões contraventados)."
        ),

        # Quantitativo
        "n_diagonais":   n_diagonais,
        "L_diag_m":      round(g["L_diag_m"], 4),
        "L_total_m":     round(L_tot, 2),
        "peso_total_kg": round(peso, 1),
    }


# ── Relatório ─────────────────────────────────────────────────────────────────

def relatorio(res: dict) -> None:
    """Imprime relatório legível do contraventamento vertical."""
    print("=" * 68)
    print("  CONTRAVENTAMENTO VERTICAL — CAMINHO DE CARGA LATERAL À FUNDAÇÃO")
    print("  EN 1993-1-1 §5.3.2 + §6.2.3 | EN 1995-1-1 §5.4 | NBR 6123 (θ=0°)")
    print("=" * 68)
    print(f"  Sistema : {res['sistema']}")
    print(f"  Direção : {res['direcao']}")
    print()
    print("  ── Demanda lateral longitudinal ──")
    print(f"    F_vento0 (θ=0°) = {res['F_vento0_kN']:.2f} kN")
    print(f"    H_imp (nocional φ={res['phi']:.5f}) = {res['H_imp_kN']:.2f} kN")
    print(f"    V_lat total = {res['V_lat_total_kN']:.2f} kN "
          f"/ {res['n_paineis']} painéis = {res['V_painel_kN']:.2f} kN/painel")
    if res["R_ext_cobertura_kN"] is not None:
        print(f"    (R_ext cobertura = {res['R_ext_cobertura_kN']:.2f} kN/extremo)")
    print()
    print("  ── Diagonal (cruz de St. André) ──")
    print(f"    painel {res['H_col_m']:.2f}×{res['b_baia_m']:.2f} m | "
          f"β={res['beta_deg']}° | ∅{res['d_mm']:.0f} mm {res['aco']}"
          + ("  (auto)" if res["d_auto"] else ""))
    print(f"    N_diag = {res['N_diag_kN']:.2f} kN ≤ N_t,Rd = {res['N_t_Rd_kN']:.2f} kN"
          f"  → η_N = {res['eta_diag_N']:.4f}  "
          f"({'✓' if res['ok_diag'] else '✗'})")
    print()
    print("  ── Caminho de carga até a fundação ──")
    print(f"    H_base (cortante → fundação)   = {res['H_base_kN']:.2f} kN")
    print(f"    N_uplift (arrancamento → anc.) = {res['N_uplift_kN']:.2f} kN")
    print()
    print("  ── Rigidez / drift (δ ≤ H/limite) ──")
    print(f"    δ = {res['delta_mm']:.3f} mm ≤ {res['delta_lim_mm']:.2f} mm  "
          f"η_δ = {res['eta_delta']:.4f}  "
          f"({'✓' if res['ok_delta'] else '✗'})")
    print()
    print(f"  η governante = {res['eta']:.4f}  "
          f"→ {'APROVADO' if res['ok'] else 'REPROVADO'}")
    print(f"  Quantitativo: {res['n_diagonais']} diagonais × "
          f"{res['L_diag_m']:.2f} m = {res['L_total_m']:.1f} m "
          f"({res['peso_total_kg']:.1f} kg)")
    print()
    print("  ⚠ " + res["nota_transversal"])
    print("=" * 68)


# ── Execução direta ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    from mlc_projeto.core.materials import GlulamMaterial
    from mlc_projeto.core.wind      import ParametrosVento
    from mlc_projeto.core.loads     import carregamentos_com_vento

    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
    mat = GlulamMaterial(classe="GL24h", classe_servico=3, duracao="curta")
    params = ParametrosVento(
        V0=45, S1=1, categoria="IV", classe="B", S3=1,
        L=20.25, H1=geo.h_ap - geo.h0, h=7, dist_portico=5.75,
    )
    load = carregamentos_com_vento(
        geo=geo, mat=mat, g_area=1.5, q_area=0.25,
        L_t=5.75, params_vento=params,
        n_pilares_linha=9, n_linhas_portico=3,
        L_cob_m=46.0, B_cob_m=2 * geo.L,
    )

    res = verificar_contraventamento_vertical(
        geo=geo, load=load, H_pilar_m=7.0,
        dist_portico=5.75, L_comp=46.0, n_porticos=2,
        n_paineis_long=2, aco="S235",
    )
    relatorio(res)
