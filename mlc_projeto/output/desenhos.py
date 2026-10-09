"""
output/desenhos.py — Desenhos cotados e em escala (issue 52).

Gera, a partir da geometria e dos resultados do pipeline, as folhas de desenho
da monografia, com a nomenclatura dos elementos usada no memorial:

    eixos 1–9 (pórticos, a cada L_T) e A, B, C (alinhamentos, a cada L);
    P1–P27   pilares, por pórtico: P(3i−2) em A, P(3i−1) em B, P(3i) em C;
    PF1, PF2 pilares de frontão (eixo 1, junto a A; eixo 9, junto a C);
    V1–V18   vigas: V(2i−1) no vão A–B e V(2i) no vão B–C do pórtico i;
    T1–T17   linhas de terças, de A para C (T1, T9 e T17 sobre os apoios);
    CV-H1/2  contraventamento da cobertura (baías 1–2 e 8–9);
    CV-V1–8  painéis verticais (A: 1–2, 8–9; C: 1–2, 8–9; B: 1–2, 2–3, 7–8, 8–9);
    CV-T1/2  painéis dos frontões (P1–PF1; PF2–P27);
    L1, L1c, L1f, L3, L3c, L3f, L3a  ligações (topo e base).

Cada folha tem a largura útil da página da tese (455 pt = 159,9 mm) e é
desenhada em escala verdadeira: incluída com largura \\textwidth, a escala
indicada vale no papel. Todas trazem escala gráfica.

Regenerado a cada execução do pipeline; não editar os PDFs à mão.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                       # noqa: E402
from matplotlib.patches import Circle, FancyBboxPatch, Polygon, Rectangle  # noqa: E402

LARGURA_FOLHA_MM = 455.0 / 72.27 * 25.4               # \textwidth da tese
MM = 1.0 / 25.4

COR_MLC = "#f1e2bd"
COR_ACO = "#9aa3ab"
COR_CONC = "#d9d9d9"
COR_CV = "#b03a2e"
COR_DESTAQUE = "#1f4e79"

plt.rcParams.update({"font.family": "DejaVu Sans", "pdf.fonttype": 42,
                     "font.size": 5.5})


# ── Nomenclatura ────────────────────────────────────────────────────────────

ALINHAMENTOS = ("A", "B", "C")


def nome_pilar(eixo: int, alinhamento: str) -> str:
    return f"P{3 * (eixo - 1) + ALINHAMENTOS.index(alinhamento) + 1}"


def nome_viga(eixo: int, vao: str) -> str:
    return f"V{2 * (eixo - 1) + (1 if vao == 'AB' else 2)}"


@dataclass
class Arranjo:
    """Geometria global e detalhes, em m (global) e mm (detalhes)."""
    L: float                    # vão de cada viga (m)
    h0: float                   # altura da viga no apoio (m)
    alpha_deg: float
    b_viga: float
    n_eixos: int
    L_T: float                  # espaçamento entre pórticos (m)
    H_pilar: float
    b_pilar: float              # ⊥ pórtico
    h_pilar: float              # no plano do pórtico
    b_canto: float
    h_canto: float
    b_terca: float
    h_terca: float
    n_paineis_terca: int        # painéis entre terças por vão
    baias_cvh: tuple            # baías (1 = entre eixos 1 e 2) com CV-H
    baias_cvv_fachada: tuple
    baias_cvv_central: tuple
    d_cvh: float
    d_cvv: float
    d_cvt: float
    det: dict = field(default_factory=dict)   # detalhes das ligações (mm)

    @property
    def h_ap(self) -> float:
        return self.h0 + self.L / 2.0 * math.tan(math.radians(self.alpha_deg))

    @property
    def comprimento(self) -> float:
        return (self.n_eixos - 1) * self.L_T

    def x_eixo(self, i: int) -> float:
        return (i - 1) * self.L_T

    def y_alinh(self, a: str) -> float:
        return ALINHAMENTOS.index(a) * self.L

    def y_tercas(self) -> list[float]:
        s = self.L / self.n_paineis_terca
        return [k * s for k in range(2 * self.n_paineis_terca + 1)]

    def extradorso(self, y: float) -> float:
        """Altura do extradorso acima do intradorso, em y (0 → 2L)."""
        yl = y % self.L if y < 2 * self.L else self.L
        d = min(yl, self.L - yl)
        return self.h0 + d * math.tan(math.radians(self.alpha_deg))

    def eixos_canto(self) -> list[tuple[int, str]]:
        return [(1, "A"), (1, "C"), (self.n_eixos, "A"), (self.n_eixos, "C")]

    def pilares_frontao(self) -> list[tuple[str, int, float]]:
        return [("PF1", 1, self.L_T), ("PF2", self.n_eixos, 2 * self.L - self.L_T)]


# ── Folha e primitivas de desenho ─────────────────────────────────────────

class Folha:
    """Figura com largura útil da tese; modelo em escala 1:escala."""

    def __init__(self, altura_mm: float, escala: float, x0: float, y0: float,
                 unidade: str = "m"):
        self.escala = escala
        self.unidade = unidade
        self.k = escala / (1000.0 if unidade == "m" else 1.0)   # modelo / mm papel
        self.w_mm, self.h_mm = LARGURA_FOLHA_MM, altura_mm
        self.fig = plt.figure(figsize=(self.w_mm * MM, altura_mm * MM))
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(x0, x0 + self.w_mm * self.k)
        self.ax.set_ylim(y0, y0 + altura_mm * self.k)
        self.ax.set_aspect("equal")
        self.ax.axis("off")
        self.x0, self.y0 = x0, y0

    def p(self, mm: float) -> float:
        """Distância no papel (mm) → unidades do modelo."""
        return mm * self.k

    def fmt(self, v: float, dec: int | None = None) -> str:
        if self.unidade == "m":
            return f"{v:.2f}".replace(".", ",")
        d = 0 if dec is None else dec
        return f"{v:.{d}f}".replace(".", ",")

    # cotas ---------------------------------------------------------------
    def cota_h(self, x1, x2, y, txt=None, y_ref=None, acima=True, fs=5.0):
        ax, t = self.ax, self.p(0.9)
        ax.plot([x1, x2], [y, y], color="k", lw=0.35)
        for x in (x1, x2):
            ax.plot([x - t, x + t], [y - t, y + t], color="k", lw=0.5)
            if y_ref is not None:
                ax.plot([x, x], [y_ref, y + (t if y > y_ref else -t)],
                        color="k", lw=0.25)
        ax.text((x1 + x2) / 2, y + (self.p(0.6) if acima else -self.p(0.6)),
                txt if txt is not None else self.fmt(abs(x2 - x1)),
                ha="center", va="bottom" if acima else "top", fontsize=fs)

    def cota_v(self, x, y1, y2, txt=None, x_ref=None, esquerda=True, fs=5.0):
        ax, t = self.ax, self.p(0.9)
        ax.plot([x, x], [y1, y2], color="k", lw=0.35)
        for y in (y1, y2):
            ax.plot([x - t, x + t], [y - t, y + t], color="k", lw=0.5)
            if x_ref is not None:
                ax.plot([x_ref, x + (t if x > x_ref else -t)], [y, y],
                        color="k", lw=0.25)
        ax.text(x + (-self.p(0.6) if esquerda else self.p(0.6)), (y1 + y2) / 2,
                txt if txt is not None else self.fmt(abs(y2 - y1)),
                ha="right" if esquerda else "left", va="center", rotation=90,
                fontsize=fs)

    def cadeia_h(self, xs, y, y_ref=None, **kw):
        for a, b in zip(xs[:-1], xs[1:]):
            self.cota_h(a, b, y, y_ref=y_ref, **kw)

    def cadeia_v(self, ys, x, x_ref=None, **kw):
        for a, b in zip(ys[:-1], ys[1:]):
            self.cota_v(x, a, b, x_ref=x_ref, **kw)

    # eixos -----------------------------------------------------------------
    def bolha(self, x, y, txt, r_mm=2.3):
        self.ax.add_patch(Circle((x, y), self.p(r_mm), fc="w", ec="k", lw=0.5,
                                 zorder=5))
        self.ax.text(x, y, txt, ha="center", va="center", fontsize=5.5,
                     fontweight="bold", zorder=6)

    def linha_eixo(self, p1, p2):
        self.ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color="0.45", lw=0.3,
                     ls=(0, (8, 2, 1, 2)), zorder=0)

    # carimbo --------------------------------------------------------------
    #: Altura do rodapé reservado ao carimbo (mm de papel).
    RODAPE_MM = 15.0

    def carimbo(self, codigo: str, titulo: str, nota: str = "",
                barra: float | None = None, divisoes: int = 5):
        """Título, notas (com quebra de linha) e escala gráfica no rodapé."""
        import textwrap
        ax = self.ax
        x = self.x0 + self.p(2.0)
        y = self.y0 + self.p(11.0)
        ax.text(x, y, f"{codigo} · {titulo} · ESCALA 1:{self.escala:g}",
                fontsize=6.0, fontweight="bold", va="bottom")
        for n, linha in enumerate(textwrap.wrap(nota, 168)[:5]):
            ax.text(x, y - self.p(0.8 + 2.0 * n), linha, fontsize=4.6, va="top",
                    color="0.25")
        if barra:
            xb = self.x0 + self.w_mm * self.k - self.p(7.0) - barra
            hb = self.p(0.9)
            d = barra / divisoes
            for i in range(divisoes):
                ax.add_patch(Rectangle((xb + i * d, y), d, hb, lw=0.4, ec="k",
                                       fc="k" if i % 2 == 0 else "w"))
            un = "m" if self.unidade == "m" else "mm"
            for i in (0, divisoes):
                v = i * d
                ax.text(xb + v, y + hb + self.p(0.5),
                        (f"{v:g}" if v else "0") + (f" {un}" if i else ""),
                        ha="center", va="bottom", fontsize=4.6)

    @classmethod
    def para_conteudo(cls, escala: float, xmin: float, xmax: float, ymin: float,
                      ymax: float, unidade: str = "m") -> "Folha":
        """Folha centrada num retângulo de conteúdo, com rodapé reservado."""
        k = escala / (1000.0 if unidade == "m" else 1.0)
        largura = LARGURA_FOLHA_MM * k
        x0 = (xmin + xmax) / 2.0 - largura / 2.0
        y0 = ymin - cls.RODAPE_MM * k
        altura_mm = (ymax - ymin) / k + cls.RODAPE_MM + 2.0
        if xmax - xmin > largura:
            raise ValueError(f"conteúdo de {xmax - xmin:.2f} não cabe em "
                             f"{largura:.2f} na escala 1:{escala:g}")
        return cls(altura_mm, escala, x0, y0, unidade=unidade)

    def salvar(self, caminho: Path) -> Path:
        caminho = Path(caminho)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        self.fig.savefig(caminho, format="pdf")
        plt.close(self.fig)
        return caminho


def _g(v: float) -> str:
    """Número curto com vírgula decimal (12,5; 8; 0,32)."""
    return f"{v:g}".replace(".", ",")


def _rot(ax, x, y, txt, cor="k", fs=5.0, rot=0, ha="center", va="center", bold=False,
         fundo=True):
    ax.text(x, y, txt, ha=ha, va=va, fontsize=fs, rotation=rot, color=cor,
            fontweight="bold" if bold else "normal", zorder=7,
            bbox=dict(fc="w", ec="none", pad=0.25) if fundo else None)


def _cruz(ax, p1, p2, p3, p4, cor=COR_CV, lw=0.6, zorder=3):
    """Diagonais de um painel com vértices p1..p4 (sentido anti-horário)."""
    ax.plot([p1[0], p3[0]], [p1[1], p3[1]], color=cor, lw=lw, zorder=zorder)
    ax.plot([p2[0], p4[0]], [p2[1], p4[1]], color=cor, lw=lw, zorder=zorder)


# ── Plantas (x = comprimento, eixos 1–9; y = largura, A → C) ───────────────

def _planta_base(arr: Arranjo, escala: float) -> Folha:
    W, B = arr.comprimento, 2 * arr.L
    k = escala / 1000.0
    f = Folha.para_conteudo(escala, -26 * k, W + 15 * k, -27 * k, B + 6 * k)
    for i in range(1, arr.n_eixos + 1):
        x = arr.x_eixo(i)
        f.linha_eixo((x, -f.p(9)), (x, B + f.p(4)))
        f.bolha(x, -f.p(12), str(i))
    for a in ALINHAMENTOS:
        y = arr.y_alinh(a)
        f.linha_eixo((-f.p(10), y), (W + f.p(3), y))
        f.bolha(-f.p(13), y, a)
    return f


def _cotas_planta(f: Folha, arr: Arranjo, ys_cadeia: list[float]):
    W, B = arr.comprimento, 2 * arr.L
    xs = [arr.x_eixo(i) for i in range(1, arr.n_eixos + 1)]
    f.cadeia_h(xs, -f.p(19), fs=4.6)
    f.cota_h(0, W, -f.p(24), fs=5.0)
    f.cadeia_v(ys_cadeia, -f.p(18.5), fs=4.6)
    f.cota_v(-f.p(23), 0, B, fs=5.0)


def _pilares_planta(f: Folha, arr: Arranjo, rotulos: bool = True):
    ax = f.ax
    for i in range(1, arr.n_eixos + 1):
        for a in ALINHAMENTOS:
            canto = (i, a) in arr.eixos_canto()
            b, h = (arr.b_canto, arr.h_canto) if canto else (arr.b_pilar, arr.h_pilar)
            x, y = arr.x_eixo(i), arr.y_alinh(a)
            ax.add_patch(Rectangle((x - b / 2, y - h / 2), b, h, fc="k", ec="k",
                                   lw=0.3, zorder=4))
            if rotulos:
                ult = i == arr.n_eixos
                _rot(ax, x + (-f.p(1.0) if ult else f.p(1.0)), y + f.p(1.2),
                     nome_pilar(i, a), fs=4.4, ha="right" if ult else "left",
                     va="bottom")
    for nome, i, y in arr.pilares_frontao():
        x = arr.x_eixo(i)
        ax.add_patch(Rectangle((x - arr.b_pilar / 2, y - arr.h_pilar / 2),
                               arr.b_pilar, arr.h_pilar, fc=COR_DESTAQUE,
                               ec=COR_DESTAQUE, lw=0.3, zorder=4))
        if rotulos:
            esq = i == arr.n_eixos
            _rot(ax, x + (-f.p(1.0) if esq else f.p(1.0)), y, nome, fs=4.4,
                 ha="right" if esq else "left", cor=COR_DESTAQUE, bold=True)


def desenho_planta_cobertura(arr: Arranjo, caminho: Path) -> Path:
    """DES-01 — Planta de cobertura e locação (vigas, pilares, terças)."""
    f = _planta_base(arr, 400)
    ax, W, B = f.ax, arr.comprimento, 2 * arr.L
    yt = arr.y_tercas()
    for j, y in enumerate(yt, start=1):
        ax.plot([0, W], [y, y], color="0.35", lw=0.45 if j in (1, 9, 17) else 0.3,
                zorder=2)
        _rot(ax, W + f.p(1.5), y, f"T{j}", fs=4.2, ha="left")
    for i in range(1, arr.n_eixos + 1):
        x = arr.x_eixo(i)
        for vao, (ya, yb) in (("AB", (0, arr.L)), ("BC", (arr.L, B))):
            ax.add_patch(Rectangle((x - arr.b_viga / 2, ya), arr.b_viga, yb - ya,
                                   fc=COR_MLC, ec="k", lw=0.4, zorder=3))
            _rot(ax, x, ya + arr.L * 0.70, nome_viga(i, vao), fs=4.4, rot=90)
    for yc in (arr.L / 2, 1.5 * arr.L):
        ax.plot([0, W], [yc, yc], color="k", lw=0.25, ls="--", zorder=2)
    _rot(ax, arr.L_T / 2, arr.L / 2, "cumeeira", fs=4.0)
    _pilares_planta(f, arr)
    _cotas_planta(f, arr, [arr.y_alinh(a) for a in ALINHAMENTOS])
    f.cadeia_v(yt[:9], W + f.p(8), esquerda=False, fs=3.8)
    f.carimbo("DES-01", "PLANTA DE COBERTURA E LOCAÇÃO",
              "Cotas em m. Vigas V1–V18 sob as terças T1–T17 (terças a cada L/8; "
              "T1, T9 e T17 sobre os apoios; T5 e T13 nas cumeeiras); pilares P1–P27 "
              "e pilares de frontão PF1 e PF2, em azul.",
              barra=10.0)
    return f.salvar(caminho)


def desenho_planta_contraventamento(arr: Arranjo, caminho: Path) -> Path:
    """DES-02 — Planta de contraventamento (CV-H, posição de CV-V e CV-T)."""
    f = _planta_base(arr, 400)
    ax, W, B = f.ax, arr.comprimento, 2 * arr.L
    yt = arr.y_tercas()
    for y in yt:
        ax.plot([0, W], [y, y], color="0.7", lw=0.25, zorder=1)
    for i in range(1, arr.n_eixos + 1):
        x = arr.x_eixo(i)
        ax.plot([x, x], [0, B], color="0.45", lw=0.5, zorder=2)
    for n, bay in enumerate(arr.baias_cvh, start=1):
        xa, xb = arr.x_eixo(bay), arr.x_eixo(bay + 1)
        for ya, yb in zip(yt[:-1], yt[1:]):
            _cruz(ax, (xa, ya), (xb, ya), (xb, yb), (xa, yb), lw=0.45)
        for ym in (arr.L * 0.5, arr.L * 1.5):
            _rot(ax, (xa + xb) / 2, ym, f"CV-H{n}", cor=COR_CV, fs=5.2, bold=True)
        for a in ALINHAMENTOS:
            y = arr.y_alinh(a)
            ax.plot([xa, xb], [y, y], color=COR_DESTAQUE, lw=1.3, zorder=4)
            for x in (xa, xb):
                ax.add_patch(Circle((x, y), f.p(0.9), fc=COR_DESTAQUE, ec="k",
                                    lw=0.3, zorder=6))
    num = 1
    for a, baias in (("A", arr.baias_cvv_fachada), ("C", arr.baias_cvv_fachada),
                     ("B", arr.baias_cvv_central)):
        dy = f.p(2.0) if a == "C" else -f.p(2.0)
        for bay in baias:
            xa, xb = arr.x_eixo(bay), arr.x_eixo(bay + 1)
            y = arr.y_alinh(a) + dy
            ax.plot([xa, xb], [y, y], color=COR_CV, lw=2.2, solid_capstyle="butt",
                    zorder=4)
            _rot(ax, (xa + xb) / 2, y + (f.p(2.4) if dy > 0 else -f.p(2.4)),
                 f"CV-V{num}", cor=COR_CV, fs=4.4, bold=True)
            num += 1
    for n, (nome, i, y_pf) in enumerate(arr.pilares_frontao(), start=1):
        x = arr.x_eixo(i)
        ya, yb = sorted((y_pf, 0.0 if i == 1 else B))
        dx = -f.p(2.0) if i == 1 else f.p(2.0)
        ax.plot([x + dx, x + dx], [ya, yb], color=COR_CV, lw=2.2,
                solid_capstyle="butt", zorder=4)
        _rot(ax, x + 2.3 * dx, (ya + yb) / 2, f"CV-T{n}", cor=COR_CV, fs=4.4,
             bold=True, rot=90)
    _pilares_planta(f, arr, rotulos=False)
    for nome, i, y in arr.pilares_frontao():
        _rot(ax, arr.x_eixo(i) + (f.p(1.4) if i == 1 else -f.p(1.4)), y, nome,
             fs=4.4, cor=COR_DESTAQUE, bold=True, ha="left" if i == 1 else "right")
    _cotas_planta(f, arr, [0, arr.L_T, arr.L, 2 * arr.L - arr.L_T, B])
    f.carimbo("DES-02", "PLANTA DE CONTRAVENTAMENTO",
              f"Cotas em m. CV-H1 e CV-H2: cruzes Ø{arr.d_cvh:g} mm nos oito painéis "
              "entre terças de cada vão das baías 1–2 e 8–9. Em traço vermelho espesso, "
              f"a posição dos painéis verticais CV-V1 a CV-V8 (Ø{arr.d_cvv:g} mm, ver "
              f"DES-03) e dos painéis de frontão CV-T1 e CV-T2 (Ø{arr.d_cvt:g} mm, ver "
              "DES-04). Em azul: escoras (terças T1, T9 e T17 das baías rígidas) e nós "
              "de topo.",
              barra=10.0)
    return f.salvar(caminho)


def _elevacao_alinhamento(f: Folha, arr: Arranjo, a: str, yb: float, baias: tuple,
                          num0: int, titulo: str):
    ax, W, H = f.ax, arr.comprimento, arr.H_pilar
    ax.plot([-f.p(3), W + f.p(3)], [yb, yb], color="k", lw=0.6)
    for i in range(1, arr.n_eixos + 1):
        x = arr.x_eixo(i)
        canto = (i, a) in arr.eixos_canto()
        b = arr.b_canto if canto else arr.b_pilar
        ax.add_patch(Rectangle((x - b / 2, yb), b, H, fc=COR_MLC, ec="k", lw=0.4,
                               zorder=3))
        ax.add_patch(Rectangle((x - arr.b_viga / 2, yb + H), arr.b_viga, arr.h0,
                               fc=COR_MLC, ec="k", lw=0.4, zorder=3))
        _rot(ax, x, yb + H * 0.35, nome_pilar(i, a), fs=4.4, rot=90)
        f.bolha(x, yb - f.p(4.0), str(i), r_mm=2.0)
    jt = {"A": 1, "B": 9, "C": 17}[a]
    ax.add_patch(Rectangle((0, yb + H + arr.h0), W, arr.h_terca, fc=COR_MLC,
                           ec="k", lw=0.4, zorder=3))
    _rot(ax, W * 0.5, yb + H + arr.h0 + arr.h_terca / 2, f"T{jt}", fs=4.2,
         fundo=False)
    for n, bay in enumerate(baias):
        xa, xb = arr.x_eixo(bay), arr.x_eixo(bay + 1)
        _cruz(ax, (xa, yb), (xb, yb), (xb, yb + H), (xa, yb + H), lw=0.7)
        _rot(ax, (xa + xb) / 2, yb + H * 0.75, f"CV-V{num0 + n}", cor=COR_CV,
             fs=4.4, bold=True)
    ax.text(-f.p(3), yb + H + arr.h0 + arr.h_terca + f.p(1.5), titulo,
            fontsize=5.6, fontweight="bold", va="bottom")
    f.cota_v(W + f.p(5), yb, yb + H, x_ref=W + f.p(1), esquerda=False, fs=4.6)
    f.cota_v(W + f.p(5), yb + H, yb + H + arr.h0, esquerda=False, fs=4.6)


def desenho_elevacoes_longitudinais(arr: Arranjo, caminho: Path) -> Path:
    """DES-03 — Elevações dos alinhamentos A (fachada) e B (central)."""
    esc, k = 400, 0.4
    W, H = arr.comprimento, arr.H_pilar
    topo = H + arr.h0 + arr.h_terca
    yA = topo + 14 * k
    f = Folha.para_conteudo(esc, -4 * k, W + 9 * k, -16 * k, yA + topo + 5 * k)
    _elevacao_alinhamento(f, arr, "A", yA, arr.baias_cvv_fachada, 1,
                          "ALINHAMENTO A — FACHADA (ALINHAMENTO C IGUAL, COM CV-V3 E CV-V4)")
    _elevacao_alinhamento(f, arr, "B", 0.0, arr.baias_cvv_central, 5,
                          "ALINHAMENTO B — LINHA CENTRAL")
    xs = [arr.x_eixo(i) for i in range(1, arr.n_eixos + 1)]
    f.cadeia_h(xs, -f.p(9.5), fs=4.6)
    f.cota_h(0, W, -f.p(14), fs=5.0)
    f.carimbo("DES-03", "ELEVAÇÕES LONGITUDINAIS",
              f"Cotas em m. Painéis CV-V com diagonais Ø{arr.d_cvv:g} mm, do nó de topo "
              "à base do pilar. Vigas vistas em seção sobre o apoio; terça de apoio "
              "(escora nas baías contraventadas) sobre as vigas.",
              barra=10.0)
    return f.salvar(caminho)


def desenho_elevacao_transversal(arr: Arranjo, caminho: Path) -> Path:
    """DES-04 — Pórtico do frontão (eixo 1), com PF1 e CV-T1."""
    esc, k = 300, 0.3
    B, H = 2 * arr.L, arr.H_pilar
    f = Folha.para_conteudo(esc, -10 * k, B + 6 * k, -17 * k,
                            H + arr.h_ap + arr.h_terca + 4 * k)
    ax = f.ax
    ax.plot([-f.p(3), B + f.p(3)], [0, 0], color="k", lw=0.6)
    tg = math.tan(math.radians(arr.alpha_deg))
    for vao, (ya, yb) in (("AB", (0.0, arr.L)), ("BC", (arr.L, B))):
        ym = (ya + yb) / 2
        ax.add_patch(Polygon([(ya, H), (yb, H), (yb, H + arr.h0), (ym, H + arr.h_ap),
                              (ya, H + arr.h0)], closed=True, fc=COR_MLC, ec="k",
                             lw=0.45, zorder=3))
        _rot(ax, ym + arr.L / 4, H + arr.h0 * 0.55, nome_viga(1, vao), fs=5.0)
    for j, y in enumerate(arr.y_tercas(), start=1):
        z = H + arr.extradorso(y)
        ax.add_patch(Rectangle((y - arr.b_terca / 2, z), arr.b_terca, arr.h_terca,
                               fc=COR_MLC, ec="k", lw=0.3, zorder=4))
        if j in (1, 5, 9, 13, 17):
            _rot(ax, y, z + arr.h_terca + f.p(1.2), f"T{j}", fs=4.2, fundo=False)
    for a in ALINHAMENTOS:
        y = arr.y_alinh(a)
        canto = (1, a) in arr.eixos_canto()
        h = arr.h_canto if canto else arr.h_pilar
        xa = y - h / 2 if a == "B" else (y if a == "A" else y - h)
        ax.add_patch(Rectangle((xa, 0), h, H, fc=COR_MLC, ec="k", lw=0.4, zorder=3))
        _rot(ax, xa + h / 2, H * 0.3, nome_pilar(1, a), fs=4.6, rot=90)
        f.bolha(y, -f.p(4.0), a, r_mm=2.0)
    nome, _, y_pf = arr.pilares_frontao()[0]
    ax.add_patch(Rectangle((y_pf - arr.h_pilar / 2, 0), arr.h_pilar, H,
                           fc=COR_DESTAQUE, ec="k", lw=0.4, zorder=3))
    _rot(ax, y_pf + f.p(1.5), H * 0.3, nome, fs=4.8, cor=COR_DESTAQUE, bold=True,
         ha="left")
    _cruz(ax, (arr.h_canto, 0), (y_pf - arr.h_pilar / 2, 0),
          (y_pf - arr.h_pilar / 2, H), (arr.h_canto, H), lw=0.7)
    _rot(ax, (arr.h_canto + y_pf) / 2, H * 0.75, "CV-T1", cor=COR_CV, fs=4.8, bold=True)
    xa_ = arr.L * 0.22
    ax.text(xa_, H + arr.h0 + xa_ * tg + f.p(2.0), f"α = {arr.alpha_deg:g}°",
            fontsize=4.8, rotation=math.degrees(math.atan(tg)), ha="center")
    f.cadeia_h([0, y_pf, arr.L, B], -f.p(9.5), fs=4.8)
    f.cota_h(0, B, -f.p(14), fs=5.0)
    f.cota_v(-f.p(5), 0, H, x_ref=-f.p(1), fs=4.8)
    f.cota_v(-f.p(5), H, H + arr.h0, fs=4.8)
    f.cota_v(arr.L / 2 + f.p(4), H, H + arr.h_ap, esquerda=False,
             txt=f"{arr.h_ap:.3f}".replace(".", ","), fs=4.6)
    f.carimbo("DES-04", "ELEVAÇÃO TRANSVERSAL — PÓRTICO DO EIXO 1 (FRONTÃO)",
              "Cotas em m. Eixos 2 a 8 iguais, sem PF e sem CV-T; eixo 9 simétrico, com "
              f"PF2 e CV-T2 junto a C. CV-T: diagonais Ø{arr.d_cvt:g} mm. O PF não apoia a "
              "viga: a ligação de topo L1f tem furos oblongos verticais (DES-08).",
              barra=10.0)
    return f.salvar(caminho)


# ── Detalhes (mm) ──────────────────────────────────────────────────────────

def _quebra(ax, x1, x2, y, amp):
    xm = (x1 + x2) / 2
    ax.plot([x1, xm - amp, xm - amp / 3, xm + amp / 3, xm + amp, x2],
            [y, y, y + amp, y - amp, y, y], color="k", lw=0.4, zorder=6)


def _pino(ax, x, y, d, oblongo=0.0):
    if oblongo:
        ax.add_patch(FancyBboxPatch((x - d / 2, y - d / 2 - oblongo), d, d + 2 * oblongo,
                                    boxstyle=f"round,pad=0,rounding_size={d / 2}",
                                    fc="w", ec="k", lw=0.35, zorder=6))
    ax.add_patch(Circle((x, y), d / 2, fc="k", ec="k", lw=0.3, zorder=7))


def desenho_detalhe_L1_L1c(arr: Arranjo, caminho: Path) -> Path:
    """DES-05 — Ligações viga–pilar: L1 (pilar lateral) e L1c (sela central)."""
    d = arr.det
    h0 = arr.h0 * 1000
    tg = math.tan(math.radians(arr.alpha_deg))
    Lv, xc = 760.0, 1950.0
    f = Folha.para_conteudo(20, -260, xc + 700, -700, h0 + Lv * tg + 230,
                            unidade="mm")
    ax = f.ax
    hp, t_top = arr.h_pilar * 1000, d["t_chapa_topo_mm"]
    # ---------- L1 ----------
    ax.add_patch(Rectangle((0, -650), hp, 650 - t_top, fc=COR_MLC, ec="k", lw=0.5))
    _quebra(ax, -40, hp + 40, -650, 20)
    ax.add_patch(Rectangle((0, -t_top), hp, t_top, fc=COR_ACO, ec="k", lw=0.5))
    ax.add_patch(Polygon([(0, 0), (Lv, 0), (Lv, h0 + Lv * tg), (0, h0)],
                         closed=True, fc=COR_MLC, ec="k", lw=0.5))
    Lp, Hp = d["L1_chapa_L_mm"], d["L1_chapa_H_mm"]
    ax.add_patch(Rectangle((0, 0), Lp, Hp, fill=False, ls="--", ec="0.25", lw=0.5,
                           zorder=5))
    ys = [h0 - d["a4c_L1_mm"] - k * d["a2_L1_mm"] for k in range(d["n_pinos_L1"])]
    for y in ys:
        _pino(ax, d["a3t_L1_mm"], y, d["d_pino_L1_mm"], oblongo=d["folga_oblongo_mm"])
    _rot(ax, Lv * 0.68, h0 * 0.45, "viga", fs=5.0)
    _rot(ax, hp / 2, -420, "pilar\nlateral", fs=4.8)
    ax.text(-200, h0 + Lv * tg + 120, "L1 — APOIO NO PILAR LATERAL", fontsize=6,
            fontweight="bold")
    f.cota_h(0, hp, -t_top - 90, y_ref=-t_top, fs=4.6)
    f.cota_h(0, hp + 30, -t_top - 170, txt=f"ℓef = {hp + 30:.0f}", fs=4.6)
    f.cota_h(0, d["a3t_L1_mm"], h0 + 70, y_ref=h0, fs=4.6)
    f.cota_h(0, Lp, -t_top - 250, txt=f"chapa embutida {Lp:.0f}", fs=4.6)
    f.cadeia_v(sorted(ys) + [h0], d["a3t_L1_mm"] + 90, esquerda=False, fs=4.2)
    f.cota_v(-90, 0, h0, x_ref=-10, fs=4.6)
    f.cota_v(-90, -t_top, 0, txt=f"{t_top:g}", fs=4.2)
    f.cota_v(Lp + 60, 0, Hp, txt=f"{Hp:.0f}", esquerda=False, fs=4.4, x_ref=Lp)
    # ---------- L1c ----------
    la, g, ts = d["l_sela_viga_mm"], d["folga_sela_mm"], d["t_sela_mm"]
    Ls = 2 * la + g
    ax.add_patch(Rectangle((xc - hp / 2, -650), hp, 650 - ts, fc=COR_MLC, ec="k",
                           lw=0.5))
    _quebra(ax, xc - hp / 2 - 40, xc + hp / 2 + 40, -650, 20)
    ax.add_patch(Rectangle((xc - Ls / 2, -ts), Ls, ts, fc=COR_ACO, ec="k", lw=0.5))
    for s in (-1, 1):
        xe, xf = xc + s * g / 2, xc + s * (g / 2 + 560)
        ax.add_patch(Polygon([(xe, 0), (xf, 0), (xf, h0 + 560 * tg), (xe, h0)],
                             closed=True, fc=COR_MLC, ec="k", lw=0.5))
        x_ch = xc + s * g / 2
        ax.add_patch(Rectangle((min(x_ch, x_ch + s * Lp), 0), Lp, Hp, fill=False,
                               ls="--", ec="0.25", lw=0.5, zorder=5))
        for y in ys:
            _pino(ax, xc + s * (g / 2 + d["a3t_L1_mm"]), y, d["d_pino_L1_mm"],
                  oblongo=d["folga_oblongo_mm"])
    _rot(ax, xc, -420, "pilar\ncentral", fs=4.8)
    ax.text(xc - 640, h0 + Lv * tg + 120, "L1c — SELA NO PILAR CENTRAL", fontsize=6,
            fontweight="bold")
    f.cota_h(xc - Ls / 2, xc + Ls / 2, -ts - 170, txt=f"sela {Ls:.0f}", fs=4.6)
    f.cota_h(xc + g / 2, xc + g / 2 + la, -ts - 90, y_ref=-ts, fs=4.6)
    f.cota_h(xc - hp / 2, xc + hp / 2, -ts - 250, fs=4.6)
    f.cota_v(xc + Ls / 2 + 50, -ts, 0, txt=f"{ts:g}", esquerda=False, fs=4.2)
    f.carimbo(
        "DES-05", "LIGAÇÕES VIGA–PILAR L1 E L1c",
        f"Cotas em mm. Gravidade por contato: chapa de topo t = {t_top:g} mm no pilar "
        f"lateral; sela {Ls:.0f}×{arr.b_viga * 1000:.0f}×{ts:g} mm no pilar central, aço "
        f"S275. Chapa embutida t = {d['t_chapa_L1_mm']:g} mm S275 em rasgo central da "
        f"viga, soldada à chapa de topo ou à sela; {d['n_pinos_L1']} pinos "
        f"Ø{d['d_pino_L1_mm']:g} por viga em furos ovalizados verticais "
        f"(±{d['folga_oblongo_mm']:g} mm): os pinos recebem só o arrancamento.",
        barra=500.0)
    return f.salvar(caminho)


def _chapa_base_planta(ax, xc, yc, base, b, h, d_chu):
    B, L = base["B_mm"], base["L_mm"]
    ax.add_patch(Rectangle((xc - B / 2, yc - L / 2), B, L, fc=COR_ACO, ec="k",
                           lw=0.5, zorder=2))
    ax.add_patch(Rectangle((xc - b / 2, yc - h / 2), b, h, fill=False, ls="--",
                           ec="0.2", lw=0.5, zorder=3))
    ax.add_patch(Rectangle((xc - base["t_alma_mm"] / 2, yc - h / 2 + 30),
                           base["t_alma_mm"], h - 60, fc="0.35", ec="k", lw=0.3,
                           zorder=3))
    for (x, y) in base["chumbadores_mm"]:
        ax.add_patch(Circle((xc + x, yc + y), 0.925 * d_chu, fc="w", ec="k",
                            lw=0.35, zorder=4))
        ax.add_patch(Circle((xc + x, yc + y), d_chu / 2, fc="k", zorder=5))


def _corte_base(f, xc, yc, base, b_pil, hef, d_chu, larg_conc, h_conc,
                chaveta=None):
    """Corte vertical da base no plano ⊥ ao pórtico (x = largura b)."""
    ax = f.ax
    B, t, pe = base["B_mm"], base["t_mm"], base["pe"]
    ax.add_patch(Rectangle((xc - larg_conc / 2, yc - h_conc), larg_conc, h_conc,
                           fc=COR_CONC, ec="k", lw=0.4, zorder=1))
    for s in (-1, 1):
        _quebra(ax, xc + s * larg_conc / 2, xc + s * larg_conc / 2, yc - h_conc, 0)
    ax.add_patch(Rectangle((xc - B / 2, yc), B, t, fc=COR_ACO, ec="k", lw=0.5, zorder=3))
    L_pe = pe["a3t_mm"] + (pe["n_horiz"] - 1) * pe["a1_mm"] + 2.5 * pe["d_mm"]
    hp = max(700.0, L_pe + 200)
    ax.add_patch(Rectangle((xc - b_pil / 2, yc + t), b_pil, hp, fc=COR_MLC, ec="k",
                           lw=0.5, zorder=3))
    _quebra(ax, xc - b_pil / 2 - 30, xc + b_pil / 2 + 30, yc + t + hp, 20)
    ax.add_patch(Rectangle((xc - base["t_alma_mm"] / 2, yc + t), base["t_alma_mm"],
                           L_pe, fc="0.35", ec="k", lw=0.3, zorder=4))
    for kk in range(pe["n_horiz"]):
        ax.plot([xc - b_pil / 2, xc + b_pil / 2],
                [yc + t + pe["a3t_mm"] + kk * pe["a1_mm"]] * 2, color="k", lw=1.0,
                zorder=5)
    xs = sorted({x for x, _ in base["chumbadores_mm"]})
    for x in xs:
        ax.plot([xc + x, xc + x], [yc - hef, yc + t + 40], color="k", lw=1.4, zorder=4)
        ax.add_patch(Rectangle((xc + x - 30, yc - hef - 12), 60, 12, fc="k", zorder=4))
        ax.add_patch(Rectangle((xc + x - 22, yc + t), 44, 20, fc="0.2", zorder=5))
    if chaveta:
        ax.add_patch(Rectangle((xc - 15, yc - chaveta), 30, chaveta, fc=COR_ACO,
                               ec="k", lw=0.4, zorder=4))
    return xs, hp, L_pe


def desenho_bases_correntes(arr: Arranjo, caminho: Path) -> Path:
    """DES-06 — Bases L3, L3c e L3f (2×2, sem chaveta): planta, corte e quadro."""
    d = arr.det
    b3 = d["bases"]["L3"]
    B, L = b3["B_mm"], b3["L_mm"]
    hef = d["h_ef_mm"]
    xc2, yc2 = 1150.0, -650.0
    f = Folha.para_conteudo(15, -440, xc2 + 700, -1250, 470, unidade="mm")
    ax = f.ax
    _chapa_base_planta(ax, 0, 0, b3, arr.b_pilar * 1000, arr.h_pilar * 1000,
                       d["d_chu_mm"])
    ax.text(-B / 2 - 150, L / 2 + 110, "PLANTA DA CHAPA", fontsize=6, fontweight="bold")
    xs = sorted({x for x, _ in b3["chumbadores_mm"]})
    ys = sorted({y for _, y in b3["chumbadores_mm"]})
    f.cadeia_h([-B / 2] + xs + [B / 2], -L / 2 - 70, y_ref=-L / 2, fs=4.4)
    f.cadeia_v([-L / 2] + ys + [L / 2], -B / 2 - 70, x_ref=-B / 2, fs=4.4)
    f.cota_h(-arr.b_pilar * 500, arr.b_pilar * 500, L / 2 + 40,
             txt=f"pilar {arr.b_pilar * 1000:.0f}×{arr.h_pilar * 1000:.0f}", fs=4.2)
    _rot(ax, B / 2 + 20, 0, "x ⊥ pórtico →", fs=4.0, ha="left")
    xs_c, hp, L_pe = _corte_base(f, xc2, yc2, b3, arr.b_pilar * 1000, hef,
                                 d["d_chu_mm"], B + 400, hef + 160)
    ax.text(xc2 - B / 2 - 200, yc2 + b3["t_mm"] + hp + 60, "CORTE (L3)", fontsize=6,
            fontweight="bold")
    f.cota_v(xc2 + B / 2 + 110, yc2 - hef, yc2, x_ref=xc2 + max(xs_c), esquerda=False,
             txt=f"hef = {hef:.0f}", fs=4.4)
    pe = b3["pe"]
    ys_pe = [yc2 + b3["t_mm"]] + [yc2 + b3["t_mm"] + pe["a3t_mm"] + kk * pe["a1_mm"]
                                  for kk in range(pe["n_horiz"])]
    f.cadeia_v(ys_pe, xc2 - B / 2 - 90, x_ref=xc2 - arr.b_pilar * 500, fs=4.2)
    # quadro das variantes
    y_q = -L / 2 - 230
    cols = (-460, -250, 30, 300)
    linhas = [("Base", "Chapa (mm)", "Pé do pilar", "Onde")]
    for kb, onde in (("L3", "A e C, exceto cantos"), ("L3c", "P11, P14, P17"),
                     ("L3f", "PF1, PF2")):
        bb = d["bases"][kb]
        linhas.append((kb, f"{bb['B_mm']:.0f}×{bb['L_mm']:.0f}×{_g(bb['t_mm'])}",
                       f"{bb['pe']['n_pinos']} cav. Ø{bb['pe']['d_mm']:.0f} "
                       f"({bb['pe']['n_vert']}×{bb['pe']['n_horiz']})", onde))
    for r, ln in enumerate(linhas):
        for txt, xx in zip(ln, cols):
            ax.text(xx, y_q - r * 62, txt, fontsize=4.6, va="top",
                    fontweight="bold" if r == 0 else "normal")
    ax.plot([cols[0], 620], [y_q - 50, y_q - 50], color="k", lw=0.3)
    f.carimbo(
        "DES-06", "BASES DOS PILARES L3, L3c E L3f",
        f"Cotas em mm. Quatro chumbadores M{d['d_chu_mm']:g} classe 8.8, moldados com "
        f"cabeça Ø60, hef = {hef:.0f} mm, em concreto {d['classe_concreto']}, com borda "
        f"≥ {d['c_borda_mm']:.0f} mm. Chapa vertical t = {b3['t_alma_mm']:g} mm soldada à "
        "chapa de base, em rasgo no pé do pilar, com cavilhas Ø20 (fileiras a cada "
        f"{pe['a1_mm']:.0f} mm, a primeira a {pe['a3t_mm']:.0f} mm da base). Aço S275.",
        barra=500.0)
    return f.salvar(caminho)


def desenho_base_ancorada(arr: Arranjo, caminho: Path) -> Path:
    """DES-07 — Base L3a (canto e central montante): 2×3 com chaveta e bloco."""
    d = arr.det
    ba = d["bases"]["L3a"]
    hef, c_b = d["h_ef_mm"], d["c_borda_mm"]
    xsa = sorted({x for x, _ in ba["chumbadores_mm"]})
    ysa = sorted({y for _, y in ba["chumbadores_mm"]})
    Bb = (xsa[-1] - xsa[0]) + 2 * c_b
    Lb = (ysa[-1] - ysa[0]) + 2 * c_b
    xc2 = Bb / 2 + 1100
    f = Folha.para_conteudo(25, -Bb / 2 - 260, xc2 + 760, -Lb / 2 - 230,
                            Lb / 2 + 150, unidade="mm")
    ax = f.ax
    ax.add_patch(Rectangle((-Bb / 2, -Lb / 2), Bb, Lb, fc=COR_CONC, ec="k", lw=0.5,
                           ls=(0, (6, 3)), zorder=1))
    _chapa_base_planta(ax, 0, 0, ba, arr.b_canto * 1000, arr.h_canto * 1000,
                       d["d_chu_mm"])
    ax.add_patch(Rectangle((-15, -d["chaveta_L_mm"] / 2), 30, d["chaveta_L_mm"],
                           fc="none", ec="k", ls=":", lw=0.7, zorder=6))
    ax.text(-Bb / 2, Lb / 2 + 70, "PLANTA (BLOCO EM CINZA)", fontsize=6,
            fontweight="bold")
    f.cadeia_h([-Bb / 2, xsa[0], xsa[-1], Bb / 2], -Lb / 2 - 80, y_ref=-Lb / 2,
               fs=4.4)
    f.cadeia_v([-Lb / 2] + ysa + [Lb / 2], -Bb / 2 - 80, x_ref=-Bb / 2, fs=4.4)
    f.cota_h(-ba["B_mm"] / 2, ba["B_mm"] / 2, ba["L_mm"] / 2 + 60,
             txt=f"chapa {ba['B_mm']:.0f}×{ba['L_mm']:.0f}×{_g(ba['t_mm'])}", fs=4.2)
    _rot(ax, 0, -ba["L_mm"] / 2 - 160, f"chaveta {d['chaveta_L_mm']:.0f} (pontilhado)",
         fs=4.2)
    xs_c, hp, L_pe = _corte_base(f, xc2, 0.0, ba, arr.b_canto * 1000, hef,
                                 d["d_chu_mm"], 1250, d["h_bloco_mm"],
                                 chaveta=d["chaveta_H_mm"])
    ax.text(xc2 - 625, ba["t_mm"] + hp + 50, "CORTE", fontsize=6, fontweight="bold")
    f.cota_v(xc2 + 700, -hef, 0, x_ref=xc2 + max(xs_c), esquerda=False,
             txt=f"hef = {hef:.0f}", fs=4.4)
    f.cota_v(xc2 + 700, -d["h_bloco_mm"], -hef, esquerda=False, fs=4.4)
    f.cota_v(xc2 - 700, -d["chaveta_H_mm"], 0, x_ref=xc2 - 20,
             txt=f"chaveta {d['chaveta_H_mm']:.0f}", fs=4.0)
    pe = ba["pe"]
    f.cota_v(xc2 - 700, ba["t_mm"], ba["t_mm"] + L_pe, x_ref=xc2 - arr.b_canto * 500,
             txt=f"pé: {pe['n_horiz']} fileiras", fs=4.0)
    f.carimbo(
        "DES-07", "BASE ANCORADA L3a — PILARES DE CANTO E CENTRAIS MONTANTES",
        f"Cotas em mm. Seis chumbadores M{d['d_chu_mm']:g} classe 8.8 moldados com "
        f"cabeça Ø60, hef = {hef:.0f} mm; chaveta de cisalhamento {d['chaveta_L_mm']:.0f} "
        f"× {d['chaveta_H_mm']:.0f} mm soldada sob a chapa; bloco de concreto "
        f"{d['classe_concreto']} de pelo menos {Bb:.0f} × {Lb:.0f} mm em planta e "
        f"{d['h_bloco_mm']:.0f} mm de altura (borda ≥ {c_b:.0f} mm). Pé do pilar: "
        f"{pe['n_pinos']} cavilhas Ø{pe['d_mm']:.0f} ({pe['n_vert']}×{pe['n_horiz']}) "
        "em chapa vertical embutida. Os olhais das diagonais CV-V e CV-T soldam-se à "
        "chapa de base.",
        barra=500.0)
    return f.salvar(caminho)


def desenho_detalhe_L1f(arr: Arranjo, caminho: Path) -> Path:
    """DES-08 — Topo do pilar de frontão (L1f): furo oblongo, não apoia a viga."""
    d = arr.det
    tp = d["L1f"]
    folga, hp = tp["folga_mm"], arr.h_pilar * 1000
    ys = [tp["a4c_mm"] + kk * tp["a2_mm"] for kk in range(tp["n_vert"])]
    Hc = ys[-1] + 1.5 * tp["d_mm"] + tp["curso_mm"]
    f = Folha.para_conteudo(10, -620, 640, -520, Hc + 230, unidade="mm")
    ax = f.ax
    t_t = tp["t_topo_mm"]
    ax.add_patch(Rectangle((-hp / 2, -480), hp, 480 - folga - t_t, fc=COR_MLC,
                           ec="k", lw=0.5))
    _quebra(ax, -hp / 2 - 40, hp / 2 + 40, -480, 18)
    ax.add_patch(Rectangle((-hp / 2, -folga - t_t), hp, t_t, fc=COR_ACO, ec="k", lw=0.5))
    ax.add_patch(Rectangle((-560, 0), 1120, Hc + 120, fc=COR_MLC, ec="k", lw=0.5))
    for s in (-1, 1):
        _quebra(ax, s * 560, s * 560, 0, 0)
    ax.add_patch(Rectangle((-tp["L_chapa_mm"] / 2, -folga), tp["L_chapa_mm"],
                           Hc + folga, fill=False, ls="--", ec="0.25", lw=0.5, zorder=5))
    for y in ys:
        _pino(ax, 0, y, tp["d_mm"], oblongo=tp["curso_mm"])
    _rot(ax, 330, Hc - 30, "viga V1 (intradorso)", fs=4.8)
    _rot(ax, 0, -300, "PF1", fs=5.4, bold=True)
    f.cota_v(-hp / 2 - 150, -folga, 0, txt=f"folga {_g(folga)}", fs=4.2, x_ref=-hp / 2)
    f.cota_h(-hp / 2, hp / 2, -folga - t_t - 70, y_ref=-folga - t_t, fs=4.4)
    f.cadeia_v([0] + ys, tp["L_chapa_mm"] / 2 + 60, esquerda=False, fs=4.2,
               x_ref=tp["L_chapa_mm"] / 2)
    f.cota_v(tp["L_chapa_mm"] / 2 + 170, -folga, Hc, esquerda=False, fs=4.2,
             txt=f"chapa {Hc + folga:.0f}")
    f.cota_h(-tp["L_chapa_mm"] / 2, tp["L_chapa_mm"] / 2, Hc + 40, fs=4.2,
             txt=f"chapa {tp['L_chapa_mm']:.0f}")
    ax.annotate("", xy=(-560, Hc / 2), xytext=(-420, Hc / 2),
                arrowprops=dict(arrowstyle="<->", lw=0.6))
    _rot(ax, -490, Hc / 2 + 40, "H", fs=4.8)
    f.carimbo(
        "DES-08", "TOPO DO PILAR DE FRONTÃO — L1f",
        f"Cotas em mm. {tp['n_vert']} cavilhas Ø{tp['d_mm']:g} em chapa embutida t = "
        f"{tp['t_chapa_mm']:g} mm S275, soldada à chapa de topo do PF (t = {t_t:g} mm). "
        f"Furos oblongos verticais com curso ±{tp['curso_mm']:g} mm contra a flecha final "
        f"de {_g(round(tp['w_viga_mm'], 1))} mm da viga no ponto; folga de {folga:g} mm entre a "
        "viga e a chapa de topo. A ligação transmite só a força horizontal H do painel "
        "CV-T.",
        barra=200.0, divisoes=4)
    return f.salvar(caminho)


# ── Conjunto ───────────────────────────────────────────────────────────────

FOLHAS = (
    ("des01_planta_cobertura.pdf", desenho_planta_cobertura),
    ("des02_planta_contraventamento.pdf", desenho_planta_contraventamento),
    ("des03_elevacoes_longitudinais.pdf", desenho_elevacoes_longitudinais),
    ("des04_elevacao_transversal.pdf", desenho_elevacao_transversal),
    ("des05_ligacoes_L1_L1c.pdf", desenho_detalhe_L1_L1c),
    ("des06_bases_correntes.pdf", desenho_bases_correntes),
    ("des07_base_ancorada.pdf", desenho_base_ancorada),
    ("des08_topo_PF_L1f.pdf", desenho_detalhe_L1f),
)


def gerar_desenhos(arr: Arranjo, pasta: Path) -> list[Path]:
    """Gera todas as folhas em `pasta` (tipicamente tese/fig)."""
    return [fn(arr, Path(pasta) / nome) for nome, fn in FOLHAS]


def flecha_no_ponto(w_meio_mm: float, x_m: float, L_m: float) -> float:
    """Flecha de viga biapoiada sob carga uniforme em x (forma exata da elástica)."""
    xi = x_m / L_m
    return w_meio_mm * 16.0 / 5.0 * xi * (1.0 - 2.0 * xi ** 2 + xi ** 3)


def arranjo_de_resultados(res: dict, geo, *, n_eixos: int, L_T: float, H_pilar: float,
                          b_pilar: float, h_pilar: float, b_canto: float,
                          h_canto: float, b_terca: float, h_terca: float,
                          d_chu_mm: float, h_ef_mm: float, c_borda_mm: float,
                          h_bloco_mm: float, chaveta_L_mm: float,
                          chaveta_H_mm: float, classe_concreto: str,
                          l_sela_viga_m: float, folga_sela_m: float,
                          t_chapa_topo_mm: float, folga_oblongo_L1_mm: float) -> Arranjo:
    """Monta o Arranjo a partir dos resultados do pipeline (fonte única)."""
    L1 = res["L1"]
    d = float(L1["d_mm"])
    esq = res["esquadro_chapas"]["L1"]
    pf, topo = res["pilar_frontao"], res["pilar_frontao"]["topo"]
    w_pf = flecha_no_ponto(float(res["ELS"]["w_fin_mm"]), L_T, float(geo.L))
    curso = 5.0 * math.ceil((w_pf + 5.0) / 5.0)

    def _base(k):
        b = res[k]
        return {"B_mm": b["B_mm"], "L_mm": b["L_mm"], "t_mm": b["t_adotada_mm"],
                "chumbadores_mm": b["geometria"]["chumbadores_mm"],
                "t_alma_mm": b["t_alma_mm"], "pe": b["pe_pilar"]}

    det = {
        "t_chapa_topo_mm": t_chapa_topo_mm,
        "n_pinos_L1": int(L1["n_pinos"]), "d_pino_L1_mm": d,
        "a2_L1_mm": float(L1["a2_mm"]), "a3t_L1_mm": float(L1["a3t_mm"]),
        "a4c_L1_mm": 3.0 * d,
        "L1_chapa_L_mm": float(esq["largura_mm"]), "L1_chapa_H_mm": float(esq["altura_mm"]),
        "t_chapa_L1_mm": float(esq["t_adotada_mm"]),
        "folga_oblongo_mm": folga_oblongo_L1_mm,
        "l_sela_viga_mm": l_sela_viga_m * 1000, "folga_sela_mm": folga_sela_m * 1000,
        "t_sela_mm": float(res["sela_central"]["t_adot_mm"]),
        "bases": {"L3": _base("base_L3"), "L3c": _base("base_L3c"),
                  "L3f": _base("base_L3f"), "L3a": _base("base_L3a_canto")},
        "d_chu_mm": d_chu_mm, "h_ef_mm": h_ef_mm, "c_borda_mm": c_borda_mm,
        "h_bloco_mm": h_bloco_mm, "chaveta_L_mm": chaveta_L_mm,
        "chaveta_H_mm": chaveta_H_mm, "classe_concreto": classe_concreto,
        # L1f: os furos oblongos exigem, na chapa, a2 ≥ 2·curso + d0 + 1,2·d0
        # (aço entre furos); na madeira a2 maior que o mínimo só favorece.
        "L1f": {
            "n_vert": int(topo["n_vert"]), "d_mm": float(topo["d_mm"]),
            "a2_mm": max(float(topo["a2_mm"]),
                         10.0 * math.ceil((2.0 * curso + 2.2 * float(topo["d_mm"])) / 10.0)),
            "a4c_mm": float(topo["a4c_mm"]),
            "t_chapa_mm": float(topo["t_chapa_mm"]), "t_topo_mm": t_chapa_topo_mm,
            "L_chapa_mm": h_pilar * 1000,
            "w_viga_mm": w_pf, "curso_mm": curso, "folga_mm": curso + 5.0,
        },
    }
    return Arranjo(
        L=float(geo.L), h0=float(geo.h0), alpha_deg=float(geo.alpha_deg),
        b_viga=float(geo.b), n_eixos=n_eixos, L_T=L_T, H_pilar=H_pilar,
        b_pilar=b_pilar, h_pilar=h_pilar, b_canto=b_canto, h_canto=h_canto,
        b_terca=b_terca, h_terca=h_terca, n_paineis_terca=8,
        baias_cvh=(1, n_eixos - 1), baias_cvv_fachada=(1, n_eixos - 1),
        baias_cvv_central=(1, 2, n_eixos - 2, n_eixos - 1),
        d_cvh=float(res["contraventamento"].get("d_mm",
                                                res["contraventamento"].get("d_barra_mm"))),
        d_cvv=float(res["contraventamento_vertical"]["d_mm"]),
        d_cvt=float(res["contraventamento_transversal"]["d_mm"]),
        det=det,
    )
