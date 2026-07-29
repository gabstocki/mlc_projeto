"""
core/loads.py — Carregamentos e combinações EN 1990. v4

MUDANÇA v4 — Viga biarticulada (peça monolítica de MLC):
    Peça única de seção variável (extradorso em duas águas, intradorso reto).
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

    Empuxo (Castigliano / força unitária, integração em dx — projeção horizontal):
        H = ∫ M_0 y_c / I dx  /  ∫ y_c² / I dx     (0 → L)

    Consequências:
        - M na cumeeira ≠ 0 em geral  → EC5 §6.4.3 ativo
        - M na base = 0               → rótula de apoio
        - H tipicamente menor que no modelo triarticulado (fictício)

Combinações EN 1990 mantidas:
    ELU_C1…C4, ELS_S1…S3

Área tributária (pórtico intermediário): L_t; extremidade: fator_trib=0,5.

Referência: EN 1990 §6.4, §6.5
            Teoria da elasticidade — viga/arco biarticulado, seção variável
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
    q_tot:           float    # kN/m — carga média (ou uniforme)
    M_max_kNm:       float    # kN·m — momento máximo na viga
    M_cumeeira_kNm:  float    # kN·m — momento na cumeeira (x=L/2)
    V_max_kN:        float    # kN   — reação vertical governante no apoio
    N_viga_kN:       float    # kN   — força normal no eixo da viga (apoio)
    V_viga_kN:       float    # kN   — cortante no eixo da viga (apoio)
    H_kN:            float    # kN   — empuxo horizontal na fundação
    x_Mmax_m:        float    # m    — posição do momento máximo
    duracao:         str
    q_esq:           float = 0.0   # kN/m — meia-água esquerda
    q_dir:           float = 0.0   # kN/m — meia-água direita
    padrao_vento:    str = ""      # id do padrão Tab.25 (se aplicável)


# ── Análise estrutural — viga biarticulada (MLC monolítica) ───────────────────

def _M0_carga_assimetrica(
    x: NDArray,
    L: float,
    q_esq: float,
    q_dir: float,
) -> tuple[NDArray, float, float]:
    """
    Momento isostático M0 e reações verticais — carga uniforme por meia-água.

        q_esq em [0, L/2],  q_dir em [L/2, L]

        R_A = (3·q_esq + q_dir)·L/8
        R_B = (q_esq + 3·q_dir)·L/8
    """
    half = L / 2.0
    R_A = (3.0 * q_esq + q_dir) * L / 8.0
    R_B = (q_esq + 3.0 * q_dir) * L / 8.0

    M0 = np.zeros_like(x)
    for i, xi in enumerate(x):
        if xi <= half:
            M0[i] = R_A * xi - q_esq * xi ** 2 / 2.0
        else:
            # M = R_A·x − q_esq·(L/2)·(x − L/4) − q_dir·(x−L/2)²/2
            M0[i] = (
                R_A * xi
                - q_esq * half * (xi - L / 4.0)
                - q_dir * (xi - half) ** 2 / 2.0
            )
    return M0, R_A, R_B


def analisar_biarticulada(
    q:         float,
    L:         float,
    h0:        float,
    h_ap:      float,
    alpha_rad: float,
    b:         float,
    n_pts:     int = 401,
    q_esq:     float | None = None,
    q_dir:     float | None = None,
) -> dict:
    """
    Viga de seção variável biarticulada (rótulas só nos apoios).

    Peça monolítica de MLC — continuidade na cumeeira (sem rótula).
    Uma vez hiperestática: H por compatibilidade (projeção horizontal dx).

        M_0(x) = momento isostático (uniforme ou assimétrico Tab.25)
        M(x)   = M_0(x) − H·y_c(x)
        H = ∫ M_0 y_c / I dx  /  ∫ y_c² / I dx

    Carga assimétrica (NBR 6123 Tab.25 — Cpb numa água, Cps na outra):
        passar q_esq e q_dir (kN/m) em cada meia-água.
        Se omitidos, usa-se q uniforme em todo o vão.
    """
    x = np.linspace(0.0, L, n_pts)

    # Resolver q_esq / q_dir
    if q_esq is None and q_dir is None:
        q_esq = q
        q_dir = q
    elif q_esq is None:
        q_esq = q_dir if q_dir is not None else 0.0
    elif q_dir is None:
        q_dir = q_esq

    if abs(q_esq) < 1e-12 and abs(q_dir) < 1e-12:
        return {
            "R_v_kN": 0.0, "R_A_kN": 0.0, "R_B_kN": 0.0, "H_kN": 0.0,
            "M_max_kNm": 0.0, "M_cumeeira_kNm": 0.0,
            "x_Mmax_m": 0.0,
            "N_apoio_kN": 0.0, "V_apoio_kN": 0.0,
            "f_c_m": (h_ap - h0) / 2.0,
            "theta_rad": math.atan(math.tan(alpha_rad) / 2.0),
            "sistema": "biarticulada",
            "q_esq": 0.0, "q_dir": 0.0,
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
    I_x = np.maximum(I_x, 1e-18)

    if abs(q_esq - q_dir) < 1e-12:
        M0 = 0.5 * q_esq * x * (L - x)
        R_A = q_esq * L / 2.0
        R_B = R_A
    else:
        M0, R_A, R_B = _M0_carga_assimetrica(x, L, q_esq, q_dir)

    num = float(np.trapezoid(M0 * y_c / I_x, x))
    den = float(np.trapezoid(y_c ** 2 / I_x, x))
    if den <= 0:
        raise ValueError("Integral ∫ y_c²/I dx nula — verificar geometria.")
    H = num / den

    M_x = M0 - H * y_c

    # Reação vertical governante (maior apoio) e no apoio A (padrão)
    R_v_gov = max(abs(R_A), abs(R_B))
    # Sinal: compr. positiva na fundação — usar valor com sinal de R_A se simétrico
    R_v = R_A if abs(R_A) >= abs(R_B) else R_B

    idx_max = int(np.argmax(np.abs(M_x)))
    M_max   = float(M_x[idx_max])
    x_Mmax  = float(x[idx_max])
    M_cum   = float(np.interp(L / 2.0, x, M_x))

    theta   = math.atan(tan_a / 2.0)
    # Esforços no eixo no apoio A (reação R_A)
    N_apoio = H * math.cos(theta) + R_A * math.sin(theta)
    V_apoio = R_A * math.cos(theta) - H * math.sin(theta)

    return {
        "R_v_kN":          round(R_v, 4),
        "R_A_kN":          round(R_A, 4),
        "R_B_kN":          round(R_B, 4),
        "R_v_gov_kN":      round(R_v_gov, 4),
        "H_kN":            round(H, 4),
        "M_max_kNm":       round(M_max, 4),
        "M_cumeeira_kNm":  round(M_cum, 4),
        "x_Mmax_m":        round(x_Mmax, 4),
        "N_apoio_kN":      round(N_apoio, 4),
        "V_apoio_kN":      round(V_apoio, 4),
        "f_c_m":           round(f_c, 4),
        "theta_rad":       round(theta, 6),
        "sistema":         "biarticulada",
        "q_esq":           q_esq,
        "q_dir":           q_dir,
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
    Carregamentos e combinações EN 1990 para viga biarticulada MLC.

    Área tributária:
        Pórtico intermediário: L_t (espaçamento entre pórticos)
        Pórtico de extremidade: L_t · fator_trib com fator_trib=0,5

    Vento θ=90° (Tab.25): varre todos os padrões Cpe (assimétrico Cpb+Cps,
    reverso, uniforme bv/st) × combinações EN 1990.

    Args:
        geo          : Geometria da viga
        mat          : Material
        g_area       : Carga permanente por área (kN/m²)
        q_area       : Sobrecarga por área (kN/m²)
        L_t          : Vão das terças = espaçamento entre pórticos (m)
        fator_trib   : 1,0 intermediário (padrão); 0,5 extremidade
        w_C1bv_m2    : Pressão vento C1 barlavento (kN/m²) — legado
        w_C1st_m2    : Pressão vento C1 sotavento (kN/m²)
        w_C2bv_m2    : Pressão vento C2 barlavento (kN/m²)
        w_C2st_m2    : Pressão vento C2 sotavento (kN/m²)
        padroes_vento: lista de padrões Tab.25 com w_esq/w_dir (kN/m²)
        vento_0:     : resultado forca_vento_paralelo_cumeeira (θ=0°)
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
    padroes_vento: list = field(default_factory=list)
    vento_0:    dict | None = None

    _combinacoes: dict = field(default_factory=dict, init=False, repr=False)
    _area_trib:   float = field(init=False, repr=False)
    _varredura_90: dict = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.fator_trib not in (0.5, 1.0):
            raise ValueError(
                "fator_trib deve ser 1.0 (pórtico intermediário) "
                "ou 0.5 (pórtico de extremidade)."
            )
        self._area_trib = self.L_t * self.fator_trib
        self._combinacoes = self._montar_combinacoes()

    @property
    def area_trib(self) -> float:
        return self._area_trib

    @property
    def varredura_vento_90(self) -> dict:
        """Resumo da varredura Tab.25 (θ=90°)."""
        return self._varredura_90

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

    # ── Análise estrutural ────────────────────────────────────
    def _analisar(
        self,
        q: float | None = None,
        q_esq: float | None = None,
        q_dir: float | None = None,
    ) -> dict:
        """Viga biarticulada — q uniforme ou (q_esq, q_dir) assimétrico."""
        if q is None:
            if q_esq is not None and q_dir is not None:
                q = 0.5 * (q_esq + q_dir)
            else:
                q = 0.0
        return analisar_biarticulada(
            q         = q,
            L         = self.geo.L,
            h0        = self.geo.h0,
            h_ap      = self.geo.h_ap,
            alpha_rad = self.geo.alpha_rad,
            b         = self.geo.b,
            q_esq     = q_esq,
            q_dir     = q_dir,
        )

    # ── Montagem das combinações ──────────────────────────────
    def _montar_combinacoes(self) -> dict[str, Combinacao]:
        g = self.g_k
        q = self.q_k
        c: dict[str, Combinacao] = {}

        def _comb(
            nome, tipo, desc, q_esq, q_dir, duracao, padrao: str = "",
        ) -> Combinacao:
            r = self._analisar(q_esq=q_esq, q_dir=q_dir)
            q_med = 0.5 * (q_esq + q_dir)
            return Combinacao(
                nome            = nome,
                tipo            = tipo,
                descricao       = desc,
                q_tot           = q_med,
                q_esq           = q_esq,
                q_dir           = q_dir,
                padrao_vento    = padrao,
                M_max_kNm       = r["M_max_kNm"],
                M_cumeeira_kNm  = r["M_cumeeira_kNm"],
                V_max_kN        = r.get("R_v_gov_kN", abs(r["R_v_kN"])),
                N_viga_kN       = r["N_apoio_kN"],
                V_viga_kN       = r["V_apoio_kN"],
                H_kN            = r["H_kN"],
                x_Mmax_m        = r["x_Mmax_m"],
                duracao         = duracao,
            )

        # ── Padrões de vento Tab.25 (θ=90°) ───────────────────
        # Cada padrão: pressões de área → lineares × área_trib
        padroes = list(self.padroes_vento)
        if not padroes:
            # Legado: só C1bv / C2st / C2bv uniformes
            padroes = [
                {
                    "id": "C1_unif_bv",
                    "w_esq_kNm2": self.w_C1bv_m2,
                    "w_dir_kNm2": self.w_C1bv_m2,
                    "descricao": "legado C1bv uniforme",
                },
                {
                    "id": "C2_unif_st",
                    "w_esq_kNm2": self.w_C2st_m2,
                    "w_dir_kNm2": self.w_C2st_m2,
                    "descricao": "legado C2st uniforme",
                },
                {
                    "id": "C2_unif_bv",
                    "w_esq_kNm2": self.w_C2bv_m2,
                    "w_dir_kNm2": self.w_C2bv_m2,
                    "descricao": "legado C2bv uniforme",
                },
            ]

        elu_vento: list[Combinacao] = []

        for p in padroes:
            pid = p["id"]
            we = p["w_esq_kNm2"] * self._area_trib
            wd = p["w_dir_kNm2"] * self._area_trib
            desc_p = p.get("descricao", pid)

            # W dominante: 1,35G + 1,5W + ψ0·1,5Q
            # Duração «curta» (não «instantanea») — EC5 §2.3.1.2; critério
            # de projeto conservador (k_mod menor). Ver memorial / materials.
            c_w = _comb(
                f"ELU_W_{pid}", "ELU",
                f"1,35G+1,5W+1,05Q | {desc_p}",
                GAMMA_G_sup * g + GAMMA_Q * we + PSI_0_Q * GAMMA_Q * q,
                GAMMA_G_sup * g + GAMMA_Q * wd + PSI_0_Q * GAMMA_Q * q,
                "curta", padrao=pid,
            )
            c[c_w.nome] = c_w
            elu_vento.append(c_w)

            # Sucção / G favorável: 0,9G + 1,5W  (se W reduz carga vertical)
            c_s = _comb(
                f"ELU_S_{pid}", "ELU",
                f"0,9G+1,5W | {desc_p}",
                GAMMA_G_inf * g + GAMMA_Q * we,
                GAMMA_G_inf * g + GAMMA_Q * wd,
                "curta", padrao=pid,
            )
            c[c_s.nome] = c_s
            elu_vento.append(c_s)

            # Q dominante com W acompanhante: 1,35G + 1,5Q + ψ0·1,5W
            c_q = _comb(
                f"ELU_Q_{pid}", "ELU",
                f"1,35G+1,5Q+0,9W | {desc_p}",
                GAMMA_G_sup * g + GAMMA_Q * q + PSI_0_W * GAMMA_Q * we,
                GAMMA_G_sup * g + GAMMA_Q * q + PSI_0_W * GAMMA_Q * wd,
                "longa", padrao=pid,
            )
            c[c_q.nome] = c_q
            elu_vento.append(c_q)

        # Aliases legados (compatibilidade main/OpenSees/relatório)
        # Governantes por |M| entre padrões com q médio > 0 e W dominante
        grav = [x for x in elu_vento if x.q_tot > 0 and x.nome.startswith("ELU_W_")]
        if not grav:
            grav = [x for x in elu_vento if x.q_tot > 0]
        gov_m = max(grav, key=lambda x: abs(x.M_max_kNm)) if grav else elu_vento[0]

        # Sucção: menor q_tot (mais negativo) entre ELU_S
        suc = [x for x in elu_vento if x.nome.startswith("ELU_S_")]
        gov_s = min(suc, key=lambda x: x.q_tot) if suc else gov_m

        # H máximo (fundação / ligações)
        gov_h = max(elu_vento, key=lambda x: abs(x.H_kN)) if elu_vento else gov_m

        c["ELU_C1"] = _comb(
            "ELU_C1", "ELU",
            "1,35G + 1,5Q + 0,9W_C1bv  (Q dominante, legado)",
            GAMMA_G_sup * g + GAMMA_Q * q + PSI_0_W * GAMMA_Q * self.w_C1bv_k,
            GAMMA_G_sup * g + GAMMA_Q * q + PSI_0_W * GAMMA_Q * self.w_C1bv_k,
            "longa", padrao="C1_unif_bv",
        )
        # ELU_C2 = alias do governante por |M| (W dominante Tab.25)
        c["ELU_C2"] = Combinacao(
            nome=gov_m.nome if gov_m.nome.startswith("ELU_W_") else "ELU_C2",
            tipo="ELU",
            descricao=f"GOVERNA |M| ← {gov_m.descricao}",
            q_tot=gov_m.q_tot, q_esq=gov_m.q_esq, q_dir=gov_m.q_dir,
            padrao_vento=gov_m.padrao_vento,
            M_max_kNm=gov_m.M_max_kNm, M_cumeeira_kNm=gov_m.M_cumeeira_kNm,
            V_max_kN=gov_m.V_max_kN, N_viga_kN=gov_m.N_viga_kN,
            V_viga_kN=gov_m.V_viga_kN, H_kN=gov_m.H_kN,
            x_Mmax_m=gov_m.x_Mmax_m, duracao=gov_m.duracao,
        )
        # Guardar também com chave estável ELU_C2 se o nome for outro
        if gov_m.nome != "ELU_C2":
            c["ELU_C2"] = Combinacao(
                nome="ELU_C2",
                tipo="ELU",
                descricao=f"GOVERNA |M| ← {gov_m.descricao}",
                q_tot=gov_m.q_tot, q_esq=gov_m.q_esq, q_dir=gov_m.q_dir,
                padrao_vento=gov_m.padrao_vento,
                M_max_kNm=gov_m.M_max_kNm, M_cumeeira_kNm=gov_m.M_cumeeira_kNm,
                V_max_kN=gov_m.V_max_kN, N_viga_kN=gov_m.N_viga_kN,
                V_viga_kN=gov_m.V_viga_kN, H_kN=gov_m.H_kN,
                x_Mmax_m=gov_m.x_Mmax_m, duracao="curta",
            )
        c["ELU_C3"] = Combinacao(
            nome="ELU_C3", tipo="ELU",
            descricao=f"Sucção governante ← {gov_s.descricao}",
            q_tot=gov_s.q_tot, q_esq=gov_s.q_esq, q_dir=gov_s.q_dir,
            padrao_vento=gov_s.padrao_vento,
            M_max_kNm=gov_s.M_max_kNm, M_cumeeira_kNm=gov_s.M_cumeeira_kNm,
            V_max_kN=gov_s.V_max_kN, N_viga_kN=gov_s.N_viga_kN,
            V_viga_kN=gov_s.V_viga_kN, H_kN=gov_s.H_kN,
            x_Mmax_m=gov_s.x_Mmax_m, duracao="curta",
        )
        c["ELU_C4"] = Combinacao(
            nome="ELU_C4", tipo="ELU",
            descricao=f"H máx ← {gov_h.descricao}",
            q_tot=gov_h.q_tot, q_esq=gov_h.q_esq, q_dir=gov_h.q_dir,
            padrao_vento=gov_h.padrao_vento,
            M_max_kNm=gov_h.M_max_kNm, M_cumeeira_kNm=gov_h.M_cumeeira_kNm,
            V_max_kN=gov_h.V_max_kN, N_viga_kN=gov_h.N_viga_kN,
            V_viga_kN=gov_h.V_viga_kN, H_kN=gov_h.H_kN,
            x_Mmax_m=gov_h.x_Mmax_m, duracao="curta",
        )

        # ELS (com W_C1bv legado + melhor padrão gravítico)
        w_els_e = gov_m.q_esq - GAMMA_G_sup * g - PSI_0_Q * GAMMA_Q * q
        # ELS usa valores característicos — G+Q+ψ0·W com padrão do gov |M|
        # Reconstruir W característico a partir do padrão
        pid_gov = gov_m.padrao_vento
        we_k = wd_k = self.w_C1bv_k
        for p in padroes:
            if p["id"] == pid_gov:
                we_k = p["w_esq_kNm2"] * self._area_trib
                wd_k = p["w_dir_kNm2"] * self._area_trib
                break
        c["ELS_S1"] = _comb(
            "ELS_S1", "ELS",
            f"G+Q+0,6W | padrão {pid_gov}",
            g + q + PSI_0_W * we_k,
            g + q + PSI_0_W * wd_k,
            "longa", padrao=pid_gov,
        )
        c["ELS_S2"] = _comb(
            "ELS_S2", "ELS",
            "G + 0,5Q  (frequente)",
            g + PSI_1_Q * q, g + PSI_1_Q * q,
            "longa",
        )
        c["ELS_S3"] = _comb(
            "ELS_S3", "ELS",
            "G  (quase-permanente — fluência)",
            g + PSI_2_Q * q, g + PSI_2_Q * q,
            "permanente",
        )

        # Metadados da varredura
        self._varredura_90 = {
            "n_padroes_cpe": len(padroes),
            "n_combinacoes_elu_vento": len(elu_vento),
            "padroes": [p["id"] for p in padroes],
            "gov_M": {
                "nome": gov_m.nome,
                "padrao": gov_m.padrao_vento,
                "M_max": gov_m.M_max_kNm,
                "H": gov_m.H_kN,
                "desc": gov_m.descricao,
            },
            "gov_succao": {
                "nome": gov_s.nome,
                "padrao": gov_s.padrao_vento,
                "q_tot": gov_s.q_tot,
                "desc": gov_s.descricao,
            },
            "gov_H": {
                "nome": gov_h.nome,
                "padrao": gov_h.padrao_vento,
                "H": gov_h.H_kN,
                "desc": gov_h.descricao,
            },
            "completo": len(padroes) >= 8,  # 2 casos × 4 padrões
        }

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
        Prefere ELU_C2 (alias da varredura Tab.25) se existir.
        """
        if "ELU_C2" in self._combinacoes and self._combinacoes["ELU_C2"].q_tot > 0:
            return self._combinacoes["ELU_C2"]
        cands = [c for c in self.combinacoes_ELU().values() if c.q_tot > 0]
        if not cands:
            cands = list(self.combinacoes_ELU().values())
        return max(cands, key=lambda c: abs(c.M_max_kNm))

    def combinacao_ELU_succao(self) -> Combinacao:
        return self._combinacoes["ELU_C3"]

    def combinacao_ELU_Hmax(self) -> Combinacao:
        """Combinação com maior |H| (fundação / L1 / L3)."""
        return self._combinacoes.get(
            "ELU_C4", self.combinacao_ELU_governante()
        )

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
        r = self._analisar(q_esq=gov.q_esq, q_dir=gov.q_dir)
        return r["M_x"]

    def V_ELU(self) -> NDArray:
        """Diagrama V(x) aproximado (kN) — média das meias-águas."""
        q = self.combinacao_ELU_governante().q_tot
        return q * (self.geo.L / 2 - self.geo.x)

    def M_g(self) -> NDArray:
        return self._analisar(self.g_k)["M_x"]

    def M_q(self) -> NDArray:
        return self._analisar(self.q_k)["M_x"]

    def M_ELS_car(self) -> NDArray:
        s1 = self._combinacoes["ELS_S1"]
        return self._analisar(q_esq=s1.q_esq, q_dir=s1.q_dir)["M_x"]

    # ── Relatório ─────────────────────────────────────────────

    def resumo(self) -> None:
        """Imprime resumo das combinações (aliases + varredura)."""
        print("=" * 76)
        print("  COMBINAÇÕES DE AÇÕES — EN 1990 | Viga biarticulada MLC")
        print(f"  L={self.geo.L}m | h0={self.geo.h0}m | "
              f"h_ap={self.geo.h_ap:.3f}m | "
              f"Área trib.={self._area_trib}m "
              f"(L_t×{self.fator_trib})")
        print("=" * 76)

        vv = self._varredura_90
        if vv:
            print(f"\n  Varredura vento θ=90° Tab.25:")
            print(f"    Padrões Cpe: {vv.get('n_padroes_cpe', 0)} "
                  f"| comb. ELU vento: {vv.get('n_combinacoes_elu_vento', 0)} "
                  f"| completo={vv.get('completo', False)}")
            print(f"    IDs: {', '.join(vv.get('padroes', []))}")
            gm = vv.get("gov_M", {})
            print(f"    Gov |M|: {gm.get('padrao')}  "
                  f"M={gm.get('M_max', 0):.1f} kNm  H={gm.get('H', 0):.1f} kN")
            gh = vv.get("gov_H", {})
            print(f"    Gov |H|: {gh.get('padrao')}  H={gh.get('H', 0):.1f} kN")
            gs = vv.get("gov_succao", {})
            print(f"    Gov sucção: {gs.get('padrao')}  q={gs.get('q_tot', 0):+.2f} kN/m")

        print(f"\n  Cargas lineares base:")
        print(f"    G  = {self.g_k:.4f} kN/m | Q = {self.q_k:.4f} kN/m")
        print(f"    W_C1bv = {self.w_C1bv_k:+.4f} kN/m | "
              f"W_C2st = {self.w_C2st_k:+.4f} kN/m")

        print(f"\n  {'Comb.':<22} {'q_med':>8} {'q_e':>8} {'q_d':>8} "
              f"{'M_max':>9} {'H':>9}  Dur.")
        print(f"  {'-'*78}")

        # Mostrar aliases + ELS (não todas as dezenas de combinações)
        keys_show = [k for k in self._combinacoes if k.startswith("ELU_C") or k.startswith("ELS_")]
        for nome in keys_show:
            c = self._combinacoes[nome]
            print(
                f"  {nome:<22} {c.q_tot:>+8.2f} {c.q_esq:>+8.2f} {c.q_dir:>+8.2f} "
                f"{c.M_max_kNm:>9.2f} {c.H_kN:>9.2f}  {c.duracao}"
            )

        gov = self.combinacao_ELU_governante()
        print(f"\n  ELU governante: {gov.nome} | padrao={gov.padrao_vento}")
        print(f"    {gov.descricao}")
        print(f"    M_max = {gov.M_max_kNm:.2f} kN·m  "
              f"em x = {gov.x_Mmax_m:.3f} m")
        print(f"    M_cumeeira = {gov.M_cumeeira_kNm:.2f} kN·m")
        print(f"    V_max = {gov.V_max_kN:.2f} kN | "
              f"N = {gov.N_viga_kN:.2f} kN | H = {gov.H_kN:.2f} kN")
        if self.vento_0:
            print(f"\n  Vento θ=0° (// cumeeira): "
                  f"F={self.vento_0.get('F_total_kN', 0):.1f} kN | "
                  f"w={self.vento_0.get('w_long_kNpm', 0):.3f} kN/m")
        print("=" * 76)


# ── Fábrica com vento ─────────────────────────────────────────────────────────

def carregamentos_com_vento(
    geo:          GeometriaViga,
    mat:          GlulamMaterial,
    g_area:       float,
    q_area:       float,
    L_t:          float,
    params_vento,
    b_pilar:      float = 0.22,
    h_pilar:      float = 0.26,
    n_pilares_linha: int = 9,
    n_linhas_portico: int = 3,
    L_cob_m:      float = 46.0,
    B_cob_m:      float | None = None,
) -> Carregamentos:
    """
    Cria Carregamentos com varredura completa Tab.25 (θ=90°) e θ=0°.

    θ=90°: todos os padrões Cpe (assimétrico, reverso, uniforme bv/st) × EN 1990
    θ=0° : força longitudinal (pilares livres + fricção) para contraventamento
    """
    from mlc_projeto.core.wind import (
        calcular_vento,
        forca_vento_paralelo_cumeeira,
    )
    res = calcular_vento(params_vento)

    if B_cob_m is None:
        B_cob_m = geo.L  # um vão; main pode passar 2·L se dois pórticos

    vento_0 = forca_vento_paralelo_cumeeira(
        params_vento,
        b_pilar=b_pilar,
        h_pilar=h_pilar,
        n_pilares_linha=n_pilares_linha,
        n_linhas_portico=n_linhas_portico,
        L_cob_m=L_cob_m,
        B_cob_m=B_cob_m,
    )

    padroes = list(res.pressoes_padrao.values())

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
        padroes_vento=padroes,
        vento_0=vento_0,
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