"""
core/geometry.py — Geometria paramétrica da viga de duplo-bisel.

Calcula h(x), A(x), I(x) e W(x) para n pontos ao longo do vão.
"""

from dataclasses import dataclass, field
import numpy as np
from numpy.typing import NDArray


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
    """
    L:         float
    h0:        float
    alpha_deg: float
    b:         float
    n_pts:     int = 100

    # Calculados automaticamente
    alpha_rad: float = field(init=False)
    h_ap:      float = field(init=False)
    x:         NDArray = field(init=False)

    def __post_init__(self) -> None:
        self.alpha_rad = np.radians(self.alpha_deg)
        self.h_ap = self.h0 + (self.L / 2) * np.tan(self.alpha_rad)
        self.x = np.linspace(0, self.L, self.n_pts)

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
            "L_h0":       self.L / self.h0,
            "h0_b":       self.h0 / self.b,
        }
