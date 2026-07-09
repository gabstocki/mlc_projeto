"""
core/loads.py — Carregamentos e combinações EN 1990. v3

MUDANÇA v3 — Pórtico de três rótulas:
    Sistema estrutural: isostático com três rótulas
        - Rótulas nas bases dos pilares
        - Rótula na cumeeira
    
    Diagrama de momento correto para 3 rótulas (eixo centroidal):
        M(x) = R_v·x - H·y_c(x) - q·x²/2

    onde (intradorso horizontal, rótulas no centroide da secção):
        R_v  = q·L/2
        f_c  = (h_ap - h0)/2          (flecha do eixo entre rótulas)
        y_c(x) = x·tan(α)/2           (ordenada do centroide)
        H    = [R_v·(L/2) - q·(L/2)²/2] / f_c  = (q·L²/8) / f_c

    Consequências:
        - M na cumeeira = 0  (rótula)
        - M na base    = 0  (rótula)
        - M_max ocorre em x ≈ L/4 (não no meio do vão)
        - M_max ≈ 75% menor que pórtico rígido
        - Viga sujeita a M + N (flexo-compressão)
        - H vai direto para a fundação (sapata com chumbadores)

Combinações EN 1990 mantidas (inalteradas):
    ELU_C1: 1,35G + 1,5Q + 0,9W_C1bv
    ELU_C2: 1,35G + 1,5W_C1bv + 1,05Q  ← governante
    ELU_C3: 0,9G  + 1,5W_C2st
    ELU_C4: 1,35G + 1,5W_C2bv + 1,05Q
    ELS_S1: G + Q + 0,6W_C1bv
    ELS_S2: G + 0,5Q
    ELS_S3: G

Área tributária (pórtico intermédio): L_t = espaçamento entre pórticos.
    Pórtico de extremidade: usar fator_trib=0,5 (meia baia).

Referência: EN 1990 §6.4, §6.5
            Estática de pórtico de três rótulas (eixo centroidal)
"""

from __future__ import annotations

import math
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
    nome:        str
    tipo:        str
    descricao:   str
    q_tot:       float    # kN/m — carga distribuída total
    M_max_kNm:   float    # kN·m — momento máximo na viga
    V_max_kN:    float    # kN   — reação vertical R_v no apoio
    N_viga_kN:   float    # kN   — força normal no eixo da viga (apoio)
    V_viga_kN:   float    # kN   — cortante no eixo da viga (apoio)
    H_kN:        float    # kN   — empuxo horizontal na fundação
    x_Mmax_m:    float    # m    — posição do momento máximo
    duracao:     str


# ── Análise estrutural do pórtico de três rótulas ────────────────────────────

def analisar_3rotulas(
    q:     float,
    L:     float,
    h0:    float,
    h_ap:  float,
    alpha_rad: float,
    n_pts: int = 200,
) -> dict:
    """
    Analisa o pórtico de três rótulas com carga uniforme q.

    Sistema isostático: rótulas nas bases + rótula na cumeeira.
    Válido para pórtico simétrico de duas águas.

    Equações de equilíbrio (rótulas no centroide):
        ΣFy = 0 → R_v = q·L/2
        ΣM_cumeeira = 0 (meia viga):
            R_v·(L/2) - H·f_c - q·(L/2)²/2 = 0
            H = [R_v·(L/2) - q·(L/2)²/2] / f_c

    Hipótese geométrica (RM + pórtico de 3 rótulas):
        intradorso horizontal; rótulas no centroide da secção retangular
        → ordenada do eixo: y_c(x) = x·tan(α)/2
        → flecha entre rótulas: f_c = (h_ap - h0)/2

    Diagrama de momento (0 ≤ x ≤ L/2, simetria para x > L/2):
        M(x) = R_v·x - H·y_c(x) - q·x²/2

    Esforços no extremo da viga (apoio):
        N = H·cos(α) + R_v·sin(α)   (compressão no eixo)
        V = R_v·cos(α) - H·sin(α)   (cortante no eixo)

    Args:
        q         : Carga distribuída (kN/m) — positivo=para baixo
        L         : Vão total (m)
        h0        : Altura da seção no apoio (m)
        h_ap      : Altura da seção na cumeeira (m)
        alpha_rad : Ângulo de inclinação da face superior (rad)
        n_pts     : Número de pontos para integração

    Returns:
        dict com R_v, H, M_max, x_Mmax, N_apoio, V_apoio, M_x, x
    """
    if abs(q) < 1e-10:
        return {
            "R_v_kN":    0.0, "H_kN":      0.0,
            "M_max_kNm": 0.0, "x_Mmax_m":  0.0,
            "N_apoio_kN":0.0, "V_apoio_kN":0.0,
            "M_x":       np.zeros(n_pts),
            "x":         np.linspace(0, L, n_pts),
        }

    # Flecha do eixo centroidal (intradorso horizontal)
    f_c = (h_ap - h0) / 2.0

    if f_c <= 0:
        raise ValueError(
            f"h_ap={h_ap:.3f} deve ser maior que h0={h0:.3f} "
            f"para o pórtico de 3 rótulas. f_c={f_c:.3f} m"
        )

    # Reações
    R_v = q * L / 2
    H   = (R_v * (L / 2) - q * (L / 2) ** 2 / 2) / f_c

    # Diagrama de momento (meia viga por simetria)
    x_half = np.linspace(0, L / 2, n_pts // 2)
    y_c    = x_half * math.tan(alpha_rad) / 2.0  # centroide
    M_half = R_v * x_half - H * y_c - q * x_half ** 2 / 2

    # Espelhar para o vão completo
    M_x = np.concatenate([M_half, M_half[-2::-1]])
    x   = np.linspace(0, L, len(M_x))

    # Momento máximo
    idx_max  = np.argmax(np.abs(M_x))
    M_max    = float(M_x[idx_max])
    x_Mmax   = float(x[idx_max])

    # Ângulo do eixo centroidal (intradorso horizontal, bisel linear):
    # y_c(x) = x·tan(α)/2  →  θ = arctan(tan(α)/2)
    theta = math.atan(math.tan(alpha_rad) / 2.0)
    N_apoio = H * math.cos(theta) + R_v * math.sin(theta)
    V_apoio = R_v * math.cos(theta) - H * math.sin(theta)

    return {
        "R_v_kN":     round(R_v,     4),
        "H_kN":       round(H,       4),
        "M_max_kNm":  round(M_max,   4),
        "x_Mmax_m":   round(x_Mmax,  4),
        "N_apoio_kN": round(N_apoio, 4),
        "V_apoio_kN": round(V_apoio, 4),
        "f_c_m":      round(f_c,     4),
        "theta_rad":  round(theta,   6),
        "M_x":        M_x,
        "x":          x,
    }


# ── Classe principal de carregamentos ────────────────────────────────────────

@dataclass
class Carregamentos:
    """
    Carregamentos e combinações EN 1990 para pórtico de três rótulas.

    Área tributária:
        Pórtico intermédio: L_t (espaçamento entre pórticos)
        Pórtico de extremidade: L_t · fator_trib com fator_trib=0,5

    Args:
        geo          : Geometria da viga (fornece h0, h_ap, alpha_rad, L)
        mat          : Material
        g_area       : Carga permanente por área (kN/m²)
        q_area       : Sobrecarga por área (kN/m²)
        L_t          : Vão das terças = espaçamento entre pórticos (m)
        fator_trib   : 1,0 intermédio (padrão); 0,5 extremidade
        w_C1bv_m2    : Pressão vento C1 barlavento (kN/m²)
        w_C1st_m2    : Pressão vento C1 sotavento (kN/m²)
        w_C2bv_m2    : Pressão vento C2 barlavento (kN/m²)
        w_C2st_m2    : Pressão vento C2 sotavento (kN/m², negativo=sucção)
    """
    geo:        GeometriaViga
    mat:        GlulamMaterial
    g_area:     float = 1.50
    q_area:     float = 0.25
    L_t:        float = 5.75
    fator_trib: float = 1.0
    w_C1bv_m2:  float = 0.0
    w_C1st_m2:  float = 0.0
    w_C2bv_m2:  float = 0.0
    w_C2st_m2:  float = 0.0

    _combinacoes: dict = field(default_factory=dict, init=False, repr=False)
    _area_trib:   float = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.fator_trib not in (0.5, 1.0):
            raise ValueError(
                "fator_trib deve ser 1.0 (pórtico intermédio) "
                "ou 0.5 (pórtico de extremidade)."
            )
        self._area_trib = self.L_t * self.fator_trib
        self._combinacoes = self._montar_combinacoes()

    @property
    def area_trib(self) -> float:
        return self._area_trib

    # ── Cargas lineares ───────────────────────────────────────
    @property
    def g_k(self) -> float:
        return self.g_area * self._area_trib

    @property
    def q_k(self) -> float:
        return self.q_area * self._area_trib

    @property
    def w_C1bv_k(self) -> float:
        return self.w_C1bv_m2 * self._area_trib

    @property
    def w_C1st_k(self) -> float:
        return self.w_C1st_m2 * self._area_trib

    @property
    def w_C2bv_k(self) -> float:
        return self.w_C2bv_m2 * self._area_trib

    @property
    def w_C2st_k(self) -> float:
        return self.w_C2st_m2 * self._area_trib

    # ── Análise estrutural para uma carga q ──────────────────
    def _analisar(self, q: float) -> dict:
        return analisar_3rotulas(
            q         = q,
            L         = self.geo.L,
            h0        = self.geo.h0,
            h_ap      = self.geo.h_ap,
            alpha_rad = self.geo.alpha_rad,
        )

    # ── Montagem das combinações ──────────────────────────────
    def _montar_combinacoes(self) -> dict[str, Combinacao]:
        g    = self.g_k
        q    = self.q_k
        w1bv = self.w_C1bv_k
        w1st = self.w_C1st_k
        w2bv = self.w_C2bv_k
        w2st = self.w_C2st_k

        c = {}

        def _comb(nome, tipo, desc, q_tot, duracao):
            r = self._analisar(q_tot)
            return Combinacao(
                nome       = nome,
                tipo       = tipo,
                descricao  = desc,
                q_tot      = q_tot,
                M_max_kNm  = r["M_max_kNm"],
                V_max_kN   = r["R_v_kN"],
                N_viga_kN  = r["N_apoio_kN"],
                V_viga_kN  = r["V_apoio_kN"],
                H_kN       = r["H_kN"],
                x_Mmax_m   = r["x_Mmax_m"],
                duracao    = duracao,
            )

        # ELU
        c["ELU_C1"] = _comb(
            "ELU_C1", "ELU",
            "1,35G + 1,5Q + 0,9W_C1bv  (Q dominante)",
            GAMMA_G_sup*g + GAMMA_Q*q + PSI_0_W*GAMMA_Q*w1bv,
            "longa",
        )
        c["ELU_C2"] = _comb(
            "ELU_C2", "ELU",
            "1,35G + 1,5W_C1bv + 1,05Q  (W_C1 dominante) ← GOVERNA",
            GAMMA_G_sup*g + GAMMA_Q*w1bv + PSI_0_Q*GAMMA_Q*q,
            "curta",
        )
        c["ELU_C3"] = _comb(
            "ELU_C3", "ELU",
            "0,9G + 1,5W_C2st  (sucção dominante)",
            GAMMA_G_inf*g + GAMMA_Q*w2st,
            "curta",
        )
        c["ELU_C4"] = _comb(
            "ELU_C4", "ELU",
            "1,35G + 1,5W_C2bv + 1,05Q  (W_C2 dominante)",
            GAMMA_G_sup*g + GAMMA_Q*w2bv + PSI_0_Q*GAMMA_Q*q,
            "curta",
        )

        # ELS
        c["ELS_S1"] = _comb(
            "ELS_S1", "ELS",
            "G + Q + 0,6W_C1bv  (característico)",
            g + q + PSI_0_W*w1bv,
            "longa",
        )
        c["ELS_S2"] = _comb(
            "ELS_S2", "ELS",
            "G + 0,5Q  (frequente)",
            g + PSI_1_Q*q,
            "longa",
        )
        c["ELS_S3"] = _comb(
            "ELS_S3", "ELS",
            "G  (quase-permanente — fluência)",
            g + PSI_2_Q*q,
            "permanente",
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
        """Combinação ELU com maior M_max (carga positiva)."""
        return max(
            (c for c in self.combinacoes_ELU().values() if c.q_tot > 0),
            key=lambda c: c.M_max_kNm,
        )

    def combinacao_ELU_succao(self) -> Combinacao:
        return self._combinacoes["ELU_C3"]

    # ── Interface de compatibilidade com módulos existentes ──

    def M_max_ELU(self) -> float:
        return self.combinacao_ELU_governante().M_max_kNm

    def V_max_ELU(self) -> float:
        return self.combinacao_ELU_governante().V_max_kN

    def N_max_ELU(self) -> float:
        """Força normal no eixo da viga (apoio) — combinação ELU governante."""
        return self.combinacao_ELU_governante().N_viga_kN

    def V_viga_ELU(self) -> float:
        """Cortante no eixo da viga (apoio) — combinação ELU governante."""
        return self.combinacao_ELU_governante().V_viga_kN

    def H_ELU(self) -> float:
        """Empuxo horizontal na fundação — combinação ELU governante."""
        return self.combinacao_ELU_governante().H_kN

    def M_ELU(self) -> NDArray:
        """Diagrama M(x) da combinação ELU governante (kN·m)."""
        gov = self.combinacao_ELU_governante()
        r   = self._analisar(gov.q_tot)
        return r["M_x"]

    def V_ELU(self) -> NDArray:
        """Diagrama V(x) aproximado (kN)."""
        q = self.combinacao_ELU_governante().q_tot
        return q * (self.geo.L / 2 - self.geo.x)

    def M_g(self) -> NDArray:
        return self._analisar(self.g_k)["M_x"]

    def M_q(self) -> NDArray:
        return self._analisar(self.q_k)["M_x"]

    def M_ELS_car(self) -> NDArray:
        return self._analisar(
            self._combinacoes["ELS_S1"].q_tot
        )["M_x"]

    # ── Relatório ─────────────────────────────────────────────

    def resumo(self) -> None:
        """Imprime resumo de todas as combinações."""
        print("=" * 76)
        print("  COMBINAÇÕES DE AÇÕES — EN 1990 | Pórtico de 3 Rótulas v3")
        print(f"  L={self.geo.L}m | h0={self.geo.h0}m | "
              f"h_ap={self.geo.h_ap:.3f}m | "
              f"Área trib.={self._area_trib}m "
              f"(L_t×{self.fator_trib})")
        print("=" * 76)

        print(f"\n  Cargas lineares:")
        print(f"    G  = {self.g_k:.4f} kN/m | Q = {self.q_k:.4f} kN/m")
        print(f"    W_C1bv = {self.w_C1bv_k:+.4f} kN/m | "
              f"W_C2st = {self.w_C2st_k:+.4f} kN/m")

        print(f"\n  {'Comb.':<10} {'Tipo':<5} {'q(kN/m)':>10} "
              f"{'M_max(kN·m)':>12} {'V_max(kN)':>11} "
              f"{'N_viga(kN)':>11} {'H_fund(kN)':>11}  Duração")
        print(f"  {'-'*82}")

        for nome, c in self._combinacoes.items():
            print(
                f"  {nome:<10} {c.tipo:<5} {c.q_tot:>+9.3f}  "
                f"{c.M_max_kNm:>12.2f} {c.V_max_kN:>11.2f} "
                f"{c.N_viga_kN:>11.2f} {c.H_kN:>11.2f}  {c.duracao}"
            )

        gov = self.combinacao_ELU_governante()
        print(f"\n  ELU governante: {gov.nome}")
        print(f"    M_max = {gov.M_max_kNm:.2f} kN·m  "
              f"em x = {gov.x_Mmax_m:.3f} m")
        print(f"    V_max = {gov.V_max_kN:.2f} kN")
        print(f"    N_viga = {gov.N_viga_kN:.2f} kN  (flexo-compressão na viga)")
        print(f"    H_fund = {gov.H_kN:.2f} kN  (empuxo → sapata)")
        print("=" * 76)


# ── Fábrica com vento ─────────────────────────────────────────────────────────

def carregamentos_com_vento(
    geo:          GeometriaViga,
    mat:          GlulamMaterial,
    g_area:       float,
    q_area:       float,
    L_t:          float,
    params_vento,
) -> Carregamentos:
    """
    Cria Carregamentos integrando pressões de vento NBR 6123.

    Args:
        geo          : Geometria da viga
        mat          : Material
        g_area       : Carga permanente por área (kN/m²)
        q_area       : Sobrecarga por área (kN/m²)
        L_t          : Vão das terças (m)
        params_vento : ParametrosVento (wind.py)

    Returns:
        Carregamentos com combinações EN 1990 para pórtico de 3 rótulas
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

    # Confirmar redução do momento
    gov = load.combinacao_ELU_governante()
    print(f"\n  Comparação com pórtico rígido:")
    print(f"    M_max 3 rótulas = {gov.M_max_kNm:.2f} kN·m")
    print(f"    M_max rígido    = {gov.q_tot * 20.25**2 / 8:.2f} kN·m")
    print(f"    Redução         = "
          f"{(1 - gov.M_max_kNm/(gov.q_tot*20.25**2/8))*100:.1f}%")