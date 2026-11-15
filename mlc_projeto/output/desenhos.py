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

from mlc_projeto.connections.chapas_aco import d0_furo  # noqa: E402
from mlc_projeto.connections.oblongo_L1 import E_RASGO_VENTILACAO_MM  # noqa: E402

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
    a_bal: float = 0.0          # balanço da viga no beiral, do eixo do apoio (m)
    a_oit: float = 0.0          # balanço da terça no oitão, do eixo do frontão (m)
    d_cvd: float = 0.0          # cruzes da alma do diafragma, baías 2–8 (issue 110)

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
        """Altura do extradorso acima do intradorso, em y (−a → 2L + a)."""
        tg = math.tan(math.radians(self.alpha_deg))
        if y < 0:
            return self.h0 + y * tg                        # beiral A
        if y > 2 * self.L:
            return self.h0 - (y - 2 * self.L) * tg         # beiral C
        yl = y % self.L if y < 2 * self.L else self.L
        d = min(yl, self.L - yl)
        return self.h0 + d * tg

    def y_tercas_ponta(self) -> list[float]:
        """Terças de ponta, na extremidade dos beirais (issue 82)."""
        if self.a_bal <= 0:
            return []
        return [-self.a_bal + self.b_terca / 2, 2 * self.L + self.a_bal - self.b_terca / 2]

    def contorno_cobertura(self) -> tuple[float, float, float, float]:
        """(x0, y0, x1, y1) da cobertura em planta, com oitões e beirais."""
        return (-self.a_oit, -self.a_bal, self.comprimento + self.a_oit,
                2 * self.L + self.a_bal)

    def eixos_canto(self) -> list[tuple[int, str]]:
        return [(1, "A"), (1, "C"), (self.n_eixos, "A"), (self.n_eixos, "C")]

    def montantes(self, a: str) -> set[int]:
        """Eixos dos pilares bipartidos (montantes das baías contraventadas, issue 104)."""
        baias = self.baias_cvv_central if a == "B" else self.baias_cvv_fachada
        return {e for bay in baias for e in (bay, bay + 1)}

    @property
    def bip(self) -> dict | None:
        """Geometria do pilar bipartido em metros (None se não houver)."""
        g = self.det.get("bipartido")
        if not g:
            return None
        return {k: g[k] / 1000.0 for k in ("a_mm", "b_l_mm", "h_l_mm", "y_l_mm", "y_no_mm")}

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
                ha="center", va="bottom" if acima else "top", fontsize=fs,
                bbox=dict(fc="w", ec="none", pad=0.15), zorder=9)

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
                fontsize=fs, bbox=dict(fc="w", ec="none", pad=0.15), zorder=9)

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
    RODAPE_MM = 19.0

    #: Nota de proteção contra corrosão das folhas com peças de aço (issue 86).
    NOTA_CORROSAO = ("PROTEÇÃO: aço galvanizado a fogo após corte, furação e solda (EN ISO 1461; "
                     "parafusos e barras roscadas EN ISO 10684); solda de obra só com reparo em "
                     "tinta rica em zinco; bases com pintura sobre o zinco (dúplex); pilarete com "
                     "intumescente R60.")

    def carimbo(self, codigo: str, titulo: str, nota: str = "",
                barra: float | None = None, divisoes: int = 5, com_escala: bool = True):
        """Título, notas (com quebra de linha) e escala gráfica no rodapé."""
        import textwrap
        ax = self.ax
        x = self.x0 + self.p(2.0)
        y = self.y0 + self.p(15.0)
        ax.text(x, y, f"{codigo} · {titulo}" + (f" · ESCALA 1:{self.escala:g}" if com_escala
                                               else " · SEM ESCALA"),
                fontsize=6.0, fontweight="bold", va="bottom")
        linhas = textwrap.wrap(nota, 168)
        if len(linhas) > 7:
            raise ValueError(f"{codigo}: nota com {len(linhas)} linhas (máx. 7) — encurtar")
        for n, linha in enumerate(linhas):
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


#: Remissão às notas gerais, no lugar das notas repetidas em cada folha.
REF_GERAIS = "Materiais, proteção, soldas e convenções: DES-00."

#: Espessuras de linha (pt): seção cortada, vista, cotas e eixos.
LW_CORTE, LW_VISTA, LW_FINA = 0.7, 0.4, 0.25


def _balao(f, x, y, marca, dx=40.0, dy=40.0, fs=3.6, r_mm=1.9):
    """Marca de peça: círculo com o código, ligado à peça por linha de chamada."""
    ax = f.ax
    xb, yb = x + dx, y + dy
    r = f.p(r_mm)
    ax.plot([x, xb - r * (1 if dx >= 0 else -1) * 0.7], [y, yb - r * 0.7 * (1 if dy >= 0 else -1)],
            color="k", lw=LW_FINA, zorder=9)
    ax.add_patch(Circle((x, y), f.p(0.35), fc="k", zorder=9))
    ax.add_patch(Circle((xb, yb), r, fc="w", ec="k", lw=LW_FINA + 0.1, zorder=10))
    ax.text(xb, yb, marca, fontsize=fs * 0.82, ha="center", va="center", zorder=11)


def _tabela(f, x, y, titulo, cab, linhas, cols_mm, fs=3.4):
    """Tabela simples (quadro de variantes): cabeçalho em negrito e filete."""
    ax = f.ax
    lh = f.p(2.6)
    ax.text(x, y, titulo, fontsize=fs + 0.6, fontweight="bold", va="bottom")
    for i, ln in enumerate([cab] + linhas):
        yy = y - f.p(1.2) - i * lh
        for c, cm in zip(ln, cols_mm):
            ax.text(x + f.p(cm), yy, str(c), fontsize=fs, va="top",
                    fontweight="bold" if i == 0 else "normal")
        if i == 0:
            ax.plot([x, x + f.p(cols_mm[-1] + 22)], [yy - lh * 0.82] * 2, color="k", lw=LW_FINA)
    return y - f.p(1.2) - (len(linhas) + 1) * lh


def _altura_lista_mm(n_itens: int) -> float:
    """Altura de papel (mm) ocupada pela lista de peças com n itens."""
    return 4.5 + (n_itens + 1) * 2.6


def chapa_topo_L1(arr) -> tuple:
    """Chapa de topo do pilar lateral: cobre a seção inteira do pilar (h × b), que é o
    comprimento de apoio da verificação de contato (issue 116)."""
    return ("chapa de topo", arr.h_pilar * 1000, arr.b_pilar * 1000, arr.det["t_chapa_topo_mm"])


def _pecas_topo(d: dict, arr, k_base: str, chapa: tuple) -> list:
    """Peças da ligação viga–pilar corrente: chapa de topo/sela, chapa embutida, pinos,
    tirante interno, luva, abas e cavilhas do topo (concepção revista)."""
    nome_ch, a_ch, b_ch, t_ch = chapa
    tir = (d.get("tirante") or {}).get(k_base)
    cav = (d.get("topo_pilar") or {}).get(k_base) or {}
    hp, bp = arr.h_pilar * 1000, arr.b_pilar * 1000
    Lp, Hp, tc = d["L1_chapa_L_mm"], d["L1_chapa_H_mm"], d["t_chapa_L1_mm"]
    n_v = 2 if k_base == "base_L3c" else 1
    it = [("CH-01", f"{nome_ch} {a_ch:.0f}×{b_ch:.0f}×{_g(t_ch)}", 1, "S275 Z",
           _g(round(_massa_chapa(a_ch, b_ch, t_ch), 1))),
          ("CH-02", f"chapa embutida {Lp:.0f}×{Hp:.0f}×{_g(tc)}", n_v, "S275",
           _g(round(_massa_chapa(Lp, Hp, tc), 1))),
          ("PN-01", f"pino Ø{_g(d['d_pino_L1_mm'])}×{arr.b_viga * 1000 - 30:.0f} + tampões",
           d["n_pinos_L1"] * n_v, "S275", _g(round(_massa_barra(d["d_pino_L1_mm"],
                                                                arr.b_viga * 1000 - 30), 1)))]
    if tir:
        L_tir = float(tir["L_corte_mm"])
        Dl = tir["D_luva_mm"]
        it += [("TR-01", f"tirante M{tir['d_mm']}×{L_tir:.0f}, porca e arruela-chapa "
                f"Ø{tir['arruela_chapa_mm']:.0f}", 1, "8.8 galv.",
                _g(round(_massa_barra(tir["d_mm"], L_tir), 1))),
               ("LV-01", f"luva roscada Ø{Dl:.0f}×60, M{tir['d_mm']}", 1, "S355",
                _g(round(_massa_barra(Dl, 60) - _massa_barra(tir["d_mm"], 60), 1)))]
    if cav:
        L_ab = cav["a3t_mm"] + (cav["n_horiz"] - 1) * cav["a1_mm"] + 2 * cav["d_mm"]
        w = (hp - 60 - (tir["furo_pilar_mm"] + 10 if tir else 0)) / 2
        it += [("AB-01", f"aba {w:.0f}×{L_ab:.0f}×{_g(cav['t_chapa_mm'])}", 2, "S275",
                _g(round(_massa_chapa(w, L_ab, cav["t_chapa_mm"]), 1))),
               ("CV-01", f"cavilha Ø{_g(cav['d_mm'])}×{bp - 30:.0f}", cav["n_pinos"], "S275",
                _g(round(_massa_barra(cav["d_mm"], bp - 30), 1)))]
    return it


def _pecas_bipartido(d: dict, arr, rc: dict) -> list:
    """Peças do pilar bipartido (por pilar central montante)."""
    g = d["bipartido"]
    a, bl, hl = g["a_mm"], g["b_l_mm"], g["h_l_mm"]
    sela, no, esp = rc["sela"], rc["no"], rc["espacadores"]
    ts = float(sela["t_chapa_mm"])
    L_aba = sela["a3t_mm"] + (sela["n_horiz"] - 1) * sela["a1_mm"] + 2 * sela["d_mm"]
    L_no = no["a3t_mm"] + (no["n_horiz"] - 1) * no["a1_mm"] + 2 * no["d_mm"]
    L_lam = arr.H_pilar * 1000 - 300 + arr.h0 * 1000 + g["folga_escora_mm"]
    n_pack = int(L_lam // esp["l1_mm"]) + 1
    ol = (d.get("lig_diag") or {}).get("CV-V") or {}
    te = ol.get("t_eye_mm", 22)
    return [
        ("LM-01", f"lâmina MLC {bl:.0f}×{hl:.0f}×{L_lam:.0f}", 2, "GL24h", "—"),
        ("ES-01", f"espaçador MLC {a:.0f}×{hl:.0f}×450 + {esp['n_parafusos']} M16 8.8",
         n_pack, "GL24h", "—"),
        ("SL-01", f"sela {a + bl:.0f}×{hl:.0f}×{_g(ts)}", 1, "S275",
         _g(round(_massa_chapa(a + bl, hl, ts), 1))),
        ("SA-01", f"aba da sela {L_aba:.0f}×{hl - 60:.0f}×{_g(ts)}", 2, "S275",
         _g(round(_massa_chapa(L_aba, hl - 60, ts), 1))),
        ("CV-01", f"cavilha Ø{_g(sela['d_mm'])}×{bl - 30:.0f}", 2 * sela["n_pinos"], "S275",
         _g(round(_massa_barra(sela["d_mm"], bl - 30), 1))),
        ("CP-01", f"chapa-capa {bl + 40:.0f}×{hl:.0f}×20", 1, "S275",
         _g(round(_massa_chapa(bl + 40, hl, 20), 1))),
        ("CA-01", f"aba da capa {L_no:.0f}×{hl - 60:.0f}×20", 1, "S275",
         _g(round(_massa_chapa(L_no, hl - 60, 20), 1))),
        ("CV-02", f"cavilha Ø{_g(no['d_mm'])}×{bl - 30:.0f}", no["n_pinos"], "S275",
         _g(round(_massa_barra(no["d_mm"], bl - 30), 1))),
        ("OL-01", f"olhal t = {_g(te)} soldado à capa (DES-11)", 1, "S235", "—"),
        ("PF-01", "parafuso M24 8.8 com porca e arruelas", 2, "8.8 galv.", "—"),
    ]


def _massa_chapa(a_mm: float, b_mm: float, t_mm: float) -> float:
    return a_mm * b_mm * t_mm * 7.85e-6


def _massa_barra(d_mm: float, L_mm: float) -> float:
    return math.pi * d_mm ** 2 / 4.0 * L_mm * 7.85e-6


def _lista_pecas(f, x, y, itens, fs=3.4, titulo="LISTA DE PEÇAS (por ligação)"):
    """Tabela marca · descrição · qtd · aço · massa (kg). itens: tuplas de 5 campos."""
    ax = f.ax
    col = [0.0, 11.0, 63.0, 67.0, 86.0]                     # mm de papel
    lh = f.p(2.6)
    ax.text(x, y, titulo, fontsize=fs + 0.6, fontweight="bold", va="bottom")
    cab = ("Marca", "Descrição", "Qtd.", "Aço", "kg")
    linhas = [cab] + [tuple(str(c) for c in it) for it in itens]
    for i, ln in enumerate(linhas):
        yy = y - f.p(1.2) - i * lh
        for j, c in enumerate(ln):
            ax.text(x + f.p(col[j]), yy, c, fontsize=fs, va="top",
                    fontweight="bold" if i == 0 else "normal",
                    ha="right" if j in (2, 4) else "left")
        if i == 0:
            ax.plot([x, x + f.p(90)], [yy - lh * 0.82] * 2, color="k", lw=LW_FINA)
    return y - f.p(1.2) - len(linhas) * lh


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


#: Espessura do graute sob a chapa de base (porca de nivelamento), mm.
GRAUTE_MM = 30.0
from mlc_projeto.checks.elu.pilar_bipartido import FOLGA_ESCORA_VIGA_MM  # noqa: E402,F401


def _solda_txt(d: dict, chave: str) -> str | None:
    """Garganta e comprimento da solda cuja descrição contém `chave` (issue 91)."""
    for peca, a, l, n in d.get("soldas", []):
        if chave in peca:
            t = f"a{_g(a)}"
            if l:
                t += f"–{l:.0f}"
            if n and int(n) >= 2:
                t += " (2 lados)"
            return t
    return None


def _solda(f, x, y, txt, dx=60.0, dy=60.0, fs=3.6):
    """Chamada de solda: seta, linha de referência e símbolo de filete (issue 91)."""
    if not txt:
        return
    ax = f.ax
    x1, y1 = x + dx, y + dy
    ax.annotate("", xy=(x, y), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", lw=0.35, color=COR_DESTAQUE,
                                mutation_scale=4, shrinkA=0, shrinkB=0), zorder=9)
    sg = 1 if dx >= 0 else -1
    tri = f.p(1.1)
    Lr = f.p(0.21 * fs * len(txt)) + 2.5 * tri
    ax.plot([x1, x1 + sg * Lr], [y1, y1], color=COR_DESTAQUE, lw=0.35, zorder=9)
    xt = x1 + sg * f.p(0.8)
    ax.add_patch(Polygon([(xt, y1), (xt + sg * tri, y1), (xt, y1 + tri)], closed=True,
                         fc=COR_DESTAQUE, ec="none", zorder=9))
    ax.text(xt + sg * (tri + f.p(0.5)), y1 + f.p(0.25), txt, fontsize=fs, color=COR_DESTAQUE,
            ha="left" if sg > 0 else "right", va="bottom", zorder=10,
            bbox=dict(fc="w", ec="none", pad=0.1))


def _nivel(f, x, y, txt, fs=4.0, comp_mm=4.0):
    """Cota de nível: triângulo sobre a linha e texto à direita."""
    ax, t = f.ax, f.p(1.1)
    ax.plot([x - f.p(comp_mm), x + f.p(comp_mm)], [y, y], color="k", lw=0.35, zorder=8)
    ax.add_patch(Polygon([(x - t * 0.7, y + t), (x + t * 0.7, y + t), (x, y)], closed=True,
                         fc="w", ec="k", lw=0.35, zorder=8))
    ax.text(x + f.p(comp_mm) + f.p(0.6), y, txt, fontsize=fs, va="center", zorder=9,
            bbox=dict(fc="w", ec="none", pad=0.1))


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
            bp = arr.bip
            if bp and i in arr.montantes(a):          # pilar bipartido: duas lâminas
                for sg in (-1, 1):
                    ax.add_patch(Rectangle((x + sg * bp["y_l_mm"] - bp["b_l_mm"] / 2,
                                            y - bp["h_l_mm"] / 2), bp["b_l_mm"], bp["h_l_mm"],
                                           fc="k", ec="k", lw=0.3, zorder=4))
            else:
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
    cx0, cy0, cx1, cy1 = arr.contorno_cobertura()
    ax.add_patch(Rectangle((cx0, cy0), cx1 - cx0, cy1 - cy0, fill=False, ec="k",
                           lw=0.6, ls=(0, (6, 2)), zorder=2))
    for j, y in enumerate(yt, start=1):
        ax.plot([cx0, cx1], [y, y], color="0.35", lw=0.45 if j in (1, 9, 17) else 0.3,
                zorder=2)
        _rot(ax, cx1 + f.p(1.5), y, f"T{j}", fs=4.2, ha="left")
    for y, nome in zip(arr.y_tercas_ponta(), ("T0", "T18")):
        ax.plot([cx0, cx1], [y, y], color="0.35", lw=0.3, zorder=2)
        _rot(ax, cx1 + f.p(1.5), y + (-f.p(1.2) if y < 0 else f.p(1.2)), nome, fs=4.2,
             ha="left")
    for i in range(1, arr.n_eixos + 1):
        x = arr.x_eixo(i)
        for vao, (ya, yb) in (("AB", (-arr.a_bal, arr.L)), ("BC", (arr.L, B + arr.a_bal))):
            ax.add_patch(Rectangle((x - arr.b_viga / 2, ya), arr.b_viga, yb - ya,
                                   fc=COR_MLC, ec="k", lw=0.4, zorder=3))
            _rot(ax, x, max(ya, 0) + arr.L * 0.70, nome_viga(i, vao), fs=4.4, rot=90)
    for yc in (arr.L / 2, 1.5 * arr.L):
        ax.plot([0, W], [yc, yc], color="k", lw=0.25, ls="--", zorder=2)
    _rot(ax, arr.L_T / 2, arr.L / 2, "cumeeira", fs=4.0)
    _pilares_planta(f, arr)
    _cotas_planta(f, arr, [arr.y_alinh(a) for a in ALINHAMENTOS])
    f.cadeia_v(yt[:9], cx1 + f.p(8), esquerda=False, fs=3.8)
    if arr.a_bal > 0:
        f.cota_v(cx1 + f.p(8), cy0, 0, esquerda=False, fs=3.8)
        f.cota_h(cx0, 0, cy1 + f.p(1.5), fs=3.8)
    f.carimbo("DES-01", "PLANTA DE COBERTURA E LOCAÇÃO",
              "Cotas em m. Vigas V1–V18 sob as terças T1–T17 (terças a cada L/8; "
              "T1, T9 e T17 sobre os apoios; T5 e T13 nas cumeeiras); pilares P1–P27 "
              "e pilares de frontão PF1 e PF2, em azul. Em tracejado, o contorno da "
              f"cobertura: beirais de {_g(round(arr.a_bal, 3))} m (vigas em balanço) em A "
              f"e C, com as terças de ponta T0 e T18, e oitões de {_g(round(arr.a_oit, 2))} m (terças "
              "em balanço) nos eixos 1 e 9, medidos dos eixos.",
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
    if arr.d_cvd:                                   # alma do diafragma (issue 110)
        for bay in range(1, arr.n_eixos):
            if bay in arr.baias_cvh:
                continue
            xa, xb = arr.x_eixo(bay), arr.x_eixo(bay + 1)
            for ya, yb in zip(yt[:-1], yt[1:]):
                _cruz(ax, (xa, ya), (xb, ya), (xb, yb), (xa, yb), cor="0.45", lw=0.22)
            if bay == arr.n_eixos // 2:
                for ym in (arr.L * 0.5, arr.L * 1.5):
                    _rot(ax, (xa + xb) / 2, ym, "CV-D", cor="0.3", fs=5.2, bold=True)
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
              "entre terças de cada vão das baías 1–2 e 8–9"
              + (f"; CV-D, alma do diafragma: cruzes Ø{arr.d_cvd:g} mm em todos os painéis "
                 "das baías 2–3 a 7–8 (traço fino cinza)" if arr.d_cvd else "")
              + ". Em traço vermelho espesso, "
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
        bp = arr.bip
        if bp and i in arr.montantes(a):              # bipartido: lâminas até a escora
            for sg in (-1, 1):
                ax.add_patch(Rectangle((x + sg * bp["y_l_mm"] - bp["b_l_mm"] / 2, yb),
                                       bp["b_l_mm"], H + arr.h0, fc=COR_MLC, ec="k", lw=0.4,
                                       zorder=3))
        else:
            ax.add_patch(Rectangle((x - b / 2, yb), b, H, fc=COR_MLC, ec="k", lw=0.4,
                                   zorder=3))
        ax.add_patch(Rectangle((x - arr.b_viga / 2, yb + H), arr.b_viga, arr.h0,
                               fc=COR_MLC, ec="k", lw=0.4, zorder=3))
        _rot(ax, x, yb + H * 0.35, nome_pilar(i, a), fs=4.4, rot=90)
        f.bolha(x, yb - f.p(4.0), str(i), r_mm=2.0)
    jt = {"A": 1, "B": 9, "C": 17}[a]
    ax.add_patch(Rectangle((-arr.a_oit, yb + H + arr.h0), W + 2 * arr.a_oit,
                           arr.h_terca, fc=COR_MLC, ec="k", lw=0.4, zorder=3))
    _rot(ax, W * 0.5, yb + H + arr.h0 + arr.h_terca / 2, f"T{jt}", fs=4.2,
         fundo=False)
    for n, bay in enumerate(baias):
        xa, xb = arr.x_eixo(bay), arr.x_eixo(bay + 1)
        bp = arr.bip
        if bp:                    # nó no topo da lâmina, no nível da escora (issue 104)
            zn, yn = yb + H + arr.h0 - 0.10, bp["y_no_mm"]
            _cruz(ax, (xa, yb), (xb, yb), (xb - yn, zn), (xa + yn, zn), lw=0.7)
        else:
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
              f"Cotas em m. Painéis CV-V com diagonais Ø{arr.d_cvv:g} mm, do nó no topo da "
              "lâmina, no nível da escora, à base do pilar vizinho. Nos montantes das baías "
              "contraventadas, o pilar é bipartido: duas lâminas dos lados da viga, até a "
              "escora (DES-07B). Vigas vistas em seção sobre o apoio; terça de apoio (escora "
              "nas baías contraventadas) sobre as vigas, prolongada em balanço nos oitões.",
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
    hb = arr.h0 - arr.a_bal * tg                           # altura na ponta do beiral
    for vao, (ya, yb) in (("AB", (0.0, arr.L)), ("BC", (arr.L, B))):
        ym = (ya + yb) / 2
        pts = [(ya, H), (yb, H), (yb, H + arr.h0), (ym, H + arr.h_ap), (ya, H + arr.h0)]
        if arr.a_bal > 0 and vao == "AB":
            pts = [(-arr.a_bal, H)] + pts[1:] + [(-arr.a_bal, H + hb)]
        elif arr.a_bal > 0:
            pts = [(ya, H), (yb + arr.a_bal, H), (yb + arr.a_bal, H + hb),
                   (yb, H + arr.h0), (ym, H + arr.h_ap), (ya, H + arr.h0)]
        ax.add_patch(Polygon(pts, closed=True, fc=COR_MLC, ec="k", lw=0.45, zorder=3))
        _rot(ax, ym + arr.L / 4, H + arr.h0 * 0.55, nome_viga(1, vao), fs=5.0)
    for y in arr.y_tercas_ponta():
        z = H + arr.extradorso(y + (arr.b_terca / 2 if y < 0 else -arr.b_terca / 2))
        ax.add_patch(Rectangle((y - arr.b_terca / 2, z), arr.b_terca, arr.h_terca,
                               fc=COR_MLC, ec="k", lw=0.3, zorder=4))
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
        bp = arr.bip
        if bp and 1 in arr.montantes(a):      # lâmina externa do bipartido, até a escora
            h = bp["h_l_mm"]
        xa = y - h / 2 if a == "B" else (y if a == "A" else y - h)
        H_p = H + arr.h0 if bp and 1 in arr.montantes(a) else H
        ax.add_patch(Rectangle((xa, 0), h, H_p, fc=COR_MLC, ec="k", lw=0.4,
                               zorder=5 if H_p > H else 3))
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
    if arr.a_bal > 0:
        for y1, y2 in ((-arr.a_bal, 0.0), (B, B + arr.a_bal)):
            f.cota_h(y1, y2, H + arr.h0 + f.p(4), y_ref=H + hb, fs=4.2,
                     txt=f"{y2 - y1:.3f}".replace(".", ","))
    f.cota_v(-f.p(5), 0, H, x_ref=-f.p(1), fs=4.8)
    f.cota_v(-f.p(5), H, H + arr.h0, fs=4.8)
    f.cota_v(arr.L / 2 + f.p(4), H, H + arr.h_ap, esquerda=False,
             txt=f"{arr.h_ap:.3f}".replace(".", ","), fs=4.6)
    f.carimbo("DES-04", "ELEVAÇÃO TRANSVERSAL — PÓRTICO DO EIXO 1 (FRONTÃO)",
              "Cotas em m. Eixos 2 a 8 iguais, sem PF e sem CV-T; eixo 9 simétrico, com "
              f"PF2 e CV-T2 junto a C. CV-T: diagonais Ø{arr.d_cvt:g} mm. O PF não apoia a "
              "viga: a ligação de topo L1f tem furos oblongos verticais (DES-08). "
              "Beirais: vigas em balanço além de A e C (cota do eixo à ponta), com "
              "terça de ponta.",
              barra=10.0)
    return f.salvar(caminho)


# ── Detalhes (mm) ──────────────────────────────────────────────────────────

def _quebra(ax, x1, x2, y, amp):
    xm = (x1 + x2) / 2
    ax.plot([x1, xm - amp, xm - amp / 3, xm + amp / 3, xm + amp, x2],
            [y, y, y + amp, y - amp, y, y], color="k", lw=0.4, zorder=6)


def _pino(ax, x, y, d, oblongo=0.0, oculto=True):
    """
    Pino em furo ovalizado; oblongo = curso simétrico ou (acima, abaixo).
    O furo é da chapa EMBUTIDA, dentro da viga: em vista, linha oculta (issue 90).
    A ponta do pino aparece na face (círculo cheio).
    """
    if oblongo:
        cima, baixo = oblongo if isinstance(oblongo, tuple) else (oblongo, oblongo)
        ax.add_patch(FancyBboxPatch((x - d / 2, y - d / 2 - baixo), d, d + cima + baixo,
                                    boxstyle=f"round,pad=0,rounding_size={d / 2}",
                                    fill=False, ec="k", lw=0.35,
                                    ls=(0, (2.0, 1.2)) if oculto else "-", zorder=6))
    ax.add_patch(Circle((x, y), d / 2, fc="k", ec="k", lw=0.3, zorder=7))


def _hachura(ax, x, y, w, h, fc=COR_ACO, zorder=5, hatch="////"):
    ax.add_patch(Rectangle((x, y), w, h, fc=fc, ec="k", lw=0.35, hatch=hatch,
                           zorder=zorder))


def _corte_viga(f, xs: float, d: dict, *, b: float, h_c: float, t_apoio: float,
                larg_apoio: float, rotulo: str, consolo: tuple | None = None,
                pilar: tuple | None = None) -> None:
    """
    Corte transversal da viga no plano da fileira de pinos (issue 90): rasgo, chapa
    embutida, pinos cortados, folga no fundo do rasgo e as duas faixas de madeira
    que se apoiam na chapa de topo ou na sela.
    """
    ax = f.ax
    tr, tc = d["t_rasgo_mm"], d["t_chapa_L1_mm"]
    Hp, Hr = d["L1_chapa_H_mm"], d["fundo_rasgo_mm"]
    dp, d0 = d["d_pino_L1_mm"], d["d0_L1_mm"]
    cima, baixo = d["folga_oblongo_mm"]
    ys = _ys_L1(d)
    # madeira (cortada) e rasgo
    ax.add_patch(Rectangle((xs - b / 2, 0), b, h_c, fc=COR_MLC, ec="k", lw=LW_CORTE,
                           zorder=2))
    ax.add_patch(Rectangle((xs - tr / 2, 0), tr, Hr, fc="w", ec="k", lw=0.4, zorder=3))
    # chapa embutida, com os furos ovalizados abertos em volta de cada pino
    _hachura(ax, xs - tc / 2, 0, tc, Hp, zorder=4)
    for y in ys:
        ax.add_patch(Rectangle((xs - tc / 2, y - d0 / 2 - baixo), tc, d0 + cima + baixo,
                               fc="w", ec="k", lw=0.3, zorder=5))
    # pinos cortados ao longo do eixo, com tampões nas faces
    rec = 15.0
    for y in ys:
        _hachura(ax, xs - b / 2 + rec, y - dp / 2, b - 2 * rec, dp, fc="0.45", zorder=6,
                 hatch="")
        for sg in (-1, 1):
            ax.add_patch(Rectangle((xs + sg * (b / 2 - rec / 2) - rec / 2, y - dp / 2), rec, dp,
                                   fc="#8c6d3f", ec="k", lw=0.3, zorder=6))
    # apoio: chapa de topo ou sela, com a largura dada
    _hachura(ax, xs - larg_apoio / 2, -t_apoio, larg_apoio, t_apoio, zorder=4)
    if consolo:                                       # enrijecedores da sela, no corte
        n, te, hc = consolo
        for k in range(n):
            xk = xs - larg_apoio / 2 + te / 2 + k * (larg_apoio - te) / max(n - 1, 1)
            _hachura(ax, xk - te / 2, -t_apoio - hc, te, hc, zorder=4)
    if pilar:                                         # topo do pilar abaixo da chapa
        bp, tvp, n_cav, a1_cav, a3_cav, dcav = pilar[:6]
        tir = pilar[6] if len(pilar) > 6 else None
        z0 = -t_apoio
        ax.add_patch(Rectangle((xs - bp / 2, z0 - 420), bp, 420, fc=COR_MLC, ec="k",
                               lw=LW_CORTE, zorder=2))
        _quebra(ax, xs - bp / 2 - 30, xs + bp / 2 + 30, z0 - 420, 15)
        if tir:                                       # furo central, tirante e luva
            fu, dt, Dl = tir["furo_pilar_mm"], tir["d_mm"], tir["D_luva_mm"]
            ax.add_patch(Rectangle((xs - fu / 2, z0 - 420), fu, 420, fc="w", ec="k",
                                   lw=LW_FINA, zorder=3))
            _hachura(ax, xs - Dl / 2, z0 - 60, Dl, 60, zorder=5)
            _hachura(ax, xs - dt / 2, z0 - 420, dt, 360, fc="0.55", zorder=4, hatch="")
        for k in range(n_cav):
            yk = z0 - a3_cav - k * a1_cav
            if yk < z0 - 400:
                break
            for sg in (-1, 1):                        # a cavilha não atravessa o furo
                x_in = (tir["furo_pilar_mm"] / 2 + 6) if tir else tvp / 2
                ax.add_patch(Rectangle((xs + sg * x_in if sg > 0 else xs - bp / 2 + 10,
                                        yk - dcav / 2), bp / 2 - 10 - x_in, dcav,
                                       fc="0.6", ec="k", lw=0.3, zorder=5))
    # cotas
    faixa = (b - tr) / 2
    f.cota_h(xs - b / 2, xs + b / 2, h_c + 40, y_ref=h_c, fs=4.0)
    f.cota_h(xs - b / 2, xs - tr / 2, 150, txt=_g(round(faixa, 1)), fs=3.6)
    f.cota_h(xs + tr / 2, xs + b / 2, 150, txt=_g(round(faixa, 1)), fs=3.6)
    f.cota_h(xs - tr / 2, xs + tr / 2, 290, txt=f"{tr:g}", fs=3.4)
    f.cota_v(xs + b / 2 + 50, Hp, Hr, txt=f"folga {Hr - Hp:.0f}", esquerda=False, fs=3.6,
             x_ref=xs + tr / 2)
    f.cota_v(xs + b / 2 + 50, 0, Hp, txt=f"chapa {Hp:.0f}", esquerda=False, fs=3.6,
             x_ref=xs + tc / 2)
    f.cota_v(xs - b / 2 - 50, Hr, h_c, txt=f"{h_c - Hr:.0f}", fs=3.6, x_ref=xs - b / 2)
    _rot(f.ax, xs, h_c + 140, rotulo, fs=5.5, bold=True, fundo=False)
    ax.text(xs, -18, "contato", fontsize=3.6, ha="center", va="center", zorder=9,
            bbox=dict(fc="w", ec="none", pad=0.1))


def _marca_corte(ax, x, y0, y1, letra):
    """Linha de corte vertical com setas e letras nas pontas."""
    ax.plot([x, x], [y0, y1], color="k", lw=0.5, ls=(0, (8, 2, 1, 2)), zorder=8)
    for y, va in ((y0, "top"), (y1, "bottom")):
        ax.annotate("", xy=(x + 45, y), xytext=(x, y),
                    arrowprops=dict(arrowstyle="-|>", lw=0.6, color="k"), zorder=8)
        ax.text(x + 60, y, letra, fontsize=6, fontweight="bold", va=va, zorder=9)


def _topo_pilar(ax, xc, y0, lig, hp, tir=None):
    """Topo do pilar: tirante central com luva sob a chapa de topo e duas abas com
    cavilhas de posicionamento, que contornam o furo (concepção revista)."""
    L = lig["a3t_mm"] + (lig["n_horiz"] - 1) * lig["a1_mm"] + 2.0 * lig["d_mm"]
    w = hp - 60.0
    if tir:
        fu, Dl = tir["furo_pilar_mm"], tir["D_luva_mm"]
        gap = fu + 10.0
        for sg in (-1, 1):                            # duas abas, uma de cada lado do furo
            x0 = xc + sg * gap / 2 if sg > 0 else xc - w / 2
            ax.add_patch(Rectangle((x0, y0 - L), (w - gap) / 2, L, fill=False, ls="--",
                                   ec="0.25", lw=LW_FINA + 0.1, zorder=5))
        ax.add_patch(Rectangle((xc - Dl / 2, y0 - 60), Dl, 60, fill=False, ec="k",
                               lw=LW_VISTA, ls=(0, (2, 1)), zorder=6))
        zf = y0 - 600
        ax.plot([xc, xc], [y0, zf], color="0.2", lw=LW_VISTA, ls=(0, (4, 2)), zorder=6)
        for sg in (-1, 1):
            ax.plot([xc + sg * fu / 2] * 2, [y0 - 60, zf], color="0.5", lw=LW_FINA,
                    ls=(0, (2, 2)), zorder=5)
    else:
        ax.add_patch(Rectangle((xc - w / 2, y0 - L), w, L, fill=False, ls="--", ec="0.25",
                               lw=0.5, zorder=5))
    for kk in range(lig["n_horiz"]):
        yk = y0 - lig["a3t_mm"] - kk * lig["a1_mm"]
        for jj in range(lig["n_vert"]):
            xk = xc + (jj - (lig["n_vert"] - 1) / 2.0) * lig["a2_mm"]
            ax.add_patch(Circle((xk, yk), lig["d_mm"] / 2, fill=False, ec="k", lw=0.4,
                                ls=(0, (1.5, 1)), zorder=6))
    return L


def _ys_L1(d: dict) -> list[float]:
    """Alturas das fileiras de pinos da L1/L1c (issue 111: 3 por fileira × 2)."""
    return [d["y_pino_alto_mm"] - k * d["a2_L1_mm"] for k in range(d.get("n_fil_L1", d["n_pinos_L1"]))]


def _nota_L1(d: dict) -> str:
    return (f"Chapa embutida t = {d['t_chapa_L1_mm']:g} mm S275 em rasgo central de "
            f"{d['t_rasgo_mm']:g} mm, soldada à chapa de topo ou à sela; {d['n_pinos_L1']} "
            f"pinos Ø{d['d_pino_L1_mm']:g} por viga ({len(d.get('x_pinos_L1_mm') or [0])} por "
            f"fileira × {d.get('n_fil_L1', d['n_pinos_L1'])} fileiras, todas no terço superior) "
            "em furos ovalizados verticais da chapa "
            f"(tracejado: dentro da viga), curso {_g(d['folga_oblongo_mm'][0])} mm acima e "
            f"{_g(d['folga_oblongo_mm'][1])} mm abaixo do pino, posicionado na montagem pela "
            "umidade medida (DES-05C): os pinos recebem só o arrancamento; a gravidade vai "
            "por contato das duas faixas de madeira ao lado do rasgo (corte).")


def desenho_detalhe_L1(arr: Arranjo, caminho: Path) -> Path:
    """DES-05 — Ligação L1 (pilar lateral): elevação e corte A–A (issue 90)."""
    d = arr.det
    h0 = arr.h0 * 1000
    tg = math.tan(math.radians(arr.alpha_deg))
    b = arr.b_viga * 1000
    Lv, xs = 760.0, 1400.0
    f = Folha.para_conteudo(20, -330, xs + b / 2 + 240,
                            -700 - 20 * (3 + _altura_lista_mm(8)), h0 + Lv * tg + 230,
                            unidade="mm")
    ax = f.ax
    hp, t_top = arr.h_pilar * 1000, d["t_chapa_topo_mm"]
    ax.add_patch(Rectangle((0, -650), hp, 650 - t_top, fc=COR_MLC, ec="k", lw=0.5))
    _quebra(ax, -40, hp + 40, -650, 20)
    ax.add_patch(Rectangle((0, -t_top), hp, t_top, fc=COR_ACO, ec="k", lw=0.5))
    ax.add_patch(Polygon([(0, 0), (Lv, 0), (Lv, h0 + Lv * tg), (0, h0)],
                         closed=True, fc=COR_MLC, ec="k", lw=0.5))
    a_bei = d.get("a_beiral_mm", 0.0)
    if a_bei > 0:                       # beiral: viga continua além do pilar (quebrada)
        xq = -200.0
        ax.add_patch(Polygon([(xq, 0), (0, 0), (0, h0), (xq, h0 + xq * tg)],
                             closed=True, fc=COR_MLC, ec="k", lw=0.5))
        ax.plot([xq, xq], [0, h0 + xq * tg], color="w", lw=1.2, zorder=6)
        _quebra(ax, xq, xq, h0 / 2, 25)
        _rot(ax, xq + 30, h0 * 0.80, f"beiral\n{a_bei:.0f} até\na ponta", fs=4.2,
             ha="left")
    Lp, Hp = d["L1_chapa_L_mm"], d["L1_chapa_H_mm"]
    ax.add_patch(Rectangle((0, 0), Lp, Hp, fill=False, ls="--", ec="0.25", lw=0.5,
                           zorder=5))
    Hr = d.get("fundo_rasgo_mm", Hp)
    xr0 = -E_RASGO_VENTILACAO_MM
    xr1 = xr0 + (d.get("L1_rasgo_L_mm") or (max(Lp, hp) + 2 * E_RASGO_VENTILACAO_MM))
    ax.plot([xr0, xr0, xr1, xr1], [0, Hr, Hr, 0], color="0.25", lw=0.4, ls=":", zorder=5)
    for _x in (xr0, xr1):
        ax.annotate("", xy=(_x, -45), xytext=(_x, 30),
                    arrowprops=dict(arrowstyle="->", lw=0.4, color=COR_DESTAQUE), zorder=8)
    ys = _ys_L1(d)
    xps = d.get("x_pinos_L1_mm") or [d["a3t_L1_mm"]]
    xp = xps[0]
    for x_ in xps:
        for y in ys:
            _pino(ax, x_, y, d["d_pino_L1_mm"], oblongo=d["folga_oblongo_mm"])
    _rot(ax, Lv * 0.75, h0 * 0.35, "viga", fs=5.0)
    _tir5 = (d.get("tirante") or {}).get("base_L3")
    if d.get("topo_pilar"):
        _topo_pilar(ax, hp / 2, -t_top, d["topo_pilar"]["base_L3"], hp, tir=_tir5)
    _rot(ax, hp / 2 + 60, -600, "pilar lateral", fs=4.6, ha="left")
    for (bx, by, mk, ddx, ddy) in ((hp * 0.8, -t_top / 2, "CH-01", 300, 40),
                                   (Lp * 0.75, Hp * 0.55, "CH-02", 160, 60),
                                   (xp, ys[0], "PN-01", -230, 40),
                                   (hp / 2, -380, "TR-01", -260, -40),
                                   (hp / 2, -t_top - 30, "LV-01", -260, 10)):
        _balao(f, bx, by, mk, dx=ddx, dy=ddy)
    ax.text(-200, h0 + Lv * tg + 120, "L1 — APOIO NO PILAR LATERAL", fontsize=6,
            fontweight="bold")
    _marca_corte(ax, xp, -110, h0 + xp * tg + 60, "A")
    # cotas: horizontais acima da viga; verticais à esquerda e à direita
    f.cadeia_h([0] + list(xps), h0 + Lv * tg + 60, y_ref=h0, fs=4.2)
    f.cota_h(0, Lp, h0 + Lv * tg + 20, txt=f"chapa e pilar {Lp:.0f}", y_ref=h0 + Lp * tg, fs=4.0)
    _acr = 60 if a_bei > 0 else 30
    _rot(ax, Lv - 20, -90, f"ℓef do apoio = {hp + _acr:.0f}\n(+30 além de cada face)",
         fs=3.8, ha="right")
    f.cadeia_v(sorted(ys) + [h0], Lp + 70, esquerda=False, fs=3.8, x_ref=xp)
    f.cota_v(-90, 0, h0, x_ref=-10, fs=4.4)
    f.cota_v(-90, -t_top, 0, txt=f"{t_top:g}", fs=4.0)
    f.cota_v(Lp + 190, Hp, Hr, txt=f"{Hr - Hp:.0f}", esquerda=False, fs=3.6, x_ref=Lp)
    f.cota_v(Lp + 190, 0, Hp, txt=f"{Hp:.0f}", esquerda=False, fs=3.8, x_ref=Lp)
    # ---------- corte A–A ----------
    tp = d.get("topo_pilar", {}) or {}
    lig = tp.get("base_L3")
    _corte_viga(f, xs, d, b=b, h_c=h0 + xp * tg, t_apoio=t_top,
                larg_apoio=arr.b_pilar * 1000, rotulo="CORTE A–A",
                pilar=(arr.b_pilar * 1000, float(lig.get("t_chapa_mm", 20.0)) if lig else 20.0,
                       int(lig["n_horiz"]) if lig else 0, float(lig["a1_mm"]) if lig else 100.0,
                       float(lig["a3t_mm"]) if lig else 140.0, float(lig["d_mm"]) if lig else 20.0,
                       (d.get("tirante") or {}).get("base_L3")))
    _solda(f, Lp * 0.45, 0, _solda_txt(d, "L1: chapa embutida"), dx=250, dy=-200)
    if _tir5:
        _solda(f, hp / 2 + _tir5["D_luva_mm"] / 2, -t_top,
               _solda_txt(d, "L3 — extremidade: luva do tirante"), dx=-330, dy=-250)
    _lista_pecas(f, f.x0 + f.p(4), -700 - f.p(3), _pecas_topo(
        d, arr, "base_L3", chapa_topo_L1(arr)))
    f.carimbo(
        "DES-05", "LIGAÇÃO VIGA–PILAR L1 — ELEVAÇÃO E CORTE A–A",
        "Cotas em mm. Gravidade por contato sobre a chapa de topo (CH-01); o arrancamento vai "
        "dos pinos (PN-01, furos ovalizados verticais da chapa embutida CH-02, posicionados "
        "na montagem pela umidade medida, DES-05C) à chapa de topo e desce pelo tirante "
        "interno (TR-01), rosqueado na luva (LV-01) e ancorado no pilarete: o pilar não "
        "trabalha à tração. Duas abas com cavilhas posicionam o topo e levam o cortante. "
        f"Rasgo prolongado {_g(E_RASGO_VENTILACAO_MM)} mm além das faces do pilar, aberto "
        "para baixo (setas). " + REF_GERAIS,
        barra=500.0)
    return f.salvar(caminho)


def desenho_detalhe_L1c(arr: Arranjo, caminho: Path) -> Path:
    """DES-05B — Ligação L1c (sela no pilar central): elevação e corte B–B (issue 90)."""
    d = arr.det
    h0 = arr.h0 * 1000
    tg = math.tan(math.radians(arr.alpha_deg))
    b = arr.b_viga * 1000
    hp = arr.h_pilar * 1000
    la, g, ts = d["l_sela_viga_mm"], d["folga_sela_mm"], d["t_sela_mm"]
    Ls = 2 * la + g
    Lp, Hp = d.get("L1c_chapa_L_mm", d["L1_chapa_L_mm"]), d["L1_chapa_H_mm"]
    xc, xs = 0.0, 1150.0
    _tc = (d.get("topo_pilar") or {}).get("base_L3c")
    # o pilar desenhado vai além da chapa vertical do topo (7 fileiras no central)
    y_pil = -650.0
    _pec = _pecas_topo(d, arr, "base_L3c", ("sela", 2 * d["l_sela_viga_mm"] + d["folga_sela_mm"],
                                            b, ts))
    enr0 = d.get("enrij_sela")
    if enr0:
        _pec.insert(1, ("EN-01", f"enrijecedor {enr0['c_mm']:.0f}×{enr0['c_mm']:.0f}×"
                        f"{_g(enr0['t_e_mm'])}", 2 * enr0["n"], "S275",
                        _g(round(_massa_chapa(enr0["c_mm"], enr0["c_mm"], enr0["t_e_mm"]) / 2, 1))))
        _pec.insert(2, ("CL-01", f"chapa lateral {enr0['h_lat_mm']:.0f}×{b:.0f}×"
                        f"{_g(enr0['t_mm'])}", 2, "S275",
                        _g(round(_massa_chapa(enr0["h_lat_mm"], b, enr0["t_mm"]), 1))))
    f = Folha.para_conteudo(20, -660, xs + b / 2 + 240,
                            y_pil - 50 - 20 * (3 + _altura_lista_mm(len(_pec))),
                            h0 + 560 * tg + 230, unidade="mm")
    ax = f.ax
    ax.add_patch(Rectangle((xc - hp / 2, y_pil), hp, -y_pil - ts, fc=COR_MLC, ec="k", lw=0.5))
    _quebra(ax, xc - hp / 2 - 40, xc + hp / 2 + 40, y_pil, 20)
    ax.add_patch(Rectangle((xc - Ls / 2, -ts), Ls, ts, fc=COR_ACO, ec="k", lw=0.5))
    enr = d.get("enrij_sela")
    if enr:
        c_e, t_l, h_l = enr["c_mm"], enr["t_mm"], enr["h_lat_mm"]
        for sg in (-1, 1):
            x_face = xc + sg * hp / 2
            ax.add_patch(Rectangle((min(x_face, x_face + sg * t_l), -ts - h_l), t_l, h_l,
                                   fc=COR_ACO, ec="k", lw=0.4, zorder=4))
            x0 = x_face + sg * t_l
            ax.add_patch(Polygon([(x0, -ts), (xc + sg * Ls / 2, -ts), (x0, -ts - c_e)],
                                 closed=True, fc=COR_ACO, ec="k", lw=0.4, zorder=4))
        _rot(ax, xc + Ls / 2 + 15, -ts - h_l + 30,
             f"{enr['n']} enrijecedores\n{c_e:.0f}×{c_e:.0f}×{_g(enr['t_e_mm'])} e chapas\n"
             f"laterais {h_l:.0f}×{_g(t_l)}", fs=3.6, ha="left")
    ys = _ys_L1(d)
    for sg in (-1, 1):
        xe, xf = xc + sg * g / 2, xc + sg * (g / 2 + 560)
        ax.add_patch(Polygon([(xe, 0), (xf, 0), (xf, h0 + 560 * tg), (xe, h0)],
                             closed=True, fc=COR_MLC, ec="k", lw=0.5))
        ax.add_patch(Rectangle((min(xe, xe + sg * Lp), 0), Lp, Hp, fill=False,
                               ls="--", ec="0.25", lw=0.5, zorder=5))
        for x_ in (d.get("x_pinos_L1c_mm") or [d["a3t_L1_mm"]]):
            for y in ys:
                _pino(ax, xc + sg * (g / 2 + x_), y, d["d_pino_L1_mm"],
                      oblongo=d["folga_oblongo_mm"])
    if d.get("topo_pilar"):
        _topo_pilar(ax, xc, -ts, d["topo_pilar"]["base_L3c"], hp,
                    tir=(d.get("tirante") or {}).get("base_L3c"))
    _rot(ax, xc + hp / 2 + 20, y_pil + 60, "pilar central", fs=4.6, ha="left")
    ax.text(xc - 640, h0 + 560 * tg + 120, "L1c — SELA NO PILAR CENTRAL", fontsize=6,
            fontweight="bold")
    xpc = xc + g / 2 + d["a3t_L1_mm"]
    _marca_corte(ax, xpc, -ts - 170, h0 + 560 * tg + 40, "B")
    f.cota_h(xc - Ls / 2, xc + Ls / 2, -ts - 300, txt=f"sela {Ls:.0f}", y_ref=-ts, fs=4.2)
    f.cota_h(xc - hp / 2, xc + hp / 2, -ts - 370, txt=f"pilar {hp:.0f}", fs=4.0)
    f.cota_h(xc - g / 2, xc + g / 2, h0 + 30, txt=f"{g:.0f}", fs=3.6)
    f.cota_h(xc - g / 2 - Lp, xc - g / 2, Hp + 40, txt=f"chapa {Lp:.0f}", y_ref=Hp, fs=3.8)
    f.cota_v(xc - Ls / 2 - 40, -ts, 0, txt=f"{ts:g}", fs=3.8)
    f.cadeia_v(sorted(ys) + [h0], xc - 600, fs=3.8, x_ref=xc - 560)
    # ---------- corte B–B (fora do pilar, sobre o consolo da sela) ----------
    consolo = None
    if enr:
        x0 = hp / 2 + enr["t_mm"]
        h_cut = enr["c_mm"] * max(0.0, (Ls / 2 - (g / 2 + d["a3t_L1_mm"]))) / (Ls / 2 - x0)
        consolo = (int(enr["n"]), float(enr["t_e_mm"]), h_cut)
    _corte_viga(f, xs, d, b=b, h_c=h0 + (g / 2 + d["a3t_L1_mm"]) * tg, t_apoio=ts,
                larg_apoio=b, rotulo="CORTE B–B", consolo=consolo)
    _solda(f, xc + g / 2 + Lp * 0.6, 0, _solda_txt(d, "L1c: chapa embutida"), dx=-120,
           dy=120)
    if enr:
        _solda(f, xc - hp / 2 - enr["t_mm"] - 15, -ts - enr["c_mm"] / 3,
               _solda_txt(d, "sela: enrijecedores"), dx=-200, dy=-150)
    _ti = (d.get("tirante") or {}).get("base_L3c")
    if _ti:
        _solda(f, xc + _ti["D_luva_mm"] / 2, -ts,
               _solda_txt(d, "L3c — central: luva do tirante"), dx=300, dy=-300)
    for (bx, by, mk, ddx, ddy) in ((xc - Ls / 2 + 40, -ts / 2, "CH-01", -180, 120),
                                   (xc + g / 2 + Lp * 0.5, Hp * 0.6, "CH-02", 200, 80),
                                   (xc - hp / 2 - 60, -ts - 60, "EN-01", -160, -60),
                                   (xc - hp / 2 - 6, -ts - 200, "CL-01", -200, -30),
                                   (xc, -420, "TR-01", -250, -40)):
        _balao(f, bx, by, mk, dx=ddx, dy=ddy)
    _lista_pecas(f, f.x0 + f.p(4), y_pil - 50 - f.p(3), _pec)
    f.carimbo(
        "DES-05B", "LIGAÇÃO VIGA–PILAR L1c — ELEVAÇÃO E CORTE B–B",
        "Cotas em mm. Gravidade por contato sobre a sela (CH-01), com enrijecedores (EN-01) "
        "sob os balanços e chapas laterais (CL-01) nas faces do pilar. Arrancamento: pinos "
        "(PN-01) na chapa embutida (CH-02), sela e tirante interno (TR-01), rosqueado na luva "
        "(LV-01) sob a sela e ancorado no pilarete; abas com cavilhas só posicionam. O corte "
        "B–B passa pela fileira de pinos, sobre o consolo da sela; o rasgo de cada viga "
        f"abre-se para o vão entre as vigas, sob a T9 e a calha (DES-10), com "
        f"{d.get('L1c_rasgo_L_mm', 0):.0f} mm da extremidade da viga, 30 além da chapa. "
        + REF_GERAIS,
        barra=500.0)
    return f.salvar(caminho)


def desenho_chapa_L1(arr: Arranjo, caminho: Path) -> Path:
    """DES-05C — Chapas embutidas L1/L1c em verdadeira grandeza e furo ovalizado (issue 90)."""
    d = arr.det
    Hp = d["L1_chapa_H_mm"]
    dp, d0 = d["d_pino_L1_mm"], d["d0_L1_mm"]
    cima, baixo = d["folga_oblongo_mm"]
    ys = _ys_L1(d)
    f = Folha.para_conteudo(10, -120, 1440, -160, Hp + 120, unidade="mm")
    ax = f.ax
    for x0, L, nome, xs_ in ((0.0, d["L1_chapa_L_mm"], "L1", d.get("x_pinos_L1_mm")),
                             (520.0, d.get("L1c_chapa_L_mm", d["L1_chapa_L_mm"]), "L1c",
                              d.get("x_pinos_L1c_mm"))):
        ax.add_patch(Rectangle((x0, 0), L, Hp, fc=COR_ACO, ec="k", lw=0.6))
        xs_ = [x0 + x for x in (xs_ or [d["a3t_L1_mm"]])]
        xp = xs_[0]
        for xp_, y in [(a_, b_) for a_ in xs_ for b_ in ys]:
            xp = xp_
            ax.add_patch(FancyBboxPatch((xp - d0 / 2, y - d0 / 2 - baixo), d0, d0 + cima + baixo,
                                        boxstyle=f"round,pad=0,rounding_size={d0 / 2}",
                                        fc="w", ec="k", lw=0.4, zorder=5))
            ax.plot([xp - d0 / 2 - 6, xp + d0 / 2 + 6], [y, y], color="0.4", lw=0.25,
                    ls=(0, (6, 2, 1, 2)), zorder=6)
        ax.plot([x0 - 20, x0 + L + 20], [-4, -4], color=COR_DESTAQUE, lw=1.2, zorder=6)
        ax.text(x0 + L / 2, Hp + 70, f"CHAPA EMBUTIDA {nome}", fontsize=5.5,
                fontweight="bold", ha="center")
        f.cota_h(x0, x0 + L, -60, txt=f"{L:.0f}", fs=4.0)
        f.cadeia_h([x0] + xs_, Hp + 25, y_ref=Hp, fs=3.8)
        f.cota_v(x0 - 40, 0, Hp, txt=f"{Hp:.0f}", fs=4.0, x_ref=x0)
        f.cadeia_v([0] + sorted(ys) + [Hp], x0 + L + 40, esquerda=False, fs=3.4,
                   x_ref=x0 + L)
        _rot(ax, x0 + L / 2, -120, f"t = {d['t_chapa_L1_mm']:g} mm, S275; solda na borda "
             "inferior", fs=3.6)
    # detalhe do furo ovalizado ampliado 4× (escala 1:2,5)
    k, xd, yd = 4.0, 1150.0, 640.0
    W, H = d0 * k, (d0 + cima + baixo) * k
    ax.add_patch(FancyBboxPatch((xd - W / 2, yd - H / 2), W, H,
                                boxstyle=f"round,pad=0,rounding_size={W / 2}",
                                fc="w", ec="k", lw=0.6, zorder=5))
    yc = yd - H / 2 + (d0 / 2 + baixo) * k                    # pino na posição de projeto
    ax.add_patch(Circle((xd, yc), dp / 2 * k, fc="0.45", ec="k", lw=0.5, zorder=6))
    ax.plot([xd - W, xd + W], [yc, yc], color="0.4", lw=0.3, ls=(0, (6, 2, 1, 2)), zorder=7)
    ax.text(xd, yd + H / 2 + 90, "DETALHE DO FURO — 1:2,5", fontsize=5.5,
            fontweight="bold", ha="center")
    f.cota_h(xd - W / 2, xd + W / 2, yd - H / 2 - 30, txt=f"d0 = {d0:g}", acima=False, fs=3.8)
    xv = xd + W / 2 + 40
    f.cota_v(xv, yd - H / 2, yd + H / 2, txt=f"{d0 + cima + baixo:g}", esquerda=False, fs=3.8)
    f.cota_v(xd - W / 2 - 40, yc + dp / 2 * k, yd + H / 2, txt=f"{cima + (d0 - dp) / 2:g}",
             fs=3.6)
    f.cota_v(xd - W / 2 - 40, yd - H / 2, yc - dp / 2 * k, txt=f"{baixo + (d0 - dp) / 2:g}",
             fs=3.6)
    _rot(ax, xd, yd - H / 2 - 110, f"pino Ø{dp:g} na posição de projeto:\ncurso {cima:g} acima "
         f"(inchamento)\ne {baixo:g} abaixo (retração e fluência)", fs=3.6)
    # tabela de montagem: folga acima de cada pino pela umidade medida
    tab = d.get("folga_acima_montagem_mm") or {}
    if tab:
        x0t, y0t, lh = 960.0, 30.0, 28.0
        us = list(tab)
        ax.text(x0t, y0t + lh * (len(ys) + 1.6), "MONTAGEM — folga acima do pino (mm)",
                fontsize=4.2, fontweight="bold")
        cab = ["pino (y)"] + [f"u = {u}" for u in us]
        for j, c in enumerate(cab):
            ax.text(x0t + j * 110, y0t + lh * len(ys), c, fontsize=3.8, fontweight="bold")
        for i, y in enumerate(sorted(ys, reverse=True)):
            yy = y0t + lh * (len(ys) - 1 - i)
            ax.text(x0t, yy, f"{i + 1} ({y:.0f})", fontsize=3.8)
            for j, u in enumerate(us):
                ax.text(x0t + (j + 1) * 110, yy, _g(tab[u][i]), fontsize=3.8)
    f.carimbo(
        "DES-05C", "CHAPAS EMBUTIDAS L1 E L1c — VERDADEIRA GRANDEZA",
        f"Cotas em mm; detalhe ampliado 4×. Furos ovalizados verticais d0 = {d0:g} mm "
        f"(pino Ø{dp:g} + folga EN 1090-2), comprimento {d0 + cima + baixo:g} mm; alturas "
        "medidas da borda inferior, soldada à chapa de topo (L1) ou à sela (L1c), em azul. "
        "Na montagem, a viga é apoiada por contato e cada pino é colocado com a folga "
        "acima da tabela, interpolada pela umidade medida da viga; o restante do curso "
        "fica abaixo do pino." + " " + REF_GERAIS,
        barra=200.0, divisoes=4)
    return f.salvar(caminho)


def _plano_e_impacto(f, xc, yc, B, L, d, rotulo_embaixo=False):
    """Plano da chapa vertical (= plano do pórtico) e choque de veículo na planta."""
    ax = f.ax
    ax.annotate("", xy=(xc, yc + L / 2 + 95), xytext=(xc, yc - L / 2 - 30),
                arrowprops=dict(arrowstyle="->", lw=0.4, color="0.35", ls=(0, (4, 2))),
                zorder=2)
    _rot(ax, xc + 18, yc + (-L / 2 - 30 if rotulo_embaixo else L / 2 + 95),
         "plano do pórtico = plano da chapa vertical", fs=3.4, ha="left", va="top")
    imp = d.get("impacto") or {}
    if imp:
        yi = yc - L / 4
        ax.annotate("", xy=(xc + B / 2 + 5, yi), xytext=(xc + B / 2 + 150, yi),
                    arrowprops=dict(arrowstyle="-|>", lw=0.7, color=COR_CV), zorder=7)
        _rot(ax, xc + B / 2 + 20, yi - 30,
             f"choque F = {imp['F_gov_kN']:.0f} kN a {_g(round(imp['h_imp_m'], 2))} m do\n"
             "piso, em qualquer direção (tubo circular)", fs=3.4, ha="left", va="top",
             cor=COR_CV)


def _chapa_base_planta(ax, xc, yc, base, b, h, d_chu, tir=None):
    B, L = base["B_mm"], base["L_mm"]
    ax.add_patch(Rectangle((xc - B / 2, yc - L / 2), B, L, fc=COR_ACO, ec="k",
                           lw=0.5, zorder=2))
    ax.add_patch(Rectangle((xc - b / 2, yc - h / 2), b, h, fill=False, ls="--",
                           ec="0.2", lw=0.5, zorder=3))
    if tir:                                   # duas abas, uma de cada lado do tirante
        gap = tir["furo_pilar_mm"] + 10.0
        for sg in (-1, 1):
            y0_ = yc + sg * gap / 2 if sg > 0 else yc - h / 2 + 30
            ax.add_patch(Rectangle((xc - base["t_alma_mm"] / 2, y0_), base["t_alma_mm"],
                                   (h - 60 - gap) / 2, fc="0.35", ec="k", lw=0.3, zorder=3))
        ax.add_patch(Circle((xc, yc), tir["d_mm"] / 2, fc="0.55", ec="k", lw=0.4, zorder=5))
    else:
        ax.add_patch(Rectangle((xc - base["t_alma_mm"] / 2, yc - h / 2 + 30),
                               base["t_alma_mm"], h - 60, fc="0.35", ec="k", lw=0.3,
                               zorder=3))
    pil = base.get("pil")
    if pil:                                   # tubo do pilarete e chapa de topo
        ax.add_patch(Circle((xc, yc), pil["D_mm"] / 2, fill=False, ec="k", lw=0.6,
                            zorder=4))
        Bt, Lt, _ = pil["chapa_topo_mm"]
        ax.add_patch(Rectangle((xc - Bt / 2, yc - Lt / 2), Bt, Lt, fill=False, ec="k",
                               lw=0.4, ls=(0, (2, 1.5)), zorder=4))
    for (x, y) in base["chumbadores_mm"]:
        ax.add_patch(Circle((xc + x, yc + y), 0.925 * d_chu, fc="w", ec="k",
                            lw=0.35, zorder=4))
        ax.add_patch(Circle((xc + x, yc + y), d_chu / 2, fc="k", zorder=5))


def _corte_base(f, xc, yc, base, b_pil, hef, d_chu, larg_conc, h_conc,
                chaveta=None, d=None, tir=None):
    """
    Corte vertical da base no plano ⊥ ao pórtico (x = largura b). Bloco com topo no
    piso acabado (±0,00), graute de nivelamento, chapa de base, pilarete e pé do
    pilar; cotas de nível e soldas (issue 91).
    """
    ax = f.ax
    B, t, pe = base["B_mm"], base["t_mm"], base["pe"]
    G = GRAUTE_MM
    ax.add_patch(Rectangle((xc - larg_conc / 2, yc - h_conc), larg_conc, h_conc,
                           fc=COR_CONC, ec="k", lw=0.4, zorder=1))
    for s in (-1, 1):
        _quebra(ax, xc + s * larg_conc / 2, xc + s * larg_conc / 2, yc - h_conc, 0)
    ax.add_patch(Rectangle((xc - B / 2 - 25, yc), B + 50, G, fc="#ececec", ec="k", lw=0.3,
                           hatch="....", zorder=2))
    yb = yc + G                                   # face inferior da chapa de base
    ax.add_patch(Rectangle((xc - B / 2, yb), B, t, fc=COR_ACO, ec="k", lw=0.5, zorder=3))
    L_pe = pe["a3t_mm"] + (pe["n_horiz"] - 1) * pe["a1_mm"] + 2.5 * pe["d_mm"]
    hp = max(700.0, L_pe + 200)
    pil = base.get("pil")
    y0 = yb + t                                   # pé da madeira
    if pil:                                       # pilarete: tubo + chapa de topo
        H_pl = pil["h_m"] * 1000
        Bt, _, tt = pil["chapa_topo_mm"]
        D = pil["D_mm"]
        h_tb = yc + H_pl - tt - yb - t
        if tir:                                   # tubo em corte: paredes e interior oco
            tw = pil["t_mm"]
            for sg in (-1, 1):
                _hachura(ax, xc + sg * (D / 2 - tw / 2) - tw / 2, yb + t, tw, h_tb, zorder=3)
        else:
            ax.add_patch(Rectangle((xc - D / 2, yb + t), D, h_tb, fc=COR_ACO,
                                   ec="k", lw=0.5, zorder=3))
        ax.add_patch(Rectangle((xc - Bt / 2, yc + H_pl - tt), Bt, tt, fc=COR_ACO,
                               ec="k", lw=LW_CORTE, zorder=3))
        y0 = yc + H_pl
        if tir:                                   # tirante, porca e arruela-chapa no tubo
            dt, ar = tir["d_mm"], tir["arruela_chapa_mm"]
            _hachura(ax, xc - dt / 2, y0 - tt - 70, dt, 70 + tt + 600, fc="0.55", zorder=6,
                     hatch="")
            _hachura(ax, xc - ar / 2, y0 - tt - 15, ar, 15, zorder=7)
            ax.add_patch(Rectangle((xc - 0.85 * dt, y0 - tt - 15 - 0.8 * dt), 1.7 * dt,
                                   0.8 * dt, fc="0.25", ec="k", lw=0.3, zorder=7))
            _rot(ax, xc + D / 2 + 30, y0 - tt - 45, "janela 60×110 (aperto da porca)",
                 fs=3.2, ha="left")
        _rot(ax, xc + D / 2 + 40, (yb + t + y0 - tt) / 2 - 40,
             f"tubo Ø{_g(D)}×{_g(pil['t_mm'])}", fs=4.0, ha="left")
        if d is not None:
            _solda(f, xc - D / 2, yb + t, f"a{_g(pil['a_solda_base_mm'])} (contorno)",
                   dx=-110, dy=55, fs=3.4)
            _solda(f, xc - D / 2, y0 - tt, f"a{_g(pil['a_solda_topo_mm'])} (contorno)",
                   dx=-110, dy=-60, fs=3.4)
    xn = xc + larg_conc / 2 + 40
    _nivel(f, xn, yc, "±0,00 piso acabado =\ntopo do bloco", fs=3.6)
    _rot(ax, xc - B / 2 - 35, yc + G / 2, f"graute {G:.0f}", fs=3.6, ha="right")
    if pil:
        _nivel(f, xn, y0, f"+{pil['h_m']:.2f} topo do\npilarete".replace(".", ","), fs=3.6)
    ax.add_patch(Rectangle((xc - b_pil / 2, y0), b_pil, hp, fc=COR_MLC, ec="k",
                           lw=LW_CORTE, zorder=3))
    _quebra(ax, xc - b_pil / 2 - 30, xc + b_pil / 2 + 30, y0 + hp, 20)
    if tir:                                       # furo central; abas atrás do corte
        fu = tir["furo_pilar_mm"]
        ax.add_patch(Rectangle((xc - fu / 2, y0), fu, hp, fc="w", ec="k", lw=LW_FINA, zorder=4))
        ax.add_patch(Rectangle((xc - tir["d_mm"] / 2, y0), tir["d_mm"], hp - 30, fc="0.55",
                               ec="k", lw=0.3, zorder=5))
        x_in = fu / 2 + 6
        for kk in range(pe["n_horiz"]):
            yk = y0 + pe["a3t_mm"] + kk * pe["a1_mm"]
            for sg in (-1, 1):
                ax.plot([xc + sg * x_in, xc + sg * b_pil / 2], [yk, yk], color="k", lw=1.0,
                        zorder=6)
    else:
        ax.add_patch(Rectangle((xc - base["t_alma_mm"] / 2, y0), base["t_alma_mm"],
                               L_pe, fc="0.35", ec="k", lw=0.3, zorder=4))
        for kk in range(pe["n_horiz"]):
            ax.plot([xc - b_pil / 2, xc + b_pil / 2],
                    [y0 + pe["a3t_mm"] + kk * pe["a1_mm"]] * 2, color="k", lw=1.0,
                    zorder=5)
    if d is not None:
        _solda(f, xc + base["t_alma_mm"] / 2, y0, _solda_txt(d, "chapa vertical do pé"),
               dx=b_pil / 2 + 60, dy=70, fs=3.4)
    hp = hp + (y0 - yc - t)
    xs = sorted({x for x, _ in base["chumbadores_mm"]})
    for x in xs:
        ax.plot([xc + x, xc + x], [yc - hef, yb + t + 40], color="k", lw=1.4, zorder=4)
        ax.add_patch(Rectangle((xc + x - 30, yc - hef - 12), 60, 12, fc="k", zorder=4))
        ax.add_patch(Rectangle((xc + x - 22, yb + t), 44, 20, fc="0.2", zorder=5))
        ax.add_patch(Rectangle((xc + x - 22, yb - 18), 44, 16, fc="0.2", zorder=5))
    if chaveta:
        ax.add_patch(Rectangle((xc - 15, yb - chaveta), 30, chaveta, fc=COR_ACO,
                               ec="k", lw=0.4, zorder=4))
    return xs, hp, L_pe


def desenho_bases_correntes(arr: Arranjo, caminho: Path) -> Path:
    """DES-06 — Bases L3, L3c e L3f (2×2, sem chaveta): planta, corte e quadro."""
    d = arr.det
    b3 = d["bases"]["L3"]
    B, L = b3["B_mm"], b3["L_mm"]
    hef = d["h_ef_mm"]
    xc2, yc2 = 1150.0, -650.0
    tirs = d.get("tirante") or {}
    f = Folha.para_conteudo(15, -440, xc2 + 760, -1250 - 15 * 20, 520, unidade="mm")
    ax = f.ax
    _chapa_base_planta(ax, 0, 0, b3, arr.b_pilar * 1000, arr.h_pilar * 1000,
                       d["d_chu_mm"], tir=tirs.get("base_L3"))
    ax.text(-B / 2 - 150, L / 2 + 110, "PLANTA DA CHAPA", fontsize=6, fontweight="bold")
    xs = sorted({x for x, _ in b3["chumbadores_mm"]})
    ys = sorted({y for _, y in b3["chumbadores_mm"]})
    f.cadeia_h([-B / 2] + xs + [B / 2], -L / 2 - 70, y_ref=-L / 2, fs=4.4)
    f.cadeia_v([-L / 2] + ys + [L / 2], -B / 2 - 70, x_ref=-B / 2, fs=4.4)
    f.cota_h(-arr.b_pilar * 500, arr.b_pilar * 500, L / 2 + 40,
             txt=f"pilar {arr.b_pilar * 1000:.0f}×{arr.h_pilar * 1000:.0f}", fs=4.2)
    _rot(ax, B / 2 + 20, L / 4, "x ⊥ pórtico →", fs=4.0, ha="left")
    _plano_e_impacto(f, 0, 0, B, L, d)
    # chaveta cruciforme sob a chapa (issue 74), pontilhada na planta
    cL = d["chaveta_L_mm"]
    for (x1, y1, x2, y2) in ((-cL / 2, 0, cL / 2, 0), (0, -cL / 2, 0, cL / 2)):
        ax.plot([x1, x2], [y1, y2], color="k", lw=1.6, ls=":", zorder=6)
    _rot(ax, 0, -L / 2 + 25, f"chaveta em cruz {cL:.0f}×{d['chaveta_H_mm']:.0f} (pontilhado)",
         fs=3.8)
    xs_c, hp, L_pe = _corte_base(f, xc2, yc2, b3, arr.b_pilar * 1000, hef,
                                 d["d_chu_mm"], B + 400, hef + 160,
                                 chaveta=d["chaveta_H_mm"], d=d, tir=tirs.get("base_L3"))
    _solda(f, xc2 + 15, yc2 + GRAUTE_MM - d["chaveta_H_mm"] / 2,
           _solda_txt(d, "chaveta em cruz"), dx=-B / 2 - 40, dy=-150, fs=3.4)
    ax.text(xc2 - B / 2 - 200, yc2 + b3["t_mm"] + hp + 60, "CORTE (L3)", fontsize=6,
            fontweight="bold")
    f.cota_v(xc2 + B / 2 + 110, yc2 - hef, yc2, x_ref=xc2 + max(xs_c), esquerda=False,
             txt=f"hef = {hef:.0f}", fs=4.4)
    pe = b3["pe"]
    y_pe = yc2 + (b3["pil"]["h_m"] * 1000 if b3.get("pil") else b3["t_mm"])
    ys_pe = [y_pe] + [y_pe + pe["a3t_mm"] + kk * pe["a1_mm"] for kk in range(pe["n_horiz"])]
    f.cadeia_v(ys_pe, xc2 - B / 2 - 90, x_ref=xc2 - arr.b_pilar * 500, fs=4.2)
    # quadro das variantes (base, pilarete, pé e tirante)
    linhas = []
    for kb, kt, onde in (("L3", "base_L3", "A e C, exceto montantes"),
                         ("L3c", "base_L3c", "B, exceto montantes"),
                         ("L3f", "base_L3f", "PF1, PF2")):
        bb, ti = d["bases"][kb], tirs.get(kt) or {}
        pl = bb["pil"]
        ct = pl["chapa_topo_mm"]
        linhas.append((kb, onde, f"{bb['B_mm']:.0f}×{bb['L_mm']:.0f}×{_g(bb['t_mm'])}",
                       f"Ø{_g(pl['D_mm'])}×{_g(pl['t_mm'])}; topo {ct[0]:.0f}×{ct[1]:.0f}×{_g(ct[2])}",
                       f"a{_g(pl['a_solda_base_mm'])} / a{_g(pl['a_solda_topo_mm'])}",
                       f"{bb['pe']['n_pinos']} × Ø{bb['pe']['d_mm']:.0f}",
                       f"M{ti.get('d_mm', 0):.0f} · furo Ø{ti.get('furo_pilar_mm', 0):.0f}"))
    _tabela(f, -440, -1250 - 15 * 3, "QUADRO DAS BASES CORRENTES",
            ("Base", "Onde", "Chapa de base", "Pilarete (tubo; chapa de topo)", "Solda tubo",
             "Pé", "Tirante interno"), linhas, (0, 10, 42, 66, 104, 122, 137))
    f.carimbo(
        "DES-06", "BASES DOS PILARES L3, L3c E L3f",
        f"Cotas em mm. Quatro chumbadores M{d['d_chu_mm']:g} 8.8 moldados com cabeça Ø60, "
        f"hef = {hef:.0f} mm, concreto {d['classe_concreto']}, borda ≥ {d['c_borda_mm']:.0f} "
        "mm; furos da chapa Ø36 com arruela-chapa soldada na montagem; graute com porca de "
        "nivelamento; chaveta em cruz leva o cortante ao concreto. O pilarete (tubo S355, "
        "chapa de topo menor que o pilar) eleva a madeira a "
        f"{_g(b3['pil']['h_m'])} m do piso e recebe o tirante interno, cuja porca e "
        "arruela-chapa se apertam por dentro do tubo, pela janela de acesso. O pé do pilar "
        "só leva o cortante do choque: duas abas soldadas à chapa de topo, uma de cada lado "
        "do tirante, com cavilhas Ø20. " + REF_GERAIS,
        barra=500.0)
    return f.salvar(caminho)


def desenho_base_ancorada(arr: Arranjo, caminho: Path) -> Path:
    """DES-07 — Base L3a dos montantes bipartidos (issue 104): chapa 3×2, dois pilaretes."""
    d = arr.det
    ba = d["bases"]["L3a"]
    bp = arr.bip
    dm = d["mont"]
    hef, c_b = dm["h_ef_mm"], dm["c_borda_mm"]
    xsa = sorted({x for x, _ in ba["chumbadores_mm"]})
    ysa = sorted({y for _, y in ba["chumbadores_mm"]})
    Bb = (xsa[-1] - xsa[0]) + 2 * c_b
    Lb = (ysa[-1] - ysa[0]) + 2 * c_b
    B, L, t = ba["B_mm"], ba["L_mm"], ba["t_mm"]
    yl, bl, hl = bp["y_l_mm"] * 1000, bp["b_l_mm"] * 1000, bp["h_l_mm"] * 1000
    pil, pe = ba["pil"], ba["pe"]
    D, tt_ = pil["D_mm"], pil["t_mm"]
    Bt, Lt, tt = pil["chapa_topo_mm"]
    H_pl = pil["h_m"] * 1000
    G = GRAUTE_MM
    L_pe = pe["a3t_mm"] + (pe["n_horiz"] - 1) * pe["a1_mm"] + 2.5 * pe["d_mm"]
    xc2 = Bb / 2 + 1000
    y_top = H_pl + L_pe + 620
    n_ch = len(ba["chumbadores_mm"])
    L_ab = pe["a3t_mm"] + (pe["n_horiz"] - 1) * pe["a1_mm"] + 2 * pe["d_mm"]
    _pec = [
        ("CB-01", f"chapa de base {B:.0f}×{L:.0f}×{_g(t)}", 1, "S275",
         _g(round(_massa_chapa(B, L, t), 1))),
        ("TB-01", f"tubo Ø{_g(D)}×{_g(tt_)}×{H_pl - G - t - tt:.0f} + respiros", 2, "S355",
         _g(round(math.pi * (D - tt_) * tt_ * (H_pl - G - t - tt) * 7.85e-6, 1))),
        ("CT-01", f"chapa de topo {Bt:.0f}×{Lt:.0f}×{_g(tt)}", 2, "S275",
         _g(round(_massa_chapa(Bt, Lt, tt), 1))),
        ("AP-01", f"chapa do pé {hl - 60:.0f}×{L_ab:.0f}×{_g(ba['t_alma_mm'])}", 2, "S275",
         _g(round(_massa_chapa(hl - 60, L_ab, ba["t_alma_mm"]), 1))),
        ("CV-01", f"cavilha Ø{pe['d_mm']:.0f}×{bl - 30:.0f}", 2 * pe["n_pinos"], "S275",
         _g(round(_massa_barra(pe["d_mm"], bl - 30), 1))),
        ("CH-01", f"chumbador M{d['d_chu_mm']:g} com cabeça Ø60, hef {hef:.0f}", n_ch, "8.8",
         "—"),
        ("AR-01", "arruela-chapa 80×80×10, soldada na montagem", n_ch, "S275",
         _g(round(_massa_chapa(80, 80, 10), 1))),
        ("CR-01", f"chaveta em cruz {dm['chaveta_L_mm']:.0f}×{d['chaveta_H_mm']:.0f}", 1,
         "S275", "—"),
    ]
    f = Folha.para_conteudo(30, -Bb / 2 - 280, xc2 + 1150,
                            -Lb / 2 - 260 - 30 * (3 + _altura_lista_mm(len(_pec))),
                            max(Lb / 2 + 160, y_top), unidade="mm")
    ax = f.ax
    # ---------- planta ----------
    ax.add_patch(Rectangle((-Bb / 2, -Lb / 2), Bb, Lb, fc=COR_CONC, ec="k", lw=0.5,
                           ls=(0, (6, 3)), zorder=1))
    ax.add_patch(Rectangle((-B / 2, -L / 2), B, L, fc=COR_ACO, ec="k", lw=0.5, zorder=2))
    for sg in (-1, 1):
        xl = sg * yl
        ax.add_patch(Rectangle((xl - bl / 2, -hl / 2), bl, hl, fill=False, ls="--", ec="0.2",
                               lw=0.5, zorder=3))
        ax.add_patch(Circle((xl, 0), D / 2, fill=False, ec="k", lw=0.6, zorder=4))
        ax.add_patch(Rectangle((xl - ba["t_alma_mm"] / 2, -hl / 2 + 30), ba["t_alma_mm"],
                               hl - 60, fc="0.35", ec="k", lw=0.3, zorder=4))
    for (x, y) in ba["chumbadores_mm"]:
        ax.add_patch(Circle((x, y), 0.925 * d["d_chu_mm"], fc="w", ec="k", lw=0.35, zorder=4))
        ax.add_patch(Circle((x, y), d["d_chu_mm"] / 2, fc="k", zorder=5))
    cL = dm["chaveta_L_mm"]
    for (x1, y1, x2, y2) in ((-cL / 2, 0, cL / 2, 0), (0, -cL / 2, 0, cL / 2)):
        ax.plot([x1, x2], [y1, y2], color="k", lw=1.4, ls=":", zorder=6)
    ax.text(-Bb / 2, Lb / 2 + 70, "PLANTA (BLOCO EM CINZA)", fontsize=6, fontweight="bold")
    _plano_e_impacto(f, 0, 0, B, L, d, rotulo_embaixo=True)
    f.cadeia_h([-Bb / 2] + xsa + [Bb / 2], -Lb / 2 - 80, y_ref=-Lb / 2, fs=4.0)
    f.cadeia_v([-Lb / 2] + ysa + [Lb / 2], -Bb / 2 - 80, x_ref=-Bb / 2, fs=4.0)
    f.cota_h(-B / 2, B / 2, L / 2 + 60, txt=f"chapa {B:.0f}×{L:.0f}×{_g(t)}", fs=4.0)
    f.cota_h(-yl, yl, -110, txt=f"{2 * yl:.0f} entre eixos das lâminas", fs=3.4)
    _rot(ax, 0, -L / 2 - 150, "lâminas e tubos tracejados; chaveta em cruz pontilhada", fs=3.6)
    # ---------- corte ⊥ ao pórtico ----------
    xc, yc = xc2, 0.0
    lc, hc = 1500.0, dm["h_bloco_mm"]
    ax.add_patch(Rectangle((xc - lc / 2, yc - hc), lc, hc, fc=COR_CONC, ec="k", lw=0.4,
                           zorder=1))
    ax.add_patch(Rectangle((xc - B / 2 - 25, yc), B + 50, G, fc="#ececec", ec="k", lw=0.3,
                           hatch="....", zorder=2))
    yb = yc + G
    ax.add_patch(Rectangle((xc - B / 2, yb), B, t, fc=COR_ACO, ec="k", lw=0.5, zorder=3))
    for sg in (-1, 1):
        xl = xc + sg * yl
        ax.add_patch(Rectangle((xl - D / 2, yb + t), D, yc + H_pl - tt - yb - t, fc=COR_ACO,
                               ec="k", lw=0.5, zorder=3))
        ax.add_patch(Rectangle((xl - Bt / 2, yc + H_pl - tt), Bt, tt, fc=COR_ACO, ec="k",
                               lw=0.5, zorder=3))
        ax.add_patch(Rectangle((xl - bl / 2, yc + H_pl), bl, L_pe + 350, fc=COR_MLC, ec="k",
                               lw=0.5, zorder=3))
        _quebra(ax, xl - bl / 2 - 20, xl + bl / 2 + 20, yc + H_pl + L_pe + 350, 15)
        ax.add_patch(Rectangle((xl - ba["t_alma_mm"] / 2, yc + H_pl), ba["t_alma_mm"], L_pe,
                               fc="0.35", ec="k", lw=0.3, zorder=4))
        for kk in range(pe["n_horiz"]):
            ax.plot([xl - bl / 2, xl + bl / 2], [yc + H_pl + pe["a3t_mm"] + kk * pe["a1_mm"]] * 2,
                    color="k", lw=1.0, zorder=5)
    # espaçador do pé (C.3.1): reparte o choque entre as lâminas
    ax.add_patch(Rectangle((xc - yl + bl / 2, yc + H_pl + 80), 2 * yl - bl, 450, fc="#e9d6a6",
                           ec="k", lw=0.4, hatch="//", zorder=2))
    _rot(ax, xc, yc + H_pl + 305, "espaçador", fs=3.4)
    for x in sorted({x for x, _ in ba["chumbadores_mm"]}):
        ax.plot([xc + x, xc + x], [yc - hef, yb + t + 40], color="k", lw=1.4, zorder=4)
        ax.add_patch(Rectangle((xc + x - 30, yc - hef - 12), 60, 12, fc="k", zorder=4))
        ax.add_patch(Rectangle((xc + x - 22, yb + t), 44, 20, fc="0.2", zorder=5))
        ax.add_patch(Rectangle((xc + x - 22, yb - 18), 44, 16, fc="0.2", zorder=5))
    ax.add_patch(Rectangle((xc - 15, yb - d["chaveta_H_mm"]), 30, d["chaveta_H_mm"],
                           fc=COR_ACO, ec="k", lw=0.4, zorder=4))
    xn = xc + lc / 2 + 40
    _nivel(f, xn, yc, "±0,00 piso acabado =\ntopo do bloco", fs=3.6)
    _nivel(f, xn, yc + H_pl, f"+{H_pl / 1000:.2f} topo dos\npilaretes".replace(".", ","), fs=3.6)
    _rot(ax, xc - B / 2 - 35, yc + G / 2, f"graute {G:.0f}", fs=3.4, ha="right")
    xr = xc + yl
    _solda(f, xr - D / 2, yb + t, f"a{_g(pil['a_solda_base_mm'])} (contorno)", dx=-150, dy=110,
           fs=3.4)
    _solda(f, xr + D / 2, yc + H_pl - tt, f"a{_g(pil['a_solda_topo_mm'])} (contorno)", dx=120,
           dy=-80, fs=3.4)
    _solda(f, xc + 15, yb - d["chaveta_H_mm"] / 2, _solda_txt(d, "chaveta da base de canto"),
           dx=-420, dy=-160, fs=3.4)
    f.cota_v(xc + lc / 2 + 220, yc - hef, yc, txt=f"hef = {hef:.0f}", esquerda=False, fs=4.0)
    f.cota_v(xc + lc / 2 + 220, yc - hc, yc - hef, esquerda=False, fs=4.0)
    f.cota_h(xc - yl - bl / 2, xc - yl + bl / 2, yc + H_pl + L_pe + 420,
             txt=f"lâmina {bl:.0f}", fs=3.6)
    f.cota_h(xc - yl + bl / 2, xc + yl - bl / 2, yc + H_pl + L_pe + 420,
             txt=f"{2 * yl - bl:.0f}", fs=3.6)
    ax.text(xc - lc / 2, y_top - 40, "CORTE ⊥ AO PÓRTICO", fontsize=6, fontweight="bold")
    _lista_pecas(f, f.x0 + f.p(4), -Lb / 2 - 260 - f.p(3), _pec,
                 titulo="LISTA DE PEÇAS (por base)")
    f.carimbo(
        "DES-07", "BASE ANCORADA L3a — PILARES MONTANTES BIPARTIDOS",
        f"Cotas em mm. Pilares de canto, laterais e centrais montantes das baías "
        f"contraventadas: duas lâminas de MLC {bl:.0f}×{hl:.0f}, cada uma sobre o seu pilarete "
        f"(tubo Ø{_g(D)}×{_g(tt_)} S355, chapa de topo {Bt:.0f}×{Lt:.0f}×{_g(tt)}), e "
        f"espaçador no pé, que reparte o choque entre as lâminas. Seis chumbadores "
        f"M{d['d_chu_mm']:g} classe 8.8 moldados com cabeça Ø60 em grelha 3 × 2 girada, "
        f"hef = {hef:.0f} mm; chaveta em cruz {cL:.0f}×{d['chaveta_H_mm']:.0f} sob a chapa; bloco "
        f"{d['classe_concreto']} de pelo menos {Bb:.0f} × {Lb:.0f} × {dm['h_bloco_mm']:.0f} mm "
        f"(borda ≥ {c_b:.0f}). Pé "
        f"de cada lâmina: {pe['n_pinos']} cavilhas Ø{pe['d_mm']:.0f} ({pe['n_vert']}×"
        f"{pe['n_horiz']}) em chapa vertical embutida. Os olhais das diagonais soldam-se à "
        "chapa de base, entre os pilaretes.  " + REF_GERAIS,
        barra=500.0)
    return f.salvar(caminho)


def desenho_detalhe_L1f(arr: Arranjo, caminho: Path) -> Path:
    """DES-08 — Topo do pilar de frontão (L1f): furo oblongo, não apoia a viga."""
    d = arr.det
    tp = d["L1f"]
    folga, hp = tp["folga_mm"], arr.h_pilar * 1000
    ys = [tp["a4c_mm"] + kk * tp["a2_mm"] for kk in range(tp["n_vert"])]
    Hc = tp["H_chapa_mm"]
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
    _solda(f, tp["L_chapa_mm"] / 4, -folga, _solda_txt(d, "L1f"), dx=200, dy=-150)
    f.carimbo(
        "DES-08", "TOPO DO PILAR DE FRONTÃO — L1f",
        f"Cotas em mm. {tp['n_vert']} cavilhas Ø{tp['d_mm']:g} em chapa embutida t = "
        f"{tp['t_chapa_mm']:g} mm S275, soldada à chapa de topo do PF (t = {t_t:g} mm). "
        f"Furos oblongos verticais com curso ±{tp['curso_mm']:g} mm contra a flecha final "
        f"de {_g(round(tp['w_viga_mm'], 1))} mm da viga no ponto; folga de {folga:g} mm entre a "
        "viga e a chapa de topo. A ligação transmite só a força horizontal H do painel "
        "CV-T." + " " + REF_GERAIS,
        barra=200.0, divisoes=4)
    return f.salvar(caminho)


def desenho_terca_viga(arr: Arranjo, caminho: Path) -> Path:
    """DES-09 — Ligação terça–viga corrente: parafusos a 45° cruzados (issue 43)."""
    d = arr.det["terca_viga"]
    bt, ht = arr.b_terca * 1000, arr.h_terca * 1000
    bv = arr.b_viga * 1000
    nf, pv, lef = d["n_por_face"], d["passo_vertical_mm"], d["l_ef_mm"]
    hv = 420.0                                               # trecho de viga mostrado
    xc = 1250.0                                              # centro da planta
    f = Folha.para_conteudo(15, -420, xc + 330, -hv - 60, ht + 140, unidade="mm")
    ax = f.ax
    # ---------- corte no plano do eixo da viga ----------
    ax.add_patch(Rectangle((-380, -hv), 760, hv, fc=COR_MLC, ec="k", lw=0.5))
    for s_ in (-1, 1):
        _quebra(ax, s_ * 380, s_ * 380, -hv, 0)
    ax.add_patch(Rectangle((-bt / 2, 0), bt, ht, fc=COR_MLC, ec="k", lw=0.6, zorder=3))
    c45 = math.cos(math.radians(45))
    y0 = d["a2_CG_terca_mm"] + lef * c45                     # 1.º parafuso: l_ef na terça
    for s_ in (-1, 1):                                       # duas faces, cruzados
        for k in range(nf):
            ye = y0 + k * pv                                 # entrada na face
            xe = s_ * bt / 2
            # desce a 45° atravessando a terça e penetra l_ef na viga
            dy = ye + lef * c45
            xf = xe - s_ * dy
            ax.plot([xe, xf], [ye, ye - dy], color="k", lw=1.1, zorder=5)
    ax.text(-380, ht + 60, "CORTE NO PLANO DO EIXO DA VIGA", fontsize=6, fontweight="bold")
    _rot(ax, 0, ht * 0.8, "terça", fs=5)
    _rot(ax, 230, -hv / 2, "viga", fs=5)
    f.cota_h(-bt / 2, bt / 2, ht + 25, y_ref=ht, fs=4.4)
    f.cota_v(bt / 2 + 150, 0, ht, x_ref=bt / 2, esquerda=False, fs=4.4)
    ys = [0, y0] + [y0 + k * pv for k in range(1, nf)]
    f.cadeia_v(ys, -bt / 2 - 60, x_ref=-bt / 2, fs=4.0)
    ax.text(bt / 2 + 20, y0 + (nf - 1) * pv + 40, "45°", fontsize=4.8)
    # ---------- planta do topo da viga (duas extremidades de terça) ----------
    ax.add_patch(Rectangle((xc - bv / 2, -hv + 40), bv, 2 * bt + 160, fc=COR_MLC,
                           ec="k", lw=0.5))
    yt = -hv + 120
    for s_ in (-1, 1):
        x0 = xc + (0 if s_ > 0 else -bv / 2)
        ax.add_patch(Rectangle((x0 + (2 if s_ > 0 else 0), yt), bv / 2 - 2, bt,
                               fc="#e9d6a6", ec="k", lw=0.5, zorder=3))
        for yy, dd in ((yt, -d["desloc_mm"]), (yt + bt, d["desloc_mm"])):
            ax.add_patch(Circle((xc + s_ * (d["x_p_mm"] + dd), yy), 6, fc="k", zorder=6))
    ax.text(xc - bv / 2, -hv + 60 + 2 * bt + 160, "PLANTA SOBRE A VIGA", fontsize=6,
            fontweight="bold")
    xa, xb = xc + d["x_p_mm"] - d["desloc_mm"], xc + d["x_p_mm"] + d["desloc_mm"]
    f.cota_h(xc, xa, yt + bt + 40, txt=f"{xa - xc:.0f}", fs=4.2)
    f.cota_h(xa, xb, yt + bt + 40, txt=f"{xb - xa:.0f}", fs=4.2)
    f.cota_h(xb, xc + bv / 2, yt + bt + 40, txt=f"{xc + bv / 2 - xb:.0f}", fs=4.2)
    f.cota_h(xc - bv / 2, xc + bv / 2, yt - 50, txt=f"viga {bv:.0f}", fs=4.2)
    _rot(ax, xc, yt + bt / 2, "junta das terças", fs=4.0)
    f.carimbo(
        "DES-09", "LIGAÇÃO TERÇA–VIGA CORRENTE",
        f"Cotas em mm. {2 * nf} parafusos autoatarraxantes de rosca total "
        f"Ø{d['d_mm']:g} por extremidade de terça ({nf} por face), inseridos pelas faces "
        f"laterais a 45° e cruzados, com penetração efetiva de {lef:.0f} mm na viga e na "
        "terça. As terças biapoiadas se encontram sobre o eixo da viga. Nas baías "
        "contraventadas, a junta recebe também o nó das diagonais (cavilhas Ø20)." + " " + REF_GERAIS,
        barra=200.0, divisoes=4)
    return f.salvar(caminho)


def _rufo(ax, pts, lw=0.9):
    """Chapa dobrada (rufo, capa, calha) como polilinha espessa."""
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=COR_DESTAQUE, lw=lw, solid_joinstyle="miter", zorder=8)


def _telha(ax, x1, y1, x2, y2, e=40.0):
    """Telha trapezoidal em corte, espessura e (ondas)."""
    ax.add_patch(Polygon([(x1, y1), (x2, y2), (x2, y2 + e), (x1, y1 + e)], closed=True,
                         fc="#c9ced3", ec="k", lw=0.35, zorder=7))


def desenho_protecao(arr: Arranjo, caminho: Path) -> Path:
    """DES-10 — Proteção construtiva: ponta do beiral, oitão e calha central (issue 83)."""
    d = arr.det
    ca = d.get("calha") or {}
    tg = math.tan(math.radians(arr.alpha_deg))
    bt, ht = arr.b_terca * 1000, arr.h_terca * 1000
    hpt = d.get("h_ponta_mm", 800.0)
    gap, pg = 20.0, 30.0                              # folga ventilada; pingadeira
    f = Folha.para_conteudo(20, -60, 3130, -260, hpt + ht + 330, unidade="mm")
    ax = f.ax
    # ---------- (a) ponta do beiral ----------
    x0 = 120.0                                        # face do topo da viga
    xb = 900.0
    ax.add_patch(Polygon([(x0, 0), (xb, 0), (xb, hpt + (xb - x0) * tg), (x0, hpt)],
                         closed=True, fc=COR_MLC, ec="k", lw=0.5))
    _quebra(ax, xb, xb, hpt / 2, 25)
    ax.add_patch(Rectangle((x0, hpt), bt, ht, fc="#e9d6a6", ec="k", lw=0.5, zorder=4))
    yt = hpt + ht                                     # topo da T0
    _telha(ax, x0 - 70, yt - 70 * tg, xb, yt + (xb - x0) * tg)   # avança 70 além do topo
    ax.plot([x0, x0], [0, yt], color="k", lw=1.6, zorder=6)      # selagem do topo
    for yy in (hpt * 0.25, hpt * 0.7, hpt + ht * 0.5):           # sarrafos verticais
        ax.add_patch(Rectangle((x0 - gap, yy - 40), gap, 80, fc="0.55", ec="k", lw=0.3,
                               zorder=7))
    _rufo(ax, [(x0 + 60, yt - 5), (x0 - gap, yt - 5), (x0 - gap, -pg),
               (x0 - gap - 25, -pg - 18)])
    ax.text(-50, hpt + ht + 250, "a) PONTA DO BEIRAL (A E C)", fontsize=6,
            fontweight="bold")
    _rot(ax, 600, hpt * 0.45, "viga (balanço)", fs=4.8)
    _rot(ax, x0 + bt / 2, hpt + ht / 2, "T0", fs=4.6)
    _rot(ax, x0 + 230, -120, "rufo de chapa galvanizada e pintada,\nsarrafos verticais "
         "(folga ventilada)", fs=3.8, ha="left")
    _rot(ax, x0 + 60, hpt + 120, "topo\nselado", fs=3.8, ha="left")
    f.cota_h(x0 - gap, x0, -200, txt=f"{gap:.0f}", y_ref=-pg, fs=3.8)
    f.cota_v(x0 - 80, -pg, 0, txt=f"{pg:.0f}", x_ref=x0 - gap, fs=3.8)
    f.cota_v(x0 - 80, 0, hpt, x_ref=x0, fs=4.2)
    # ---------- (b) oitão ----------
    xo = 1250.0                                       # topo da terça em balanço
    xq = 1720.0
    ax.add_patch(Rectangle((xo, 0), xq - xo, ht, fc="#e9d6a6", ec="k", lw=0.5))
    _quebra(ax, xq, xq, ht / 2, 25)
    _telha(ax, xo, ht, xq, ht)
    ax.plot([xo, xo], [0, ht], color="k", lw=1.6, zorder=6)
    for yy in (ht * 0.3, ht * 0.75):
        ax.add_patch(Rectangle((xo - gap, yy - 40), gap, 80, fc="0.55", ec="k", lw=0.3,
                               zorder=7))
    _rufo(ax, [(xo + 150, ht + 45), (xo - gap, ht + 45), (xo - gap, -pg),
               (xo - gap - 25, -pg - 18)])
    ax.text(xo - 150, hpt + ht + 250, "b) OITÃO (EIXOS 1 E 9)", fontsize=6,
            fontweight="bold")
    _rot(ax, xo + 330, ht * 0.45, "terça (balanço)", fs=4.8)
    _rot(ax, xo + 170, ht + 160, "rufo sobre a última\nonda da telha", fs=3.8, ha="left")
    f.cota_v(xo - 80, -pg, 0, txt=f"{pg:.0f}", x_ref=xo - gap, fs=3.8)
    # ---------- (c) calha central ----------
    xc, yv = 2590.0, 0.0                              # eixo B; topo das vigas no apoio
    yv = 300.0
    g = d.get("folga_sela_mm", 20.0)
    for sg in (-1, 1):
        xe, xf = xc + sg * g / 2, xc + sg * 520
        ax.add_patch(Polygon([(xe, yv - 260), (xf, yv - 260),
                              (xf, yv + 520 * tg), (xe, yv)],
                             closed=True, fc=COR_MLC, ec="k", lw=0.5))
        _quebra(ax, xe, xf, yv - 260, 15)
    ax.add_patch(Rectangle((xc - bt / 2, yv), bt, ht, fc="#e9d6a6", ec="k", lw=0.5,
                           zorder=4))
    yT = yv + ht
    _rufo(ax, [(xc - bt / 2 - 35, yT - 30), (xc - bt / 2 - 35, yT + 10),
               (xc + bt / 2 + 35, yT + 10), (xc + bt / 2 + 35, yT - 30)], lw=0.7)
    Bc, Hc = ca.get("B_mm", 300.0), ca.get("H_mm", 150.0)
    fv = ca.get("borda_sobre_T9_mm", 232.0) - Hc - 20.0     # folga + desnível
    yf = yT + 50.0
    for sg in (-1, 1):                                       # suportes nas faces da T9
        xs_ = xc + sg * (bt / 2 + 8)
        ax.plot([xs_, xs_, xc + sg * Bc / 2], [yT - 120, yf, yf], color="0.3", lw=0.8,
                zorder=7)
    _rufo(ax, [(xc - Bc / 2 - 40, yf + Hc), (xc - Bc / 2, yf + Hc), (xc - Bc / 2, yf),
               (xc + Bc / 2, yf), (xc + Bc / 2, yf + Hc), (xc + Bc / 2 + 40, yf + Hc)])
    ax.add_patch(Rectangle((xc - Bc / 2 + 4, yf + 4), Bc - 8, Hc / 2 - 4, fc="#bcd3e6",
                           ec="none", zorder=6))
    yb = yT + ca.get("borda_sobre_T9_mm", 232.0)
    ip = ca.get("inclinacao_ultimo_pano", 0.09)
    for sg in (-1, 1):
        ax.add_patch(Rectangle((xc + sg * (Bc / 2 + 20) - 15, yf + Hc), 30, yb - yf - Hc,
                               fc=COR_ACO, ec="k", lw=0.3, zorder=7))   # perfil de borda
        _telha(ax, xc + sg * (Bc / 2 - 40), yb, xc + sg * 520, yb + (520 - Bc / 2) * ip)
    ax.text(xc - 520, hpt + ht + 250, "c) CALHA CENTRAL (LINHA B)", fontsize=6,
            fontweight="bold")
    _rot(ax, xc, yT - ht / 2, "T9", fs=4.6)
    _rot(ax, xc + 380, yv - 120, "viga", fs=4.6)
    _rot(ax, xc - 380, yv - 120, "viga", fs=4.6)
    _rot(ax, xc + Bc / 2 + 80, yT - 70, "capa da T9\ncom pingadeiras", fs=3.8, ha="left")
    _rot(ax, xc - 520, yb + 170, f"último pano a {100 * ip:.1f} %".replace(".", ","),
         fs=3.8, ha="left")
    f.cota_h(xc - Bc / 2, xc + Bc / 2, yf - 60, txt=f"{Bc:.0f}", fs=3.8)
    f.cota_v(xc - Bc / 2 - 70, yf, yf + Hc, txt=f"{Hc:.0f}", fs=3.8)
    f.cota_v(xc + bt / 2 + 190, yT, yf, txt="50", esquerda=False, fs=3.8, x_ref=xc)
    f.cota_v(xc + 500, yT, yb, txt=f"{yb - yT:.0f}", esquerda=False, fs=3.8, x_ref=xc + Bc / 2 + 35)
    off = ca.get("offset_saida_m", 0.40) * 1000
    f.carimbo(
        "DES-10", "PROTEÇÃO CONSTRUTIVA — BEIRAL, OITÃO E CALHA CENTRAL",
        "Cotas em mm. Rufos e capas de chapa de aço galvanizada e pintada, sem contato "
        f"com a madeira: folga ventilada de {gap:.0f} mm sobre sarrafos verticais e "
        f"pingadeira {pg:.0f} mm abaixo da madeira. Topos de vigas e terças selados com "
        "selante microporoso antes do rufo. Calha central "
        f"{Bc:.0f}×{Hc:.0f} mm, declividade 0,5 %, em suportes nas faces da T9, "
        "50 mm acima da capa da terça; telhas do último pano sobre perfis de borda. "
        f"Uma saída por pórtico, {off:.0f} mm fora do eixo (nunca sobre a L1c), com "
        f"condutor Ø{ca.get('d_condutor_mm', 100):.0f} afastado do pilar, com junta "
        f"deslizante de {_g(d.get('junta_condutor_mm') or 30)} mm junto à saída (a calha "
        "sobe com a viga sob sucção), e ladrão com "
        "descarga livre visível ao lado; pontos altos e juntas de dilatação a meio vão; "
        "extremidades da calha abertas nos oitões (extravasores)."
        + " " + REF_GERAIS,
        barra=500.0)
    return f.salvar(caminho)


# ── Conjunto ───────────────────────────────────────────────────────────────

# ── Folhas da issue 91: topo dos pilares, terminais, juntas das terças, pilarete ──

NOTA_ACO = ("AÇO: chapas, sela, enrijecedores e chapas de nó S275 (EN 10025-2); cavilhas lisas "
            "S275, f_u,k ≥ 400 MPa; pinos das diagonais S355; olhais e barras S235; tubo do "
            "pilarete S355; chumbadores e parafusos 8.8; eletrodo compatível com o metal de base.")


def _terminal(f, x0, y0, ld, nome):
    """Olhal soldado, pino, forquilha de catálogo, rosca recalcada e barra (EN 1993-1-8 §3.13)."""
    ax = f.ax
    d0, dp = ld["d_0_mm"], ld["d_pino_mm"]
    a, c = ld["a_borda_mm"], ld["c_borda_mm"]
    te, tf = ld["t_eye_mm"], ld["t_fork_mm"]
    lsol = ld["l_solda_mm"]
    W = max(lsol, 2 * c + d0)
    hc = d0 / 2 + c + 20.0
    Lo = hc + d0 / 2 + a
    db, dr = ld["d_barra_mm"], ld["d_rosca_mm"] or ld["d_barra_mm"]
    # chapa de apoio (base ou nó)
    _hachura(ax, x0 - 20, y0 - W / 2 - 40, 20, W + 80, zorder=3)
    # olhal
    ax.add_patch(Rectangle((x0, y0 - W / 2), Lo, W, fc=COR_ACO, ec="k", lw=0.6, zorder=4))
    ax.add_patch(Circle((x0 + hc, y0), d0 / 2, fc="w", ec="k", lw=0.5, zorder=5))
    ax.add_patch(Circle((x0 + hc, y0), dp / 2, fc="0.45", ec="k", lw=0.4, hatch="////",
                        zorder=6))
    # forquilha (catálogo), em contorno
    rf = 1.15 * dp
    xb = x0 + Lo + 12
    ax.add_patch(FancyBboxPatch((x0 + hc - rf, y0 - rf), xb - (x0 + hc - rf), 2 * rf,
                                boxstyle=f"round,pad=0,rounding_size={rf}", fill=False,
                                ec="0.25", lw=0.5, ls=(0, (3, 1.5)), zorder=7))
    Lcorpo = 1.6 * dr
    ax.add_patch(Rectangle((xb, y0 - 0.8 * dr), Lcorpo, 1.6 * dr, fill=False, ec="0.25",
                           lw=0.5, ls=(0, (3, 1.5)), zorder=7))
    xr = xb + Lcorpo
    ax.add_patch(Rectangle((xr, y0 - dr / 2), 2.0 * dr, dr, fc="0.75", ec="k", lw=0.4,
                           hatch="||||", zorder=5))
    xbar = xr + 2.0 * dr
    ax.add_patch(Rectangle((xbar, y0 - db / 2), 110, db, fc=COR_ACO, ec="k", lw=0.4, zorder=5))
    _quebra(ax, xbar + 110, xbar + 110, y0, 8)
    # cotas do olhal (Fig. 3.11)
    f.cota_h(x0 + hc + d0 / 2, x0 + Lo, y0 + W / 2 + 18, txt=f"a = {a:g}", fs=3.4)
    f.cota_v(x0 + hc + d0 / 2 + 8, y0 + d0 / 2, y0 + W / 2, txt=f"c = {c:g}", esquerda=False,
             fs=3.2)
    f.cota_v(x0 - 40, y0 - W / 2, y0 + W / 2, txt=f"{W:.0f}", fs=3.4)
    f.cota_h(x0, x0 + hc, y0 - W / 2 - 18, txt=f"{hc:.0f}", acima=False, fs=3.4)
    _solda(f, x0 - 20, y0 + W / 2 - 10, f"a{_g(ld['a_solda_mm'])}–{lsol:.0f} (2 lados)",
           dx=-30, dy=45, fs=3.4)
    _rot(ax, x0 + Lo / 2 + 15, y0 - W / 2 - 55,
         f"olhal t = {te:g} {ld['aco_chapa']}  ·  d0 = {d0:g}", fs=3.6)
    _rot(ax, xb + 25, y0 + 0.8 * dr + 30,
         f"forquilha de catálogo, t ≥ {tf:g} por face,\nN_Rd ≥ {ld['requisito_manilha_kN']:.0f} kN",
         fs=3.4, ha="left")
    _rot(ax, xr + dr, y0 - dr / 2 - 30, f"rosca recalcada M{dr:g}", fs=3.4)
    _rot(ax, xbar + 55, y0 + db / 2 + 25, f"barra Ø{db:g} S235", fs=3.4)
    ax.text(x0 - 20, y0 + W / 2 + 85, f"{nome} — pino Ø{dp:g} {ld['aco_pino']}",
            fontsize=5.4, fontweight="bold")
    # corte pelo pino: olhal entre as faces da forquilha
    xs = xbar + 200
    fg = 2.0
    for sg in (-1, 1):
        xf = xs + sg * (te / 2 + fg + tf / 2)
        ax.add_patch(Rectangle((xf - tf / 2, y0 - rf), tf, 2 * rf, fc="none", ec="0.25",
                               lw=0.5, ls=(0, (3, 1.5)), zorder=5))
    _hachura(ax, xs - te / 2, y0 - W / 2, te, W, zorder=4)
    Lp = te + 2 * (fg + tf) + 2 * 14
    _hachura(ax, xs - Lp / 2, y0 - dp / 2, Lp, dp, fc="0.55", zorder=6, hatch="")
    for sg in (-1, 1):
        ax.add_patch(Rectangle((xs + sg * (Lp / 2 - 6) - 3, y0 - dp / 2 - 4), 6, dp + 8,
                               fc="0.2", zorder=7))
    f.cota_h(xs - te / 2, xs + te / 2, y0 + rf + 22, txt=f"{te:g}", fs=3.2)
    f.cota_h(xs + te / 2 + fg, xs + te / 2 + fg + tf, y0 + rf + 22, txt=f"{tf:g}", fs=3.2)
    f.cota_h(xs - Lp / 2, xs + Lp / 2, y0 - rf - 22, txt=f"pino {Lp:.0f}", acima=False, fs=3.2)
    _rot(ax, xs, y0 + rf + 70, "CORTE PELO PINO", fs=3.8, bold=True, fundo=False)


def desenho_terminais(arr: Arranjo, caminho: Path) -> Path:
    """DES-11 — Terminais das diagonais: olhal, pino, forquilha e rosca (issues 44, 91)."""
    d = arr.det
    lds = d["lig_diag"]
    ordem = [k for k in ("CV-V", "CV-T", "CV-H") if k in lds]
    passo = 300.0
    f = Folha.para_conteudo(5, -175, 610, -passo * (len(ordem) - 1) - 130, 180, unidade="mm")
    for i, k in enumerate(ordem):
        _terminal(f, 0.0, -i * passo, lds[k], k)
    f.carimbo(
        "DES-11", "TERMINAIS DAS DIAGONAIS DE CONTRAVENTAMENTO",
        "Cotas em mm. Dimensionados por capacidade (a resistência da barra), EN 1993-1-8 §3.13 "
        "(Tab. 3.9 e Fig. 3.11) e §4.5.3.3: olhal soldado à chapa de base (CV-V e CV-T, "
        "DES-07) ou à chapa do montante (CV-H, DES-09B); pino em corte duplo com "
        "contrapino; forquilha e esticador de catálogo, com resistência certificada não "
        "inferior à indicada; extremidade da barra recalcada, de modo que a rosca não governe. "
        "Folga de 2 mm entre o olhal e cada face da forquilha. O nó de topo das baías "
        "contraventadas, onde chegam a escora e as diagonais, não é detalhado nesta folha. "
        + REF_GERAIS,
        barra=100.0, divisoes=4)
    return f.salvar(caminho)


def _elev_junta(f, xc, jt, lig, bt, ht, bv, titulo):
    """Elevação ao longo da terça: junta sobre a viga, chapa no rasgo superior, cavilhas
    e as pontas dos parafusos a 45° (issue 91)."""
    ax = f.ax
    cr, rg, ch = jt["corrente"], jt["rasgo"], lig["chapa"]
    Lc, hcp, prof = ch["L_chapa_mm"], ch["h_chapa_mm"], ch["profundidade_rasgo_mm"]
    Lt = Lc / 2 + 130
    ax.add_patch(Rectangle((xc - bv / 2, -260), bv, 260, fc=COR_MLC, ec="k", lw=0.5))
    _quebra(ax, xc - bv / 2 - 30, xc + bv / 2 + 30, -260, 12)
    for sg in (-1, 1):
        x0 = xc + sg * 1.0
        ax.add_patch(Rectangle((min(x0, x0 + sg * Lt), 0), Lt, ht, fc=COR_MLC, ec="k",
                               lw=0.5, zorder=2))
        _quebra(ax, xc + sg * (Lt + 1), xc + sg * (Lt + 1), ht / 2, 0)
    ax.plot([xc - Lc / 2 - 10, xc - Lc / 2 - 10, xc + Lc / 2 + 10, xc + Lc / 2 + 10],
            [ht, ht - prof, ht - prof, ht], color="0.25", lw=0.4, ls=":", zorder=5)
    ax.add_patch(Rectangle((xc - Lc / 2, ht - hcp), Lc, hcp, fill=False, ls="--", ec="0.2",
                           lw=0.5, zorder=5))
    for sg in (-1, 1):
        for i in range(int(lig["n_horiz"])):
            for j in range(int(lig["n_vert"])):
                ax.add_patch(Circle((xc + sg * (lig["a3t_mm"] + i * lig["a1_mm"]),
                                     ht - rg["a4c_mm"] - j * lig["a2_mm"]), lig["d_mm"] / 2,
                                    fc="k", ec="k", lw=0.3, zorder=7))
    # parafusos a 45°: pontas na face próxima (cheias) e na oposta (tracejadas)
    c45 = math.cos(math.radians(45.0))
    y0 = cr["a2_CG_terca_adotado_mm"] + cr["l_ef_mm"] * c45
    zs = [y0 + k * cr["passo_vertical_mm"] for k in range(int(cr["n_por_face"]))]
    for sg in (-1, 1):
        for xx, cheio in ((cr["x_p_mm"] - cr["deslocamento_faces_mm"], True),
                          (cr["x_p_mm"] + cr["deslocamento_faces_mm"], False)):
            for z in zs:
                ax.add_patch(Circle((xc + sg * xx, z), cr["d_mm"] / 2 + 1,
                                    fc="0.3" if cheio else "none", ec="0.3", lw=0.3,
                                    ls="-" if cheio else (0, (1, 1)), zorder=6))
    zi, zsup = rg["z_cruzamento_inf_mm"], rg["z_cruzamento_sup_mm"]
    xm = cr["x_p_mm"] + cr["deslocamento_faces_mm"] + 20
    ax.add_patch(Rectangle((xc - xm, zi), 2 * xm, zsup - zi, fc="none", ec="0.5", lw=0.3,
                           hatch="\\\\\\\\", zorder=3))
    f.cota_v(xc + Lc / 2 + 60, ht - prof, ht, txt=f"rasgo {prof:.0f}", esquerda=False,
             fs=3.4, x_ref=xc + Lc / 2 + 10)
    f.cota_v(xc + Lc / 2 + 140, zsup, ht, txt=f"livre {ht - zsup:.0f}", esquerda=False,
             fs=3.4, x_ref=xc + xm)
    xs_ = [xc] + [xc + lig["a3t_mm"] + i * lig["a1_mm"] for i in range(int(lig["n_horiz"]))] \
        + [xc + Lc / 2]
    f.cadeia_h(xs_, ht + 40, y_ref=ht, fs=3.4)
    f.cota_h(xc - Lc / 2, xc + Lc / 2, ht + 100, txt=f"chapa {Lc:.0f}×{hcp:.0f}", fs=3.6)
    zz = [ht - rg["a4c_mm"] - j * lig["a2_mm"] for j in range(int(lig["n_vert"]))]
    f.cadeia_v(sorted(zz) + [ht], xc - Lc / 2 - 50, x_ref=xc - Lc / 2, fs=3.4)
    f.cota_h(xc - bv / 2, xc + bv / 2, -150, txt=f"viga {bv:.0f}", fs=3.4)
    _rot(ax, xc, ht + 200, titulo, fs=5.2, bold=True, fundo=False)


def desenho_juntas_tercas(arr: Arranjo, caminho: Path) -> Path:
    """DES-09B — Junta das terças sobre a viga: emenda da corda e montante (issue 91)."""
    d = arr.det
    jt = d["junta_terca"]
    bt, ht, bv = arr.b_terca * 1000, arr.h_terca * 1000, arr.b_viga * 1000
    em, mo = jt["emenda"], jt["montante"]
    xe = 0.0
    xm = em["chapa"]["L_chapa_mm"] / 2 + 130 + 250 + mo["chapa"]["L_chapa_mm"] / 2 + 130
    xs = xm + mo["chapa"]["L_chapa_mm"] / 2 + 130 + 420
    f = Folha.para_conteudo(25, -em["chapa"]["L_chapa_mm"] / 2 - 270, xs + 330, -320,
                            ht + 260, unidade="mm")
    ax = f.ax
    _elev_junta(f, xe, jt, em, bt, ht, bv,
                f"EMENDA DA CORDA (T1, T17): {em['n_pinos']} cav. por lado")
    _elev_junta(f, xm, jt, mo, bt, ht, bv,
                f"MONTANTE (baías contraventadas): {mo['n_pinos']} cav. por lado")
    # corte transversal da terça sobre a viga
    cr, rg = jt["corrente"], jt["rasgo"]
    ax.add_patch(Rectangle((xs - 300, -260), 600, 260, fc=COR_MLC, ec="k", lw=0.5))
    for s_ in (-1, 1):
        _quebra(ax, xs + s_ * 300, xs + s_ * 300, -260, 0)
    ax.add_patch(Rectangle((xs - bt / 2, 0), bt, ht, fc=COR_MLC, ec="k", lw=0.6, zorder=3))
    prof = mo["chapa"]["profundidade_rasgo_mm"]
    tr = mo["t_chapa_mm"] + 4.0
    t_m = (bt - 2 * tr) / 3.0                       # chapas duplas: três partes de madeira
    for sg in (-1, 1):
        xp_ = xs + sg * (t_m / 2 + tr / 2)
        ax.add_patch(Rectangle((xp_ - tr / 2, ht - prof), tr, prof, fc="w", ec="k", lw=0.4,
                               zorder=4))
        _hachura(ax, xp_ - mo["t_chapa_mm"] / 2, ht - mo["chapa"]["h_chapa_mm"],
                 mo["t_chapa_mm"], mo["chapa"]["h_chapa_mm"], zorder=5)
    c45 = math.cos(math.radians(45.0))
    y0 = cr["a2_CG_terca_adotado_mm"] + cr["l_ef_mm"] * c45
    for s_ in (-1, 1):
        for k in range(int(cr["n_por_face"])):
            ye = y0 + k * cr["passo_vertical_mm"]
            dy = ye + cr["l_ef_mm"] * c45
            ax.plot([xs + s_ * bt / 2, xs + s_ * bt / 2 - s_ * dy], [ye, ye - dy], color="k",
                    lw=0.9, zorder=6)
    ax.plot([xs - bt / 2 - 20, xs + bt / 2 + 20], [rg["z_cruzamento_sup_mm"]] * 2, color=COR_CV,
            lw=0.4, ls=(0, (3, 2)), zorder=7)
    f.cota_v(xs + bt / 2 + 60, rg["z_cruzamento_sup_mm"], ht - prof,
             txt=f"{ht - prof - rg['z_cruzamento_sup_mm']:.0f}", esquerda=False, fs=3.4,
             x_ref=xs + tr / 2)
    f.cota_v(xs + bt / 2 + 60, ht - prof, ht, txt=f"{prof:.0f}", esquerda=False, fs=3.4)
    f.cota_h(xs - bt / 2, xs + bt / 2, ht + 30, y_ref=ht, fs=3.6)
    _rot(ax, xs, ht + 190, "CORTE DA TERÇA (MONTANTE)", fs=5.2, bold=True, fundo=False)
    _rot(ax, xs + bt / 2 + 25, rg["z_cruzamento_sup_mm"] - 45, "parafuso a 45°\nmais alto",
         fs=3.2, ha="left", cor=COR_CV)
    f.carimbo(
        "DES-09B", "JUNTA DAS TERÇAS SOBRE A VIGA — EMENDA DA CORDA E MONTANTE",
        f"Cotas em mm. As terças são biapoiadas: a corda do diafragma (T1 e T17) tem "
        f"{jt['n_emendas']} juntas por linha, uma sobre cada viga intermediária, e cada uma "
        f"transmite {_g(round(em['F_Ed_kN'], 1))} kN em tração e compressão; nas baías "
        f"contraventadas a junta é também montante da treliça da cobertura "
        f"({_g(round(mo['F_Ed_kN'], 1))} kN). Chapas t = {mo['t_chapa_mm']:g} em rasgos "
        f"SUPERIORES de {mo['t_chapa_mm'] + 4:g} mm das duas terças, atravessando a junta, "
        "uma na emenda e duas no montante (quatro planos de corte por cavilha, corte), com "
        "cavilhas Ø20 paralelas às fibras de cada lado: "
        f"o rasgo não desce abaixo de {rg['profundidade_max_mm']:.0f} mm, para ficar "
        f"{10:.0f} mm acima do cruzamento dos parafusos a 45° da junta corrente (hachurado; "
        "DES-09), que continuam a levar o arrancamento. "
        + REF_GERAIS,
        barra=500.0)
    return f.salvar(caminho)


def desenho_pilar_bipartido(arr: Arranjo, caminho: Path) -> Path:
    """DES-07B — Topo do pilar bipartido dos montantes (issue 104): sela, nó e escora."""
    d = arr.det
    g = d["bipartido"]
    rc = g["res"]["pilar_central_contraventado"]
    a, bl, hl, yl, yn = g["a_mm"], g["b_l_mm"], g["h_l_mm"], g["y_l_mm"], g["y_no_mm"]
    h0, bv = arr.h0 * 1000, arr.b_viga * 1000
    folga = g["folga_escora_mm"]
    zt = h0 + folga                                    # topo das lâminas = apoio da escora
    ht = arr.h_terca * 1000
    sela, no = rc["sela"], rc["no"]
    ts = float(sela["t_chapa_mm"])
    esc = d.get("escora_lig") or {}
    par = d.get("escora_paraf") or {}
    beta = math.radians(d.get("lig_diag", {}).get("CV-V", {}).get("beta_deg", 55.8))
    _pec = _pecas_bipartido(d, arr, rc)
    f = Folha.para_conteudo(20, -a / 2 - bl - 520, yn + 1150,
                            -1150 - 20 * (3 + _altura_lista_mm(len(_pec))), zt + ht + 260,
                            unidade="mm")
    ax = f.ax
    # lâminas
    for sg in (-1, 1):
        x0 = sg * (a / 2) if sg > 0 else -(a / 2 + bl)
        ax.add_patch(Rectangle((x0, -1050), bl, zt + 1050, fc=COR_MLC, ec="k", lw=0.6, zorder=2))
        _quebra(ax, x0 - 25, x0 + bl + 25, -1050, 15)
    # viga em seção sobre a sela, com folga sob a escora
    ax.add_patch(Rectangle((-bv / 2, 0), bv, h0, fc="#e9d6a6", ec="k", lw=0.5, zorder=2))
    _rot(ax, 0, h0 * 0.55, "viga\n(seção)", fs=4.4)
    # sela: chapa sob a viga e abas embutidas nas lâminas, com cavilhas
    L_aba = sela["a3t_mm"] + (sela["n_horiz"] - 1) * sela["a1_mm"] + 2 * sela["d_mm"]
    _hachura(ax, -a / 2 - bl / 2, -ts, a + bl, ts, zorder=4)
    for sg in (-1, 1):
        xa = sg * yl
        ax.add_patch(Rectangle((xa - ts / 2, -ts - L_aba), ts, L_aba, fill=False, ls="--",
                               ec="0.2", lw=0.5, zorder=4))
        for k in range(int(sela["n_horiz"])):
            zk = -ts - sela["a3t_mm"] - k * sela["a1_mm"]
            ax.plot([xa - bl / 2, xa + bl / 2], [zk, zk], color="k", lw=0.9, zorder=5)
    # escora (terça) sobre as lâminas
    ax.add_patch(Rectangle((-a / 2 - bl - 480, zt), a + 2 * bl + 480 + yn + 900, ht, fc=COR_MLC,
                           ec="k", lw=0.5, zorder=3))
    _quebra(ax, -a / 2 - bl - 480, -a / 2 - bl - 480, zt + ht / 2, 0)
    _rot(ax, -a / 2 - bl - 240, zt + ht / 2, "escora (terça T1/T9)", fs=4.2)
    # nó por contato: chapa-capa sobre o topo da lâmina, aba com duas cavilhas e olhal
    tc_ = 20.0
    _hachura(ax, a / 2, zt - tc_, bl + 40, tc_, zorder=6)
    L_no = no["a3t_mm"] + (no["n_horiz"] - 1) * no["a1_mm"] + 2 * no["d_mm"]
    ax.add_patch(Rectangle((yl - 10, zt - tc_ - L_no), 20, L_no, fill=False, ls="--", ec="0.2",
                           lw=LW_FINA + 0.1, zorder=4))
    for k in range(int(no["n_horiz"])):
        zk = zt - tc_ - no["a3t_mm"] - k * no["a1_mm"]
        ax.plot([yl - bl / 2, yl + bl / 2], [zk, zk], color="k", lw=0.9, zorder=5)
    xo0, zo = a / 2 + bl, zt - tc_ - 70
    ax.add_patch(Rectangle((xo0, zo - 60), yn - xo0 + 60, 130, fc=COR_ACO, ec="k",
                           lw=LW_VISTA, zorder=5))
    ax.add_patch(Circle((yn, zo), 18, fc="w", ec="k", lw=0.4, zorder=6))
    ax.annotate("", xy=(yl, zt - tc_ - 4), xytext=(yl, zt + 120),
                arrowprops=dict(arrowstyle="-|>", lw=0.6, color=COR_CV), zorder=8)
    _rot(ax, yl - 20, zt + 150, "contato", fs=3.4, ha="right", cor=COR_CV)
    xd = yn + 900 * math.cos(beta)
    ax.plot([yn, xd], [zo, zo - 900 * math.sin(beta)], color=COR_CV, lw=2.0, zorder=4)
    _rot(ax, xd - 40, zo - 900 * math.sin(beta) + 60, "diagonal CV-V\n(DES-11)", fs=4.0,
         ha="right", cor=COR_CV)
    # chapa da escora (embutida na terça) parafusada à chapa do nó
    ax.add_patch(Rectangle((xo0 + 20, zo - 40), 150, zt + 160 - zo + 40, fill=False,
                           ls=(0, (2, 1.5)), ec=COR_DESTAQUE, lw=0.6, zorder=6))
    for zz in (zo + 10, zo + 90):
        ax.add_patch(Circle((xo0 + 95, zz), 12, fc=COR_DESTAQUE, zorder=7))
    # cotas
    f.cota_v(a / 2 + bl + 30, h0, zt, txt=f"folga {folga:.0f}", esquerda=False, fs=3.6,
             x_ref=bv / 2)
    f.cota_v(-a / 2 - bl - 90, 0, h0, txt=f"h0 = {h0:.0f}", fs=3.8, x_ref=-a / 2 - bl)
    f.cota_h(-a / 2 - bl, -a / 2, -1000, txt=f"{bl:.0f}", acima=False, fs=3.6)
    f.cota_h(-a / 2, a / 2, -1000, txt=f"{a:.0f}", acima=False, fs=3.6)
    f.cota_h(a / 2, a / 2 + bl, -1000, txt=f"{bl:.0f}", acima=False, fs=3.6)
    f.cota_h(0, yn, zt + ht + 60, y_ref=zt + ht, txt=f"nó a {yn:.0f} do eixo", fs=3.6)
    f.cota_v(yl + bl / 2 + 60, zt - tc_ - L_no, zt - tc_, txt=f"aba {L_no:.0f}",
             esquerda=False, fs=3.4)
    _solda(f, yl + ts / 2, -ts, _solda_txt(d, "aba da sela"), dx=260, dy=-180, fs=3.4)
    _solda(f, xo0 + 2, zo + 40, _solda_txt(d, "olhal das diagonais CV-V"), dx=-260, dy=230,
           fs=3.4)
    _rot(ax, -yl, -620, f"sela: {sela['n_pinos']} cav.\nØ{sela['d_mm']:g} por lâmina", fs=3.6)
    _rot(ax, yl, -620, f"capa do nó: {no['n_pinos']} cav.\nØ{no['d_mm']:g} na aba", fs=3.6)
    ax.text(-a / 2 - bl - 500, zt + ht + 180, "TOPO DO PILAR BIPARTIDO — VISTA NO PLANO DA "
            "FACHADA", fontsize=5.6, fontweight="bold")
    esp = rc["espacadores"]
    for (bx, by, mk, ddx, ddy) in ((-yl, -ts / 2, "SL-01", -260, -120),
                                   (-yl, -ts - 200, "SA-01", -260, -60),
                                   (yl + 40, zt - 10, "CP-01", 120, 230),
                                   (yl, zt - 200, "CA-01", 230, -40),
                                   ((xo0 + yn) / 2, zo - 50, "OL-01", 260, -120),
                                   (xo0 + 95, zo + 50, "PF-01", 330, 60)):
        _balao(f, bx, by, mk, dx=ddx, dy=ddy)
    _lista_pecas(f, f.x0 + f.p(4), -1150 - f.p(3), _pec, titulo="LISTA DE PEÇAS (por pilar)")
    f.carimbo(
        "DES-07B", "PILAR BIPARTIDO DOS MONTANTES — TOPO, SELA E NÓ",
        f"Cotas em mm. Montantes das baías contraventadas: duas lâminas de MLC {bl:.0f}×"
        f"{hl:.0f}, distância livre {a:.0f}, da base até a escora, com espaçadores de MLC a cada "
        f"{esp['l1_mm']:.0f} mm e no pé (EN 1995-1-1, Anexo C). A viga apoia-se na sela "
        "(SL-01, abas SA-01 nas lâminas) e fica livre sob a escora, com folga para o "
        "inchamento. Nó por contato: a chapa-capa (CP-01) apoia-se no topo da lâmina e leva "
        "a componente vertical da diagonal, que é sempre para baixo; a aba (CA-01) com duas "
        "cavilhas só posiciona e ancora o arrancamento das terças. A escora, com duas chapas "
        f"embutidas, liga-se ao olhal (OL-01) por {par.get('n_parafusos', 2)} "
        f"M{par.get('d_mm', 24):g} 8.8 (PF-01): escora e diagonal concorrem no mesmo ponto. "
        + REF_GERAIS,
        barra=500.0)
    return f.salvar(caminho)


TITULOS_FOLHAS = {
    "DES-00": "Notas gerais e convenções",
    "DES-01": "Planta de cobertura e locação",
    "DES-02": "Planta de contraventamento",
    "DES-03": "Elevações longitudinais",
    "DES-04": "Elevação transversal (frontão)",
    "DES-05": "Ligação viga–pilar L1 e topo do pilar lateral",
    "DES-05B": "Ligação viga–pilar L1c (sela) e topo do pilar central",
    "DES-05C": "Chapas embutidas L1 e L1c em verdadeira grandeza",
    "DES-06": "Bases correntes L3, L3c e L3f, pilarete e tirante",
    "DES-07": "Base ancorada L3a dos montantes bipartidos",
    "DES-07B": "Pilar bipartido: topo, sela e nó",
    "DES-08": "Topo do pilar de frontão (L1f)",
    "DES-09": "Ligação terça–viga corrente",
    "DES-09B": "Junta das terças: emenda da corda e montante",
    "DES-10": "Proteção construtiva",
    "DES-11": "Terminais das diagonais",
}


def desenho_notas_gerais(arr: Arranjo, caminho: Path) -> Path:
    """DES-00 — Notas gerais: materiais, proteção, soldas, furos, convenções e folhas."""
    import textwrap
    d = arr.det
    tirs = d.get("tirante") or {}
    d_tir = sorted({int(t["d_mm"]) for t in tirs.values()}) or [24]
    blocos_esq = [
        ("1. MATERIAIS", [
            "Madeira lamelada colada GL24h (EN 14080), pinus com lamelas tratadas, classe "
            "de serviço 3 (EN 1995-1-1).",
            "Chapas, sela, enrijecedores, abas e capas: S275 (EN 10025-2); chapas de topo e "
            "selas com propriedades na espessura, classe Z (EN 1993-1-10).",
            "Tubos dos pilaretes e luvas dos tirantes: S355. Olhais e barras das diagonais: "
            "S235. Pinos das diagonais: S355.",
            "Cavilhas e pinos das ligações em madeira: S275, f_u,k ≥ 400 MPa.",
            "Chumbadores, parafusos e tirantes internos (M" + "/M".join(str(x) for x in d_tir)
            + "): classe 8.8 (EN ISO 898-1). Parafusos autoatarraxantes: produto com "
            "avaliação técnica (ETA).",
        ]),
        ("2. PROTEÇÃO", [
            "Aço galvanizado a fogo após corte, furação e solda (EN ISO 1461); parafusos e "
            "barras roscadas, EN ISO 10684. Solda de obra só com reparo em tinta rica em zinco.",
            "Bases: pintura sobre o zinco (sistema dúplex). Pilaretes: pintura intumescente "
            "R60 sobre o zinco.",
            "Madeira: impregnante pigmentado (EN 927), retardante de chama nas faces "
            "expostas; topos protegidos por rufos ventilados (DES-10).",
        ]),
    ]
    blocos_dir = [
        ("3. SOLDAS", [
            "Filete, EN 1993-1-8 §4.5.3.3, eletrodo compatível com o metal de base; de "
            "oficina, salvo indicação.",
            "Chamada em azul: aN–L = garganta N e comprimento L (mm); \"2 lados\" = cordão "
            "duplo; \"contorno\" = todo o perímetro.",
        ]),
        ("4. FUROS E FOLGAS", [
            "Madeira: furo igual ao diâmetro da cavilha. Chapas: d0 = d + 2 mm (EN 1090-2); "
            "furos ovalizados conforme DES-05C.",
            "Chapa de base: furo Ø36 com arruela-chapa soldada na montagem.",
            "Pilares correntes: furo central Ø(d + 16) para o tirante interno, feito pelo "
            "fabricante por ranhuras nas lamelas centrais antes da colagem; drena pela "
            "janela do pilarete.",
        ]),
        ("5. CONVENÇÕES", [
            "Cotas em mm nos detalhes e em m nas plantas; níveis em m acima do piso acabado "
            "(±0,00 = topo do bloco).",
            "Linha grossa: seção cortada; média: vista; fina: cotas e eixos. Tracejado: "
            "oculto. Traço e ponto: eixo.",
            "Balão: marca da peça, com a lista de peças da folha. Hachura cruzada: aço em "
            "corte; ocre: madeira.",
        ]),
    ]
    W, col = LARGURA_FOLHA_MM, 76.0
    f = Folha.para_conteudo(1, 0.0, W, 0.0, 112.0, unidade="mm")
    ax = f.ax

    def _coluna(x, y, blocos):
        for tit, itens in blocos:
            ax.text(x, y, tit, fontsize=5.6, fontweight="bold", va="top")
            y -= 3.6
            for it in itens:
                linhas = textwrap.wrap(it, 62)
                ax.text(x, y, "–", fontsize=4.6, va="top")
                for ln in linhas:
                    ax.text(x + 2.2, y, ln, fontsize=4.6, va="top")
                    y -= 2.35
                y -= 0.6
            y -= 1.6
        return y

    y_e = _coluna(2.0, 110.0, blocos_esq)
    y_d = _coluna(2.0 + col + 4.0, 110.0, blocos_dir)
    y = min(y_e, y_d) - 2.0
    ax.text(2.0, y, "6. FOLHAS", fontsize=5.6, fontweight="bold", va="top")
    y -= 3.6
    itens = list(TITULOS_FOLHAS.items())
    meio = (len(itens) + 1) // 2
    for k, (cod, tit) in enumerate(itens):
        xx = 2.0 if k < meio else 2.0 + col + 4.0
        yy = y - (k % meio) * 2.6
        ax.text(xx, yy, cod, fontsize=4.6, fontweight="bold", va="top")
        ax.text(xx + 13.0, yy, tit, fontsize=4.6, va="top")
    f.carimbo("DES-00", "NOTAS GERAIS E CONVENÇÕES",
              "Estas notas valem para todas as folhas; cada folha traz só o que lhe é próprio.",
              com_escala=False)
    return f.salvar(caminho)


FOLHAS = (
    ("des00_notas_gerais.pdf", desenho_notas_gerais),
    ("des01_planta_cobertura.pdf", desenho_planta_cobertura),
    ("des02_planta_contraventamento.pdf", desenho_planta_contraventamento),
    ("des03_elevacoes_longitudinais.pdf", desenho_elevacoes_longitudinais),
    ("des04_elevacao_transversal.pdf", desenho_elevacao_transversal),
    ("des05_ligacao_L1.pdf", desenho_detalhe_L1),
    ("des05b_ligacao_L1c.pdf", desenho_detalhe_L1c),
    ("des05c_chapa_L1.pdf", desenho_chapa_L1),
    ("des06_bases_correntes.pdf", desenho_bases_correntes),
    ("des07_base_ancorada.pdf", desenho_base_ancorada),
    ("des07b_pilar_bipartido.pdf", desenho_pilar_bipartido),
    ("des08_topo_PF_L1f.pdf", desenho_detalhe_L1f),
    ("des09_terca_viga.pdf", desenho_terca_viga),
    ("des09b_juntas_tercas.pdf", desenho_juntas_tercas),
    ("des10_protecao.pdf", desenho_protecao),
    ("des11_terminais.pdf", desenho_terminais),
)


def gerar_desenhos(arr: Arranjo, pasta: Path) -> list[Path]:
    """Gera todas as folhas em `pasta` (tipicamente tese/fig)."""
    return [fn(arr, Path(pasta) / nome) for nome, fn in FOLHAS]


from mlc_projeto.checks.els.deslocamento_succao import flecha_no_ponto  # noqa: E402,F401


def detalhe_topo_pf(topo: dict, w_fin_mm: float, L_T: float, L: float) -> dict:
    """
    Detalhe da ligação L1f (fonte única para desenho e quadro de espaçamentos):
    curso do furo oblongo ≥ flecha da viga no ponto do PF + 5 mm e ≥ `curso_min_mm`
    do topo (subida sob sucção, issue 112), folga = curso
    + 5 mm, passo das cavilhas na chapa a2 ≥ 2·curso + d0 + 1,2·d0 (aço entre
    furos), nunca menor que o mínimo da madeira, e chapa até e4 = 1,5·d0 acima
    do centro do raio da extremidade do furo mais alto (d0 = d + folga, issue 79).
    """
    d = float(topo["d_mm"])
    d0 = d0_furo(d)
    w = flecha_no_ponto(float(w_fin_mm), L_T, float(L))
    curso = 5.0 * math.ceil((w + 5.0) / 5.0)
    # issue 112: curso também contra a subida da viga sob sucção (deslocamento_succao)
    curso = max(curso, float(topo.get("curso_min_mm") or 0.0))
    a2 = max(float(topo["a2_mm"]), 10.0 * math.ceil((2.0 * curso + 2.2 * d0) / 10.0))
    n_vert, a4c = int(topo["n_vert"]), float(topo["a4c_mm"])
    H = math.ceil(a4c + (n_vert - 1) * a2 + curso + 1.5 * d0)
    return {"w_viga_mm": w, "curso_mm": curso, "folga_mm": curso + 5.0, "a2_mm": a2,
            "d_mm": d, "d0_mm": d0, "a4c_mm": a4c, "n_vert": n_vert, "H_chapa_mm": H}


def arranjo_de_resultados(res: dict, geo, *, n_eixos: int, L_T: float, H_pilar: float,
                          b_pilar: float, h_pilar: float, b_canto: float,
                          h_canto: float, b_terca: float, h_terca: float,
                          d_chu_mm: float, h_ef_mm: float, c_borda_mm: float,
                          h_bloco_mm: float, chaveta_L_mm: float,
                          chaveta_H_mm: float, classe_concreto: str,
                          l_sela_viga_m: float, folga_sela_m: float,
                          t_chapa_topo_mm: float, folga_oblongo_L1_mm,
                          a_oit: float = 0.0, a_beiral_mm: float = 0.0,
                          ancoragem_mont: dict | None = None) -> Arranjo:
    """Monta o Arranjo a partir dos resultados do pipeline (fonte única)."""
    L1 = res["L1"]
    d = float(L1["d_mm"])
    esq = res["esquadro_chapas"]["L1"]
    pf, topo = res["pilar_frontao"], res["pilar_frontao"]["topo"]
    _tf = detalhe_topo_pf(topo, float(res["ELS"]["w_fin_mm"]), L_T, float(geo.L))
    w_pf, curso = _tf["w_viga_mm"], _tf["curso_mm"]

    def _base(k):
        b = res[k]
        return {"B_mm": b["B_mm"], "L_mm": b["L_mm"], "t_mm": b["t_adotada_mm"],
                "chumbadores_mm": b["geometria"]["chumbadores_mm"],
                "t_alma_mm": b["t_alma_mm"], "pe": b["pe_pilar"],
                "pil": b.get("pilarete")}

    det = {
        "t_chapa_topo_mm": t_chapa_topo_mm, "a_beiral_mm": a_beiral_mm,
        "n_pinos_L1": int(L1["n_pinos"]), "d_pino_L1_mm": d,
        "n_fil_L1": int(L1["n_linhas"]),
        "x_pinos_L1_mm": esq.get("x_pinos_mm"),
        "x_pinos_L1c_mm": res["esquadro_chapas"]["L1c"].get("x_pinos_mm"),
        "a2_L1_mm": float(L1["a2_mm"]), "a3t_L1_mm": float(L1["a3t_mm"]),
        "a4c_L1_mm": float(L1.get("a4c_topo_mm", 3.0 * d)),
        "L1_chapa_L_mm": float(esq["largura_mm"]), "L1_chapa_H_mm": float(esq["altura_mm"]),
        "fundo_rasgo_mm": float(esq.get("fundo_rasgo_mm", esq["altura_mm"])),
        "t_chapa_L1_mm": float(esq["t_adotada_mm"]),
        "t_rasgo_mm": float(esq.get("t_rasgo_mm", float(esq["t_adotada_mm"]) + 4.0)),
        "d0_L1_mm": float(esq.get("d0_mm", d0_furo(d))),
        "L1c_chapa_L_mm": float(res["esquadro_chapas"]["L1c"]["largura_mm"]),
        "L1_rasgo_L_mm": float(esq.get("L_rasgo_mm", 0.0)),
        "L1c_rasgo_L_mm": float(res["esquadro_chapas"]["L1c"].get("L_rasgo_mm", 0.0)),
        "y_pino_alto_mm": float(res["oblongo_L1"]["y_topo_mm"]) if "oblongo_L1" in res
                          else float(geo.h0) * 1000 - float(L1.get("a4c_topo_mm", 3 * d)),
        "folga_acima_montagem_mm": (res.get("oblongo_L1") or {}).get("folga_acima_montagem_mm"),
        "calha": res.get("calha"),
        "junta_condutor_mm": (res.get("deslocamento_succao") or {}).get("condutor", {})
                             .get("junta_deslizante_mm"),
        "h_ponta_mm": float(geo.h_ponta) * 1000 if hasattr(geo, "h_ponta") else 800.0,
        "folga_oblongo_mm": folga_oblongo_L1_mm,
        "topo_pilar": {k: res["ligacao_topo_pilar"]["variantes"][k]["cavilhas"]
                       for k in ("base_L3", "base_L3c")}
                      if "ligacao_topo_pilar" in res else None,
        "enrij_sela": ({"c_mm": res["sela_central"]["enrijecedores"]["dim_enrij_mm"][0],
                        "t_mm": res["sela_central"]["enrijecedores"]["t_enrij_mm"],
                        "t_e_mm": res["sela_central"]["enrijecedores"]["t_enrij_mm"],
                        "h_lat_mm": res["sela_central"]["enrijecedores"]["h_lateral_mm"],
                        "n": res["sela_central"]["enrijecedores"]["n_enrij"]}
                       if "enrijecedores" in res.get("sela_central", {}) else None),
        "l_sela_viga_mm": l_sela_viga_m * 1000, "folga_sela_mm": folga_sela_m * 1000,
        "t_sela_mm": float(res["sela_central"]["t_adot_mm"]),
        "bases": {"L3": _base("base_L3"), "L3c": _base("base_L3c"),
                  "L3f": _base("base_L3f"), "L3a": _base("base_L3a_canto")},
        "d_chu_mm": d_chu_mm, "h_ef_mm": h_ef_mm, "c_borda_mm": c_borda_mm,
        "h_bloco_mm": h_bloco_mm, "chaveta_L_mm": chaveta_L_mm,
        "chaveta_H_mm": chaveta_H_mm, "classe_concreto": classe_concreto,
        # bases L3a dos montantes: embutimento, borda, bloco e chaveta próprios (issue 109)
        "mont": dict({"h_ef_mm": h_ef_mm, "c_borda_mm": c_borda_mm,
                      "h_bloco_mm": h_bloco_mm, "chaveta_L_mm": chaveta_L_mm},
                     **(ancoragem_mont or {})),
        # L1f: os furos oblongos exigem, na chapa, a2 ≥ 2·curso + d0 + 1,2·d0
        # (aço entre furos); na madeira a2 maior que o mínimo só favorece.
        "terca_viga": {
            "n_por_face": int(res["ligacao_terca_viga"]["corrente"]["n_por_face"]),
            "passo_vertical_mm": float(res["ligacao_terca_viga"]["corrente"]["passo_vertical_mm"]),
            "l_ef_mm": float(res["ligacao_terca_viga"]["corrente"]["l_ef_mm"]),
            "d_mm": float(res["ligacao_terca_viga"]["corrente"]["d_mm"]),
            "a1_CG_mm": float(res["ligacao_terca_viga"]["corrente"]["a1_CG_adotado_mm"]),
            "x_p_mm": float(res["ligacao_terca_viga"]["corrente"]["x_p_mm"]),
            "desloc_mm": float(res["ligacao_terca_viga"]["corrente"]["deslocamento_faces_mm"]),
            "a2_CG_terca_mm": float(res["ligacao_terca_viga"]["corrente"]["a2_CG_terca_adotado_mm"]),
        },
        # issue 104: pilar bipartido dos montantes das baías contraventadas
        "bipartido": (dict(res["pilar_central_contraventado"]["geometria"],
                           folga_escora_mm=FOLGA_ESCORA_VIGA_MM,
                           res={k: res[k] for k in ("pilar_contraventado", "pilar_lateral_montante",
                                                    "pilar_central_contraventado") if k in res})
                      if "geometria" in res.get("pilar_central_contraventado", {}) else None),
        "escora_lig": (res.get("no_contraventamento") or {}).get("ligacao_escora_central"),
        "escora_paraf": ((res.get("no_escora_parafusos") or {}).get("interfaces") or {}).get("central"),
        # issue 91: soldas, terminais, juntas das terças, topo dos pilares, impacto
        "soldas": [(x["peca"], float(x["a_mm"]), x.get("l_mm"), x.get("n_cordoes"))
                   for x in (res.get("soldas") or {}).get("itens", [])],
        "lig_diag": {
            nome: dict(res[k], d_barra_mm=float(res[cv].get("d_mm", res[cv].get("d_barra_mm"))),
                       d_rosca_mm=float(res[cv].get("d_rosca_mm", 0.0)),
                       beta_deg=float(res[cv].get("beta_deg", 55.0) or 55.0))
            for nome, k, cv in (("CV-V", "lig_diag_vertical", "contraventamento_vertical"),
                                ("CV-T", "lig_diag_transversal", "contraventamento_transversal"),
                                ("CV-H", "lig_diag_cobertura", "contraventamento"))
            if k in res},
        "junta_terca": ({
            "corrente": res["ligacao_terca_viga"]["corrente"],
            "montante": res["ligacao_terca_viga"]["montante"],
            "emenda": res["ligacao_terca_viga"].get("emenda_corda"),
            "rasgo": res["ligacao_terca_viga"].get("rasgo_superior"),
            "n_emendas": int(res.get("corda_beiral", {}).get("n_emendas", 0)),
        } if res["ligacao_terca_viga"].get("rasgo_superior") else None),
        "topo_var": ({k: res["ligacao_topo_pilar"]["variantes"][k]
                      for k in ("base_L3", "base_L3c")}
                     if "ligacao_topo_pilar" in res else None),
        "impacto": (res.get("impacto_veiculo") or {}).get("forcas"),
        "tirante": (res.get("tirante_interno") or {}).get("variantes"),
        "L1f": {
            "n_vert": int(topo["n_vert"]), "d_mm": float(topo["d_mm"]),
            "a2_mm": _tf["a2_mm"], "d0_mm": _tf["d0_mm"], "H_chapa_mm": _tf["H_chapa_mm"],
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
        det=det, a_bal=float(getattr(geo, "a_bal", 0.0)), a_oit=float(a_oit),
        d_cvd=float(res.get("diafragma_cobertura", {}).get("d_diafragma_mm", 0.0)),
    )
