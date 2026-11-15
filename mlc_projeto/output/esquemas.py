"""
output/esquemas.py — Figuras esquemáticas do memorial (issue 63).

  · ESQ-01  variáveis da varredura global: α, h₀, h_ap, b e L na viga de duplo-bisel;
  · ESQ-02  modelo estrutural do pórtico transversal: vigas V, pilares P, rótulas,
            apoios e carregamento, com a nomenclatura da issue 52;
  · ESQ-03  modelo do apoio horizontal: do arco abatido (apoio indeslocável) à
            viga biapoiada (apoio livre), passando pela mola de rigidez k_ap.
  · ESQ-04  nó de topo das baías contraventadas: por que o pilar montante é
            bipartido (issue 104) — as quatro soluções examinadas, no plano da fachada.

Ao contrário das folhas de `desenhos.py`, não são desenhos em escala: a altura
da viga é ampliada para que as grandezas fiquem legíveis, o que se declara na
própria figura. A geometria sai do pipeline (GeometriaViga), de modo que as
proporções acompanham o projeto. Regeneradas a cada execução.
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                   # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch, Polygon, Rectangle  # noqa: E402

from mlc_projeto.output.desenhos import COR_DESTAQUE, COR_MLC, LARGURA_FOLHA_MM, MM  # noqa: E402

plt.rcParams.update({"font.family": "DejaVu Sans", "pdf.fonttype": 42,
                     "font.size": 7.0, "mathtext.fontset": "dejavuserif"})

COR_COTA = "0.15"
COR_CARGA = "#8c3b00"


def _fig(altura_mm: float):
    fig = plt.figure(figsize=(LARGURA_FOLHA_MM * MM, altura_mm * MM))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_aspect("equal", adjustable="datalim")
    ax.axis("off")
    return fig, ax


def _cota(ax, p1, p2, txt, off=(0.0, 0.0), fs=7.5, rot=0, ha="center", va="center"):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle="<->", mutation_scale=7,
                                 lw=0.6, color=COR_COTA))
    xm, ym = (p1[0] + p2[0]) / 2 + off[0], (p1[1] + p2[1]) / 2 + off[1]
    ax.text(xm, ym, txt, fontsize=fs, rotation=rot, ha=ha, va=va,
            bbox=dict(fc="w", ec="none", pad=0.4))


def _rotula(ax, x, y, r):
    ax.add_patch(Circle((x, y), r, fc="w", ec="k", lw=0.8, zorder=6))


def _apoio_fixo(ax, x, y, s):
    ax.add_patch(Polygon([(x, y), (x - s, y - 1.4 * s), (x + s, y - 1.4 * s)],
                         closed=True, fc="w", ec="k", lw=0.8, zorder=5))
    ax.plot([x - 1.5 * s, x + 1.5 * s], [y - 1.4 * s] * 2, color="k", lw=0.8)
    for k in range(5):
        xx = x - 1.5 * s + k * 0.75 * s
        ax.plot([xx, xx - 0.5 * s], [y - 1.4 * s, y - 1.9 * s], color="k", lw=0.5)


def _apoio_movel(ax, x, y, s):
    ax.add_patch(Polygon([(x, y), (x - s, y - 1.2 * s), (x + s, y - 1.2 * s)],
                         closed=True, fc="w", ec="k", lw=0.8, zorder=5))
    for dx in (-0.55 * s, 0.55 * s):
        ax.add_patch(Circle((x + dx, y - 1.45 * s), 0.25 * s, fc="w", ec="k", lw=0.6))
    ax.plot([x - 1.5 * s, x + 1.5 * s], [y - 1.7 * s] * 2, color="k", lw=0.8)


def _carga(ax, x0, x1, y, h, n=11):
    ax.plot([x0, x1], [y + h, y + h], color=COR_CARGA, lw=0.8)
    for k in range(n):
        x = x0 + (x1 - x0) * k / (n - 1)
        ax.add_patch(FancyArrowPatch((x, y + h), (x, y), arrowstyle="-|>",
                                     mutation_scale=5, lw=0.6, color=COR_CARGA))


# ── ESQ-01 ────────────────────────────────────────────────────────────────────

def esquema_variaveis_viga(geo, caminho: Path, *, faixas: dict | None = None) -> Path:
    """Elevação e seção da viga com as variáveis da varredura cotadas."""
    L, h0, a = float(geo.L), float(geo.h0), float(geo.alpha_deg)
    hap = h0 + L / 2 * math.tan(math.radians(a))
    ev = 2.5                                               # ampliação vertical
    fig, ax = _fig(50.0)
    # elevação (unidades: m na horizontal, m·ev na vertical)
    pts = [(0, 0), (L, 0), (L, h0 * ev), (L / 2, hap * ev), (0, h0 * ev)]
    ax.add_patch(Polygon(pts, closed=True, fc=COR_MLC, ec="k", lw=0.9))
    ax.plot([L / 2, L / 2], [0, hap * ev], color="0.5", lw=0.5, ls="--")
    _apoio_fixo(ax, 0.0, 0.0, 0.35)
    _apoio_movel(ax, L, 0.0, 0.35)
    _cota(ax, (0, -1.6), (L, -1.6), r"$L$")
    _cota(ax, (-0.8, 0), (-0.8, h0 * ev), r"$h_0$", off=(-0.5, 0))
    _cota(ax, (L / 2 + 0.6, 0), (L / 2 + 0.6, hap * ev), r"$h_{ap}$", off=(0.7, 0))
    # ângulo α no apoio esquerdo
    r = 3.2
    th = math.degrees(math.atan2((hap - h0) * ev, L / 2))
    xs = [r * math.cos(math.radians(t)) for t in range(0, int(th) + 1)]
    ys = [h0 * ev + r * math.sin(math.radians(t)) for t in range(0, int(th) + 1)]
    ax.plot([0, r + 0.6], [h0 * ev, h0 * ev], color="0.4", lw=0.5, ls=":")
    ax.plot(xs, ys, color=COR_COTA, lw=0.6)
    ax.text(r + 0.3, h0 * ev + 0.55, r"$\alpha$", fontsize=8)
    ax.text(L / 2, hap * ev + 0.5, "cumeeira", ha="center", fontsize=6.5)
    ax.text(L * 0.75, h0 * ev * 0.45, "intradorso reto", ha="center", fontsize=6.5)
    ax.text(L * 0.78, (h0 + (hap - h0) * 0.42) * ev + 0.35, "extradorso inclinado",
            ha="center", fontsize=6.5, rotation=-th * 0.9)
    # seção transversal (escala própria, ao lado)
    x0, b = L + 3.0, float(geo.b) * ev * 3
    hs = h0 * ev
    ax.add_patch(Rectangle((x0, 0), b, hs, fc=COR_MLC, ec="k", lw=0.9))
    for k in range(1, 8):
        ax.plot([x0, x0 + b], [hs * k / 8] * 2, color="0.6", lw=0.3)
    _cota(ax, (x0, -0.6), (x0 + b, -0.6), r"$b$")
    _cota(ax, (x0 + b + 0.5, 0), (x0 + b + 0.5, hs), r"$h(x)$", off=(0.9, 0))
    ax.text(x0 + b / 2, hs + 0.5, "seção", ha="center", fontsize=6.5)
    if faixas:
        ax.text(0, -3.0, faixas, fontsize=6.5, va="top")
    ax.text(0, -3.9, "altura da viga ampliada; sem escala", fontsize=6.0,
            va="top", color="0.4")
    ax.set_xlim(-2.5, L + 9.5)
    ax.set_ylim(-4.6, hap * ev + 1.5)
    return _salvar(fig, caminho)


# ── ESQ-02 ────────────────────────────────────────────────────────────────────

def esquema_modelo_portico(geo, caminho: Path, *, H_pilar: float) -> Path:
    """Modelo de cálculo de um pórtico transversal intermediário."""
    L, h0, a = float(geo.L), float(geo.h0), float(geo.alpha_deg)
    hap = h0 + L / 2 * math.tan(math.radians(a))
    H = float(H_pilar)
    fig, ax = _fig(82.0)
    s = 0.45
    ab = float(getattr(geo, "a_bal", 0.0))
    tg = math.tan(math.radians(a))
    hb = h0 - ab * tg
    for vao, xa in (("V(2i−1)", 0.0), ("V(2i)", L)):
        pts = [(xa, H), (xa + L, H), (xa + L, H + h0), (xa + L / 2, H + hap), (xa, H + h0)]
        if ab > 0 and xa == 0.0:                       # beiral em A
            pts = [(-ab, H)] + pts[1:] + [(-ab, H + hb)]
        elif ab > 0:                                    # beiral em C
            pts = [(xa, H), (xa + L + ab, H), (xa + L + ab, H + hb), (xa + L, H + h0),
                   (xa + L / 2, H + hap), (xa, H + h0)]
        ax.add_patch(Polygon(pts, closed=True, fc=COR_MLC, ec="0.55", lw=0.5))
        # eixo do modelo (linha do centroide) e carga
        xs_e = [xa, xa + L / 2, xa + L]
        zs_e = [H + h0 / 2, H + hap / 2, H + h0 / 2]
        if ab > 0 and xa == 0.0:
            xs_e, zs_e = [-ab] + xs_e, [H + hb / 2] + zs_e
        elif ab > 0:
            xs_e, zs_e = xs_e + [xa + L + ab], zs_e + [H + hb / 2]
        ax.plot(xs_e, zs_e, color="k", lw=1.2)
        x_c0 = xa - ab if (ab > 0 and xa == 0.0) else xa
        x_c1 = xa + L + ab if (ab > 0 and xa > 0) else xa + L
        _carga(ax, x_c0 + 0.3, x_c1 - 0.3, H + hap + 0.3, 1.2)
        ax.text(xa + L / 2, H + hap + 2.0, r"$q_{esq}$ | $q_{dir}$", ha="center",
                fontsize=7, color=COR_CARGA)
        ax.text(xa + L * 0.27, H + h0 * 0.35, vao, ha="center", fontsize=7.5,
                fontweight="bold")
    for i, (x, nome, al) in enumerate(((0.0, "P(3i−2)", "A"), (L, "P(3i−1)", "B"),
                                       (2 * L, "P(3i)", "C"))):
        ax.plot([x, x], [0, H], color="k", lw=1.6)
        _rotula(ax, x, H, 0.3)
        _apoio_fixo(ax, x, 0, s)
        ult = i == 2
        ax.text(x + (-0.5 if ult else 0.5), H * 0.5, nome, fontsize=7.5,
                fontweight="bold", va="center", ha="right" if ult else "left")
        ax.add_patch(Circle((x, -2.0), 0.75, fc="w", ec="k", lw=0.7))
        ax.text(x, -2.0, al, ha="center", va="center", fontsize=7.5, fontweight="bold")
    # apoio horizontal livre da viga sobre o pilar lateral direito (sem empuxo)
    ax.annotate("viga biapoiada:\nsem empuxo (H = 0)", xy=(2 * L - 0.2, H + 0.3),
                xytext=(2 * L - 7.5, H + hap + 3.6), fontsize=6.5, ha="center",
                arrowprops=dict(arrowstyle="->", lw=0.5))
    ax.annotate("pilares articulados\nno topo e na base", xy=(L + 0.2, H * 0.15),
                xytext=(L + 6.0, H * 0.32), fontsize=6.5,
                arrowprops=dict(arrowstyle="->", lw=0.5))
    _cota(ax, (0, -3.6), (L, -3.6), r"$L$")
    _cota(ax, (L, -3.6), (2 * L, -3.6), r"$L$")
    if ab > 0:
        _cota(ax, (-ab, H + hap + 2.6), (0, H + hap + 2.6), r"$a$ (beiral)",
              off=(0.9, 0.5), ha="left")
        _cota(ax, (2 * L, H + hap + 2.6), (2 * L + ab, H + hap + 2.6), r"$a$", off=(0, 0.5))
    _cota(ax, (-1.4, 0), (-1.4, H), r"$H$", off=(-0.8, 0))
    ax.text(2 * L + 1.0, -4.6,
            "estabilidade no plano do pórtico: diafragma da cobertura → frontões (CV-T)",
            fontsize=6.0, ha="right", va="top", color="0.35")
    ax.set_xlim(-3.5 - ab, 2 * L + 2.0 + ab)
    ax.set_ylim(-6.2, H + hap + 5.0)
    return _salvar(fig, caminho)


# ── ESQ-03 ────────────────────────────────────────────────────────────────────

def esquema_apoio_horizontal(caminho: Path) -> Path:
    """Os dois extremos do apoio horizontal e o caso intermediário (mola)."""
    fig, ax = _fig(40.0)
    Lm, h0, hap = 10.0, 0.6, 1.6
    casos = (("(a) apoio indeslocável", "arco abatido: H > 0,\nmomento aliviado", "fixo"),
             ("(b) apoio elástico", "H depende de $k_{ap}$\nfrente à rigidez do arco", "mola"),
             ("(c) apoio livre", "viga biapoiada: H = 0,\nmomento $qL^2/8$", "livre"))
    for n, (tit, txt, tipo) in enumerate(casos):
        x0 = n * (Lm + 3.2)
        pts = [(x0, 0), (x0 + Lm, 0), (x0 + Lm, h0), (x0 + Lm / 2, hap), (x0, h0)]
        ax.add_patch(Polygon(pts, closed=True, fc=COR_MLC, ec="k", lw=0.8))
        _carga(ax, x0 + 0.2, x0 + Lm - 0.2, hap + 0.15, 0.7, n=9)
        _apoio_fixo(ax, x0, 0, 0.35)
        xr = x0 + Lm
        if tipo == "fixo":
            _apoio_fixo(ax, xr, 0, 0.35)
        else:
            _apoio_movel(ax, xr, 0, 0.35)
        if tipo == "mola":
            zx = [xr + 0.45 + 0.18 * k for k in range(9)]
            zy = [0.3 + (0.18 if k % 2 else -0.18) * (0 < k < 8) for k in range(9)]
            ax.plot(zx, zy, color="k", lw=0.7)
            ax.plot([zx[-1], zx[-1]], [-0.3, 0.9], color="k", lw=1.0)
            ax.text(xr + 1.2, 1.15, r"$k_{ap}$", fontsize=7.5, ha="center")
        if tipo != "livre":
            for xh, d in ((x0, 1), (xr, -1)):
                ax.add_patch(FancyArrowPatch((xh - d * 1.6, -0.35), (xh - d * 0.3, -0.35),
                                             arrowstyle="-|>", mutation_scale=7, lw=0.9,
                                             color=COR_DESTAQUE))
            ax.text(x0 + Lm / 2, -0.75, "H", color=COR_DESTAQUE, ha="center", fontsize=7.5)
        ax.text(x0 + Lm / 2, hap + 1.35, tit, ha="center", fontsize=7.5, fontweight="bold")
        ax.text(x0 + Lm / 2, -1.25, txt, ha="center", va="top", fontsize=6.5)
    ax.set_xlim(-1.8, 3 * (Lm + 3.2) - 1.4)
    ax.set_ylim(-3.6, hap + 2.2)
    return _salvar(fig, caminho)


def _salvar(fig, caminho: Path) -> Path:
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(caminho, format="pdf")
    plt.close(fig)
    return caminho


def esquema_no_topo(caminho: Path) -> Path:
    """
    ESQ-04 — Nó de topo das baías contraventadas, no plano da fachada: a força da
    escora chega h0 acima do topo do pilar; quatro maneiras de levá-la à diagonal.
    """
    from matplotlib.patches import FancyBboxPatch  # noqa: F401
    fig, ax = _fig(50.0)
    COR_F, COR_MAL, COR_BOM = "#1f4e79", "#b03a2e", "#2e7d32"
    W = 10.0                              # largura de cada painel (unidades)
    Hp, h0, ht = 6.0, 2.0, 0.7            # pilar, viga e terça (fora de escala)

    def _arrow(x0, y0, x1, y1, cor, lw=1.3):
        ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=8,
                                     lw=lw, color=cor, zorder=8))

    def _base(xc, bip=False):
        # pilar(es), viga em seção sobre o apoio e escora (terça) sobre a viga
        if bip:
            for sg in (-1, 1):
                ax.add_patch(Rectangle((xc + sg * 1.05 - 0.4, 0), 0.8, Hp + h0, fc=COR_MLC,
                                       ec="k", lw=0.7, zorder=2))
        else:
            ax.add_patch(Rectangle((xc - 0.7, 0), 1.4, Hp, fc=COR_MLC, ec="k", lw=0.7, zorder=2))
        ax.add_patch(Rectangle((xc - 0.6, Hp), 1.2, h0, fc="#e9d6a6", ec="k", lw=0.7, zorder=3))
        ax.add_patch(Rectangle((xc - 3.0, Hp + h0), 6.8, ht, fc=COR_MLC, ec="k", lw=0.7,
                               zorder=3))
        ax.plot([xc - 3.6, xc + 4.4], [0, 0], color="k", lw=0.8)
        ax.text(xc + 3.7, Hp + h0 + ht / 2, "escora", fontsize=5.4, va="center", ha="right",
                zorder=9)
        ax.text(xc, Hp + h0 / 2, "viga", fontsize=5.2, ha="center", va="center", rotation=90,
                zorder=9)

    def _diag(xc, x_no, y_no):
        ax.plot([x_no, xc + 4.2], [y_no, 0.0], color="#b03a2e", lw=1.4, zorder=4)
        ax.add_patch(Circle((x_no, y_no), 0.16, fc="w", ec="k", lw=0.7, zorder=9))

    rot = ("(a) Nó no topo do pilar", "(b) Nó na escora, pela viga",
           "(c) Pórtico de aço", "(d) Pilar bipartido")
    for i in range(4):
        xc = 1.8 + i * W
        _base(xc, bip=(i == 3))
        ax.text(xc + 0.6, -1.0, rot[i], fontsize=6.4, ha="center", va="top",
                fontweight="bold", color=COR_BOM if i == 3 else "k")
        yH = Hp + h0 + ht / 2
        _arrow(xc - 4.1, yH, xc - 3.05, yH, COR_F)
        ax.text(xc - 4.1, yH + 0.45, "H", fontsize=6.6, color=COR_F)
    # (a) nó no topo do pilar: binário H·h0 sem equilíbrio
    xc = 1.8
    _diag(xc, xc + 0.7, Hp)
    ax.add_patch(FancyArrowPatch((xc + 2.6, Hp + 0.2), (xc + 2.6, Hp + h0 + 0.6),
                                 connectionstyle="arc3,rad=0.5", arrowstyle="-|>",
                                 mutation_scale=8, lw=1.1, color=COR_MAL, zorder=8))
    ax.text(xc - 1.0, Hp - 1.3, "binário H·h₀\nsem equilíbrio", fontsize=5.4,
            color=COR_MAL, va="center", ha="right")
    _cota(ax, (xc - 1.2, Hp), (xc - 1.2, Hp + h0), "h₀", off=(-0.45, 0), fs=6.4)
    # (b) nó na escora apoiado na viga: força vertical ⊥ às fibras; umidade
    xc = 1.8 + W
    _diag(xc, xc + 1.0, Hp + h0 - 0.2)
    _arrow(xc + 0.2, Hp + h0 - 0.1, xc + 0.2, Hp + 0.4, COR_MAL, lw=1.0)
    ax.text(xc - 1.0, Hp - 1.3, "D desce pela viga,\n⊥ às fibras: o\ninchamento "
            "da viga\ntensiona a diagonal", fontsize=5.4, color=COR_MAL, va="center", ha="right")
    # (c) pórtico de aço ao lado da viga: excentricidade no pilar
    xc = 1.8 + 2 * W
    for sg in (-1, 1):
        ax.add_patch(Rectangle((xc + sg * 0.75 - 0.08, Hp), 0.16, h0, fc="0.45", ec="k", lw=0.5,
                               zorder=4))
    ax.add_patch(Rectangle((xc - 0.83, Hp + h0 - 0.12), 1.66, 0.12, fc="0.45", ec="k", lw=0.5,
                           zorder=4))
    _diag(xc, xc + 0.75, Hp + h0 - 0.2)
    _arrow(xc + 0.75, Hp + h0 - 0.3, xc + 0.75, Hp + 0.1, COR_MAL, lw=1.0)
    ax.text(xc - 1.0, Hp - 1.3, "D chega ao pilar\nfora do eixo:\nmomento no pilar",
            fontsize=5.4, color=COR_MAL, va="center", ha="right")
    # (d) pilar bipartido: forças concorrentes; D desce pela lâmina // às fibras
    xc = 1.8 + 3 * W
    _diag(xc, xc + 1.05, Hp + h0 - 0.2)
    _arrow(xc + 1.05, Hp + h0 - 0.5, xc + 1.05, 1.0, COR_BOM, lw=1.0)
    ax.text(xc - 1.6, Hp - 1.3, "forças concorrentes;\nD desce pela lâmina,\n// às fibras",
            fontsize=5.4, color=COR_BOM, va="center", ha="right")
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(-3.4, 4 * W - 2.2)
    ax.set_ylim(-1.8, Hp + h0 + ht + 1.0)
    fig.savefig(caminho, format="pdf")
    plt.close(fig)
    return caminho


def gerar_esquemas(geo, pasta: Path, *, H_pilar: float, faixas: str | None = None) -> list[Path]:
    pasta = Path(pasta)
    return [
        esquema_variaveis_viga(geo, pasta / "esq01_variaveis_viga.pdf", faixas=faixas),
        esquema_modelo_portico(geo, pasta / "esq02_modelo_portico.pdf", H_pilar=H_pilar),
        esquema_apoio_horizontal(pasta / "esq03_apoio_horizontal.pdf"),
        esquema_no_topo(pasta / "esq04_no_topo.pdf"),
    ]
