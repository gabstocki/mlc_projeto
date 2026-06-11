"""
output/report.py — Relatório consolidado de verificação.

Agrega todos os resultados, exporta DataFrame para Excel e
gera memorial em LaTeX compilável com pdflatex.
"""

import pandas as pd
from pathlib import Path

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial

OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"


def gerar_relatorio(
    resultados: dict,
    geo:        GeometriaViga,
    mat:        GlulamMaterial,
    nome:       str = "relatorio_mlc",
) -> None:
    """
    Gera relatório consolidado em Excel e LaTeX.

    Args:
        resultados : Dict com todos os resultados por verificação
        geo        : Geometria da viga
        mat        : Material
        nome       : Nome base do arquivo de saída
    """
    OUTPUT_DIR.mkdir(exist_ok=True)

    # ── DataFrame consolidado ─────────────────────────────────
    linhas = []
    for verif, res in resultados.items():
        if isinstance(res, dict) and "eta" in res:
            linhas.append({
                "Verificação": verif,
                "η":           round(res["eta"], 3),
                "OK":          "✓" if res.get("ok") else "✗",
            })

    df = pd.DataFrame(linhas)
    df.to_excel(OUTPUT_DIR / f"{nome}.xlsx", index=False)
    print(f"  Excel: {OUTPUT_DIR / nome}.xlsx")

    # TODO: gerar memorial LaTeX e compilar PDF
    print("  LaTeX/PDF: a implementar em report.py")
