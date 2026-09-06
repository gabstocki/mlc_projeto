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

    Empuxo (Castigliano / força unitária horizontal no apoio liberado):
        Estado unitário: m(x) = −y_c(x) (flexão), n(x) = cos θ (normal no eixo).
        δ11 = ∫ y_c²/(EI) ds + ∫ cos²θ/(EA) ds     (flexão + AXIAL)
        H   = ∫ M_0 y_c/(EI) ds / δ11              (0 → L; E cancela)

        O termo axial ∫cos²θ/(EA) NÃO pode ser desprezado: para viga ABATIDA
        (flecha do eixo y_c ≪ altura h) ele domina o denominador. Desprezá-lo
        (versão até v4) superestimava H em ~3,5× e invertia o sinal de M_cum.

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
from scipy.integrate import trapezoid

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial


# ── Coeficientes EN 1990 ─────────────────────────────────────────────────────

# Coeficientes de ações permanentes — EN 1990 (issue 4).
# STR/GEO — Tab. A1.2(B):
GAMMA_G_sup = 1.35   # permanente desfavorável
GAMMA_G_inf = 1.00   # permanente FAVORÁVEL (EN 1990 Tab. A1.2(B); NÃO 0,90 da NBR)
# EQU (perda de equilíbrio estático / uplift) — Tab. A1.2(A):
GAMMA_G_EQU_estab    = 0.90   # permanente estabilizante (resiste ao uplift)
GAMMA_G_EQU_desestab = 1.10   # permanente desestabilizante
GAMMA_Q     = 1.50

# Coeficientes ψ — cobertura CATEGORIA H (não acessível, só manutenção).
# EN 1990 Tab. A1.1 (categoria H): ψ0 = ψ1 = ψ2 = 0 para a sobrecarga.
# EN 1991-1-1 §3.3.2(1): a sobrecarga de cobertura (cat. H) NÃO é concomitante
# com vento nem neve → Q e W são ações variáveis alternativas (issue 3).
PSI_0_Q     = 0.00   # categoria H (era 0,70 — categorias A–D)
PSI_1_Q     = 0.00   # categoria H (era 0,50 — categorias A–D); issue 5
PSI_2_Q     = 0.00
# Vento: ψ0,W=0,6 (EN 1990 Tab. A1.1). Não se aplica como acompanhante da
# sobrecarga aqui, pois Q (cat. H) e W não são concomitantes.
PSI_0_W     = 0.60
PSI_2_W     = 0.00

# Aceleração da gravidade (peso próprio — EN 1991-1-1 §4)
G_GRAVIDADE = 9.81   # m/s²


# ── Peso próprio característico g_k (EN 1991-1-1 §4 + EN 14080) ───────────────

def peso_proprio_gk(
    geo:          GeometriaViga,
    mat:          GlulamMaterial,
    L_t:          float,
    b_terca:      float,
    h_terca:      float,
    s_terca:      float,
    g_telha_kNm2:        float,
    g_instalacoes_kNm2:  float,
    g_ms2:        float = G_GRAVIDADE,
) -> dict:
    """
    Peso próprio característico g_k por m² de projeção horizontal da cobertura,
    DISCRIMINADO por parcela (issue 1).

    Referências:
        EN 1991-1-1 §4.1 — peso próprio a partir das dimensões nominais e da
                           massa específica do material.
        EN 14080       — massa específica média ρ_mean do glulam.

        γ = ρ_mean · g                                   [kN/m³]

    Parcelas (por m² de projeção horizontal):
        g_MLC       = (∫ A(x) dx · γ) / L_viga / L_t     viga de duplo-bisel,
                      volume por integração exata de A(x)=b·h(x), distribuído
                      sobre a largura tributária L_t.
        g_terças    = γ · (b_terça · h_terça) / s_terça
        g_cobertura = g_telha + g_instalações            (valores DECLARADOS —
                      da ficha técnica da telha / estimativa de projeto)

    Dois g_k distintos, fisicamente corretos:
        g_k_viga  = g_MLC + g_terças + g_cobertura   → carga na VIGA principal
        g_k_terça = g_terças + g_cobertura           → carga na TERÇA (a terça
                    NÃO carrega o peso próprio da viga MLC; g_terças·s reproduz
                    o peso linear da própria terça)

    Pilares excluídos: não carregam a viga; o seu peso próprio entra no axial do
    pilar e é desprezável face a R_v (~2,5 kN vs ~200 kN).

    Returns:
        dict com γ, cada parcela e os totais g_k_viga e g_k_terça (kN/m²).
    """
    if L_t <= 0 or s_terca <= 0:
        raise ValueError("L_t e s_terca devem ser positivos")

    gamma = mat.rho_mean * g_ms2 / 1000.0                 # kN/m³

    x = np.linspace(0.0, geo.L, 2001)
    V_viga = float(trapezoid(geo.A(x), x))            # m³ por viga
    q_viga_lin = V_viga * gamma / geo.L                  # kN/m (horizontal)
    g_mlc = q_viga_lin / L_t                             # kN/m²

    g_tercas = gamma * (b_terca * h_terca) / s_terca     # kN/m²
    g_cobertura = g_telha_kNm2 + g_instalacoes_kNm2      # kN/m²

    g_k_viga = g_mlc + g_tercas + g_cobertura
    g_k_terca = g_tercas + g_cobertura

    return {
        "gamma_kNm3":      round(gamma, 4),
        "rho_mean_kgm3":   mat.rho_mean,
        "V_viga_m3":       round(V_viga, 4),
        "q_viga_lin_kNm":  round(q_viga_lin, 4),
        "g_mlc_kNm2":      round(g_mlc, 4),
        "g_tercas_kNm2":   round(g_tercas, 4),
        "g_telha_kNm2":    round(g_telha_kNm2, 4),
        "g_instalacoes_kNm2": round(g_instalacoes_kNm2, 4),
        "g_cobertura_kNm2": round(g_cobertura, 4),
        "g_k_viga_kNm2":   round(g_k_viga, 4),
        "g_k_terca_kNm2":  round(g_k_terca, 4),
        "norma":           "EN 1991-1-1 §4.1 | EN 14080 (ρ_mean)",
    }


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
    H_kN:            float    # kN   — empuxo horizontal EFETIVO (0 se não desenvolve)
    x_Mmax_m:        float    # m    — posição do momento máximo
    duracao:         str
    q_esq:           float = 0.0   # kN/m — meia-água esquerda
    q_dir:           float = 0.0   # kN/m — meia-água direita
    padrao_vento:    str = ""      # id do padrão Tab.25 (se aplicável)
    H_rigido_kN:     float = 0.0   # kN   — empuxo Castigliano (apoio rígido; auditoria)


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
    *,
    desenvolve_empuxo: bool,
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
            "H_rigido_kN": 0.0,
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
    A_x   = np.maximum(b * h_x, 1e-18)

    if abs(q_esq - q_dir) < 1e-12:
        M0 = 0.5 * q_esq * x * (L - x)
        R_A = q_esq * L / 2.0
        R_B = R_A
    else:
        M0, R_A, R_B = _M0_carga_assimetrica(x, L, q_esq, q_dir)

    # Empuxo H por Castigliano — inclui flexibilidade de FLEXÃO e AXIAL.
    # Integração ao longo do eixo do centroide: ds = dx / cos θ (θ constante ⇒
    # ds/dx cancela em H, mas mantido explícito por rigor). Ver docstring.
    theta   = math.atan(tan_a / 2.0)
    ds_dx   = 1.0 / math.cos(theta)
    num      = float(trapezoid(M0 * y_c / I_x * ds_dx, x))
    den_flex = float(trapezoid(y_c ** 2 / I_x * ds_dx, x))
    den_ax   = float(trapezoid(math.cos(theta) ** 2 / A_x * ds_dx, x))
    den = den_flex + den_ax
    if den <= 0:
        raise ValueError("Integral de flexibilidade nula — verificar geometria.")
    H_rigido = num / den                        # Castigliano (apoio rígido)

    # Empuxo EFETIVO — issue 35/38 (Opção B):
    #   desenvolve_empuxo=True  → apoio horizontal rígido: H = H_rígido.
    #   desenvolve_empuxo=False → pilar biarticulado é MECANISMO lateral, o empuxo
    #     NÃO se desenvolve (H_dev≈0, ver empuxo_acoplado.py) → viga BIAPOIADA,
    #     H=0, M=M0 (isostático). O H_rígido fica no retorno para a auditoria.
    H = H_rigido if desenvolve_empuxo else 0.0

    M_x = M0 - H * y_c

    # Reação vertical governante (maior apoio) e no apoio A (padrão)
    R_v_gov = max(abs(R_A), abs(R_B))
    # Sinal: compr. positiva na fundação — usar valor com sinal de R_A se simétrico
    R_v = R_A if abs(R_A) >= abs(R_B) else R_B

    idx_max = int(np.argmax(np.abs(M_x)))
    M_max   = float(M_x[idx_max])
    x_Mmax  = float(x[idx_max])
    M_cum   = float(np.interp(L / 2.0, x, M_x))

    # theta (inclinação do eixo do centroide) já definido acima.
    # Esforços no eixo no apoio A (reação R_A)
    N_apoio = H * math.cos(theta) + R_A * math.sin(theta)
    V_apoio = R_A * math.cos(theta) - H * math.sin(theta)

    return {
        "R_v_kN":          round(R_v, 4),
        "R_A_kN":          round(R_A, 4),
        "R_B_kN":          round(R_B, 4),
        "R_v_gov_kN":      round(R_v_gov, 4),
        "H_kN":            round(H, 4),
        "H_rigido_kN":     round(H_rigido, 4),
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
    # Opção B (issue 35/38): empuxo NÃO se desenvolve (viga biapoiada). Default
    # True mantém o modelo de apoio rígido (retrocompatível).
    empuxo_desenvolve: bool = True

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
            desenvolve_empuxo = self.empuxo_desenvolve,
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
                H_rigido_kN     = r.get("H_rigido_kN", r["H_kN"]),
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

            # Vento dominante (pressão): 1,35G + 1,5W. Categoria H → SEM Q
            # (EN 1991-1-1 §3.3.2(1); ψ0,Q=0, EN 1990 Tab. A1.1). Duração «curta»
            # (EC5 §2.3.1.2; critério conservador — ver materials/memorial).
            c_w = _comb(
                f"ELU_W_{pid}", "ELU",
                f"1,35G+1,5W (cat.H: sem Q) | {desc_p}",
                GAMMA_G_sup * g + GAMMA_Q * we,
                GAMMA_G_sup * g + GAMMA_Q * wd,
                "curta", padrao=pid,
            )
            c[c_w.nome] = c_w
            elu_vento.append(c_w)

            # Vento dominante (sucção) → situação de UPLIFT/EQU: 0,9G_estab + 1,5W
            # (EN 1990 Tab. A1.2(A), G estabilizante = 0,90 — NÃO é valor NBR;
            # issue 4). Sem Q (cat. H, não concomitante). Alimenta a verificação
            # de ancoragem/uplift (issue 33). Para STR o favorável seria 1,00
            # (Tab. A1.2(B)), mas a resistência do membro é governada pela
            # gravidade/vento-pressão, não pela sucção.
            c_s = _comb(
                f"ELU_S_{pid}", "ELU",
                f"0,9G+1,5W (EQU Tab.A1.2(A); sem Q) | {desc_p}",
                GAMMA_G_EQU_estab * g + GAMMA_Q * we,
                GAMMA_G_EQU_estab * g + GAMMA_Q * wd,
                "curta", padrao=pid,
            )
            c[c_s.nome] = c_s
            elu_vento.append(c_s)

        # Sobrecarga dominante — categoria H: SEM vento (não concomitante,
        # EN 1991-1-1 §3.3.2(1)). Uma única combinação gravítica (independe do
        # padrão de vento). Duração «média» — sobrecarga (EC5 Tab. 2.1 / §3.1.3).
        c_q_grav = _comb(
            "ELU_Q", "ELU",
            "1,35G+1,5Q (cat.H: sem vento)",
            GAMMA_G_sup * g + GAMMA_Q * q,
            GAMMA_G_sup * g + GAMMA_Q * q,
            "media",
        )
        c[c_q_grav.nome] = c_q_grav
        elu_vento.append(c_q_grav)

        # Aliases legados (compatibilidade main/OpenSees/relatório)
        # Governante por |M| entre TODAS as combinações de sentido gravítico
        # (q_tot > 0): vento-pressão dominante (ELU_W_) e sobrecarga (ELU_Q).
        grav = [x for x in elu_vento if x.q_tot > 0]
        gov_m = max(grav, key=lambda x: abs(x.M_max_kNm)) if grav else elu_vento[0]

        # Sucção: menor q_tot (mais negativo) entre ELU_S
        suc = [x for x in elu_vento if x.nome.startswith("ELU_S_")]
        gov_s = min(suc, key=lambda x: x.q_tot) if suc else gov_m

        # H máximo (fundação / ligações)
        gov_h = max(elu_vento, key=lambda x: abs(x.H_kN)) if elu_vento else gov_m

        c["ELU_C1"] = _comb(
            "ELU_C1", "ELU",
            "1,35G + 1,5Q  (Q dominante, cat.H: sem vento)",
            GAMMA_G_sup * g + GAMMA_Q * q,
            GAMMA_G_sup * g + GAMMA_Q * q,
            "media",
        )
        # ELU_C2 = alias (chave estável) do governante por |M| — Tab.25 (vento,
        # duração "curta") OU sobrecarga Q (duração "media"). Herda a duração REAL
        # do governante: o k_mod downstream (flexão/pilar/cisalhamento) depende
        # disso — antes era fixado em "curta", subestimando f_d quando Q governava.
        c["ELU_C2"] = Combinacao(
            nome="ELU_C2",
            tipo="ELU",
            descricao=f"GOVERNA |M| ← {gov_m.descricao}",
            q_tot=gov_m.q_tot, q_esq=gov_m.q_esq, q_dir=gov_m.q_dir,
            padrao_vento=gov_m.padrao_vento,
            M_max_kNm=gov_m.M_max_kNm, M_cumeeira_kNm=gov_m.M_cumeeira_kNm,
            V_max_kN=gov_m.V_max_kN, N_viga_kN=gov_m.N_viga_kN,
            V_viga_kN=gov_m.V_viga_kN, H_kN=gov_m.H_kN,
            H_rigido_kN=gov_m.H_rigido_kN,
            x_Mmax_m=gov_m.x_Mmax_m, duracao=gov_m.duracao,
        )
        c["ELU_C3"] = Combinacao(
            nome="ELU_C3", tipo="ELU",
            descricao=f"Sucção governante ← {gov_s.descricao}",
            q_tot=gov_s.q_tot, q_esq=gov_s.q_esq, q_dir=gov_s.q_dir,
            padrao_vento=gov_s.padrao_vento,
            M_max_kNm=gov_s.M_max_kNm, M_cumeeira_kNm=gov_s.M_cumeeira_kNm,
            V_max_kN=gov_s.V_max_kN, N_viga_kN=gov_s.N_viga_kN,
            V_viga_kN=gov_s.V_viga_kN, H_kN=gov_s.H_kN,
            H_rigido_kN=gov_s.H_rigido_kN,
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
            H_rigido_kN=gov_h.H_rigido_kN,
            x_Mmax_m=gov_h.x_Mmax_m, duracao="curta",
        )

        # ELS característico — categoria H: Q e W NÃO concomitantes
        # (EN 1991-1-1 §3.3.2(1)). Para a flecha descendente governa G+Q (sem
        # vento; o vento é sucção/uplift — flecha ascendente, ver issues 6/33).
        c["ELS_S1"] = _comb(
            "ELS_S1", "ELS",
            "G + Q  (característico, cat.H: sem vento)",
            g + q, g + q,
            "longa",
        )
        # Frequente e quase-permanente — categoria H: ψ1=ψ2=0 (EN 1990 Tab. A1.1)
        # ⇒ AMBAS reduzem-se a G (a sobrecarga não entra). Ver issue 5.
        c["ELS_S2"] = _comb(
            "ELS_S2", "ELS",
            "G  (frequente; cat.H ψ1=0 ⇒ sem Q)",
            g + PSI_1_Q * q, g + PSI_1_Q * q,
            "longa",
        )
        c["ELS_S3"] = _comb(
            "ELS_S3", "ELS",
            "G  (quase-permanente ψ2=0; base da fluência)",
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

    def tabela_combinacoes(self) -> list[dict]:
        """
        Tabela COMPLETA das combinações ELU por padrão de vento (issue 28).

        Para cada um dos 8 padrões Cpe da Tab.25 (C1/C2 × asim/rev/unif.bv/unif.st)
        há 2 combinações: ELU_W (1,35G+1,5W, pressão) e ELU_S (0,9G+1,5W, sucção);
        mais ELU_Q (1,35G+1,5Q, sem vento). Total 8×2+1 = 17 (a cat. H reduziu de
        24 → 17 ao tornar Q e vento não concomitantes — issue 3).

        Cada linha traz: id do padrão, caso Tab.25, Cpb/Cps (C_esq/C_dir),
        q_esq/q_dir, M_max, H, duração e a marcação da(s) governante(s).
        """
        padroes = {p["id"]: p for p in self.padroes_vento}
        combos = self._combinacoes

        # Governantes (mesmos critérios dos aliases ELU_C2/C3/C4)
        elu = [v for k, v in combos.items()
               if k.startswith(("ELU_W_", "ELU_S_")) or k == "ELU_Q"]
        grav = [x for x in elu if x.q_tot > 0]
        suc = [x for x in elu if x.nome.startswith("ELU_S_")]
        gov_M = max(grav, key=lambda x: abs(x.M_max_kNm)).nome if grav else None
        gov_S = min(suc, key=lambda x: x.q_tot).nome if suc else None
        gov_H = max(elu, key=lambda x: abs(x.H_kN)).nome if elu else None

        linhas: list[dict] = []
        for pid, p in padroes.items():
            for grupo, pref in (("W", "ELU_W_"), ("S", "ELU_S_")):
                c = combos.get(f"{pref}{pid}")
                if c is None:
                    continue
                gov = []
                if c.nome == gov_M:
                    gov.append("|M|")
                if c.nome == gov_S:
                    gov.append("uplift")
                if c.nome == gov_H:
                    gov.append("|H|")
                linhas.append({
                    "nome":     c.nome,
                    "grupo":    grupo,
                    "combo":    "1,35G+1,5W" if grupo == "W" else "0,9G+1,5W",
                    "padrao":   pid,
                    "caso":     p.get("caso_tab", ""),
                    "tipo_pad": p.get("tipo", ""),
                    "C_esq":    round(float(p.get("C_esq", 0.0)), 3),
                    "C_dir":    round(float(p.get("C_dir", 0.0)), 3),
                    "q_esq":    round(c.q_esq, 3),
                    "q_dir":    round(c.q_dir, 3),
                    "M_max_kNm": round(c.M_max_kNm, 1),
                    "H_kN":     round(c.H_kN, 1),
                    "duracao":  c.duracao,
                    "governa":  "+".join(gov),
                })
        # ELU_Q (gravítica, sem vento)
        cq = combos.get("ELU_Q")
        if cq is not None:
            gov = []
            if cq.nome == gov_M:
                gov.append("|M|")
            linhas.append({
                "nome": cq.nome, "grupo": "Q", "combo": "1,35G+1,5Q",
                "padrao": "—", "caso": "—", "tipo_pad": "sem vento",
                "C_esq": None, "C_dir": None,
                "q_esq": round(cq.q_esq, 3), "q_dir": round(cq.q_dir, 3),
                "M_max_kNm": round(cq.M_max_kNm, 1), "H_kN": round(cq.H_kN, 1),
                "duracao": cq.duracao, "governa": "+".join(gov),
            })
        return linhas

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
        """Cortante ⊥ ao eixo (apoio) — combinação ELU governante por |M|."""
        return self.combinacao_ELU_governante().V_viga_kN

    def combinacao_ELU_Vtransversal(self) -> Combinacao:
        """
        Combinação que MAXIMIZA o cortante transversal |V_viga| (⊥ ao eixo).

        A combinação que governa o cortante transversal NÃO é necessariamente a
        que governa |M|: sob vento assimétrico a descompensação R_A vs empuxo H
        pode elevar V = R_A·cosθ − H·senθ. Usada na verificação de cisalhamento
        (§6.1.7), referida ao eixo da peça (issue 12).
        """
        cands = list(self.combinacoes_ELU().values())
        return max(cands, key=lambda c: abs(c.V_viga_kN))

    def V_viga_max_ELU(self) -> float:
        """Máximo cortante transversal |V_viga| (⊥ ao eixo) entre combinações ELU."""
        return abs(self.combinacao_ELU_Vtransversal().V_viga_kN)

    def H_ELU(self) -> float:
        """Empuxo horizontal EFETIVO na fundação — ELU governante (0 na Opção B)."""
        return self.combinacao_ELU_governante().H_kN

    def H_rigido_ELU(self) -> float:
        """Empuxo Castigliano de apoio RÍGIDO — ELU governante (auditoria issue 38;
        independe de o empuxo se desenvolver ou não)."""
        return self.combinacao_ELU_governante().H_rigido_kN

    def M_ELU(self) -> NDArray:
        """Diagrama M(x) da combinação ELU governante (kN·m)."""
        gov = self.combinacao_ELU_governante()
        r = self._analisar(q_esq=gov.q_esq, q_dir=gov.q_dir)
        return r["M_x"]

    def diagramas_MVN_ELU(self) -> dict:
        """
        Diagramas M(x), V(x) e N(x) da combinação ELU governante — derivação
        rigorosa no eixo da peça (issue 27, coerente com a issue 12).

        Da análise biarticulada:
            M(x)  = M_0(x) − H·y_c(x)            (momento fletor)
            S(x)  = dM_0/dx                       (cortante vertical da viga simples)
            θ(x)  = arctan(dy_c/dx)               (inclinação local do eixo centroidal)
        Projetando o empuxo H (horizontal, constante) e S(x) no eixo local:
            N(x)  = H·cosθ + S·senθ               (normal no eixo; compressão +)
            V(x)  = S·cosθ − H·senθ               (cortante ⊥ ao eixo)

        Coincide, nos apoios, com N_apoio/V_apoio de `analisar_biarticulada`.
        """
        gov = self.combinacao_ELU_governante()
        r = self._analisar(q_esq=gov.q_esq, q_dir=gov.q_dir)
        x   = np.asarray(r["x"], dtype=float)
        M   = np.asarray(r["M_x"], dtype=float)
        M0  = np.asarray(r["M0_x"], dtype=float)
        H   = float(r["H_kN"])

        S = np.gradient(M0, x)                      # dM_0/dx (cortante viga simples)
        # Inclinação local do eixo centroidal — ANALÍTICA (y_c = x_sim·tanα/2):
        # slope = +tanα/2 (x<L/2), −tanα/2 (x>L/2). Kink no ápice → V salta ali.
        L = float(self.geo.L)
        slope_mag = math.tan(self.geo.alpha_rad) / 2.0
        theta = np.where(x < L / 2.0, math.atan(slope_mag), -math.atan(slope_mag))
        N = H * np.cos(theta) + S * np.sin(theta)  # kN (compressão +)
        V = S * np.cos(theta) - H * np.sin(theta)  # kN (⊥ eixo)
        return {
            "x": x, "M": M, "V": V, "N": N, "S": S,
            "H_kN": H, "comb": gov.nome,
            "M_max_kNm": float(M[np.argmax(np.abs(M))]),
            "V_max_kN":  float(V[np.argmax(np.abs(V))]),
            "N_max_kN":  float(N[np.argmax(np.abs(N))]),
        }

    def V_ELU(self) -> NDArray:
        """Diagrama V(x) (kN) — cortante ⊥ ao eixo, DERIVADO do M(x) real
        (issue 27; substitui a antiga aproximação q·(L/2−x) de viga simples)."""
        return self.diagramas_MVN_ELU()["V"]

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
    empuxo_desenvolve: bool = True,
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
        empuxo_desenvolve=empuxo_desenvolve,
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