"""
checks/elu/flexo_compressao.py — Flexo-compressão unificado. v2

ATUALIZAÇÃO v2 — Pórtico de 3 rótulas:

    Dois elementos verificados:

    1. VIGA — flexo-compressão real (M + N):
       Delega para flexao.py → verifica_flexao()
       EC5 §6.3.2 Eq. 6.23
       M_d ≠ 0 (momento no vão) + N_d ≠ 0 (empuxo interno)

    2. PILAR — compressão simples (M = 0):
       Delega para pilares.py → verifica_pilar()
       EC5 §6.3.2 Eq. 6.23 simplificada
       M_d = 0 (rótulas em ambas as extremidades)
       N_d = R_v (reação vertical)

    O resultado consolidado retorna o η governante entre os dois
    elementos e é chamado diretamente pelo main.py.

Referência: EC5 §6.3.2 Eq. 6.23
"""

from __future__ import annotations

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.loads     import Carregamentos
from mlc_projeto.core.wind      import ParametrosVento

from mlc_projeto.checks.elu.flexao   import verifica_flexao
from mlc_projeto.checks.elu.pilares  import verifica_pilar


def verifica_flexo_compressao(
    geo:          GeometriaViga,
    mat:          GlulamMaterial,
    load:         Carregamentos,
    b_pilar:      float          = 0.20,
    h_pilar:      float          = 0.20,
    H_pilar:      float          = 7.0,
    s:            float          = 1.00,
    sistema:      str            = "3rotulas",
    params_vento: ParametrosVento | None = None,
) -> dict:
    """
    Verifica flexo-compressão da viga e compressão do pilar.

    Pórtico de 3 rótulas:
        Viga : EC5 §6.3.2 com M + N  → verifica_flexao()
        Pilar: EC5 §6.3.2 com N puro → verifica_pilar()

    Args:
        geo          : Geometria da viga principal
        mat          : Material (k_mod duração curta — vento dominante)
        load         : Carregamentos com combinações EN 1990
        b_pilar      : Largura da seção do pilar (m)
        h_pilar      : Altura da seção do pilar no plano do pórtico (m)
        H_pilar      : Comprimento do pilar (m)
        s            : Espaçamento entre terças (m) — l_ef fora do plano
        sistema      : "3rotulas" (único sistema suportado nesta versão)
        params_vento : Não utilizado — mantido por compatibilidade

    Returns:
        dict consolidado com resultados da viga, do pilar e η governante
    """
    # ── Viga — flexo-compressão EC5 §6.3.2 ───────────────────
    res_viga = verifica_flexao(geo, mat, load, s=s)

    # ── Pilar — compressão simples EC5 §6.3.2 ────────────────
    N_d_pilar = load.V_max_ELU()   # kN — reação vertical
    res_pilar = verifica_pilar(
        mat=mat,
        b=b_pilar,
        h=h_pilar,
        H=H_pilar,
        N_d=N_d_pilar,
    )

    # ── Resultado consolidado ─────────────────────────────────
    eta_viga  = res_viga["eta"]
    eta_pilar = res_pilar["eta"]
    eta_gov   = max(eta_viga, eta_pilar)
    elem_gov  = "viga" if eta_viga >= eta_pilar else "pilar"

    return {
        # ── Viga ─────────────────────────────────────────────
        "viga": {
            "M_max_kNm":      res_viga["M_max_kNm"],
            "N_d_kN":         res_viga["N_d_kN"],
            "x_Mmax_m":       res_viga["x_Mmax_m"],
            "h_x_m":          res_viga["h_x_m"],
            "lambda_rel_y":   res_viga["lambda_rel_y"],
            "k_c_y":          res_viga["k_c_y"],
            "sigma_c_MPa":    res_viga["sigma_c_MPa"],
            "sigma_m_MPa":    res_viga["sigma_m_MPa"],
            "eta_no_plano":   res_viga["eta_no_plano"],
            "eta_fora_plano": res_viga["eta_fora_plano"],
            "eta":            eta_viga,
            "ok":             res_viga["ok"],
            "plano_gov":      res_viga["plano_gov"],
        },
        # ── Pilar ─────────────────────────────────────────────
        "pilar": {
            "b_m":          b_pilar,
            "h_m":          h_pilar,
            "H_m":          H_pilar,
            "l_ef_m":       res_pilar["l_ef_m"],
            "lambda":       res_pilar["lambda"],
            "lambda_rel":   res_pilar["lambda_rel"],
            "k_c":          res_pilar["k_c"],
            "N_d_kN":       N_d_pilar,
            "sigma_c_MPa":  res_pilar["sigma_c_MPa"],
            "eta":          eta_pilar,
            "ok":           res_pilar["ok"],
        },
        # ── Consolidado ───────────────────────────────────────
        "eta":      round(eta_gov, 4),
        "ok":       eta_gov <= 1.0,
        "elem_gov": elem_gov,
        "norma":    "EC5 §6.3.2 Eq. 6.23",
        "sistema":  "biarticulada",
    }


# ── Execução direta ───────────────────────────────────────────────────────────

if __name__ == "__main__":

    from mlc_projeto.core.loads import carregamentos_com_vento

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

    res = verifica_flexo_compressao(
        geo=geo, mat=mat, load=load,
        b_pilar=0.20, h_pilar=0.20,
        H_pilar=7.0, s=1.00,
    )

    print("VERIFICAÇÃO FLEXO-COMPRESSÃO — EC5 §6.3.2")
    print(f"Sistema: {res['sistema']}\n")

    v = res["viga"]
    p = res["pilar"]

    print(f"  VIGA:")
    print(f"    M_d={v['M_max_kNm']:.2f} kN·m | N_d={v['N_d_kN']:.2f} kN")
    print(f"    σ_c={v['sigma_c_MPa']:.4f} MPa | σ_m={v['sigma_m_MPa']:.4f} MPa")
    print(f"    k_c={v['k_c_y']:.4f} | η_no_plano={v['eta_no_plano']:.4f} | "
          f"η_fora_plano={v['eta_fora_plano']:.4f}")
    print(f"    η_viga = {v['eta']:.4f}  "
          f"({'✓' if v['ok'] else '✗'})\n")

    print(f"  PILAR ({p['b_m']}×{p['h_m']} m):")
    print(f"    N_d={p['N_d_kN']:.2f} kN | M_d=0 kN·m")
    print(f"    σ_c={p['sigma_c_MPa']:.4f} MPa")
    print(f"    λ={p['lambda']:.1f} | λ_rel={p['lambda_rel']:.4f} | "
          f"k_c={p['k_c']:.4f}")
    print(f"    η_pilar = {p['eta']:.4f}  "
          f"({'✓' if p['ok'] else '✗'})\n")

    ok = "✓ APROVADO" if res["ok"] else "✗ REPROVADO"
    print(f"  η GOVERNANTE = {res['eta']:.4f}  "
          f"({res['elem_gov']} governa)  → {ok}")