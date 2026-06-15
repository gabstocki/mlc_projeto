"""
core/loads.py — Carregamentos e combinações de ações.

Implementa todas as combinações ELU e ELS conforme EN 1990,
integradas com o vento calculado pela NBR 6123 (wind.py).

Coeficientes ψ — EN 1990 Tabela A1.1 (coberturas industriais):
    Sobrecarga cobertura Q: ψ₀=0,70 | ψ₁=0,50 | ψ₂=0,00
    Vento              W : ψ₀=0,60 | ψ₁=0,20 | ψ₂=0,00

Combinações ELU fundamentais (EN 1990 Eq. 6.10):
    C1: 1,35G + 1,5Q + 0,9W_C1bv   — Q dominante + vento C1 barlavento
    C2: 1,35G + 1,5W_C1bv + 1,05Q  — vento C1 barlavento dominante
    C3: 0,90G + 1,5W_C2st           — sucção C2 sotavento dominante
    C4: 1,35G + 1,5W_C2bv + 1,05Q  — vento C2 barlavento dominante

Combinações ELS (EN 1990 §6.5):
    S1: G + Q + 0,6W_C1bv           — característico
    S2: G + 0,5Q                    — frequente
    S3: G                           — quase-permanente (fluência)

Referência: EN 1990 §6.4, §6.5, Tabela A1.1
            ABNT NBR 6123 (vento via wind.py)
"""

from __future__ import annotations

from dataclasses import dataclass, field
import numpy as np
from numpy.typing import NDArray

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial


# ── Coeficientes EN 1990 — Tabela A1.1 ───────────────────────────────────────

# Coeficientes parciais ELU
GAMMA_G_sup = 1.35   # permanente desfavorável
GAMMA_G_inf = 0.90   # permanente favorável (sucção)
GAMMA_Q     = 1.50   # variável dominante
GAMMA_Q_red = 1.05   # variável acompanhante (ψ₀·γ_Q = 0,70×1,50)

# Coeficientes ψ
PSI_0_Q = 0.70   # sobrecarga cobertura
PSI_0_W = 0.60   # vento
PSI_1_Q = 0.50
PSI_1_W = 0.20
PSI_2_Q = 0.00
PSI_2_W = 0.00


# ── Dataclass de combinação ───────────────────────────────────────────────────

@dataclass
class Combinacao:
    """
    Uma combinação de ações com seus esforços resultantes.

    Attributes:
        nome       : Identificador da combinação
        tipo       : "ELU" ou "ELS"
        descricao  : Expressão da combinação
        q_tot      : Carga distribuída total resultante (kN/m)
                     Positivo = para baixo | Negativo = para cima (sucção)
        M_max_kNm  : Momento máximo (kN·m)
        V_max_kN   : Cortante máximo no apoio (kN)
        duracao    : Duração do carregamento dominante (para k_mod)
    """
    nome:       str
    tipo:       str
    descricao:  str
    q_tot:      float
    M_max_kNm:  float
    V_max_kN:   float
    duracao:    str


# ── Classe principal de carregamentos ────────────────────────────────────────

@dataclass
class Carregamentos:
    """
    Carregamentos e combinações de ações para a viga.

    Integra cargas permanentes, variáveis e vento (NBR 6123)
    com as combinações EN 1990 ELU e ELS.

    Args:
        geo           : Geometria da viga
        mat           : Material
        g_k           : Carga permanente característica (kN/m)
        q_k           : Sobrecarga característica (kN/m)
        w_C1bv_k      : Vento C1 barlavento — karga linear (kN/m), positivo=baixo
        w_C1st_k      : Vento C1 sotavento  — karga linear (kN/m)
        w_C2bv_k      : Vento C2 barlavento — karga linear (kN/m)
        w_C2st_k      : Vento C2 sotavento  — karga linear (kN/m), negativo=sucção
    """
    geo:       GeometriaViga
    mat:       GlulamMaterial
    g_k:       float = 8.625    # kN/m — permanente
    q_k:       float = 1.4375   # kN/m — sobrecarga cobertura
    # Cargas de vento lineares (kN/m) — do wind.py × dist_porticos
    # Positivo = empurra para baixo | Negativo = sucção (para cima)
    w_C1bv_k:  float = 0.0      # C1 barlavento
    w_C1st_k:  float = 0.0      # C1 sotavento
    w_C2bv_k:  float = 0.0      # C2 barlavento
    w_C2st_k:  float = 0.0      # C2 sotavento (sucção — negativo)

    # Calculado após init
    _combinacoes: dict = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        self._combinacoes = self._montar_combinacoes()

    # ── Diagrama de momento para carga uniforme ───────────────

    def _M(self, q: float) -> NDArray:
        """M(x) para viga bi-apoiada com carga uniforme q (kN/m → kN·m)."""
        x = self.geo.x
        return q * x * (self.geo.L - x) / 2

    def _V_max(self, q: float) -> float:
        """Cortante máximo no apoio (kN)."""
        return abs(q) * self.geo.L / 2

    def _M_max(self, q: float) -> float:
        """Momento máximo (kN·m)."""
        return abs(q) * self.geo.L**2 / 8

    # ── Montagem das combinações ──────────────────────────────

    def _montar_combinacoes(self) -> dict[str, Combinacao]:
        """
        Monta todas as combinações ELU e ELS conforme EN 1990.

        Para cada combinação calcula q_tot resultante e os esforços.
        """
        g  = self.g_k
        q  = self.q_k
        w1bv = self.w_C1bv_k   # C1 barlavento (positivo = para baixo)
        w1st = self.w_C1st_k   # C1 sotavento
        w2bv = self.w_C2bv_k   # C2 barlavento
        w2st = self.w_C2st_k   # C2 sotavento (negativo = sucção)
        L    = self.geo.L

        combinacoes = {}

        # ── ELU ───────────────────────────────────────────────

        # C1: Sobrecarga dominante + vento C1 acompanhante
        # 1,35G + 1,5Q + ψ₀·γ_Q·W_C1bv = 1,35G + 1,5Q + 0,9W
        q_C1 = GAMMA_G_sup*g + GAMMA_Q*q + PSI_0_W*GAMMA_Q*w1bv
        combinacoes["ELU_C1"] = Combinacao(
            nome      = "ELU_C1",
            tipo      = "ELU",
            descricao = "1,35G + 1,5Q + 0,9W_C1bv (Q dominante)",
            q_tot     = q_C1,
            M_max_kNm = self._M_max(q_C1),
            V_max_kN  = self._V_max(q_C1),
            duracao   = "longa",
        )

        # C2: Vento C1 barlavento dominante + sobrecarga acompanhante
        # 1,35G + 1,5W_C1bv + ψ₀·γ_Q·Q = 1,35G + 1,5W + 1,05Q
        q_C2 = GAMMA_G_sup*g + GAMMA_Q*w1bv + PSI_0_Q*GAMMA_Q*q
        combinacoes["ELU_C2"] = Combinacao(
            nome      = "ELU_C2",
            tipo      = "ELU",
            descricao = "1,35G + 1,5W_C1bv + 1,05Q (W_C1 dominante)",
            q_tot     = q_C2,
            M_max_kNm = self._M_max(q_C2),
            V_max_kN  = self._V_max(q_C2),
            duracao   = "curta",
        )

        # C3: Sucção dominante — mais desfavorável para instabilidade
        # 0,9G + 1,5W_C2st  (γ_G inferior pois G é favorável aqui)
        q_C3 = GAMMA_G_inf*g + GAMMA_Q*w2st
        combinacoes["ELU_C3"] = Combinacao(
            nome      = "ELU_C3",
            tipo      = "ELU",
            descricao = "0,9G + 1,5W_C2st (sucção dominante)",
            q_tot     = q_C3,
            M_max_kNm = self._M_max(q_C3),
            V_max_kN  = self._V_max(q_C3),
            duracao   = "curta",
        )

        # C4: Vento C2 barlavento dominante
        # 1,35G + 1,5W_C2bv + 1,05Q
        q_C4 = GAMMA_G_sup*g + GAMMA_Q*w2bv + PSI_0_Q*GAMMA_Q*q
        combinacoes["ELU_C4"] = Combinacao(
            nome      = "ELU_C4",
            tipo      = "ELU",
            descricao = "1,35G + 1,5W_C2bv + 1,05Q (W_C2 dominante)",
            q_tot     = q_C4,
            M_max_kNm = self._M_max(q_C4),
            V_max_kN  = self._V_max(q_C4),
            duracao   = "curta",
        )

        # ── ELS ───────────────────────────────────────────────

        # S1: Característico — flecha total
        q_S1 = g + q + PSI_0_W*w1bv
        combinacoes["ELS_S1"] = Combinacao(
            nome      = "ELS_S1",
            tipo      = "ELS",
            descricao = "G + Q + 0,6W_C1bv (característico)",
            q_tot     = q_S1,
            M_max_kNm = self._M_max(q_S1),
            V_max_kN  = self._V_max(q_S1),
            duracao   = "longa",
        )

        # S2: Frequente
        q_S2 = g + PSI_1_Q*q
        combinacoes["ELS_S2"] = Combinacao(
            nome      = "ELS_S2",
            tipo      = "ELS",
            descricao = "G + 0,5Q (frequente)",
            q_tot     = q_S2,
            M_max_kNm = self._M_max(q_S2),
            V_max_kN  = self._V_max(q_S2),
            duracao   = "longa",
        )

        # S3: Quase-permanente — base para fluência
        q_S3 = g + PSI_2_Q*q   # PSI_2_Q = 0 → só permanente
        combinacoes["ELS_S3"] = Combinacao(
            nome      = "ELS_S3",
            tipo      = "ELS",
            descricao = "G + 0,0Q (quase-permanente — fluência)",
            q_tot     = q_S3,
            M_max_kNm = self._M_max(q_S3),
            V_max_kN  = self._V_max(q_S3),
            duracao   = "permanente",
        )

        return combinacoes

    # ── Acesso às combinações ─────────────────────────────────

    @property
    def combinacoes(self) -> dict[str, Combinacao]:
        """Todas as combinações ELU e ELS."""
        return self._combinacoes

    def combinacoes_ELU(self) -> dict[str, Combinacao]:
        """Apenas combinações ELU."""
        return {k: v for k, v in self._combinacoes.items()
                if v.tipo == "ELU"}

    def combinacoes_ELS(self) -> dict[str, Combinacao]:
        """Apenas combinações ELS."""
        return {k: v for k, v in self._combinacoes.items()
                if v.tipo == "ELS"}

    def combinacao_ELU_governante(self) -> Combinacao:
        """
        Combinação ELU com maior M_max — governa flexão e cumeeira.

        Para verificações de compressão ou sucção, avaliar C3 separadamente.
        """
        return max(
            self.combinacoes_ELU().values(),
            key=lambda c: c.M_max_kNm
        )

    def combinacao_ELU_succao(self) -> Combinacao:
        """Combinação ELU de sucção — governa instabilidade lateral."""
        return self._combinacoes["ELU_C3"]

    # ── Compatibilidade com módulos existentes ────────────────
    # Mantém interface anterior para não quebrar os módulos de verificação

    def M_max_ELU(self) -> float:
        """Momento máximo ELU governante (kN·m)."""
        return self.combinacao_ELU_governante().M_max_kNm

    def V_max_ELU(self) -> float:
        """Cortante máximo ELU governante (kN)."""
        return self.combinacao_ELU_governante().V_max_kN

    def M_ELU(self) -> NDArray:
        """Diagrama M(x) da combinação ELU governante (kN·m)."""
        return self._M(self.combinacao_ELU_governante().q_tot)

    def V_ELU(self) -> NDArray:
        """Diagrama V(x) da combinação ELU governante (kN)."""
        q = self.combinacao_ELU_governante().q_tot
        return q * (self.geo.L / 2 - self.geo.x)

    def M_g(self) -> NDArray:
        """Diagrama M(x) — carga permanente apenas (kN·m)."""
        return self._M(self.g_k)

    def M_q(self) -> NDArray:
        """Diagrama M(x) — sobrecarga apenas (kN·m)."""
        return self._M(self.q_k)

    def M_ELS_car(self) -> NDArray:
        """Diagrama M(x) ELS característico (kN·m)."""
        return self._M(self._combinacoes["ELS_S1"].q_tot)

    # ── Relatório ─────────────────────────────────────────────

    def resumo(self) -> None:
        """Imprime resumo de todas as combinações."""
        print("=" * 72)
        print("  COMBINAÇÕES DE AÇÕES — EN 1990")
        print(f"  Vão L = {self.geo.L} m")
        print("=" * 72)
        print(f"\n  Cargas características:")
        print(f"    G  = {self.g_k:.4f} kN/m (permanente)")
        print(f"    Q  = {self.q_k:.4f} kN/m (sobrecarga)")
        print(f"    W_C1bv = {self.w_C1bv_k:+.4f} kN/m (vento C1 barlavento)")
        print(f"    W_C1st = {self.w_C1st_k:+.4f} kN/m (vento C1 sotavento)")
        print(f"    W_C2bv = {self.w_C2bv_k:+.4f} kN/m (vento C2 barlavento)")
        print(f"    W_C2st = {self.w_C2st_k:+.4f} kN/m (vento C2 sotavento)")

        print(f"\n  {'Comb.':<10} {'Tipo':<5} {'q_tot(kN/m)':>12} "
              f"{'M_max(kN·m)':>13} {'V_max(kN)':>11}  Descrição")
        print(f"  {'-'*68}")

        for nome, c in self._combinacoes.items():
            sinal = "↓" if c.q_tot >= 0 else "↑"
            print(
                f"  {nome:<10} {c.tipo:<5} {c.q_tot:>+11.3f}{sinal} "
                f"{c.M_max_kNm:>13.2f} {c.V_max_kN:>11.2f}  {c.descricao}"
            )

        gov = self.combinacao_ELU_governante()
        print(f"\n  ELU governante (maior M): {gov.nome} — "
              f"M = {gov.M_max_kNm:.2f} kN·m | "
              f"k_mod duração '{gov.duracao}'")
        print("=" * 72)


# ── Fábrica: integra wind.py → Carregamentos ─────────────────────────────────

def carregamentos_com_vento(
    geo:          GeometriaViga,
    mat:          GlulamMaterial,
    g_k_m2:       float,
    q_k_m2:       float,
    dist_portico: float,
    params_vento,               # ParametrosVento do wind.py
) -> Carregamentos:
    """
    Cria objeto Carregamentos integrando cargas de área com vento NBR 6123.

    Converte pressões de vento (kN/m²) em cargas lineares (kN/m)
    multiplicando pela distância entre pórticos.

    Args:
        geo          : Geometria da viga
        mat          : Material
        g_k_m2       : Carga permanente por área (kN/m²)
        q_k_m2       : Sobrecarga por área (kN/m²)
        dist_portico : Distância entre pórticos (m)
        params_vento : ParametrosVento (do wind.py)

    Returns:
        Carregamentos com todas as combinações EN 1990 + vento
    """
    from mlc_projeto.core.wind import calcular_vento

    res = calcular_vento(params_vento)

    # Cargas lineares (kN/m) = pressão (kN/m²) × distância (m)
    d = dist_portico

    return Carregamentos(
        geo      = geo,
        mat      = mat,
        g_k      = g_k_m2  * d,
        q_k      = q_k_m2  * d,
        w_C1bv_k = res.cargas["C1"]["barlavento_kNm"],
        w_C1st_k = res.cargas["C1"]["sotavento_kNm"],
        w_C2bv_k = res.cargas["C2"]["barlavento_kNm"],
        w_C2st_k = res.cargas["C2"]["sotavento_kNm"],
    )


# ── Execução direta ───────────────────────────────────────────────────────────

if __name__ == "__main__":

    from mlc_projeto.core.geometry  import GeometriaViga
    from mlc_projeto.core.materials import GlulamMaterial
    from mlc_projeto.core.wind      import ParametrosVento

    geo = GeometriaViga(L=20.25, h0=1.2, alpha_deg=5.0, b=0.28)
    mat = GlulamMaterial(classe="GL24h", classe_servico=2, duracao="longa")

    params_vento = ParametrosVento(
        V0=45.0, S1=1.0, categoria="IV", classe="B", S3=1.0,
        L=20.25, H1=1.0, h=7.0, dist_portico=5.75,
    )

    load = carregamentos_com_vento(
        geo          = geo,
        mat          = mat,
        g_k_m2       = 1.50,
        q_k_m2       = 0.25,
        dist_portico = 5.75,
        params_vento = params_vento,
    )

    load.resumo()

    # Mostrar combinação governante
    gov = load.combinacao_ELU_governante()
    suc = load.combinacao_ELU_succao()

    print(f"\n  Verificação de sucção:")
    print(f"  {suc.nome}: q = {suc.q_tot:+.3f} kN/m", end="")
    if suc.q_tot < 0:
        print(" ← CARGA RESULTANTE PARA CIMA — verificar ancoragem")
    else:
        print(" ← carga resultante para baixo")