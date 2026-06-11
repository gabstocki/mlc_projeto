"""
core/loads.py — Carregamentos e combinações EN 1990.

Calcula diagramas de M(x), V(x) e monta combinações ELU/ELS.
Referência: EN 1990 §6.4 + EN 1991-1-1
"""

from dataclasses import dataclass
import numpy as np
from numpy.typing import NDArray

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial


@dataclass
class Carregamentos:
    """
    Carregamentos aplicados à viga.

    Args:
        geo  : Geometria da viga
        mat  : Material
        g_k  : Carga permanente característica (kN/m) — inclui PP estrutural
        q_k  : Sobrecarga de cobertura característica (kN/m)
        w_k  : Carga de vento característica (kN/m) — positivo = pressão
    """
    geo: GeometriaViga
    mat: GlulamMaterial
    g_k: float = 5.0    # kN/m — valor padrão para estimativa inicial
    q_k: float = 3.0    # kN/m
    w_k: float = 2.0    # kN/m

    # Coeficientes EN 1990 — Tabela A1.1
    gamma_G:  float = 1.35
    gamma_Q:  float = 1.50
    psi_0_q:  float = 0.70   # sobrecarga de cobertura
    psi_0_w:  float = 0.60   # vento
    psi_2_q:  float = 0.00

    def _momento_viga_bi_apoiada(
        self, q: float, x: NDArray
    ) -> NDArray:
        """M(x) para viga bi-apoiada com carga uniforme q (kN/m → kN·m)."""
        L = self.geo.L
        return q * x * (L - x) / 2  # kN·m

    def _cortante_viga_bi_apoiada(
        self, q: float, x: NDArray
    ) -> NDArray:
        """V(x) para viga bi-apoiada com carga uniforme q (kN/m → kN)."""
        L = self.geo.L
        return q * (L / 2 - x)  # kN

    # ── Combinação ELU fundamental (EN 1990 Eq. 6.10) ────────
    def q_ELU(self) -> float:
        """Carga de cálculo ELU (kN/m)."""
        return self.gamma_G * self.g_k + self.gamma_Q * self.q_k

    def M_ELU(self) -> NDArray:
        """Diagrama de momento fletor ELU (kN·m)."""
        return self._momento_viga_bi_apoiada(self.q_ELU(), self.geo.x)

    def V_ELU(self) -> NDArray:
        """Diagrama de esforço cortante ELU (kN)."""
        return self._cortante_viga_bi_apoiada(self.q_ELU(), self.geo.x)

    # ── Combinação ELS característica ─────────────────────────
    def q_ELS_car(self) -> float:
        """Carga de cálculo ELS característica (kN/m)."""
        return self.g_k + self.q_k

    def M_ELS_car(self) -> NDArray:
        """Diagrama de momento ELS característico (kN·m)."""
        return self._momento_viga_bi_apoiada(self.q_ELS_car(), self.geo.x)

    def M_g(self) -> NDArray:
        """Diagrama de momento — ação permanente apenas (kN·m)."""
        return self._momento_viga_bi_apoiada(self.g_k, self.geo.x)

    def M_q(self) -> NDArray:
        """Diagrama de momento — ação variável apenas (kN·m)."""
        return self._momento_viga_bi_apoiada(self.q_k, self.geo.x)

    def M_max_ELU(self) -> float:
        """Momento máximo de cálculo ELU (kN·m)."""
        return float(np.max(np.abs(self.M_ELU())))

    def V_max_ELU(self) -> float:
        """Cortante máximo de cálculo ELU (kN)."""
        return float(np.max(np.abs(self.V_ELU())))
