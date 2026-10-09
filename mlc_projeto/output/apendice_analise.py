"""
output/apendice_analise.py — Apêndice de análise estática da viga (issue 51).

Gera, a partir das combinações do pipeline, o apêndice da monografia com:

    · os diagramas M/V/N da combinação governante;
    · os diagramas M/V/N de TODAS as combinações ELU sobrepostos;
    · a tabela de esforços por combinação (cargas por meia-água, M, reações,
      cortante e normal no eixo da peça).

Os números saem de `Carregamentos` (os mesmos que alimentam as verificações).
O .tex e as figuras são regenerados a cada execução do pipeline; não editar à mão.
"""

from __future__ import annotations

import math
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt     # noqa: E402
import numpy as np                  # noqa: E402

from mlc_projeto.output.figuras import plot_diagramas_MVN   # noqa: E402
from mlc_projeto.output.formatacao import fmt_sig           # noqa: E402

FIG_GOV = "analise_MVN_governante.pdf"
FIG_TODAS = "analise_MVN_combinacoes.pdf"


def _n(x: float, d: int | None = None) -> str:
    """
    Três algarismos significativos, vírgula decimal (issue 53); `d` ignorado.
    Resultados de cálculo: os zeros finais contam como significativos (2,10).
    """
    s = fmt_sig(float(x), zeros=True)
    return "$-$" + s[1:] if s.startswith("-") else s


def _rotulo_padrao(pid: str) -> tuple[str, str]:
    """('t1, esq.' | 'α = 90°, b1', c_pi) a partir do id do padrão."""
    m = re.match(r"T10_(?:(t\d)_(esq|dir)|a90_(b\d))_cpi([+-][\d.]+)", pid)
    if not m:
        return pid, ""
    t, lado, faixa, cpi = m.groups()
    pad = (f"$\\alpha = 90^\\circ$, {faixa}" if faixa
           else f"$\\alpha = 0^\\circ$, {t}, {'esq.' if lado == 'esq' else 'dir.'}")
    cpi = cpi.replace(".", "{,}")
    return pad, f"${cpi}$"


def linhas_esforcos(load) -> list[dict]:
    """
    Esforços de cada combinação ELU física, agrupadas por expressão e numeradas
    em sequência. V e N extremos estão nos apoios e são tomados da decomposição
    analítica no eixo (issue 12) — o gradiente numérico do diagrama é unilateral
    nas extremidades e os subestima em ~0,5 %.
    """
    combos = load.combinacoes
    ordem = ("1,35G+1,5W", "0,9G+1,5W", "1,35G+1,5Q")
    tab = sorted(load.tabela_combinacoes(), key=lambda t: ordem.index(t["combo"]))
    th = math.atan(math.tan(load.geo.alpha_rad) / 2.0)
    cs, sn = math.cos(th), math.sin(th)
    linhas = []
    for i, t in enumerate(tab, start=1):
        c = combos[t["nome"]]
        d = load.diagramas_MVN_ELU(c)
        R_A, R_B, H = d["R_A_kN"], d["R_B_kN"], d["H_kN"]
        V_ap = (R_A * cs - H * sn, -(R_B * cs - H * sn))
        N_ap = (H * cs + R_A * sn, H * cs + R_B * sn)
        pad, cpi = (("sem vento", "") if t["grupo"] == "Q"
                    else _rotulo_padrao(t["padrao"]))
        # governantes pelos mesmos critérios da tabela de combinações (issue 28)
        gov = [{"|M|": "|M|", "uplift": "sucção"}[g]
               for g in t["governa"].split("+") if g in ("|M|", "uplift")]
        linhas.append({
            "n": i, "nome": c.nome, "combo": t["combo"], "padrao": pad, "cpi": cpi,
            "q_esq": c.q_esq, "q_dir": c.q_dir,
            "M_max": c.M_max_kNm, "x_M": c.x_Mmax_m, "M_cum": c.M_cumeeira_kNm,
            "R_A": R_A, "R_B": R_B,
            "V_max": max(V_ap, key=abs), "N_max": max(N_ap, key=abs),
            "duracao": c.duracao, "governa": ", ".join(gov),
            "_d": d,
        })
    return linhas


def plot_todas_combinacoes(load, geo, linhas: list[dict], out_path: Path) -> Path:
    """M/V/N de todas as combinações sobrepostos; as governantes em destaque."""
    fig, axes = plt.subplots(3, 1, figsize=(7.2, 7.6), sharex=True)
    fig.subplots_adjust(hspace=0.22, left=0.13, right=0.97, top=0.95, bottom=0.08)
    chaves = (("M", "M(x)  [kN·m]"), ("V", "V(x)  [kN]"), ("N", "N(x)  [kN]"))
    destaque = {}
    for l in linhas:
        if "|M|" in l["governa"]:
            destaque[l["nome"]] = ("#1f4e79", f"{l['n']}: governante de |M|")
        elif "sucção" in l["governa"]:
            destaque[l["nome"]] = ("#8c3b00", f"{l['n']}: governante de sucção")
    for ax, (k, ylab) in zip(axes, chaves):
        ax.axhline(0.0, color="0.4", lw=0.8)
        ax.axvline(float(geo.L) / 2.0, color="0.7", lw=0.7, ls="--")
        for l in linhas:
            if l["nome"] in destaque:
                continue
            ax.plot(l["_d"]["x"], l["_d"][k], color="0.65", lw=0.7)
        for l in linhas:
            if l["nome"] in destaque:
                cor, rot = destaque[l["nome"]]
                ax.plot(l["_d"]["x"], l["_d"][k], color=cor, lw=1.8, label=rot)
        ax.set_ylabel(ylab, fontsize=9)
        ax.grid(True, alpha=0.25, lw=0.5)
        ax.tick_params(labelsize=8)
    axes[0].plot([], [], color="0.65", lw=0.7, label="demais combinações")
    axes[0].legend(fontsize=7.5, loc="upper right", framealpha=0.9)
    axes[2].set_xlabel("x  [m]  (cumeeira em L/2, tracejado)", fontsize=9)
    fig.suptitle(f"Diagramas de esforços — {len(linhas)} combinações ELU", fontsize=10)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, format="pdf")
    plt.close(fig)
    return out_path


def gerar_apendice_analise(load, geo, tese_dir: Path,
                           nome_tex: str = "apendiceC.tex") -> Path:
    """Escreve o apêndice de análise estática e as duas figuras em tese_dir/fig."""
    tese_dir = Path(tese_dir)
    linhas = linhas_esforcos(load)
    plot_diagramas_MVN(load, geo, tese_dir / "fig" / FIG_GOV)
    plot_todas_combinacoes(load, geo, linhas, tese_dir / "fig" / FIG_TODAS)

    gov = next(l for l in linhas if "|M|" in l["governa"])
    suc = next(l for l in linhas if "sucção" in l["governa"])
    n_W = sum(l["combo"].startswith("1,35G+1,5W") for l in linhas)
    n_S = sum(l["combo"].startswith("0,9G") for l in linhas)
    M_env = max(linhas, key=lambda l: l["M_max"])
    M_neg = min(linhas, key=lambda l: l["M_max"])

    P: list[str] = []
    a = P.append
    a("% =============================================================================\n"
      f"% {nome_tex} — ANÁLISE ESTÁTICA DA VIGA PRINCIPAL\n"
      "% GERADO AUTOMATICAMENTE por mlc_projeto/output/apendice_analise.py a cada\n"
      "% execução do pipeline (issue 51). NÃO EDITAR À MÃO.\n"
      "% =============================================================================\n\n"
      "\\chapter{ANÁLISE ESTÁTICA DA VIGA PRINCIPAL}\\label{ap:analise-estatica}\n\n"
      "Este apêndice reúne os resultados da análise estática da viga principal, "
      "biapoiada e sem empuxo, descrita no \\autoref{cap:modelagem}, para todas as "
      f"combinações de estado-limite último: {n_W} com vento dominante sob "
      f"$1{{,}}35\\,G + 1{{,}}5\\,W$, {n_S} com vento de sucção sob "
      "$0{,}9\\,G + 1{,}5\\,W$, uma para cada padrão de coeficientes de pressão, "
      "e a de sobrecarga dominante $1{,}35\\,G + 1{,}5\\,Q$. Os esforços são "
      "referidos ao eixo da peça: o cortante $V$ é perpendicular ao eixo e o "
      "esforço normal $N$ é positivo em compressão. Os valores são os da execução "
      "do programa que produziu o memorial, de onde este apêndice é gerado.\n\n")

    expr = {"1,35G+1,5W": "$1{,}35\\,G + 1{,}5\\,W$",
            "0,9G+1,5W": "$0{,}9\\,G + 1{,}5\\,W$",
            "1,35G+1,5Q": "$1{,}35\\,G + 1{,}5\\,Q$"}
    governa = ["a flexão"]
    if gov is max(linhas, key=lambda l: abs(l["V_max"])):
        governa.append("o cortante")
    if gov is max(linhas, key=lambda l: abs(l["N_max"])):
        governa.append("o esforço normal")
    governa = (", ".join(governa[:-1]) + " e " + governa[-1]
               if len(governa) > 1 else governa[0])
    a("\\section{COMBINAÇÃO GOVERNANTE}\\label{sec:an-governante}\n\n"
      f"A combinação {gov['n']}, {expr[gov['combo']]}, "
      f"governa {governa} da viga, com momento máximo "
      f"de {_n(gov['M_max'], 2)}~kN$\\cdot$m a {_n(gov['x_M'], 2)}~m do apoio. "
      "A \\autoref{fig:an-mvn-governante} apresenta os seus diagramas.\n\n"
      "\\figura\n{Diagramas de esforços da combinação governante}\n{0.85}\n"
      f"{{fig/{FIG_GOV}}}\n{{Elaborado pelo autor (2026)}}\n"
      "{an-mvn-governante}\n{}\n{}\n\n")

    a("\\section{TODAS AS COMBINAÇÕES}\\label{sec:an-todas}\n\n"
      "A \\autoref{fig:an-mvn-todas} sobrepõe os diagramas das "
      f"{len(linhas)} combinações, e a \\autoref{{tab:an-esforcos}} lista os "
      "esforços de cada uma. O momento varia entre "
      f"{_n(M_neg['M_max'])}~kN$\\cdot$m, na combinação {M_neg['n']}, e "
      f"{_n(M_env['M_max'])}~kN$\\cdot$m, na combinação {M_env['n']}. A combinação "
      f"{suc['n']} é a de maior sucção e governa o arrancamento das bases e a "
      "flambagem lateral com o intradorso comprimido.\n\n"
      "\\figura\n{Diagramas de esforços de todas as combinações de "
      "estado-limite último}\n{0.85}\n"
      f"{{fig/{FIG_TODAS}}}\n{{Elaborado pelo autor (2026)}}\n"
      "{an-mvn-todas}\n{}\n{}\n\n")

    a("\\tabela{Esforços na viga principal por combinação de estado-limite último}"
      "{\\scriptsize\\setlength{\\tabcolsep}{2.6pt}\n"
      "\\begin{tabular}{@{}rllrrrrrrrrr@{}}\n"
      "\\toprule\n"
      "    \\textbf{Nº} & \\textbf{Padrão de vento} & \\textbf{$c_{pi}$} & "
      "\\textbf{$q_{esq}$} & \\textbf{$q_{dir}$} & \\textbf{$M_{max}$} & "
      "\\textbf{$x$} & \\textbf{$M_{cum}$} & \\textbf{$R_A$} & \\textbf{$R_B$} & "
      "\\textbf{$V_{max}$} & \\textbf{$N_{max}$} \\\\\n"
      "    & & & \\multicolumn{2}{c}{(kN/m)} & (kN$\\cdot$m) & (m) & "
      "(kN$\\cdot$m) & (kN) & (kN) & (kN) & (kN) \\\\\n")
    grupo = None
    titulos = {"1,35G+1,5W": "Vento dominante, " + expr["1,35G+1,5W"],
               "0,9G+1,5W": "Vento de sucção, " + expr["0,9G+1,5W"],
               "1,35G+1,5Q": "Sobrecarga dominante, " + expr["1,35G+1,5Q"]}
    for l in linhas:
        if l["combo"] != grupo:
            grupo = l["combo"]
            a("\\midrule\n"
              f"    \\multicolumn{{12}}{{@{{}}l}}{{\\textit{{{titulos[grupo]}}}}} \\\\\n")
        ini, fim = ("\\textbf{", "}") if l["governa"] else ("", "")
        cel = [str(l["n"]), l["padrao"], l["cpi"],
               _n(l["q_esq"], 2), _n(l["q_dir"], 2), _n(l["M_max"]),
               _n(l["x_M"], 2), _n(l["M_cum"]), _n(l["R_A"]), _n(l["R_B"]),
               _n(l["V_max"]), _n(l["N_max"], 2)]
        a("    " + " & ".join(f"{ini}{c}{fim}" if c else "" for c in cel) + " \\\\\n")
    a("\\bottomrule\n\\end{tabular}}"
      "{Elaborado pelo autor (2026)}{an-esforcos}{}{}\n\n"
      "Na tabela, $q_{esq}$ e $q_{dir}$ são as cargas de cálculo por meia-água, "
      "positivas no sentido da gravidade; $x$ é a posição do momento máximo "
      "$M_{max}$ a partir do apoio esquerdo; $M_{cum}$ é o momento na cumeeira; "
      "$R_A$ e $R_B$ são as reações verticais nos apoios; $V_{max}$ e $N_{max}$ "
      "são o cortante e o esforço normal no eixo da peça, cujos extremos ocorrem "
      "nos apoios. "
      "As linhas em negrito são as combinações governantes. As combinações de "
      "vento têm duração curta e a de sobrecarga, duração média, o que define "
      "o $k_{mod}$ de cada verificação.\n")

    out = tese_dir / nome_tex
    out.write_text("".join(P), encoding="utf-8")
    return out
