"""
checks/elu/succao_uplift.py — Verificação da combinação de sucção (issue 33).

Objetivo
--------
Ao corrigir o peso próprio (issue 1), a combinação de sucção deixou de ficar
mascarada e revela ESFORÇOS INVERSOS reais que o dimensionamento de gravidade
não cobre:

  · Reação vertical NEGATIVA (uplift) nos apoios → ancoragem tracionada.
  · Empuxo horizontal INVERTIDO (para dentro) → o tirante, sendo tração-apenas,
    fica FROUXO sob sucção; o empuxo invertido vai à FUNDAÇÃO (cortante na base,
    sem alívio por atrito, pois a base está tracionada).

Modelo (combinação ELU de sucção, 0,9G + 1,5W_suc)
--------------------------------------------------
  R_A, R_B < 0  → uplift por apoio (tração na ancoragem).
  H < 0         → empuxo invertido (inward).

  Apoio de EXTREMIDADE (uma água):
      N_uplift = |R_ext| − γ_G,inf·W_pilar        (tração líquida na ancoragem)
      V_base   = |H|                               (empuxo invertido, tirante frouxo)
  Apoio CENTRAL (dois vãos):
      N_uplift = |R_esq| + |R_dir| − γ_G,inf·W_pilar
      V_base   ≈ 0                                 (empuxos dos dois vãos cancelam)

  Ancoragem (chumbadores) — interação tração+cortante:
      η = N_uplift/R_anc + V_base/R_anc            (linear, conservador)
      R_anc = n_chu · F_chu
  A verificação definitiva dos chumbadores (aço + cone de concreto + arrancamento
  + interação N–V) segue EN 1992-4 / EN 1993-1-8; aqui faz-se a verificação de
  projeto com R_anc lumped e interação linear conservadora.

Notas
-----
  · A resistência da PEÇA sob sucção não governa: os momentos de sucção são
    pequenos face à gravidade (|M_suc| ≪ |M_grav|); o concern é o CAMINHO DE
    CARGA da ancoragem/fundação.
  · O peso da fundação (bloco/sapata) é favorável adicional ao uplift global
    (EN 1997) e não está aqui modelado — a verificar no projeto de fundação.

Referências
-----------
  EN 1990 Tab. A1.2(A) — EQU: uplift é situação de equilíbrio; G estabilizante
        com γ_G = 0,90 (issue 4 — valor EN 1990, não NBR; STR usaria 1,00, Tab. A1.2(B))
  EN 1993-1-1 §6.2.3 (tirante tração-apenas) ; EN 1992-4 / EN 1993-1-8 (ancoragem)
"""

from __future__ import annotations

from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.loads import (
    Carregamentos, analisar_biarticulada, GAMMA_G_EQU_estab, G_GRAVIDADE,
)


def verificar_succao_uplift(
    load:          Carregamentos,
    geo:           GeometriaViga,
    F_chu_kN:      float,
    n_chu:         int,
    b_pilar:       float,
    h_pilar:       float,
    H_pilar_m:     float,
    rho_mean_kgm3: float,
    com_tirante:   bool = True,
    gamma_G_inf:   float = GAMMA_G_EQU_estab,   # EQU estabilizante (EN 1990 Tab. A1.2(A))
    g_ms2:         float = G_GRAVIDADE,
    N_brace_anc_kN: float = 0.0,
    n_chu_canto: int | None = None,
    V_brace_kN: float = 0.0,
    chaveta_cisalhamento: bool = False,
) -> dict:
    """
    Verifica a combinação de sucção: uplift na ancoragem e empuxo invertido
    (tirante frouxo → fundação).

    Args:
        load          : carregamentos (fornece a combinação de sucção)
        geo           : geometria da viga
        F_chu_kN      : resistência por chumbador (kN) — lumped (EN 1992-4 no detalhe)
        n_chu         : nº de chumbadores por base
        b_pilar,h_pilar,H_pilar_m : seção/altura do pilar (peso próprio favorável)
        rho_mean_kgm3 : densidade média do glulam (peso do pilar)
        com_tirante   : se há tirante (tração-apenas → frouxo sob sucção)
        gamma_G_inf   : coeficiente da ação permanente favorável (EN 1990)
        N_brace_anc_kN: tração de download do contraventamento (Σ V_Ed·tanβ) que
                        chega à ancoragem do pilar de CANTO (montante de painel),
                        CONCOMITANTE ao uplift de sucção — mesmo evento de vento
                        (issue 36). Somada só na base de extremidade/canto.

    Returns:
        dict com esforços de sucção, verificação da ancoragem (externa e central),
        η governante, ok e o caminho de carga.
    """
    c = load.combinacao_ELU_succao()
    q_med = 0.5 * (c.q_esq + c.q_dir)
    r = analisar_biarticulada(
        q=q_med, L=geo.L, h0=geo.h0, h_ap=geo.h_ap,
        alpha_rad=geo.alpha_rad, b=geo.b, q_esq=c.q_esq, q_dir=c.q_dir,
        desenvolve_empuxo=load.empuxo_desenvolve,
    )
    R_A = float(r["R_A_kN"])
    R_B = float(r["R_B_kN"])
    H_suc = float(c.H_kN)                       # com sinal (<0 = invertido)

    # Há uplift? (alguma reação vertical negativa)
    ha_uplift = (R_A < 0.0) or (R_B < 0.0)
    empuxo_invertido = H_suc < 0.0

    # Peso próprio do pilar (favorável ao uplift) — γ_G,inf
    W_pilar = (rho_mean_kgm3 * g_ms2 / 1000.0) * (b_pilar * h_pilar * H_pilar_m)
    W_pilar_fav = gamma_G_inf * W_pilar

    # Uplift por apoio (tração positiva)
    uplift_ext = max(0.0, -R_A, -R_B)                       # extremidade (maior |R|<0)
    uplift_cen = max(0.0, -(R_A + R_B))                     # central (soma dos vãos)

    N_uplift_ext = max(0.0, uplift_ext - W_pilar_fav)       # tração líquida ancoragem
    N_uplift_cen = max(0.0, uplift_cen - W_pilar_fav)

    # Cortante na base de EXTREMIDADE pelo empuxo de sucção:
    #   · SEM tirante: o empuxo SEMPRE vai à base (|H|), invertido ou não;
    #   · COM tirante: só quando invertido (tirante frouxo, sem alívio por atrito
    #     — base tracionada); com tirante ativo (H>0) o empuxo é absorvido pela
    #     barra e V_base ≈ 0.
    # No apoio central, os empuxos dos dois vãos cancelam (V_base ≈ 0).
    V_base_ext = abs(H_suc) if (not com_tirante or empuxo_invertido) else 0.0

    # Capacidade de ancoragem (lumped) e interação N–V (linear, conservadora).
    #
    # A base de CANTO tem ancoragem PRÓPRIA (`n_chu_canto`). Antes, todas as
    # bases partilhavam o mesmo `n_chu`, que é dimensionado pelo esforço
    # HORIZONTAL — nulo no modelo adotado (Opção B, H=0) — e portanto caía
    # sempre no mínimo construtivo de 4. Só que o canto acumula o uplift da
    # sucção MAIS os downloads dos dois painéis de contraventamento, chegando a
    # ~4,4× a demanda da extremidade. Dimensionar as três bases pela mesma
    # ancoragem mínima é o que fazia o canto reprovar.
    R_anc = max(1e-9, n_chu * F_chu_kN)
    _n_canto = int(n_chu if n_chu_canto is None else n_chu_canto)
    R_anc_canto = max(1e-9, _n_canto * F_chu_kN)
    eta_N_ext = N_uplift_ext / R_anc
    eta_V_ext = V_base_ext / R_anc
    eta_ext = eta_N_ext + eta_V_ext                        # interação linear
    eta_N_cen = N_uplift_cen / R_anc
    eta_cen = eta_N_cen                                     # V≈0 no central

    # Base de CANTO (montante de contraventamento): soma a tração do download
    # Σ V_Ed·tanβ, concomitante ao uplift de sucção (mesmo vento) — issue 36.
    N_brace = max(0.0, float(N_brace_anc_kN))
    # ── Cortante na base de canto ────────────────────────────────────────
    # Os painéis de contraventamento entregam à MESMA base, na mesma combinação
    # de vento, uma força horizontal (H_base do painel longitudinal + do
    # frontão) além do arrancamento. Antes, só o empuxo do arco (`V_base_ext`)
    # entrava aqui — e ele é NULO na Opção B, pelo que o cortante do
    # contraventamento simplesmente não era verificado.
    #
    # Não há atrito a ajudar: no caso governante a base está TRACIONADA, sem
    # compressão sob a chapa. O cortante tem de ir pelos chumbadores ou por uma
    # chaveta. Com `chaveta_cisalhamento=True` o corte é transmitido pela
    # chaveta e desacoplado das barras — mas a chaveta passa a exigir a sua
    # própria verificação de esmagamento do concreto.
    V_canto = V_base_ext + max(0.0, float(V_brace_kN))
    V_canto_nos_chumbadores = 0.0 if chaveta_cisalhamento else V_canto

    N_uplift_canto = N_uplift_ext + N_brace
    eta_N_canto = N_uplift_canto / R_anc_canto
    eta_canto = eta_N_canto + V_canto_nos_chumbadores / R_anc_canto

    eta_gov = max(eta_ext, eta_cen, eta_canto)
    if N_brace > 0.0 and eta_canto >= eta_ext and eta_canto >= eta_cen:
        base_gov = "canto (contraventado)"
    elif eta_ext >= eta_cen:
        base_gov = "extremidade"
    else:
        base_gov = "central"
    ok = eta_gov <= 1.0

    return {
        "sistema":         "Combinação de sucção — uplift + empuxo invertido",
        "norma":           "EN 1990 | EN 1993-1-1 §6.2.3 | EN 1992-4/EN 1993-1-8",
        "comb":            c.nome,
        "duracao":         c.duracao,
        # Esforços de sucção (com sinal)
        "q_suc_kNpm":      round(q_med, 3),
        "R_A_kN":          round(R_A, 3),
        "R_B_kN":          round(R_B, 3),
        "H_suc_kN":        round(H_suc, 3),
        "ha_uplift":       ha_uplift,
        "empuxo_invertido": empuxo_invertido,
        "tirante_frouxo":  bool(com_tirante and empuxo_invertido),
        # Pesos favoráveis
        "W_pilar_kN":      round(W_pilar, 3),
        "W_pilar_fav_kN":  round(W_pilar_fav, 3),
        "gamma_G_inf":     gamma_G_inf,
        # Ancoragem — apoio de extremidade (governa o empuxo invertido)
        "N_uplift_ext_kN": round(N_uplift_ext, 3),
        "V_base_ext_kN":   round(V_base_ext, 3),
        "eta_N_ext":       round(eta_N_ext, 4),
        "eta_V_ext":       round(eta_V_ext, 4),
        "eta_ext":         round(eta_ext, 4),
        # Ancoragem — apoio central (governa o uplift, V≈0)
        "N_uplift_cen_kN": round(N_uplift_cen, 3),
        "eta_cen":         round(eta_cen, 4),
        # Ancoragem — base de CANTO (uplift sucção + download contravent., issue 36)
        "N_brace_anc_kN":     round(N_brace, 3),
        "N_uplift_canto_kN":  round(N_uplift_canto, 3),
        "n_chu_canto":        _n_canto,
        "V_canto_kN":         round(V_canto, 3),
        "V_canto_nos_chumbadores_kN": round(V_canto_nos_chumbadores, 3),
        "chaveta_cisalhamento": bool(chaveta_cisalhamento),
        "R_anc_canto_kN":     round(R_anc_canto, 3),
        "eta_N_canto":        round(eta_N_canto, 4),
        "eta_canto":          round(eta_canto, 4),
        # Capacidade
        "F_chu_kN":        F_chu_kN,
        "n_chu":           n_chu,
        "R_anc_kN":        round(R_anc, 1),
        # Resultado
        "base_gov":        base_gov,
        "eta":             round(eta_gov, 4),
        "ok":              ok,
        "nota_tirante": (
            "Tirante tração-apenas: sob sucção o empuxo inverte (H<0) e a barra "
            "fica frouxa; o empuxo invertido |H| vai à fundação como cortante na "
            "base de extremidade (sem atrito — base tracionada)."
            if (com_tirante and empuxo_invertido)
            else (
                "Sem tirante: o empuxo de sucção |H| vai à fundação como cortante "
                "na base de extremidade, concomitante ao uplift (interação N–V)."
                if not com_tirante
                else "Sem inversão de empuxo relevante nesta combinação."
            )
        ),
        "nota_anc": (
            "Interação N–V linear (conservadora); verificação definitiva dos "
            "chumbadores (aço + cone de concreto + arrancamento + interação) por "
            "EN 1992-4 / EN 1993-1-8. Peso da fundação (favorável, EN 1997) não "
            "incluído. Base de CANTO: soma a tração do download do contraventamento "
            "(Σ V_Ed·tanβ), concomitante ao uplift de sucção (issue 36); Σ dos dois "
            "painéis é envelope conservador (uma direção de vento atua por vez)."
        ),
    }


def relatorio(res: dict) -> None:
    """Imprime relatório legível da verificação de sucção/uplift."""
    print("=" * 68)
    print("  COMBINAÇÃO DE SUCÇÃO — UPLIFT + EMPUXO INVERTIDO (issue 33)")
    print("  EN 1990 | EN 1993-1-1 §6.2.3 | EN 1992-4/EN 1993-1-8")
    print("=" * 68)
    print(f"  Combinação: {res['comb']} ({res['duracao']})")
    print(f"  q_suc={res['q_suc_kNpm']:+.2f} kN/m | R_A={res['R_A_kN']:+.1f} "
          f"R_B={res['R_B_kN']:+.1f} kN | H={res['H_suc_kN']:+.1f} kN")
    print(f"  uplift={res['ha_uplift']} | empuxo invertido={res['empuxo_invertido']} "
          f"| tirante frouxo={res['tirante_frouxo']}")
    print()
    print("  ── Apoio de EXTREMIDADE (governa empuxo invertido) ──")
    print(f"    N_uplift={res['N_uplift_ext_kN']:.1f} kN (− W_pilar,fav="
          f"{res['W_pilar_fav_kN']:.1f}) | V_base={res['V_base_ext_kN']:.1f} kN")
    print(f"    η_N={res['eta_N_ext']:.3f} + η_V={res['eta_V_ext']:.3f} "
          f"→ η_ext={res['eta_ext']:.3f}")
    print("  ── Apoio CENTRAL (governa uplift, V≈0) ──")
    print(f"    N_uplift={res['N_uplift_cen_kN']:.1f} kN → η_cen={res['eta_cen']:.3f}")
    if res.get("N_brace_anc_kN", 0.0) > 0.0:
        print("  ── Base de CANTO (uplift + download contravent., issue 36) ──")
        print(f"    N={res['N_uplift_ext_kN']:.1f}+{res['N_brace_anc_kN']:.1f}="
              f"{res['N_uplift_canto_kN']:.1f} kN + V_base={res['V_base_ext_kN']:.1f} kN "
              f"→ η_canto={res['eta_canto']:.3f}")
    print()
    print(f"  Ancoragem: {res['n_chu']}×{res['F_chu_kN']:.0f} kN = "
          f"{res['R_anc_kN']:.0f} kN")
    print(f"  η governante ({res['base_gov']}) = {res['eta']:.4f}  "
          f"→ {'APROVADO' if res['ok'] else 'REPROVADO'}")
    print(f"  ⚠ {res['nota_tirante']}")
    print(f"  ⚠ {res['nota_anc']}")
    print("=" * 68)


# ── Execução direta ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    from mlc_projeto.core.materials import GlulamMaterial
    from mlc_projeto.core.wind import ParametrosVento
    from mlc_projeto.core.loads import carregamentos_com_vento, peso_proprio_gk

    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
    mat = GlulamMaterial("GL24h", 3, "curta")
    pv = ParametrosVento(V0=45, S1=1, categoria="IV", classe="B", S3=1,
                         L=20.25, H1=geo.h_ap - geo.h0, h=7, dist_portico=5.75)
    pp = peso_proprio_gk(geo, GlulamMaterial("GL24h", 3, "longa"),
                         5.75, 0.20, 0.58, 2.53, 0.10, 0.10)
    load = carregamentos_com_vento(
        geo, mat, pp["g_k_viga_kNm2"], 0.25, 5.75, pv,
        n_pilares_linha=9, n_linhas_portico=3, L_cob_m=46.0, B_cob_m=2 * geo.L,
    )
    res = verificar_succao_uplift(
        load, geo, F_chu_kN=80.0, n_chu=4,
        b_pilar=0.32, h_pilar=0.27, H_pilar_m=7.0, rho_mean_kgm3=mat.rho_mean,
        com_tirante=True,
    )
    relatorio(res)
