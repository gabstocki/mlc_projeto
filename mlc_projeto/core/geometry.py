"""
core/geometry.py — Geometria paramétrica da viga de duplo-bisel.

Calcula h(x), A(x), I(x) e W(x) para n pontos ao longo do vão.

Beiral (issue 82): a viga pode prolongar-se em BALANÇO além de cada apoio, de
a_bal (projeção horizontal medida do eixo do apoio). O extradorso continua a
água, de modo que a altura decresce até h_ponta = h0 − a_bal·tg α na ponta. O
vão 0 ≤ x ≤ L continua a ser o domínio de h(x) e das verificações; o balanço
entra na análise pelos momentos e reações que transmite aos apoios.
"""

from dataclasses import dataclass, field
import numpy as np
from numpy.typing import NDArray

from mlc_projeto.core.validacao import (
    exigir_inteiro_minimo,
    exigir_nao_negativo,
    exigir_no_intervalo,
    exigir_positivo,
)


@dataclass
class GeometriaViga:
    """
    Parâmetros geométricos de uma viga de duplo-bisel.

    Args:
        L         : Vão (m)
        h0        : Altura no apoio (m)
        alpha_deg : Ângulo de inclinação da cumeeira (graus)
        b         : Largura da seção transversal (m)
        n_pts     : Número de pontos ao longo do vão para integração
        a_bal     : Balanço do beiral além de cada apoio, projeção horizontal
                    a partir do eixo do apoio (m); 0 = viga sem beiral
    """
    L:         float
    h0:        float
    alpha_deg: float
    b:         float
    n_pts:     int = 100
    a_bal:     float = 0.0

    # Calculados automaticamente
    alpha_rad: float = field(init=False)
    h_ap:      float = field(init=False)
    x:         NDArray = field(init=False)

    def __post_init__(self) -> None:
        # ── Pré-condições de domínio (AUD-013) ────────────────────────────
        # Anteriores a qualquer verificação normativa: uma geometria com vão,
        # altura ou largura nula/negativa, ou com ângulo não finito, não
        # descreve uma estrutura e não pode gerar utilização nem aprovação.
        self.L  = exigir_positivo("L", self.L, unidade="m")
        self.h0 = exigir_positivo("h0", self.h0, unidade="m")
        self.b  = exigir_positivo("b", self.b, unidade="m")
        # tan(α) diverge em 90°; α<0 inverteria o bisel (h decrescente do apoio
        # para a cumeeira), fora da tipologia representada por esta classe.
        self.alpha_deg = exigir_no_intervalo(
            "alpha_deg", self.alpha_deg,
            minimo=0.0, maximo=90.0, incluir_maximo=False, unidade="graus",
        )
        # n_pts < 2 impede np.linspace de definir um intervalo e torna espúria
        # qualquer integração/varredura ao longo do vão.
        self.n_pts = exigir_inteiro_minimo("n_pts", self.n_pts, minimo=2)

        self.alpha_rad = np.radians(self.alpha_deg)
        self.h_ap = self.h0 + (self.L / 2) * np.tan(self.alpha_rad)
        self.x = np.linspace(0, self.L, self.n_pts)

        # Coerência do resultado derivado.
        exigir_positivo("h_ap (derivado de h0, L e alpha_deg)", self.h_ap, unidade="m")
        self.a_bal = exigir_nao_negativo("a_bal", self.a_bal, unidade="m")
        exigir_positivo("h_ponta (derivado de h0, a_bal e alpha_deg)",
                        self.h_ponta, unidade="m")

    @property
    def h_ponta(self) -> float:
        """Altura na ponta do balanço do beiral (m); = h0 sem beiral."""
        return float(self.h0 - self.a_bal * np.tan(self.alpha_rad))

    def h_balanco(self, u: float | NDArray) -> float | NDArray:
        """Altura no balanço à distância horizontal u do eixo do apoio (m)."""
        u = np.asarray(u, dtype=float)
        return self.h0 - u * np.tan(self.alpha_rad)

    def h(self, x: float | NDArray) -> float | NDArray:
        """
        Altura da seção em x (m).

        A viga de duplo-bisel tem h crescente do apoio até a cumeeira.
        Para 0 ≤ x ≤ L/2: h(x) = h0 + x·tan(α)
        Por simetria: h(x) = h(L-x) para L/2 < x ≤ L
        """
        x = np.asarray(x, dtype=float)
        x_sim = np.where(x <= self.L / 2, x, self.L - x)
        return self.h0 + x_sim * np.tan(self.alpha_rad)

    def A(self, x: float | NDArray) -> float | NDArray:
        """Área da seção transversal em x (m²)."""
        return self.b * self.h(x)

    def I(self, x: float | NDArray) -> float | NDArray:
        """Momento de inércia em torno do eixo y em x (m⁴)."""
        return self.b * self.h(x) ** 3 / 12

    def W(self, x: float | NDArray) -> float | NDArray:
        """Módulo resistente em x (m³)."""
        return self.b * self.h(x) ** 2 / 6

    def resumo(self) -> dict:
        """Retorna os parâmetros geométricos principais."""
        return {
            "L_m":        self.L,
            "h0_m":       self.h0,
            "h_ap_m":     self.h_ap,
            "alpha_deg":  self.alpha_deg,
            "b_m":        self.b,
            "a_bal_m":    self.a_bal,
            "h_ponta_m":  self.h_ponta,
            "L_h0":       self.L / self.h0,
            "h0_b":       self.h0 / self.b,
        }
