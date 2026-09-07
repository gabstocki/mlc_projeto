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

    Returns:
        dict com as linhas do quadro, os totais e a declaração de escopo.
    """
    # Compressão: maior reação vertical de ELU; tração: menor (uplift).
    N_comp = max(abs(float(c.V_max_kN)) for c in load.combinacoes_ELU().values())

    # Empuxo do arco na base (0 na Opção B — o pilar birotulado não o transmite).
    H_arco = abs(float(load.H_ELU()))

    # Horizontais dos contraventamentos, por painel, à fundação.
    H_long   = float(cv_vertical.get("H_base_kN", 0.0))
    H_transv = float(cv_transversal.get("H_base_kN", 0.0))

    linhas = [
        CargaBase(
            tipo="Extremidade (pilar lateral)",
            n_bases=max(0, n_pilares_linha * 2 - 4),
            N_comp_kN=N_comp,
            N_tracao_kN=float(res_succao["N_uplift_ext_kN"]),
            H_kN=H_arco,
            origem="reação vertical + uplift de sucção; H do arco (0 na Opção B)",
        ),
        CargaBase(
            tipo="Central (pilar do apoio partilhado)",
            n_bases=n_pilares_linha,
            N_comp_kN=2.0 * N_comp,
            N_tracao_kN=float(res_succao["N_uplift_cen_kN"]),
            H_kN=0.0,
            origem="soma das reações dos dois vãos; empuxos cancelam-se",
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

    return {
        "titulo": "Cargas de cálculo (ELU) destinadas à fundação",
        "linhas": [c.como_linha() for c in linhas],
        "cargas": linhas,
        "totais": {
            "H_longitudinal_total_kN": round(H_long * n_paineis_long, 1),
            "H_transversal_total_kN":  round(H_transv * n_paineis_transv, 1),
            "n_paineis_long":          n_paineis_long,
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
