"""
core/loads.py — Carregamentos e combinações de ações. v2

CORREÇÃO v2:
    Área tributária da viga principal = L_t/2
    (metade do vão das terças — cada pórtico recebe metade da carga)

    Cada terça é biapoiada nos dois pórticos.
    Por metro de viga: q = g_area × L_t/2

Combinações EN 1990 completas:

    ELU_C1: 1,35G + 1,5Q + 0,9W_C1bv   — Q dominante
    ELU_C2: 1,35G + 1,5W_C1bv + 1,05Q  — W_C1 dominante ← GOVERNANTE
    ELU_C3: 0,9G  + 1,5W_C2st           — sucção dominante
    ELU_C4: 1,35G + 1,5W_C2bv + 1,05Q  — W_C2 dominante

    ELS_S1: G + Q + 0,6W_C1bv           — característico
    ELS_S2: G + 0,5Q                    — frequente
    ELS_S3: G                           — quase-permanente (fluência)

Coeficientes ψ — EN 1990 Tab. A1.1 (coberturas industriais):
    Q (sobrecarga cobertura): ψ₀=0,70 | ψ₁=0,50 | ψ₂=0,00
    W (vento):                ψ₀=0,60 | ψ₁=0,20 | ψ₂=0,00

Referência: EN 1990 §6.4, §6.5, Tab. A1.1
"""

from __future__ import annotations

from dataclasses import dataclass, field
import numpy as np
from numpy.typing import NDArray

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial


# ── Coeficientes EN 1990 ─────────────────────────────────────────────────────

GAMMA_G_sup = 1.35
GAMMA_G_inf = 0.90
GAMMA_Q     = 1.50
PSI_0_Q     = 0.70
PSI_0_W     = 0.60
PSI_1_Q     = 0.50
PSI_2_Q     = 0.00
PSI_2_W     = 0.00


# ── Dataclass de combinação ───────────────────────────────────────────────────

@dataclass
class Combinacao:
    """Uma combinação de ações com esforços resultantes."""
    nome:       str
    tipo:       str
    descricao:  str
    q_tot:      float   # kN/m — positivo=baixo, negativo=cima
    M_max_kNm:  float
    V_max_kN:   float
    duracao:    str


# ── Classe principal ──────────────────────────────────────────────────────────

@dataclass
class Carregamentos:
    """
    Carregamentos e combinações EN 1990 para a viga principal.

    ÁREA TRIBUTÁRIA CORRETA: L_t/2
    Cada pórtico recebe metade da carga de cada terça biapoiada.
    Por metro de viga: q = pressão × L_t/2

    Args:
        geo          : Geometria da viga
        mat          : Material
        g_area       : Carga permanente por área (kN/m²)
        q_area       : Sobrecarga por área (kN/m²)
        L_t          : Vão das terças = espaçamento entre pórticos (m)
        w_C1bv_m2    : Pressão vento C1 barlavento (kN/m²)
        w_C1st_m2    : Pressão vento C1 sotavento (kN/m²)
        w_C2bv_m2    : Pressão vento C2 barlavento (kN/m²)
        w_C2st_m2    : Pressão vento C2 sotavento (kN/m², negativo=sucção)
    """
    geo:       GeometriaViga
    mat:       GlulamMaterial
    g_area:    float = 1.50    # kN/m²
    q_area:    float = 0.25    # kN/m²
    L_t:       float = 5.75    # m
    w_C1bv_m2: float = 0.0     # kN/m²
    w_C1st_m2: float = 0.0
    w_C2bv_m2: float = 0.0
    w_C2st_m2: float = 0.0     # negativo = sucção

    _combinacoes: dict = field(default_factory=dict, init=False, repr=False)
    _area_trib:   float = field(init=False, repr=False)

    def __post_init__(self) -> None:
        # Área tributária correta = L_t/2
        self._area_trib = self.L_t / 2
        self._combinacoes = self._montar_combinacoes()

    @property
    def area_trib(self) -> float:
        """Área tributária por metro de viga (m) = L_t/2."""
        return self._area_trib

    # ── Cargas lineares na viga ───────────────────────────────

    @property
    def g_k(self) -> float:
        """Carga permanente linear (kN/m) = g_area × L_t/2."""
        return self.g_area * self._area_trib

    @property
    def q_k(self) -> float:
        """Sobrecarga linear (kN/m) = q_area × L_t/2."""
        return self.q_area * self._area_trib

    @property
    def w_C1bv_k(self) -> float:
        """Vento C1 barlavento linear (kN/m)."""
        return self.w_C1bv_m2 * self._area_trib

    @property
    def w_C1st_k(self) -> float:
        """Vento C1 sotavento linear (kN/m)."""
        return self.w_C1st_m2 * self._area_trib

    @property
    def w_C2bv_k(self) -> float:
        """Vento C2 barlavento linear (kN/m)."""
        return self.w_C2bv_m2 * self._area_trib

    @property
    def w_C2st_k(self) -> float:
        """Vento C2 sotavento linear (kN/m)."""
        return self.w_C2st_m2 * self._area_trib

    # ── Diagramas de momento ──────────────────────────────────

    def _M(self, q: float) -> NDArray:
        """M(x) bi-apoiada carga uniforme q (kN/m → kN·m)."""
        x = self.geo.x
        return q * x * (self.geo.L - x) / 2

    def _M_max(self, q: float) -> float:
        """Momento máximo (kN·m)."""
        return abs(q) * self.geo.L**2 / 8

    def _V_max(self, q: float) -> float:
        """Cortante máximo (kN)."""
        return abs(q) * self.geo.L / 2

    # ── Montagem das combinações EN 1990 ──────────────────────

    def _montar_combinacoes(self) -> dict[str, Combinacao]:
        g   = self.g_k
        q   = self.q_k
        w1bv = self.w_C1bv_k
        w1st = self.w_C1st_k
        w2bv = self.w_C2bv_k
        w2st = self.w_C2st_k

        c = {}

        # ── ELU ───────────────────────────────────────────────

        # C1: Q dominante + vento acompanhante
        q_C1 = GAMMA_G_sup*g + GAMMA_Q*q + PSI_0_W*GAMMA_Q*w1bv
        c["ELU_C1"] = Combinacao(
            nome="ELU_C1", tipo="ELU",
            descricao="1,35G + 1,5Q + 0,9W_C1bv  (Q dominante)",
            q_tot=q_C1, M_max_kNm=self._M_max(q_C1),
            V_max_kN=self._V_max(q_C1), duracao="longa",
        )

        # C2: Vento C1 barlavento dominante ← GOVERNA
        q_C2 = GAMMA_G_sup*g + GAMMA_Q*w1bv + PSI_0_Q*GAMMA_Q*q
        c["ELU_C2"] = Combinacao(
            nome="ELU_C2", tipo="ELU",
            descricao="1,35G + 1,5W_C1bv + 1,05Q  (W_C1 dominante)",
            q_tot=q_C2, M_max_kNm=self._M_max(q_C2),
            V_max_kN=self._V_max(q_C2), duracao="curta",
        )

        # C3: Sucção dominante
        q_C3 = GAMMA_G_inf*g + GAMMA_Q*w2st
        c["ELU_C3"] = Combinacao(
            nome="ELU_C3", tipo="ELU",
            descricao="0,9G + 1,5W_C2st  (sucção dominante)",
            q_tot=q_C3, M_max_kNm=self._M_max(q_C3),
            V_max_kN=self._V_max(q_C3), duracao="curta",
        )

        # C4: Vento C2 barlavento dominante
        q_C4 = GAMMA_G_sup*g + GAMMA_Q*w2bv + PSI_0_Q*GAMMA_Q*q
        c["ELU_C4"] = Combinacao(
            nome="ELU_C4", tipo="ELU",
            descricao="1,35G + 1,5W_C2bv + 1,05Q  (W_C2 dominante)",
            q_tot=q_C4, M_max_kNm=self._M_max(q_C4),
            V_max_kN=self._V_max(q_C4), duracao="curta",
        )

        # ── ELS ───────────────────────────────────────────────

        q_S1 = g + q + PSI_0_W*w1bv
        c["ELS_S1"] = Combinacao(
            nome="ELS_S1", tipo="ELS",
            descricao="G + Q + 0,6W_C1bv  (característico)",
            q_tot=q_S1, M_max_kNm=self._M_max(q_S1),
            V_max_kN=self._V_max(q_S1), duracao="longa",
        )

        q_S2 = g + PSI_1_Q*q
        c["ELS_S2"] = Combinacao(
            nome="ELS_S2", tipo="ELS",
            descricao="G + 0,5Q  (frequente)",
            q_tot=q_S2, M_max_kNm=self._M_max(q_S2),
            V_max_kN=self._V_max(q_S2), duracao="longa",
        )

        q_S3 = g + PSI_2_Q*q   # PSI_2_Q = 0 → só permanente
        c["ELS_S3"] = Combinacao(
            nome="ELS_S3", tipo="ELS",
            descricao="G  (quase-permanente — fluência)",
            q_tot=q_S3, M_max_kNm=self._M_max(q_S3),
            V_max_kN=self._V_max(q_S3), duracao="permanente",
        )

        return c

    # ── Acesso ───────────────────────────────────────────────

    @property
    def combinacoes(self) -> dict[str, Combinacao]:
        return self._combinacoes

    def combinacoes_ELU(self) -> dict[str, Combinacao]:
        return {k: v for k, v in self._combinacoes.items()
                if v.tipo == "ELU"}

    def combinacoes_ELS(self) -> dict[str, Combinacao]:
        return {k: v for k, v in self._combinacoes.items()
                if v.tipo == "ELS"}

    def combinacao_ELU_governante(self) -> Combinacao:
        """Combinação ELU com maior M_max (positivo)."""
        return max(
            (c for c in self.combinacoes_ELU().values() if c.q_tot > 0),
            key=lambda c: c.M_max_kNm
        )

    def combinacao_ELU_succao(self) -> Combinacao:
        """Combinação ELU de sucção."""
        return self._combinacoes["ELU_C3"]

    # ── Interface de compatibilidade ──────────────────────────

    def M_max_ELU(self) -> float:
        return self.combinacao_ELU_governante().M_max_kNm

    def V_max_ELU(self) -> float:
        return self.combinacao_ELU_governante().V_max_kN

    def M_ELU(self) -> NDArray:
        return self._M(self.combinacao_ELU_governante().q_tot)

    def V_ELU(self) -> NDArray:
        q = self.combinacao_ELU_governante().q_tot
        return q * (self.geo.L / 2 - self.geo.x)

    def M_g(self) -> NDArray:
        return self._M(self.g_k)

    def M_q(self) -> NDArray:
        return self._M(self.q_k)

    def M_ELS_car(self) -> NDArray:
        return self._M(self._combinacoes["ELS_S1"].q_tot)

    # ── Relatório ─────────────────────────────────────────────

    def resumo(self) -> None:
        print("=" * 74)
        print("  COMBINAÇÕES DE AÇÕES — EN 1990  (v2 — área tributária corrigida)")
        print(f"  Vão viga L_v = {self.geo.L} m | "
              f"Vão terças L_t = {self.L_t} m | "
              f"Área trib. = L_t/2 = {self._area_trib} m")
        print("=" * 74)

        print(f"\n  Cargas lineares na viga principal:")
        print(f"    G  = {self.g_k:.4f} kN/m  "
              f"(= {self.g_area} kN/m² × {self._area_trib} m)")
        print(f"    Q  = {self.q_k:.4f} kN/m  "
              f"(= {self.q_area} kN/m² × {self._area_trib} m)")
        print(f"    W_C1bv = {self.w_C1bv_k:+.4f} kN/m")
        print(f"    W_C1st = {self.w_C1st_k:+.4f} kN/m")
        print(f"    W_C2bv = {self.w_C2bv_k:+.4f} kN/m")
        print(f"    W_C2st = {self.w_C2st_k:+.4f} kN/m")

        print(f"\n  {'Comb.':<10} {'Tipo':<5} {'q_tot(kN/m)':>12} "
              f"{'M_max(kN·m)':>13} {'V_max(kN)':>11}  Descrição")
        print(f"  {'-'*72}")

        for nome, c in self._combinacoes.items():
            sinal = "↓" if c.q_tot >= 0 else "↑"
            print(
                f"  {nome:<10} {c.tipo:<5} {c.q_tot:>+11.4f}{sinal} "
                f"{c.M_max_kNm:>13.2f} {c.V_max_kN:>11.2f}  {c.descricao}"
            )

        gov = self.combinacao_ELU_governante()
        suc = self.combinacao_ELU_succao()
        print(f"\n  ELU governante: {gov.nome} — "
              f"M = {gov.M_max_kNm:.2f} kN·m | "
              f"k_mod duração '{gov.duracao}'")
        print(f"  Sucção ELU_C3: q = {suc.q_tot:+.4f} kN/m "
              f"{'← para cima' if suc.q_tot < 0 else '← ainda para baixo'}")
        print("=" * 74)


# ── Fábrica: integra wind.py → Carregamentos ─────────────────────────────────

def carregamentos_com_vento(
    geo:          GeometriaViga,
    mat:          GlulamMaterial,
    g_area:       float,
    q_area:       float,
    L_t:          float,
    params_vento,
) -> "Carregamentos":
    """
    Cria Carregamentos integrando pressões de vento NBR 6123.

    Converte pressões (kN/m²) para cargas lineares via área tributária L_t/2.

    Args:
        geo          : Geometria da viga
        mat          : Material
        g_area       : Carga permanente por área (kN/m²)
        q_area       : Sobrecarga por área (kN/m²)
        L_t          : Vão das terças (m)
        params_vento : ParametrosVento (wind.py)

    Returns:
        Carregamentos com todas as combinações EN 1990
    """
    from mlc_projeto.core.wind import calcular_vento
    res = calcular_vento(params_vento)

    return Carregamentos(
        geo       = geo,
        mat       = mat,
        g_area    = g_area,
        q_area    = q_area,
        L_t       = L_t,
        w_C1bv_m2 = res.pressoes["C1"]["barlavento_kNm2"],
        w_C1st_m2 = res.pressoes["C1"]["sotavento_kNm2"],
        w_C2bv_m2 = res.pressoes["C2"]["barlavento_kNm2"],
        w_C2st_m2 = res.pressoes["C2"]["sotavento_kNm2"],
    )


# ── Execução direta ───────────────────────────────────────────────────────────

if __name__ == "__main__":

    from mlc_projeto.core.geometry  import GeometriaViga
    from mlc_projeto.core.materials import GlulamMaterial
    from mlc_projeto.core.wind      import ParametrosVento

    geo = GeometriaViga(L=20.25, h0=0.60, alpha_deg=4.5, b=0.26)
    mat = GlulamMaterial(classe="GL24h", classe_servico=2, duracao="longa")

    params_vento = ParametrosVento(
        V0=45.0, S1=1.0, categoria="IV", classe="B", S3=1.0,
        L=20.25, H1=1.0, h=7.0, dist_portico=5.75,
    )

    load = carregamentos_com_vento(
        geo=geo, mat=mat,
        g_area=1.50, q_area=0.25,
        L_t=5.75,
        params_vento=params_vento,
    )

    load.resumo()