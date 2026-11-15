"""
output/tab_retracao.py — Tabela da retração impedida pelas chapas embutidas (issue 115).

Gerada do resultado `retracao_chapas` a cada execução, em tese/tab_retracao.tex,
para que o quadro do cap. 8 não se desatualize em relação ao programa.
Linhas com o mesmo arranjo e a mesma solução são agrupadas.
"""

from __future__ import annotations

import re
from pathlib import Path

from mlc_projeto.output.formatacao import fmt_sig


def _solucao(s: str) -> str:
    m = re.search(r"curso ±(\d+)", s)
    if "já ovalizados" in s:
        return f"Já ovalizado, curso $\\pm {m.group(1)}$ mm"
    if "ovalizados" in s:
        return f"Ovalizado, curso $\\pm {m.group(1)}$ mm"
    return "Furo redondo"


def _rotulo(r: str) -> str:
    r = r.replace("–", "--").replace(" — ", ", ")
    return r.replace("_canto", " de canto").replace("_central", " central").replace("_", " ")


def _juntar(rots: list[str]) -> str:
    s = "; ".join(rots)
    return s[0].upper() + s[1:]


def tabela_retracao(grupos: list[dict]) -> str:
    linhas: dict[tuple, list[str]] = {}
    for g in grupos:
        chave = (int(g["n_perp"]), float(g["D_perp_mm"]), float(g["delta_mm"]), _solucao(g["solucao"]))
        linhas.setdefault(chave, []).append(_rotulo(g["rotulo"]))
    L = ["% tab_retracao.tex — GERADA por mlc_projeto/output/tab_retracao.py (issue 115). NÃO EDITAR À MÃO.",
         r"\tabela{Retração impedida pelas chapas embutidas}{\footnotesize",
         r"\begin{tabular}{p{5.6cm}crr p{3.4cm}}", r"\toprule",
         r"    \textbf{Ligação} & \textbf{Fileiras} & \textbf{$D_\perp$ (mm)} & \textbf{$\delta$ (mm)} & \textbf{Solução} \\",
         r"\midrule"]
    for (n, D, dl, sol), rot in linhas.items():
        L.append(f"    {_juntar(rot)} & {n} & {D:.0f} & $\\pm {fmt_sig(dl, 3)}$ & {sol} \\\\")
    L += [r"\bottomrule", r"\end{tabular}}{Elaborado pelo autor (2026)}{retracao}{}{}", ""]
    return "\n".join(L)


def gerar_tab_retracao(tese: Path, grupos: list[dict]) -> Path:
    p = Path(tese) / "tab_retracao.tex"
    p.write_text(tabela_retracao(grupos), encoding="utf-8")
    return p
