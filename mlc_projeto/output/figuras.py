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


def plot_ligacao_L1c(
    out_path: Path,
    *,
    h_viga_m: float,
    b_viga_m: float,
    h_pilar_m: float,
    l_apoio_viga_m: float,
    folga_m: float,
    t_sela_mm: float,
    t_chapa_mm: float,
    d_pino_mm: float,
    n_pinos: int,
    a2_mm: float,
    a4c_mm: float,
    a3_mm: float,
    alpha_deg: float,
) -> Path | None:
    """
    Desenho da ligação L1c (pilar central) — issue 42. Elevação no plano do
    pórtico, com escala gráfica e cotas em mm. Gerado dos parâmetros do
    dimensionamento: sela metálica de apoio por contato, duas vigas com chapa
    embutida e pinos no terço superior (só arrancamento).
    """
    try:
        import math
        from matplotlib.patches import Rectangle, Circle, Polygon
        mm = 1.0
        H = h_viga_m * 1000
        hp = h_pilar_m * 1000
        la = l_apoio_viga_m * 1000
        g = folga_m * 1000
        L_sela = 2 * la + g
        Lv = 900.0                         # trecho de viga desenhado
        tan_a = math.tan(math.radians(alpha_deg))

        fig, ax = plt.subplots(figsize=(8.27, 6.2))
        ax.set_aspect("equal")
        y0 = 0.0                            # topo da sela = intradorso das vigas
        # pilar central
        ax.add_patch(Rectangle((-hp / 2, -900), hp, 900 - t_sela_mm,
                               fc="#e8d9b5", ec="k", lw=1.0))
        # sela
        ax.add_patch(Rectangle((-L_sela / 2, -t_sela_mm), L_sela, t_sela_mm,
                               fc="#9aa3ab", ec="k", lw=1.0))
        for s in (-1, 1):
            x_end = s * g / 2                     # topo da viga junto à folga
            x_far = s * (g / 2 + Lv)
            # viga (intradorso horizontal, extradorso inclinado subindo p/ fora? 
            # junto ao pilar central fica a cumeeira do vão adjacente — aqui é
            # o APOIO de cada viga, de altura h0 junto ao apoio)
            top_near = H
            top_far = H + Lv * tan_a
            ax.add_patch(Polygon([(x_end, 0), (x_far, 0), (x_far, top_far),
                                  (x_end, top_near)], closed=True,
                                 fc="#f3e3bf", ec="k", lw=1.0))
            # chapa embutida (vista em projeção, tracejada)
            xc0 = x_end
            xc1 = s * (g / 2 + a3_mm + 2 * d_pino_mm)
            y_top = H - a4c_mm + 2 * d_pino_mm
            y_bot = -t_sela_mm
            ax.add_patch(Rectangle((min(xc0, xc1), y_bot), abs(xc1 - xc0),
                                   y_top - y_bot, fill=False, ls="--", ec="0.3",
                                   lw=0.8))
            # pinos
            xp = s * (g / 2 + a3_mm)
            for i in range(n_pinos):
                yp = H - a4c_mm - i * a2_mm
                ax.add_patch(Circle((xp, yp), d_pino_mm / 2, fc="k"))
            ax.text(s * (g / 2 + Lv / 2), H / 2,
                    "V1" if s < 0 else "V2", ha="center", fontsize=11)
        ax.text(0, -500, "P\ncentral", ha="center", va="center", fontsize=10)

        def cota_h(x0, x1, y, txt):
            ax.annotate("", (x0, y), (x1, y),
                        arrowprops=dict(arrowstyle="<->", lw=0.7))
            ax.text((x0 + x1) / 2, y - 25, txt, ha="center", va="top", fontsize=8)

        def cota_v(x, y0_, y1, txt):
            ax.annotate("", (x, y0_), (x, y1),
                        arrowprops=dict(arrowstyle="<->", lw=0.7))
            ax.text(x + 15, (y0_ + y1) / 2, txt, va="center", fontsize=8,
                    rotation=90)

        cota_h(-L_sela / 2, L_sela / 2, -t_sela_mm - 60,
               f"sela {L_sela:.0f} × {b_viga_m*1000:.0f} × t={t_sela_mm:g}")
        cota_h(-hp / 2, hp / 2, -330, f"pilar {hp:.0f}")
        cota_h(g / 2, g / 2 + la, -190, f"apoio {la:.0f}")
        cota_h(g / 2, g / 2 + a3_mm, H + 120, f"a3 = {a3_mm:.0f}")
        cota_v(g / 2 + Lv + 40, 0, H + Lv * tan_a, f"h0 = {H:.0f}")
        xr = (g / 2 + a3_mm) + 60
        cota_v(xr, H - a4c_mm, H, f"{a4c_mm:.0f}")
        cota_v(xr + 70, H - a4c_mm - (n_pinos - 1) * a2_mm, H - a4c_mm,
               f"{n_pinos-1}×{a2_mm:.0f}")
        ax.text(-Lv - 20, H + Lv * tan_a + 150,
                f"L1c — {n_pinos} pinos Ø{d_pino_mm:g} por viga (furos ovalizados "
                f"verticais), chapa embutida t={t_chapa_mm:g} S275 soldada à sela.\n"
                "Gravidade por contato na sela; pinos só para arrancamento.",
                fontsize=8, va="bottom")
        # escala gráfica (500 mm)
        xs, ys = Lv - 500, -860
        for k in range(5):
            ax.add_patch(Rectangle((xs + 100 * k, ys), 100, 18,
                                   fc="k" if k % 2 == 0 else "w", ec="k", lw=0.6))
        ax.text(xs, ys + 30, "0", fontsize=7, ha="center")
        ax.text(xs + 500, ys + 30, "500 mm", fontsize=7, ha="center")
        ax.text(xs + 250, ys - 30, "Elevação no plano do pórtico — cotas em mm",
                ha="center", va="top", fontsize=8)
        ax.set_xlim(-Lv - 100, Lv + 200)
        ax.set_ylim(-920, H + Lv * tan_a + 400)
        ax.axis("off")
        fig.tight_layout()
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_path, format=out_path.suffix.lstrip(".") or "pdf")
        plt.close(fig)
        return out_path
    except Exception as exc:   # figura é acessória: nunca derruba o pipeline
        print(f"  ⚠ figura L1c não gerada: {exc}")
        return None
