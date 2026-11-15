"""
output/custo.py — Estimativa preliminar de custo, gerada pelo pipeline (issue 99).

As quantidades saem da própria execução:
  · vigas: integração de A(x) ao longo do vão, com o balanço do beiral
    (`predim.varredura_global.volume_mlc_m3`, o mesmo volume da varredura);
  · terças: por lista de peças (issue 117) — todas as linhas, inclusive as de ponta
    (T0 e T18), no comprimento com os oitões, e o acréscimo de largura das escoras
    centrais; a relação g_terças·A/γ, que supunha espaçamento uniforme até os
    beirais, subestimava o volume em ~12 %;
  · pilares: maciços (b × h × comprimento da madeira), bipartidos (2 lâminas até a
    escora) e os espaçadores das lâminas, como na lista do desenho;
  · aço de contraventamento: massa de cada sistema, calculada nos módulos de CV.

Os preços e percentuais são DADOS DE ENTRADA declarados (cotação a confirmar), não
resultado do cálculo. Escreve tese/tab_custo_quantidades.tex, tab_custo_composicao.tex,
tab_custo_sensibilidade.tex e devolve as macros de texto. Não editar os .tex à mão.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mlc_projeto.output.formatacao import fmt_sig

PRECO_MLC_M3 = 5200.0            # R$/m³ — valor central do patamar de venda (4.000–6.400)
PRECO_MLC_FAIXA = (4000.0, 6400.0)
PRECO_ACO_KG = 18.0              # R$/kg — S235 em barra, fabricado e montado
PCT_LIGACOES = 0.15              # do custo da madeira
PCT_MONTAGEM = 0.12              # do subtotal de materiais
PCT_BDI = 0.25                   # do subtotal direto


@dataclass(frozen=True)
class Quantidades:
    V_vigas: float
    V_tercas: float
    V_pilares: float
    n_vigas: int
    n_pilares: int
    n_bipartidos: int
    m_cv_vertical: float
    m_cv_cobertura: float
    m_cv_transversal: float
    d_cv_vertical: float
    d_cv_cobertura: float
    d_cv_transversal: float
    area_planta: float
    m_cv_diafragma: float = 0.0     # cruzes CV-D da alma do diafragma (issue 110)
    d_cv_diafragma: float = 0.0
    V_espacadores: float = 0.0      # espaçadores dos pilares bipartidos (issue 117)
    n_linhas_tercas: int = 0
    L_terca: float = 0.0

    @property
    def V_mlc(self) -> float:
        return self.V_vigas + self.V_tercas + self.V_pilares + self.V_espacadores

    @property
    def m_aco(self) -> float:
        return (self.m_cv_vertical + self.m_cv_cobertura + self.m_cv_transversal
                + self.m_cv_diafragma)


def volume_tercas_m3(*, n_linhas: int, L_m: float, b_m: float, h_m: float,
                     n_escoras_largas: int = 0, L_escora_m: float = 0.0,
                     b_escora_m: float = 0.0) -> float:
    """Terças por lista de peças: linhas × comprimento × seção, mais o acréscimo
    de largura das escoras que substituem a terça em algumas baías."""
    return (n_linhas * L_m * b_m * h_m
            + n_escoras_largas * L_escora_m * max(b_escora_m - b_m, 0.0) * h_m)


def volume_espacadores_m3(*, n_bipartidos: int, L_lamina_mm: float, l1_mm: float,
                          a_mm: float, h_l_mm: float, comp_mm: float = 450.0) -> float:
    """Espaçadores (ES-01 da lista do pilar bipartido): um a cada l1, a × h_l × 450."""
    n_pack = int(L_lamina_mm // l1_mm) + 1
    return n_bipartidos * n_pack * a_mm * h_l_mm * comp_mm * 1e-9


def compor(q: Quantidades, preco_mlc: float = PRECO_MLC_M3) -> dict:
    mlc = q.V_mlc * preco_mlc
    aco = q.m_aco * PRECO_ACO_KG
    lig = PCT_LIGACOES * mlc
    mont = PCT_MONTAGEM * (mlc + aco + lig)
    direto = mlc + aco + lig + mont
    bdi = PCT_BDI * direto
    total = direto + bdi
    return {"mlc": mlc, "aco": aco, "ligacoes": lig, "montagem": mont, "direto": direto,
            "bdi": bdi, "total": total, "por_m2": total / q.area_planta}


def _r(x: float) -> str:
    """Valor monetário com três algarismos significativos: é uma estimativa."""
    return fmt_sig(x, 3)


def _v(x: float) -> str:
    """Quantidade com três algarismos significativos (regra de precisão do cap. 7)."""
    return fmt_sig(x, 3)


def _diam(d: float) -> str:
    return f"$\\varnothing$ {d:.0f} mm"


def tabelas(q: Quantidades) -> dict[str, str]:
    c = compor(q)
    cab = "% {nome} — GERADA por mlc_projeto/output/custo.py (issue 99). NÃO EDITAR À MÃO."
    quant = [cab.format(nome="tab_custo_quantidades.tex"),
             r"\tabela{Quantidades de madeira lamelada colada e de aço de contraventamento}{\footnotesize",
             r"\begin{tabular}{llrr}", r"\toprule",
             r"    \textbf{Material} & \textbf{Elemento} & \textbf{Quantidade} & \textbf{Unidade} \\",
             r"\midrule",
             f"    MLC GL24h & Vigas principais ({q.n_vigas}), com os beirais & {_v(q.V_vigas)} & m\\textsuperscript{{3}} \\\\",
             (f"              & Terças ({q.n_linhas_tercas} linhas de {fmt_sig(q.L_terca, 3)} m, com as escoras) & {_v(q.V_tercas)} & m\\textsuperscript{{3}} \\\\"
              if q.n_linhas_tercas else
              f"              & Terças                     & {_v(q.V_tercas)} & m\\textsuperscript{{3}} \\\\"),
             f"              & Pilares ({q.n_pilares}, dos quais {q.n_bipartidos} bipartidos) & {_v(q.V_pilares)} & m\\textsuperscript{{3}} \\\\",
             ] + ([f"              & Espaçadores dos pilares bipartidos & {_v(q.V_espacadores)} & m\\textsuperscript{{3}} \\\\"]
                  if q.V_espacadores else []) + [
             r"\addlinespace",
             f"    \\textbf{{Subtotal MLC}} & & \\textbf{{{_v(q.V_mlc)}}} & \\textbf{{m\\textsuperscript{{3}}}} \\\\",
             r"\midrule",
             f"    Aço S235 & Contraventamento vertical, {_diam(q.d_cv_vertical)} & {_v(q.m_cv_vertical)} & kg \\\\",
             f"             & Contraventamento da cobertura, {_diam(q.d_cv_cobertura)} & {_v(q.m_cv_cobertura)} & kg \\\\",
             f"             & Contraventamento transversal, {_diam(q.d_cv_transversal)} & {_v(q.m_cv_transversal)} & kg \\\\",
             ] + ([f"             & Alma do diafragma (CV-D), {_diam(q.d_cv_diafragma)} & {_v(q.m_cv_diafragma)} & kg \\\\"]
                  if q.m_cv_diafragma else []) + [
             r"\addlinespace",
             f"    \\textbf{{Subtotal aço}} & & \\textbf{{{_v(q.m_aco)}}} & \\textbf{{kg}} \\\\",
             r"\bottomrule",
             r"\end{tabular}}{Elaborado pelo autor (2026)}{custo-quantidades}{}{}", ""]
    comp = [cab.format(nome="tab_custo_composicao.tex"),
            r"\tabela{Composição do custo estimado da estrutura}{\footnotesize",
            r"\begin{tabular}{llr}", r"\toprule",
            r"    \textbf{Parcela} & \textbf{Origem} & \textbf{Valor (R\$)} \\", r"\midrule",
            f"    Material MLC            & \\autoref{{tab:custo-quantidades}} & {_r(c['mlc'])} \\\\",
            f"    Aço de contraventamento & \\autoref{{tab:custo-quantidades}} & {_r(c['aco'])} \\\\",
            f"    Ligações e ferragens    & Percentual                      & {_r(c['ligacoes'])} \\\\",
            f"    Montagem                & Percentual                      & {_r(c['montagem'])} \\\\",
            r"\addlinespace",
            f"    \\textbf{{Subtotal direto}} & & \\textbf{{{_r(c['direto'])}}} \\\\", r"\midrule",
            f"    BDI                     & Percentual                      & {_r(c['bdi'])} \\\\",
            r"\addlinespace",
            f"    \\textbf{{Total estimado}} & & \\textbf{{{_r(c['total'])}}} \\\\",
            r"\bottomrule",
            r"\end{tabular}}{Elaborado pelo autor (2026)}{custo-composicao}{}{}", ""]
    sens = [cab.format(nome="tab_custo_sensibilidade.tex"),
            r"\tabela{Custo total estimado em função do preço unitário da MLC}{\footnotesize",
            r"\begin{tabular}{lrrr}", r"\toprule",
            r"    \textbf{Cenário} & \textbf{R\$/m\textsuperscript{3}} & \textbf{Total (R\$)} & \textbf{R\$/m\textsuperscript{2}} \\",
            r"\midrule"]
    for rot, p, neg in (("Limite inferior de mercado", PRECO_MLC_FAIXA[0], False),
                        ("Adotado", PRECO_MLC_M3, True),
                        ("Limite superior de mercado", PRECO_MLC_FAIXA[1], False)):
        cc = compor(q, p)
        cel = [rot, f"{p:,.0f}".replace(",", "."), _r(cc["total"]), _r(cc["por_m2"])]
        if neg:
            cel = [f"\\textbf{{{x}}}" for x in cel]
        sens.append("    " + " & ".join(cel) + r" \\")
    sens += [r"\bottomrule",
             r"\end{tabular}}{Elaborado pelo autor (2026)}{custo-sensibilidade}{}{}", ""]
    return {"tab_custo_quantidades.tex": "\n".join(quant),
            "tab_custo_composicao.tex": "\n".join(comp),
            "tab_custo_sensibilidade.tex": "\n".join(sens)}


def macros_custo(q: Quantidades, V_vigas_min: float | None = None) -> str:
    c = compor(q)
    pm = lambda x: f"{round(100 * x):d}"
    L = [f"\\newcommand{{\\custoTotal}}{{{_r(c['total'])}}}",
         f"\\newcommand{{\\custoPorMetro}}{{{_r(c['por_m2'])}}}",
         f"\\newcommand{{\\custoPorMetroEn}}{{{_r(c['por_m2']).replace('.', ',')}}}",
         f"\\newcommand{{\\custoTotalMi}}{{{fmt_sig(c['total'] / 1e6, 3)}}}",
         f"\\newcommand{{\\custoTotalMiEn}}{{{fmt_sig(c['total'] / 1e6, 3, decimal='.')}}}",
         f"\\newcommand{{\\custoArea}}{{{q.area_planta:,.0f}}}".replace(",", "."),
         f"\\newcommand{{\\custoPctMadeira}}{{{pm(c['mlc'] / c['total'])}}}",
         f"\\newcommand{{\\custoPctAco}}{{{pm(c['aco'] / c['total'])}}}",
         f"\\newcommand{{\\custoVolTercas}}{{{_v(q.V_tercas)}}}",
         f"\\newcommand{{\\custoVolMLC}}{{{_v(q.V_mlc)}}}",
         f"\\newcommand{{\\custoMassaAco}}{{{_v(q.m_aco)}}}"]
    if V_vigas_min is not None:
        dif = (q.V_vigas - V_vigas_min) * PRECO_MLC_M3
        L += [f"\\newcommand{{\\custoPctVolMin}}{{{pm(V_vigas_min / q.V_vigas)}}}",
              f"\\newcommand{{\\custoDifVolMin}}{{{_r(dif / 1e3)}}}"]
    return "\n".join(L) + "\n"


def gerar_custo(tese: Path, q: Quantidades, V_vigas_min: float | None = None) -> dict:
    for nome, txt in tabelas(q).items():
        (tese / nome).write_text(txt, encoding="utf-8")
    c = compor(q)
    c["macros"] = macros_custo(q, V_vigas_min)
    return c
