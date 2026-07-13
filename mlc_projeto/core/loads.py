"""
core/loads.py — Carregamentos e combinações EN 1990. v4

MUDANÇA v4 — Viga biarticulada (peça monolítica de MLC):
    Peça única de secção variável (extradorso em duas águas, intradorso reto).
    Rótulas apenas nos apoios — NÃO há rótula na cumeeira (continuidade real).

    Grau de hiperestaticidade: 1 (empuxo H por compatibilidade).

    Eixo centroidal (intradorso horizontal):
        y_c(x) = x_sim · tan(α)/2
        f_c    = (h_ap − h0)/2
        I(x)   = b · h(x)³ / 12

    Sistema isostático auxiliar (H = 0):
        M_0(x) = (q/2) · x · (L − x)

    Momento real:
        M(x) = M_0(x) − H · y_c(x)

    Empuxo (Castigliano / força unitária, integração em dx — projecção horizontal):
        H = ∫ M_0 y_c / I dx  /  ∫ y_c² / I dx     (0 → L)

    Consequências:
        - M na cumeeira ≠ 0 em geral  → EC5 §6.4.3 activo
        - M na base = 0               → rótula de apoio
        - H tipicamente menor que no modelo triarticulado (fictício)

Combinações EN 1990 mantidas:
    ELU_C1…C4, ELS_S1…S3

Área tributária (pórtico intermédio): L_t; extremidade: fator_trib=0,5.

Referência: EN 1990 §6.4, §6.5
            Teoria da elasticidade — viga/arco biarticulado, secção variável
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
    nome:            str
    tipo:            str
    descricao:       str
    q_tot:           float    # kN/m — carga distribuída total
    M_max_kNm:       float    # kN·m — momento máximo na viga
    M_cumeeira_kNm:  float    # kN·m — momento na cumeeira (x=L/2)
    V_max_kN:        float    # kN   — reação vertical R_v no apoio
    N_viga_kN:       float    # kN   — força normal no eixo da viga (apoio)
    V_viga_kN:       float    # kN   — cortante no eixo da viga (apoio)
    H_kN:            float    # kN   — empuxo horizontal na fundação
    x_Mmax_m:        float    # m    — posição do momento máximo
    duracao:         str


# ── Análise estrutural — viga biarticulada (MLC monolítica) ───────────────────

def analisar_biarticulada(
    q:         float,
    L:         float,
    h0:        float,
    h_ap:      float,
    alpha_rad: float,
    b:         float,
    n_pts:     int = 401,
) -> dict:
    """
    Viga de secção variável biarticulada (rótulas só nos apoios).

    Peça monolítica de MLC — continuidade na cumeeira (sem rótula).
    Uma vez hiperestática: H por compatibilidade (projecção horizontal dx).

        M_0(x) = (q/2)·x·(L−x)
        M(x)   = M_0(x) − H·y_c(x)
        H = ∫ M_0 y_c / I dx  /  ∫ y_c² / I dx

    y_c, I no eixo centroidal (intradorso horizontal).
    """
    x = np.linspace(0.0, L, n_pts)

    if abs(q) < 1e-10:
        return {
            "R_v_kN": 0.0, "H_kN": 0.0,
            "M_max_kNm": 0.0, "M_cumeeira_kNm": 0.0,
            "x_Mmax_m": 0.0,
            "N_apoio_kN": 0.0, "V_apoio_kN": 0.0,
            "f_c_m": (h_ap - h0) / 2.0,
            "theta_rad": math.atan(math.tan(alpha_rad) / 2.0),
            "sistema": "biarticulada",
            "M_x": np.zeros(n_pts),
            "M0_x": np.zeros(n_pts),
            "y_c": np.zeros(n_pts),
            "x": x,
        }

    f_c = (h_ap - h0) / 2.0
    if f_c <= 0 or b <= 0:
        raise ValueError(
            f"Geometria inválida para biarticulada: "
            f"h_ap={h_ap:.3f}, h0={h0:.3f}, b={b:.3f}"
        )

    tan_a = math.tan(alpha_rad)
    x_sim = np.where(x <= L / 2.0, x, L - x)
    y_c   = x_sim * tan_a / 2.0
    h_x   = h0 + x_sim * tan_a
    I_x   = b * h_x ** 3 / 12.0

    # Evitar divisão por zero numérica (I sempre > 0 se h0>0)
    I_x = np.maximum(I_x, 1e-18)

    M0 = 0.5 * q * x * (L - x)

    num = float(np.trapezoid(M0 * y_c / I_x, x))
    den = float(np.trapezoid(y_c ** 2 / I_x, x))
    if den <= 0:
        raise ValueError("Integral ∫ y_c²/I dx nula — verificar geometria.")
    H = num / den

    M_x = M0 - H * y_c

    R_v = q * L / 2.0
    idx_max = int(np.argmax(np.abs(M_x)))
    M_max   = float(M_x[idx_max])
    x_Mmax  = float(x[idx_max])
    M_cum   = float(np.interp(L / 2.0, x, M_x))

    theta   = math.atan(tan_a / 2.0)
    N_apoio = H * math.cos(theta) + R_v * math.sin(theta)
    V_apoio = R_v * math.cos(theta) - H * math.sin(theta)

    return {
        "R_v_kN":          round(R_v, 4),
        "H_kN":            round(H, 4),
        "M_max_kNm":       round(M_max, 4),
        "M_cumeeira_kNm":  round(M_cum, 4),
        "x_Mmax_m":        round(x_Mmax, 4),
        "N_apoio_kN":      round(N_apoio, 4),
        "V_apoio_kN":      round(V_apoio, 4),
        "f_c_m":           round(f_c, 4),
        "theta_rad":       round(theta, 6),
        "sistema":         "biarticulada",
        "M_x":             M_x,
        "M0_x":            M0,
        "y_c":             y_c,
        "x":               x,
    }


def analisar_3rotulas(
    q:     float,
    L:     float,
    h0:    float,
    h_ap:  float,
    alpha_rad: float,
    n_pts: int = 200,
    b:     float | None = None,
) -> dict:
    """
    LEGADO — pórtico triarticulado (rótula fictícia na cumeeira).

    Mantido só para comparação. O pipeline de projeto usa
    ``analisar_biarticulada``. Se ``b`` for fornecido, ignora-se (API).
    """
    f_c = (h_ap - h0) / 2.0
    if abs(q) < 1e-10:
        return {
            "R_v_kN": 0.0, "H_kN": 0.0,
            "M_max_kNm": 0.0, "M_cumeeira_kNm": 0.0,
            "x_Mmax_m": 0.0,
            "N_apoio_kN": 0.0, "V_apoio_kN": 0.0,
            "f_c_m": f_c, "sistema": "3rotulas_legado",
            "M_x": np.zeros(n_pts),
            "x": np.linspace(0, L, n_pts),
        }
    if f_c <= 0:
        raise ValueError(f"h_ap={h_ap:.3f} deve ser > h0={h0:.3f}")

    R_v = q * L / 2
    H   = (R_v * (L / 2) - q * (L / 2) ** 2 / 2) / f_c
    x_half = np.linspace(0, L / 2, n_pts // 2)
    y_c    = x_half * math.tan(alpha_rad) / 2.0
    M_half = R_v * x_half - H * y_c - q * x_half ** 2 / 2
    M_x = np.concatenate([M_half, M_half[-2::-1]])
    x   = np.linspace(0, L, len(M_x))
    idx_max = int(np.argmax(np.abs(M_x)))
    theta = math.atan(math.tan(alpha_rad) / 2.0)
    return {
        "R_v_kN":         round(R_v, 4),
        "H_kN":           round(H, 4),
        "M_max_kNm":      round(float(M_x[idx_max]), 4),
        "M_cumeeira_kNm": 0.0,
        "x_Mmax_m":       round(float(x[idx_max]), 4),
        "N_apoio_kN":     round(H * math.cos(theta) + R_v * math.sin(theta), 4),
        "V_apoio_kN":     round(R_v * math.cos(theta) - H * math.sin(theta), 4),
        "f_c_m":          round(f_c, 4),
        "theta_rad":      round(theta, 6),
        "sistema":        "3rotulas_legado",
        "M_x":            M_x,
        "x":              x,
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
        """Viga biarticulada monolítica — sem rótula na cumeeira."""
        return analisar_biarticulada(
            q         = q,
            L         = self.geo.L,
            h0        = self.geo.h0,
            h_ap      = self.geo.h_ap,
            alpha_rad = self.geo.alpha_rad,
            b         = self.geo.b,
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
                nome            = nome,
                tipo            = tipo,
                descricao       = desc,
                q_tot           = q_tot,
                M_max_kNm       = r["M_max_kNm"],
                M_cumeeira_kNm  = r["M_cumeeira_kNm"],
                V_max_kN        = r["R_v_kN"],
                N_viga_kN       = r["N_apoio_kN"],
                V_viga_kN       = r["V_apoio_kN"],
                H_kN            = r["H_kN"],
                x_Mmax_m        = r["x_Mmax_m"],
                duracao         = duracao,
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
        """
        Combinação ELU governante: maior |M_max| entre combinações
        com carga vertical de sentido gravítico (q_tot > 0).
        """
        cands = [c for c in self.combinacoes_ELU().values() if c.q_tot > 0]
        if not cands:
            # fallback: maior |M| entre todas as ELU
            cands = list(self.combinacoes_ELU().values())
        return max(cands, key=lambda c: abs(c.M_max_kNm))

    def combinacao_ELU_succao(self) -> Combinacao:
        return self._combinacoes["ELU_C3"]

    # ── Interface de compatibilidade com módulos existentes ──

    def M_max_ELU(self) -> float:
        return self.combinacao_ELU_governante().M_max_kNm

    def M_cumeeira_ELU(self) -> float:
        """Momento na cumeeira (x=L/2) — biarticulada, em geral ≠ 0."""
        return self.combinacao_ELU_governante().M_cumeeira_kNm

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
        print("  COMBINAÇÕES DE AÇÕES — EN 1990 | Viga biarticulada MLC v4")
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
              f"{'M_max':>10} {'M_cum':>10} {'V':>9} "
              f"{'N':>10} {'H':>10}  Dur.")
        print(f"  {'-'*88}")

        for nome, c in self._combinacoes.items():
            print(
                f"  {nome:<10} {c.tipo:<5} {c.q_tot:>+9.3f}  "
                f"{c.M_max_kNm:>10.2f} {c.M_cumeeira_kNm:>10.2f} "
                f"{c.V_max_kN:>9.2f} {c.N_viga_kN:>10.2f} "
                f"{c.H_kN:>10.2f}  {c.duracao}"
            )

        gov = self.combinacao_ELU_governante()
        print(f"\n  ELU governante: {gov.nome} | sistema biarticulado")
        print(f"    M_max = {gov.M_max_kNm:.2f} kN·m  "
              f"em x = {gov.x_Mmax_m:.3f} m")
        print(f"    M_cumeeira = {gov.M_cumeeira_kNm:.2f} kN·m  "
              f"(§6.4.3 — continuidade MLC)")
        print(f"    V_max = {gov.V_max_kN:.2f} kN")
        print(f"    N_viga = {gov.N_viga_kN:.2f} kN")
        print(f"    H_fund = {gov.H_kN:.2f} kN  (empuxo por compatibilidade)")
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
    mat = GlulamMaterial(classe="GL24h", classe_servico=3, duracao="longa")

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