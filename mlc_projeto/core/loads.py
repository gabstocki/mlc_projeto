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
from mlc_projeto.core.wind import ParametrosVento, calcular_vento, ResultadoVento


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
    vento: ResultadoVento | None = None

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

    def q_vento_C1(self) -> float:
        """
        Carga de vento de cálculo — Carregamento 1 barlavento (kN/m).
        Governa flexão positiva — empurra para baixo.
        """
        if self.vento is None:
            return 0.0
        return self.vento.cargas["C1"]["barlavento_kNm"]

    def q_vento_C2_sot(self) -> float:
        """
        Carga de vento de cálculo — Carregamento 2 sotavento (kN/m).
        Governa sucção — puxa para cima. Valor negativo.
        """
        if self.vento is None:
            return 0.0
        return self.vento.cargas["C2"]["sotavento_kNm"]

    def q_ELU_com_vento(self) -> float:
        """
        Combinação ELU com vento dominante (kN/m) — EN 1990 Eq. 6.10.

        1,35·G + 1,5·W + 1,05·Q
        Vento C1 barlavento — mais desfavorável para flexão positiva.
        """
        return (1.35 * self.g_k
                + 1.50 * self.q_vento_C1()
                + 1.05 * self.q_k)

    def q_ELU_succao(self) -> float:
        """
        Combinação ELU com sucção dominante (kN/m) — EN 1990 Eq. 6.10.

        0,9·G + 1,5·W_sucção
        Vento C2 sotavento — verifica instabilidade lateral e ancoragem.
        Valor pode ser negativo — carga resultante para cima.
        """
        return (0.9 * self.g_k
                + 1.50 * self.q_vento_C2_sot())
                
    def V_max_ELU(self) -> float:
        """Cortante máximo de cálculo ELU (kN)."""
        return float(np.max(np.abs(self.V_ELU())))
