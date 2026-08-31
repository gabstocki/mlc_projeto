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
  EN 1990 (combinação de sucção; ação permanente favorável γ_G,inf)
  EN 1993-1-1 §6.2.3 (tirante tração-apenas) ; EN 1992-4 / EN 1993-1-8 (ancoragem)
"""

from __future__ import annotations

from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.loads import (
    Carregamentos, analisar_biarticulada, GAMMA_G_inf, G_GRAVIDADE,
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
    gamma_G_inf:   float = GAMMA_G_inf,
    g_ms2:         float = G_GRAVIDADE,
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

    Returns:
        dict com esforços de sucção, verificação da ancoragem (externa e central),
        η governante, ok e o caminho de carga.
    """
    c = load.combinacao_ELU_succao()
    q_med = 0.5 * (c.q_esq + c.q_dir)
    r = analisar_biarticulada(
        q=q_med, L=geo.L, h0=geo.h0, h_ap=geo.h_ap,
        alpha_rad=geo.alpha_rad, b=geo.b, q_esq=c.q_esq, q_dir=c.q_dir,
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

    # Empuxo invertido: tirante frouxo → cortante na base de EXTREMIDADE.
    # No apoio central, os empuxos dos dois vãos cancelam (V_base ≈ 0).
    V_base_ext = abs(H_suc) if (com_tirante and empuxo_invertido) else 0.0

    # Capacidade de ancoragem (lumped) e interação N–V (linear, conservadora)
    R_anc = max(1e-9, n_chu * F_chu_kN)
    eta_N_ext = N_uplift_ext / R_anc
    eta_V_ext = V_base_ext / R_anc
    eta_ext = eta_N_ext + eta_V_ext                        # interação linear
    eta_N_cen = N_uplift_cen / R_anc
    eta_cen = eta_N_cen                                     # V≈0 no central

    eta_gov = max(eta_ext, eta_cen)
    base_gov = "extremidade" if eta_ext >= eta_cen else "central"
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
            else "Sem inversão de empuxo relevante nesta combinação."
        ),
        "nota_anc": (
            "Interação N–V linear (conservadora); verificação definitiva dos "
            "chumbadores (aço + cone de concreto + arrancamento + interação) por "
            "EN 1992-4 / EN 1993-1-8. Peso da fundação (favorável, EN 1997) não "
            "incluído."
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
