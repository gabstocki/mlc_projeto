"""
output/cargas_fundacao.py — Quadro de cargas destinadas à fundação.

Propósito
---------
Este projeto NÃO dimensiona fundações: não há sondagem, e a prática adotada é
entregar ao projetista de fundações os ESFORÇOS que chegam a cada base, para
que ele as dimensione com os dados geotécnicos.

O módulo consolida esses esforços num quadro único, por TIPO DE BASE, com a
combinação governante de cada efeito. É o entregável de interface entre a
superestrutura e a fundação — e substitui a situação anterior, em que os
esforços existiam dispersos por vários módulos e nenhum documento os reunia.

O que este quadro NÃO é
-----------------------
Não é verificação de fundação. Não contém tensão admissível do solo, dimensão
da sapata em planta, deslizamento, tombamento, recalque nem armadura. Esses
itens dependem de sondagem e são responsabilidade do projeto de fundações.
O quadro declara isso explicitamente para que a ausência seja registrada, e não
confundida com "verificado".

Convenção de sinais
-------------------
    N_comp   > 0  compressão que desce à fundação
    N_tracao > 0  tração/arrancamento (uplift) — a fundação deve ancorar
    H        > 0  força horizontal na base, em módulo

Todos os valores são de CÁLCULO (ELU), nas combinações governantes de cada
efeito, salvo indicação em contrário na linha.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class CargaBase:
    """Esforços de cálculo numa base, com a origem de cada parcela."""
    tipo:        str
    n_bases:     int
    N_comp_kN:   float
    N_tracao_kN: float
    H_kN:        float
    origem:      str

    def como_linha(self) -> dict:
        return {
            "Base":            self.tipo,
            "n":               self.n_bases,
            "N_comp (kN)":     round(self.N_comp_kN, 1),
            "N_tração (kN)":   round(self.N_tracao_kN, 1),
            "H (kN)":          round(self.H_kN, 1),
            "Origem":          self.origem,
        }


def montar_quadro_cargas_fundacao(
    *,
    load,
    res_succao: dict,
    cv_vertical: dict,
    cv_transversal: dict,
    n_pilares_linha: int,
    n_linhas_portico: int,
    n_paineis_long: int,
    n_paineis_transv: int,
    cv_vertical_central: dict | None = None,
    n_paineis_central: int = 0,
    V_base_corrente_kN: float = 0.0,
    pilar_frontao: dict | None = None,
    n_pilares_frontao: int = 0,
) -> dict:
    """
    Consolida os esforços de cálculo que chegam a cada tipo de base.

    Args:
        load             : Carregamentos (reações verticais e empuxo)
        res_succao       : saída de checks/elu/succao_uplift
        cv_vertical      : saída do contraventamento vertical (longitudinal)
        cv_transversal   : saída do contraventamento transversal (frontões)
        n_pilares_linha  : pilares por alinhamento ao longo do comprimento
        n_linhas_portico : alinhamentos de pilares
        n_paineis_*      : painéis de cruz em cada direção
        cv_vertical_central : contraventamento vertical da linha central (issue 64)
        V_base_corrente_kN  : cortante nas bases correntes — envelope do vento
                              no pilar e do impacto de veículo (acidental, issue 48)
        pilar_frontao    : saída de checks/elu/pilar_frontao (issue 52)
        n_pilares_frontao: quantidade de pilares de frontão

    Returns:
        dict com as linhas do quadro, os totais e a declaração de escopo.
    """
    # Compressão: maior reação vertical de ELU; tração: menor (uplift).
    N_comp = max(abs(float(c.V_max_kN)) for c in load.combinacoes_ELU_fisicas().values())

    # Empuxo do arco na base (0 na Opção B — o pilar birotulado não o transmite).
    H_arco = abs(float(load.H_ELU()))

    # Horizontais dos contraventamentos, por painel, à fundação.
    H_long   = float(cv_vertical.get("H_base_kN", 0.0))
    H_transv = float(cv_transversal.get("H_base_kN", 0.0))
    cvc = cv_vertical_central or {}
    H_cen = float(cvc.get("H_base_kN", 0.0))
    D_cen = float(cvc.get("N_uplift_kN", 0.0))
    # Montantes centrais: painéis contíguos, metade em cada extremidade; cada
    # grupo de k painéis tem k+1 pilares montantes (no pilar comum a dois
    # painéis o download de um anula o arrancamento do outro) — envelope.
    _k = int(n_paineis_central) // 2
    n_cen_cv = min(n_pilares_linha, 2 * (_k + 1)) if (cvc and _k) else 0

    linhas = [
        CargaBase(
            tipo="Extremidade (pilar lateral)",
            n_bases=max(0, n_pilares_linha * 2 - 4),
            N_comp_kN=N_comp,
            N_tracao_kN=float(res_succao["N_uplift_ext_kN"]),
            H_kN=max(H_arco, float(V_base_corrente_kN)),
            origem="reação vertical + uplift de sucção; H = impacto de veículo (acidental)",
        ),
        CargaBase(
            tipo="Central (pilar do apoio partilhado)",
            n_bases=n_pilares_linha - n_cen_cv,
            N_comp_kN=2.0 * N_comp,
            N_tracao_kN=float(res_succao["N_uplift_cen_kN"]),
            H_kN=float(V_base_corrente_kN),
            origem="soma das reações dos dois vãos; H = impacto de veículo (acidental)",
        ),
        CargaBase(
            tipo="Canto (montante de contraventamento)",
            n_bases=4,
            N_comp_kN=N_comp + float(cv_vertical.get("N_uplift_kN", 0.0))
                      + float(cv_transversal.get("N_uplift_kN", 0.0)),
            N_tracao_kN=float(res_succao["N_uplift_canto_kN"]),
            H_kN=H_long + H_transv,
            origem="reação + downloads dos dois painéis; H dos dois contraventamentos",
        ),
    ]
    if n_cen_cv:
        linhas.insert(2, CargaBase(
            tipo="Central montante (contraventamento)",
            n_bases=n_cen_cv,
            N_comp_kN=2.0 * N_comp + D_cen,
            N_tracao_kN=float(res_succao.get("N_uplift_cen_cv_kN", 0.0)),
            H_kN=H_cen,
            origem="2 reações + download do painel central; H do painel",
        ))
    if pilar_frontao and n_pilares_frontao:
        _b = pilar_frontao["base"]
        linhas.append(CargaBase(
            tipo="Pilar de frontão (montante do CV-T)",
            n_bases=int(n_pilares_frontao),
            N_comp_kN=float(pilar_frontao["montante"]["N_comp_kN"]),
            N_tracao_kN=float(_b["N_t_persistente_kN"]),
            H_kN=max(float(_b["V_persistente_kN"]), float(_b["V_acidental_kN"])),
            origem="peso próprio + download da cruz; H do painel (não apoia a viga)",
        ))

    return {
        "titulo": "Cargas de cálculo (ELU) destinadas à fundação",
        "linhas": [c.como_linha() for c in linhas],
        "cargas": linhas,
        "totais": {
            "H_longitudinal_total_kN": round(H_long * n_paineis_long
                                             + H_cen * n_paineis_central, 1),
            "H_transversal_total_kN":  round(H_transv * n_paineis_transv, 1),
            "n_paineis_long":          n_paineis_long + n_paineis_central,
            "n_paineis_transv":        n_paineis_transv,
            "n_linhas_portico":        n_linhas_portico,
        },
        "escopo": (
            "ESFORÇOS PARA DIMENSIONAMENTO DE FUNDAÇÃO POR TERCEIROS. Este "
            "projeto NÃO dimensiona fundações: não há sondagem. Não estão "
            "verificados tensão admissível do solo, dimensões da sapata em "
            "planta, deslizamento, tombamento, recalque nem armadura — todos "
            "dependem de investigação geotécnica."
        ),
        "premissas": [
            "Valores de CÁLCULO (ELU), nas combinações governantes de cada efeito.",
            "Tração = arrancamento; a fundação deve ancorá-la (peso próprio da "
            "sapata e do solo sobrejacente NÃO estão descontados aqui).",
            "A base de canto acumula uplift de sucção e os downloads dos "
            "painéis longitudinal e transversal — é a mais solicitada.",
            "A ancoragem chumbador–concreto (EN 1992-4) permanece NÃO VALIDADA "
            "enquanto não houver dados certificados do produto.",
        ],
    }


def imprimir_quadro(q: dict) -> None:
    """Imprime o quadro no formato do memorial."""
    print("\n" + "=" * 78)
    print(f"  {q['titulo'].upper()}")
    print("=" * 78)
    print(f"  {'Base':<38}{'n':>3}{'N_comp':>9}{'N_tração':>10}{'H':>8}")
    print(f"  {'-'*76}")
    for l in q["linhas"]:
        print(f"  {l['Base']:<38}{l['n']:>3}{l['N_comp (kN)']:>9.1f}"
              f"{l['N_tração (kN)']:>10.1f}{l['H (kN)']:>8.1f}")
    print(f"  {'-'*76}")
    t = q["totais"]
    print(f"  H longitudinal total = {t['H_longitudinal_total_kN']:.1f} kN "
          f"({t['n_paineis_long']} painéis)")
    print(f"  H transversal  total = {t['H_transversal_total_kN']:.1f} kN "
          f"({t['n_paineis_transv']} painéis/frontão)")
    print(f"\n  ⚠ {q['escopo']}")


# ── Esforços CARACTERÍSTICOS por ação (issue 102) ─────────────────────────────

def esforcos_caracteristicos(*, load, geo, gamma_kNm3: float, pilares: dict,
                             H_pilar_mad_m: float, cv_vertical: dict,
                             cv_vertical_central: dict, cv_transversal: dict,
                             pilar_frontao: dict, V_impacto_kN: float,
                             V_vento_pilar_d_kN: float, gamma_Q: float = 1.5) -> list[dict]:
    """
    Esforços característicos em cada tipo de base, separados por ação, para que
    o projeto de fundações faça as suas próprias combinações (EN 1990):

      · G — reação da viga sob g_k (com o beiral) + peso próprio do pilar;
      · Q — reação sob q_k (sobrecarga de cobertura, categoria H);
      · W — vento: maior compressão e maior arrancamento entre os padrões de
        Cpe (reações da viga), mais a parcela dos painéis de contraventamento
        nas bases montantes e a força horizontal; para os painéis, cuja ação
        dominante é o vento, toma-se o valor de cálculo dividido por γ_Q;
      · A_d — choque de veículo (acidental, já característico): horizontal.

    Convenção: compressão > 0; arrancamento informado positivo na coluna própria.
    """
    from mlc_projeto.core.loads import analisar_biarticulada

    def _R(qe, qd, fG=0.0):
        # fG: fator da ação permanente, para o peso próprio variável (issue 114)
        r = analisar_biarticulada(q=0.5 * (qe + qd), L=geo.L, h0=geo.h0, h_ap=geo.h_ap,
                                  alpha_rad=geo.alpha_rad, b=geo.b, q_esq=qe, q_dir=qd,
                                  desenvolve_empuxo=load.empuxo_desenvolve, a_bal=geo.a_bal,
                                  g_var_kNm3=fG * load.gamma_mlc_kNm3
                                  if getattr(load, "peso_viga_variavel", False) else 0.0)
        return float(r["R_A_kN"]), float(r["R_B_kN"])      # A = externo, B = central

    RG = _R(load.g_k, load.g_k, fG=1.0)
    RQ = _R(load.q_k, load.q_k)
    RW = [_R(p["w_esq_kNm2"] * load.area_trib, p["w_dir_kNm2"] * load.area_trib)
          for p in load.padroes_vento]
    WA_c, WA_t = max(max(r[0] for r in RW), 0.0), max(-min(r[0] for r in RW), 0.0)
    WB_c, WB_t = max(max(r[1] for r in RW), 0.0), max(-min(r[1] for r in RW), 0.0)

    def _pp(chave):
        b, h = pilares[chave]
        return gamma_kNm3 * b * h * H_pilar_mad_m

    cvv_V = float(cv_vertical.get("N_uplift_kN", 0.0)) / gamma_Q
    cvv_H = float(cv_vertical.get("H_base_kN", 0.0)) / gamma_Q
    cvc_V = float(cv_vertical_central.get("N_uplift_kN", 0.0)) / gamma_Q
    cvc_H = float(cv_vertical_central.get("H_base_kN", 0.0)) / gamma_Q
    cvt_V = float(cv_transversal.get("N_uplift_kN", 0.0)) / gamma_Q
    cvt_H = float(cv_transversal.get("H_base_kN", 0.0)) / gamma_Q
    W_pil = V_vento_pilar_d_kN / gamma_Q
    linhas = [
        dict(base="Extremidade", G=RG[0] + _pp("lateral"), Q=RQ[0], W_c=WA_c, W_t=WA_t,
             W_H=W_pil, A_H=V_impacto_kN),
        dict(base="Central", G=2 * RG[1] + _pp("central"), Q=2 * RQ[1], W_c=2 * WB_c,
             W_t=2 * WB_t, W_H=W_pil, A_H=V_impacto_kN),
        dict(base="Central montante", G=2 * RG[1] + _pp("central"), Q=2 * RQ[1],
             W_c=2 * WB_c + cvc_V, W_t=2 * WB_t + cvc_V, W_H=cvc_H, A_H=V_impacto_kN),
        dict(base="Canto", G=RG[0] + _pp("canto"), Q=RQ[0], W_c=WA_c + cvv_V + cvt_V,
             W_t=WA_t + cvv_V + cvt_V, W_H=math.hypot(cvv_H, cvt_H), A_H=V_impacto_kN),
        dict(base="Pilar de frontão", G=float(pilar_frontao.get("G_k_kN", _pp("lateral"))), Q=0.0,
             W_c=cvt_V, W_t=cvt_V, W_H=cvt_H, A_H=V_impacto_kN),
    ]
    for l in linhas:
        for k in ("G", "Q", "W_c", "W_t", "W_H", "A_H"):
            l[k] = round(l[k], 1)
    return linhas


def gerar_tex_caracteristicos(linhas: list[dict], caminho) -> "Path":
    """Tabela LaTeX dos esforços característicos por ação (gerada pelo pipeline)."""
    from pathlib import Path
    from mlc_projeto.output.formatacao import fmt_sig

    def n(x):
        return fmt_sig(x, 3) if abs(x) >= 0.05 else "--"

    P = ["% tab_cargas_fundacao_k.tex — GERADO por mlc_projeto/output/cargas_fundacao.py "
         "(issue 102). NÃO EDITAR À MÃO.\n",
         "\\tabela{Esforços característicos por ação entregues ao projeto de fundação}"
         "{\\footnotesize\n\\begin{tabular}{lrrrrrr}\n\\toprule\n"
         "    & \\multicolumn{3}{c}{\\textbf{Vertical (kN)}} & \\textbf{Arranc. (kN)} & "
         "\\multicolumn{2}{c}{\\textbf{Horizontal (kN)}} \\\\\n"
         "    \\cmidrule(lr){2-4}\\cmidrule(lr){5-5}\\cmidrule(lr){6-7}\n"
         "    \\textbf{Base} & \\textbf{$G_k$} & \\textbf{$Q_k$} & \\textbf{$W_k$} & "
         "\\textbf{$W_k$} & \\textbf{$W_k$} & \\textbf{$A_d$} \\\\\n\\midrule\n"]
    for l in linhas:
        P.append(f"    {l['base']} & {n(l['G'])} & {n(l['Q'])} & {n(l['W_c'])} & "
                 f"{n(l['W_t'])} & {n(l['W_H'])} & {n(l['A_H'])} \\\\\n")
    P.append("\\bottomrule\n\\end{tabular}}{Elaborado pelo autor (2026)}"
             "{cargas-fundacao-k}{}{}\n")
    caminho = Path(caminho)
    caminho.write_text("".join(P), encoding="utf-8")
    return caminho


def gerar_tex_calculo(q: dict, caminho) -> "Path":
    """Tabela LaTeX dos esforços de CÁLCULO por tipo de base (gerada pelo pipeline)."""
    from pathlib import Path
    from mlc_projeto.output.formatacao import fmt_sig
    nomes = {"Extremidade (pilar lateral)": "Extremidade",
             "Central (pilar do apoio partilhado)": "Central",
             "Central montante (contraventamento)": "Central montante",
             "Canto (montante de contraventamento)": "Canto",
             "Pilar de frontão (montante do CV-T)": "Pilar de frontão"}
    P = ["% tab_cargas_fundacao.tex — GERADO por mlc_projeto/output/cargas_fundacao.py "
         "(issue 102). NÃO EDITAR À MÃO.\n",
         "\\tabela{Esforços de cálculo entregues ao projeto de fundação}{\\footnotesize\n"
         "\\begin{tabular}{lcrrr}\n\\toprule\n"
         "    \\textbf{Base} & \\textbf{Quantidade} & \\textbf{Compressão} & \\textbf{Tração} & "
         "\\textbf{Horizontal} \\\\\n    & & \\textbf{(kN)} & \\textbf{(kN)} & \\textbf{(kN)} \\\\\n"
         "\\midrule\n"]
    for c in q["cargas"]:
        P.append(f"    {nomes.get(c.tipo, c.tipo)} & {c.n_bases} & {fmt_sig(c.N_comp_kN, 3)} & "
                 f"{fmt_sig(c.N_tracao_kN, 3)} & {fmt_sig(c.H_kN, 3)} \\\\\n")
    P.append("\\bottomrule\n\\end{tabular}}{Elaborado pelo autor (2026)}{cargas-fundacao}{}{}\n")
    caminho = Path(caminho)
    caminho.write_text("".join(P), encoding="utf-8")
    return caminho
