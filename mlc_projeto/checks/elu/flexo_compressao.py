"""
checks/elu/flexo_compressao.py — Flexo-compressão do pilar dimensionado.

Ponto de entrada chamado pelo main.py com a geometria do pilar já definida
após o comparativo de sistemas em pilares.py.

Delega o cálculo para pilares.py que contém a implementação completa
de esforços por sistema e verificação EC5 §6.3.2.

Parâmetros do pilar recomendados pelo comparativo:
    Sistema A (rígido-articulado): b=0,22m × h=0,80m | η=0,94
    Sistema B (totalmente rígido):  b=0,22m × h=0,80m | η=0,97
    Sistema C (isostático):         b=0,14m × h=0,30m | η=0,86

Referência: EC5 §6.3.2, Eq. 6.23
"""

from __future__ import annotations

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.loads     import Carregamentos
from mlc_projeto.core.wind      import ParametrosVento, calcular_vento

from mlc_projeto.checks.elu.pilares import (
    esforcos_pilar,
    verifica_pilar,
    Sistema,
)


def verifica_flexo_compressao(
    geo:          GeometriaViga,
    mat:          GlulamMaterial,
    load:         Carregamentos,
    b_pilar:      float   = 0.22,
    h_pilar:      float   = 0.80,
    H_pilar:      float   = 7.0,
    sistema:      Sistema = "A",
    params_vento: ParametrosVento | None = None,
) -> dict:
    """
    Verifica flexo-compressão do pilar com instabilidade — EC5 §6.3.2 Eq. 6.23.

    Calcula os esforços no pilar conforme o sistema estrutural adotado
    e verifica a condição:

        (σ_c,0,d / (k_c · f_c,0,d))² + σ_m,d / f_m,d ≤ 1,0

    Sistemas disponíveis:
        A — Rígido-articulado: knee-frame, base articulada | l_ef = 1,5H
        B — Totalmente rígido:  knee-frame, base engastada  | l_ef = 1,0H
        C — Isostático:         pino no canto, sem momento  | l_ef = 2,0H

    Args:
        geo          : Geometria da viga principal (para cálculo de EI_viga)
        mat          : Material do pilar (GL24h duração curta — vento dominante)
        load         : Carregamentos (fornece q_vert da combinação ELU_C2)
        b_pilar      : Largura da seção do pilar (m)
        h_pilar      : Altura da seção do pilar no plano do pórtico (m)
        H_pilar      : Comprimento do pilar (m)
        sistema      : "A", "B" ou "C"
        params_vento : Parâmetros de vento NBR 6123 para carga horizontal
                       Se None, usa pressão zero (conservador — só compressão)

    Returns:
        dict com esforços, k_c, λ_rel, η e ok
    """
    # ── Pressão de vento na fachada ───────────────────────────
    if params_vento is not None:
        res_v       = calcular_vento(params_vento)
        w_fachada   = res_v.pressoes["C1"]["barlavento_kNm2"]
    else:
        w_fachada   = 0.0

    q_horiz = w_fachada * H_pilar   # kN/m distribuído na altura

    # ── Carga vertical — combinação ELU_C2 ───────────────────
    q_vert  = load.combinacoes["ELU_C2"].q_tot   # kN/m

    # ── Rigidez da viga (valor médio) ─────────────────────────
    h_medio  = (geo.h0 + geo.h_ap) / 2
    EI_viga  = mat.E0_05 * 1e-3 * geo.b * h_medio**3 / 12  # kN·m²

    # ── Rigidez do pilar ──────────────────────────────────────
    EI_pilar = mat.E0_05 * 1e-3 * b_pilar * h_pilar**3 / 12  # kN·m²

    # ── Esforços no pilar pelo sistema ────────────────────────
    esf = esforcos_pilar(
        sistema  = sistema,
        q_vert   = q_vert,
        q_horiz  = q_horiz,
        L        = geo.L,
        H        = H_pilar,
        EI_viga  = EI_viga,
        EI_pilar = EI_pilar,
    )

    # ── Momento governante ────────────────────────────────────
    M_gov = max(abs(esf["M_d_topo_kNm"]), abs(esf["M_d_base_kNm"]))

    # ── Verificação EC5 §6.3.2 ────────────────────────────────
    res = verifica_pilar(
        mat     = mat,
        b       = b_pilar,
        h       = h_pilar,
        H       = H_pilar,
        N_d     = esf["N_d_kN"],
        M_d     = M_gov,
        sistema = sistema,
    )

    # ── Resultado consolidado ─────────────────────────────────
    return {
        # Geometria do pilar
        "sistema":        sistema,
        "b_pilar_m":      b_pilar,
        "h_pilar_m":      h_pilar,
        "H_pilar_m":      H_pilar,
        "l_ef_m":         res["l_ef_m"],
        # Esforços
        "N_d_kN":         esf["N_d_kN"],
        "M_d_topo_kNm":   esf["M_d_topo_kNm"],
        "M_d_base_kNm":   esf["M_d_base_kNm"],
        "M_d_gov_kNm":    round(M_gov, 3),
        "V_d_kN":         esf["V_d_kN"],
        "H_empuxo_kN":    esf["H_empuxo_kN"],
        # Verificação §6.3.2
        "lambda":         res["lambda"],
        "lambda_rel":     res["lambda_rel"],
        "k_c":            res["k_c"],
        "sigma_c_MPa":    res["sigma_c_MPa"],
        "sigma_m_MPa":    res["sigma_m_MPa"],
        "f_c0d_MPa":      res["f_c0d_MPa"],
        "f_md_MPa":       res["f_md_MPa"],
        # Resultado
        "eta":            res["eta"],
        "ok":             res["ok"],
        "norma":          "EC5 §6.3.2 Eq. 6.23",
        "nota":           esf["nota"],
    }


# ── Execução direta ───────────────────────────────────────────────────────────

if __name__ == "__main__":

    from mlc_projeto.core.loads import carregamentos_com_vento

    geo = GeometriaViga(L=20.25, h0=0.60, alpha_deg=4.5, b=0.26)
    mat = GlulamMaterial(classe="GL24h", classe_servico=2, duracao="curta")

    params_vento = ParametrosVento(
        V0=45.0, S1=1.0, categoria="IV", classe="B", S3=1.0,
        L=20.25, H1=1.0, h=7.0, dist_portico=5.75,
    )

    load = carregamentos_com_vento(
        geo=geo, mat=mat,
        g_area=1.50, q_area=0.25,
        L_t=5.75,
        params_vento=params_vento,
    )

    print("VERIFICAÇÃO DE FLEXO-COMPRESSÃO DOS PILARES")
    print("Geometria recomendada pelo comparativo: Sistema A, b=0,22m × h=0,80m\n")

    for sistema, b, h, descricao in [
        ("A", 0.22, 0.80, "Rígido-articulado — knee-frame, base articulada"),
        ("B", 0.22, 0.80, "Totalmente rígido  — knee-frame, base engastada"),
        ("C", 0.14, 0.30, "Isostático         — pino no canto + contraventamento"),
    ]:
        res = verifica_flexo_compressao(
            geo=geo, mat=mat, load=load,
            b_pilar=b, h_pilar=h, H_pilar=7.0,
            sistema=sistema,
            params_vento=params_vento,
        )

        ok = "✓" if res["ok"] else "✗"
        print(f"  {ok} Sistema {sistema} — {descricao}")
        print(f"     Seção: {b}×{h} m | l_ef={res['l_ef_m']} m | "
              f"λ={res['lambda']:.1f} | λ_rel={res['lambda_rel']:.4f} | "
              f"k_c={res['k_c']:.4f}")
        print(f"     N_d={res['N_d_kN']:.2f} kN | "
              f"M_d={res['M_d_gov_kNm']:.2f} kN·m | "
              f"H_emp={res['H_empuxo_kN']:.2f} kN")
        print(f"     σ_c={res['sigma_c_MPa']:.4f} MPa | "
              f"σ_m={res['sigma_m_MPa']:.4f} MPa | "
              f"f_c0d={res['f_c0d_MPa']:.4f} MPa")
        print(f"     η = {res['eta']:.4f}  ({'OK' if res['ok'] else 'REPROVADO'})\n")