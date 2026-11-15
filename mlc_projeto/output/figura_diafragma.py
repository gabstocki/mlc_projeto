"""
output/figura_diafragma.py — Caminho da força transversal pelo diafragma (issue 110).

Deslocamento transversal do topo de cada pórtico no modelo em planta
(`opensees.diafragma_espacial`), para a força de cálculo H_tr distribuída e para
100 kN só no pórtico central, com as reações nos painéis dos frontões.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt     # noqa: E402


def gerar_figura_diafragma(df: dict, H_tr_kN: float, caminho: Path) -> Path:
    c5 = df["portico_central_100kN"]
    n = len(df["uy_portico_mm"])
    eixos = list(range(1, n + 1))
    fig, ax = plt.subplots(figsize=(6.3, 2.9))
    ax.plot(eixos, df["uy_portico_mm"], "o-", color="0.15", lw=1.2, ms=3.5,
            label=f"$H_{{tr}}$ = {H_tr_kN:.0f} kN distribuída pelos {n} pórticos")
    ax.plot(eixos, c5["uy_portico_mm"], "s--", color="0.55", lw=1.0, ms=3.2,
            label=f"100 kN só no pórtico {n // 2 + 1}")
    r1, r2 = df["R_frontoes_kN"]
    c1, c2 = c5["R_frontoes_kN"]
    ymax = max(max(df["uy_portico_mm"]), max(c5["uy_portico_mm"])) * 1.35
    for x, ra, rb in ((1, r1, c1), (n, r2, c2)):
        ax.text(x, 1.0, f"frontão\n{ra:.1f} / {rb:.1f} kN".replace(".", ","),
                ha="center", va="bottom", fontsize=6.5)
    ax.set_xlim(0.3, n + 0.7)
    ax.set_ylim(0, ymax)
    ax.set_xticks(eixos)
    ax.set_xlabel("Eixo do pórtico", fontsize=8)
    ax.set_ylabel("Deslocamento transversal\ndo topo (mm)", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.legend(fontsize=6.8, loc="upper right", frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    caminho = Path(caminho)
    fig.savefig(caminho)
    plt.close(fig)
    return caminho
