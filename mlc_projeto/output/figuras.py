"""
output/figuras.py — Figuras do memorial (issue 27).

Diagramas de esforços M(x), V(x), N(x) ao longo da viga, da combinação ELU
governante, para o anexo de análise (reprodutibilidade do memorial).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")               # sem display (geração de arquivo)
import matplotlib.pyplot as plt     # noqa: E402


def plot_diagramas_MVN(load, geo, out_path: Path) -> Path | None:
    """
    Gera o diagrama M/V/N da combinação ELU governante e salva em out_path (PDF).

    Args:
        load : Carregamentos (fornece diagramas_MVN_ELU)
        geo  : GeometriaViga
        out_path : caminho do PDF de saída

    Returns:
        Path do arquivo gerado, ou None se indisponível.
    """
    if load is None or not hasattr(load, "diagramas_MVN_ELU"):
        return None

    d = load.diagramas_MVN_ELU()
    x, M, V, N = d["x"], d["M"], d["V"], d["N"]
    L = float(geo.L)

    fig, axes = plt.subplots(3, 1, figsize=(7.2, 6.6), sharex=True)
    fig.subplots_adjust(hspace=0.28, left=0.13, right=0.97, top=0.94, bottom=0.09)

    especs = [
        (axes[0], M, "M(x)  [kN·m]", "#1f4e79", "Momento fletor"),
        (axes[1], V, "V(x)  [kN]",   "#8c3b00", "Cortante ⊥ ao eixo"),
        (axes[2], N, "N(x)  [kN]",   "#2d5a27", "Normal no eixo (compressão +)"),
    ]
    for ax, y, ylab, cor, titulo in especs:
        ax.axhline(0.0, color="0.4", lw=0.8)
        ax.fill_between(x, y, 0.0, color=cor, alpha=0.20)
        ax.plot(x, y, color=cor, lw=1.6)
        ax.axvline(L / 2.0, color="0.7", lw=0.7, ls="--")  # cumeeira
        ax.set_ylabel(ylab, fontsize=9)
        ax.set_title(titulo, fontsize=9, loc="left", color=cor)
        ax.grid(True, alpha=0.25, lw=0.5)
        ax.tick_params(labelsize=8)
        # valor extremo anotado
        i = int(abs(y).argmax())
        ax.annotate(f"{y[i]:.0f}", (x[i], y[i]), fontsize=8, color=cor,
                    xytext=(4, 4), textcoords="offset points")

    axes[2].set_xlabel("x  [m]  (0 → L; cumeeira em L/2, tracejado)", fontsize=9)
    fig.suptitle(
        f"Diagramas de esforços — combinação {d['comb']} "
        f"(H = {d['H_kN']:.0f} kN)",
        fontsize=10, y=0.985,
    )

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, format="pdf")
    plt.close(fig)
    return out_path
