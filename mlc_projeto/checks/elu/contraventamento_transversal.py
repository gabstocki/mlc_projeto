"""
checks/elu/contraventamento_transversal.py — Contraventamento transversal.

Objetivo (issue 31 — Opção 2)
-----------------------------
No plano do pórtico (⊥ cumeeira), com pilares birotulados (topo e base) e
ligações viga-pilar rotuladas, o pórtico é um MECANISMO sway (α_cr,sway → 0):
não resiste a carga lateral transversal por ação de pórtico. A estabilidade
transversal é provida por um sistema de contraventamento (Opção 2), que também
é o que torna legítima a hipótese de `l_ef = 1,0·H` dos pilares (topo travado,
non-sway — ver checks/elu/pilares.py e o modelo `pilar_vento_90`).

Cadeia de forças (direção transversal, ⊥ cumeeira, θ=90°)
--------------------------------------------------------
  Vento θ=90° (arrasto nos pilares) + força nocional (EN 1993-1-1 §5.3.2)
       ↓  metade do arrasto de cada pilar vai ao TOPO
  Diafragma de cobertura (viga horizontal ao longo do comprimento)
       ↓  reação nas extremidades
  Pórticos de extremidade / FRONTÕES contraventados (cruzes de St. André)
       ↓
  FUNDAÇÃO  (reação horizontal H_base + arrancamento N_uplift)

Consequência (acoplamento)
--------------------------
Com o diafragma travando o topo dos pilares internos, `l_ef = 1,0·H` (non-sway)
fica válido → o dimensionamento de pilares.py e o `pilar_vento_90` (modelo
biapoiado, topo travado) tornam-se legítimos nesta direção. Esta verificação
devolve `lateral_estavel_transv`, que alimenta a classificação sway/non-sway em
checks/elu/estabilidade_global.py.

Modelo de cálculo
-----------------
  · Painel de cruz de St. André no plano do frontão: só a diagonal TRACIONADA
    é ativa (reuso de contraventamento_vertical.verifica_painel_vertical).
  · Diafragma como viga horizontal biapoiada nos frontões:
        w_tr = H_tr / L_comp ;  R_gable = H_tr / 2 ;
        M_diaf = H_tr·L_comp/8 ;  N_corda = M_diaf / B_cob
    (força de corda pequena — diafragma muito profundo, B_cob ≈ 2·L).

Referências
-----------
  EN 1995-1-1 §5.4 (análise/estabilidade do sistema)
  EN 1993-1-1 §5.3.2 (imperfeições globais, φ) e §6.2.3 (diagonal à tração)
  NBR 6123 (arrasto θ=90° nos pilares, via core/wind.py)
"""

from __future__ import annotations

import math

from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.loads import Carregamentos, GAMMA_Q
from mlc_projeto.core.wind import (
    ParametrosVento, forca_vento_pilar_90,
)

# Reuso das utilidades genéricas de painel de cruz de St. André — mecânica
# idêntica à do contraventamento vertical (issue 14). Exceção de import
# checks→checks deliberada e documentada (análoga a creep.py → deflection.py),
# para não duplicar a verificação de diagonal/rigidez/EN 1993-1-1 §6.2.3.
from mlc_projeto.checks.elu.contraventamento_vertical import (
    geometria_painel,
    verifica_painel_vertical,
    forca_nocional,
    escolher_diametro,
)


# ── Demanda lateral transversal (θ=90° + nocional) ────────────────────────────

def demanda_transversal(
    load:         Carregamentos,
    params_vento: ParametrosVento,
    H_pilar_m:    float,
    b_pilar:      float,
    h_pilar:      float,
    n_frames:     int,
    n_porticos:   int = 2,
    gamma_Q:      float = GAMMA_Q,
) -> dict:
    """
    Força horizontal transversal (⊥ cumeeira) ao nível da cobertura.

    Composição:
      · Arrasto de vento θ=90° em cada pilar (NBR 6123, via forca_vento_pilar_90):
        modelo biapoiado → metade da força vai ao topo (diafragma).
      · Força nocional global — EN 1993-1-1 §5.3.2: H_imp = φ·V_vertical_total.

    Args:
        load, params_vento : ações do projeto
        H_pilar_m          : pé-direito (m)
        b_pilar, h_pilar   : seção do pilar (h = dimensão no plano do pórtico)
        n_frames           : nº de pórticos ao longo do comprimento
        n_porticos         : vãos lado a lado (2 → 3 pilares por frame)

    Returns:
        dict com F_col, reações de topo, nocional e demanda total H_tr.
    """
    n_col_por_frame = n_porticos + 1
    n_col = n_frames * n_col_por_frame

    # Arrasto θ=90° por pilar (característico) → design → reação de topo
    w90 = forca_vento_pilar_90(params_vento, b_pilar=b_pilar, h_pilar=h_pilar)
    F_col_k = float(w90["F_pilar_kN"])
    F_col_d = gamma_Q * F_col_k
    H_vento_topo = n_col * F_col_d / 2.0        # metade ao topo (diafragma)

    # Força nocional sobre a carga vertical total do galpão (§5.3.2)
    gov = load.combinacao_ELU_governante()
    R_v = abs(float(gov.V_max_kN))
    V_vert_total = 2.0 * n_porticos * R_v * n_frames
    noc = forca_nocional(V_vert_total, H_pilar_m, m_colunas=n_frames)
    H_imp = noc["H_imp_kN"]

    H_tr = H_vento_topo + H_imp

    return {
        "F_col_k_kN":     round(F_col_k, 3),
        "F_col_d_kN":     round(F_col_d, 3),
        "n_colunas":      n_col,
        "H_vento_topo_kN": round(H_vento_topo, 3),
        "phi":            noc["phi"],
        "V_vert_total_kN": round(V_vert_total, 1),
        "H_imp_kN":       H_imp,
        "H_tr_kN":        round(H_tr, 3),
    }


# ── Diafragma de cobertura (viga horizontal entre frontões) ───────────────────

def verifica_diafragma(
    H_tr_kN:  float,
    L_comp_m: float,
    B_cob_m:  float,
) -> dict:
    """
    Diafragma de cobertura como viga horizontal biapoiada nos frontões.

        w_tr    = H_tr / L_comp        (carga distribuída ao longo do comprimento)
        R_gable = H_tr / 2             (reação em cada frontão)
        M_diaf  = H_tr·L_comp / 8      (momento máximo da viga-diafragma)
        N_corda = M_diaf / B_cob       (força axial nas cordas/beirais)

    A corda é o elemento de beiral (perímetro da cobertura). N_corda deve ser
    somada ao dimensionamento desse elemento — reportada aqui para rastreio.
    """
    if L_comp_m <= 0 or B_cob_m <= 0:
        raise ValueError("L_comp_m e B_cob_m devem ser positivos")
    w_tr = H_tr_kN / L_comp_m
    R_gable = H_tr_kN / 2.0
    M_diaf = H_tr_kN * L_comp_m / 8.0
    N_corda = M_diaf / B_cob_m
    return {
        "w_tr_kNpm":   round(w_tr, 4),
        "R_gable_kN":  round(R_gable, 3),
        "M_diaf_kNm":  round(M_diaf, 2),
        "B_cob_m":     round(B_cob_m, 3),
        "N_corda_kN":  round(N_corda, 3),
        "norma":       "diafragma de cobertura (viga horizontal biapoiada)",
    }


# ── Verificação completa do contraventamento transversal ──────────────────────

def verificar_contraventamento_transversal(
    geo:            GeometriaViga,
    load:           Carregamentos,
    params_vento:   ParametrosVento,
    H_pilar_m:      float = 7.0,
    dist_portico:   float = 5.75,
    L_comp:         float = 46.0,
    n_porticos:     int   = 2,
    b_pilar:        float = 0.32,
    h_pilar:        float = 0.27,
    n_gables:       int   = 2,
    n_paineis_por_gable: int = 1,
    b_baia_gable_m: float | None = None,
    B_cob_m:        float | None = None,
    aco:            str   = "S235",
    d_mm:           float | None = None,
    eta_alvo:       float = 0.90,
    drift_lim:      float = 300.0,
) -> dict:
    """
    Verifica o sistema de contraventamento transversal (Opção 2, issue 31):
    diafragma de cobertura + frontões contraventados, com caminho de carga
    à fundação, para o vento θ=90° e as forças nocionais.

    Args:
        geo, load, params_vento : modelo de projeto
        H_pilar_m, dist_portico, L_comp, n_porticos : geometria do galpão
        b_pilar, h_pilar    : seção do pilar (arrasto θ=90°)
        n_gables            : nº de frontões contraventados (2 extremidades)
        n_paineis_por_gable : painéis de cruz por frontão
        b_baia_gable_m      : largura da baía de cruz no frontão (default: entre
                              montantes de frontão ≈ dist_portico)
        B_cob_m             : profundidade do diafragma (default 2·L do pórtico)
        aco, d_mm           : aço e diâmetro da diagonal (d_mm=None → auto)
        eta_alvo, drift_lim : critérios de projeto da diagonal/painel

    Returns:
        dict com demanda, diafragma, painel do frontão, caminho de carga,
        η, ok e `lateral_estavel_transv` (alimenta estabilidade_global).
    """
    if b_baia_gable_m is None:
        b_baia_gable_m = dist_portico
    if B_cob_m is None:
        B_cob_m = 2.0 * geo.L
    n_pan_gable = max(1, int(n_paineis_por_gable))

    n_frames = max(2, round(L_comp / dist_portico) + 1)

    # 1) Demanda transversal (vento θ=90° + nocional)
    dem = demanda_transversal(
        load, params_vento, H_pilar_m, b_pilar, h_pilar,
        n_frames=n_frames, n_porticos=n_porticos,
    )
    H_tr = dem["H_tr_kN"]

    # 2) Diafragma → reação por frontão
    diaf = verifica_diafragma(H_tr, L_comp, B_cob_m)
    R_gable = diaf["R_gable_kN"]

    # 3) Cortante por painel de cruz no frontão
    V_painel = R_gable / n_pan_gable

    # 4) Diâmetro (auto) e verificação do painel do frontão
    g = geometria_painel(H_pilar_m, b_baia_gable_m)
    d_auto = d_mm is None
    if d_auto:
        N_diag_req = V_painel / g["cos_beta"]
        d_mm = escolher_diametro(N_diag_req, aco=aco, eta_alvo=eta_alvo)
    d_mm = float(d_mm)

    painel = verifica_painel_vertical(
        V_Ed_kN=V_painel, H_col_m=H_pilar_m, b_baia_m=b_baia_gable_m,
        d_mm=d_mm, aco=aco, drift_lim=drift_lim,
    )

    lateral_estavel_transv = painel["ok"]

    # 5) Quantitativo (2 diagonais por cruz)
    n_diagonais = 2 * n_pan_gable * n_gables
    L_tot = n_diagonais * g["L_diag_m"]
    peso = L_tot * (math.pi * (d_mm / 1000) ** 2 / 4) * 7850.0

    return {
        "sistema": "Contraventamento transversal (diafragma + frontões)",
        "norma":   "EN 1993-1-1 §5.3.2+§6.2.3 | EN 1995-1-1 §5.4 | NBR 6123 (θ=90°)",
        "direcao": "transversal (⊥ cumeeira, plano do pórtico, θ=90°)",

        # Demanda
        "F_col_d_kN":     dem["F_col_d_kN"],
        "n_colunas":      dem["n_colunas"],
        "H_vento_topo_kN": dem["H_vento_topo_kN"],
        "phi":            dem["phi"],
        "H_imp_kN":       dem["H_imp_kN"],
        "H_tr_kN":        H_tr,

        # Diafragma
        "w_tr_kNpm":      diaf["w_tr_kNpm"],
        "B_cob_m":        diaf["B_cob_m"],
        "M_diaf_kNm":     diaf["M_diaf_kNm"],
        "N_corda_kN":     diaf["N_corda_kN"],
        "R_gable_kN":     R_gable,
        "n_gables":       n_gables,

        # Painel do frontão
        "H_col_m":        H_pilar_m,
        "b_baia_m":       b_baia_gable_m,
        "n_paineis_gable": n_pan_gable,
        "V_painel_kN":    round(V_painel, 3),
        "beta_deg":       painel["beta_deg"],
        "d_mm":           d_mm,
        "d_auto":         d_auto,
        "aco":            aco,
        "N_diag_kN":      painel["N_diag_kN"],
        "N_t_Rd_kN":      painel["N_t_Rd_kN"],
        "eta_diag_N":     painel["eta_N"],
        "ok_diag":        painel["ok_N"],

        # Caminho de carga até a fundação
        "H_base_kN":      painel["H_base_kN"],
        "N_uplift_kN":    painel["N_uplift_kN"],

        # Rigidez / ELS
        "delta_mm":       painel["delta_mm"],
        "delta_lim_mm":   painel["delta_lim_mm"],
        "eta_delta":      painel["eta_delta"],
        "ok_delta":       painel["ok_delta"],

        # Resultado
        "eta":            painel["eta"],
        "ok":             painel["ok"],
        "lateral_estavel_transv": lateral_estavel_transv,

        # Acoplamento com o dimensionamento dos pilares
        "nota_pilar": (
            "Com o diafragma travando os topos, l_ef=1,0·H (non-sway) é válido "
            "para os pilares no plano do pórtico → dimensionamento de pilares.py "
            "e modelo pilar_vento_90 (biapoiado) legítimos nesta direção."
        ),
        "nota_corda": (
            f"Força de corda do diafragma N_corda={diaf['N_corda_kN']:.1f} kN a "
            "somar ao elemento de beiral (verificação do membro, à parte)."
        ),

        # Quantitativo
        "n_diagonais":    n_diagonais,
        "L_diag_m":       round(g["L_diag_m"], 4),
        "L_total_m":      round(L_tot, 2),
        "peso_total_kg":  round(peso, 1),
    }


# ── Relatório ─────────────────────────────────────────────────────────────────

def relatorio(res: dict) -> None:
    """Imprime relatório legível do contraventamento transversal."""
    print("=" * 68)
    print("  CONTRAVENTAMENTO TRANSVERSAL — DIAFRAGMA + FRONTÕES → FUNDAÇÃO")
    print("  EN 1993-1-1 §5.3.2 + §6.2.3 | EN 1995-1-1 §5.4 | NBR 6123 (θ=90°)")
    print("=" * 68)
    print(f"  Sistema : {res['sistema']}")
    print(f"  Direção : {res['direcao']}")
    print()
    print("  ── Demanda transversal ──")
    print(f"    Arrasto θ=90°: {res['n_colunas']} pilares × {res['F_col_d_kN']:.2f} kN "
          f"→ topo = {res['H_vento_topo_kN']:.2f} kN")
    print(f"    H_imp (nocional φ={res['phi']:.5f}) = {res['H_imp_kN']:.2f} kN")
    print(f"    H_tr total = {res['H_tr_kN']:.2f} kN")
    print()
    print("  ── Diafragma de cobertura ──")
    print(f"    w_tr={res['w_tr_kNpm']:.3f} kN/m | B_cob={res['B_cob_m']:.1f} m | "
          f"N_corda={res['N_corda_kN']:.2f} kN")
    print(f"    R_gable = {res['R_gable_kN']:.2f} kN (por frontão)")
    print()
    print("  ── Diagonal do frontão (cruz de St. André) ──")
    print(f"    painel {res['H_col_m']:.2f}×{res['b_baia_m']:.2f} m | "
          f"β={res['beta_deg']}° | ∅{res['d_mm']:.0f} mm {res['aco']}"
          + ("  (auto)" if res["d_auto"] else ""))
    print(f"    N_diag={res['N_diag_kN']:.2f} kN ≤ N_t,Rd={res['N_t_Rd_kN']:.2f} kN "
          f"→ η_N={res['eta_diag_N']:.4f}  ({'✓' if res['ok_diag'] else '✗'})")
    print()
    print("  ── Caminho de carga até a fundação ──")
    print(f"    H_base (cortante) = {res['H_base_kN']:.2f} kN | "
          f"N_uplift (arrancamento) = {res['N_uplift_kN']:.2f} kN")
    print()
    print(f"    δ = {res['delta_mm']:.3f} mm ≤ {res['delta_lim_mm']:.2f} mm  "
          f"η_δ = {res['eta_delta']:.4f}  ({'✓' if res['ok_delta'] else '✗'})")
    print()
    print(f"  η governante = {res['eta']:.4f}  "
          f"→ {'APROVADO' if res['ok'] else 'REPROVADO'}")
    print(f"  Quantitativo: {res['n_diagonais']} diagonais × "
          f"{res['L_diag_m']:.2f} m = {res['L_total_m']:.1f} m "
          f"({res['peso_total_kg']:.1f} kg)")
    print(f"  ✓ {res['nota_pilar']}")
    print("=" * 68)


# ── Execução direta ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    from mlc_projeto.core.materials import GlulamMaterial
    from mlc_projeto.core.loads import carregamentos_com_vento

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

    res = verificar_contraventamento_transversal(
        geo=geo, load=load, params_vento=params,
        H_pilar_m=7.0, dist_portico=5.75, L_comp=46.0, n_porticos=2,
        b_pilar=0.32, h_pilar=0.27, aco="S235",
    )
    relatorio(res)
