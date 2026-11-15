"""
connections/soldas.py — Soldas de filete das ligações (issue 78).

Método simplificado da EN 1993-1-8 §4.5.3.3: a resultante por unidade de
comprimento, F_w,Ed, não excede F_w,Rd = f_vw,d·a, com
f_vw,d = f_u/(√3·β_w·γ_M2). Em cada ligação, n cordões de comprimento l
recebem uma força paralela a eles, uma normal e, quando há excentricidade fora
do plano, um momento resistido pelo binário entre cordões afastados de z:

    f_par = F_par/(n·l)     f_norm = F_norm/(n·l) + M/(z·l)
    F_w,Ed = √(f_par² + f_norm²)

A garganta é a menor da série com taxa ≤ 0,90 (componente dúctil), respeitando
a ≥ 3 mm e a ≤ 0,7·t da chapa mais fina (EN 1993-1-8 §4.5.2).
"""

from __future__ import annotations

import math

from mlc_projeto.connections.chapas_aco import ACO_CHAPA, GAMMA_M2

GARGANTAS_MM = (4.0, 5.0, 6.0, 8.0, 10.0, 12.0)
ETA_ALVO = 0.90


def f_vw_d(aco: str = "S275") -> float:
    """Resistência de cálculo ao corte da solda (MPa = N/mm²)."""
    return ACO_CHAPA[aco]["f_u"] / math.sqrt(3.0) / (ACO_CHAPA[aco]["beta_w"] * GAMMA_M2)


def filete(*, peca: str, F_par_kN: float = 0.0, F_norm_kN: float = 0.0, M_kNm: float = 0.0,
           z_mm: float | None = None, l_mm: float, n_cordoes: int = 2, t_min_mm: float,
           aco: str = "S275") -> dict:
    """Menor garganta da série que atende; η com a garganta adotada."""
    n, l = float(n_cordoes), float(l_mm)
    f_par = F_par_kN * 1e3 / (n * l)
    f_norm = F_norm_kN * 1e3 / (n * l)
    if M_kNm and z_mm:
        f_norm += M_kNm * 1e6 / (z_mm * l)
    F = math.hypot(f_par, f_norm)                       # N/mm
    fv = f_vw_d(aco)
    a_max = 0.7 * t_min_mm
    a = next((g for g in GARGANTAS_MM if g <= a_max + 1e-9 and F / (fv * g) <= ETA_ALVO),
             None)
    if a is None:
        a = max(g for g in GARGANTAS_MM if g <= a_max + 1e-9)
    eta = F / (fv * a)
    return {"peca": peca, "a_mm": a, "l_mm": l, "n_cordoes": n_cordoes,
            "F_w_Ed_Nmm": round(F, 1), "F_w_Rd_Nmm": round(fv * a, 1),
            "eta": round(eta, 4), "ok": eta <= 1.0, "a_max_mm": round(a_max, 1)}


def gerar_tex(itens: list[dict], caminho) -> "Path":
    """Quadro LaTeX das soldas (gerado pelo pipeline), em duas tabelas se longo."""
    from pathlib import Path
    from mlc_projeto.output.formatacao import fmt_eta
    linhas = []
    for x in itens:
        l = f"{x['l_mm']:.0f}" if x.get("l_mm") else "--"
        linhas.append(f"    {x['peca']} & {x['a_mm']:g} & {l} & {fmt_eta(x['eta'])} \\\\\n")
    meio = (len(linhas) + 1) // 2
    P = ["% tab_soldas.tex — GERADO por mlc_projeto/connections/soldas.py (issue 78). "
         "NÃO EDITAR À MÃO.\n"]
    for parte, (ini, fim, rot, lab) in enumerate(((0, meio, "Soldas de filete das ligações (1/2)",
                                                   "soldas-1"),
                                                  (meio, len(linhas), "Soldas de filete das ligações (2/2)",
                                                   "soldas-2"))):
        P.append(f"\\tabela{{{rot}}}{{\\footnotesize\n\\begin{{tabular}}{{p{{9.6cm}}rrr}}\n"
                 "\\toprule\n    \\textbf{Solda} & \\textbf{$a$ (mm)} & \\textbf{$\\ell$ (mm)} & "
                 "\\textbf{$\\eta$} \\\\\n\\midrule\n")
        P.extend(linhas[ini:fim])
        P.append(f"\\bottomrule\n\\end{{tabular}}}}{{Elaborado pelo autor (2026)}}{{{lab}}}{{}}{{}}\n\n")
    caminho = Path(caminho)
    caminho.write_text("".join(P).replace("×", "$\\times$"), encoding="utf-8")
    return caminho
