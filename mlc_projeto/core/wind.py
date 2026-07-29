"""
core/wind.py — Carregamento de vento conforme NBR 6123.

Cobertura isolada a duas águas simétricas — Tabela 25 (NBR 6123:2023;
equiv. Tab. 18 na ed. 1988).

Direcções (convenção NBR / ensaios coberturas isoladas):
    θ = 90° — vento **perpendicular à cumeeira** (no plano dos pórticos)
              → Cpb (barlavento) + Cps (sotavento) em **dois carregamentos**
    θ = 0°  — vento **paralelo à cumeeira** (longitudinal ao galpão)
              → força horizontal em pilares livres + contraventamento
                (estrutura aberta sem vedações)

Referência: ABNT NBR 6123:2023 § coberturas isoladas; EN 1990 (combinações)
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math


# ── Parâmetros ────────────────────────────────────────────────────────────────

@dataclass
class ParametrosVento:
    """
    Parâmetros de vento para o galpão — NBR 6123.

    Args:
        V0          : Velocidade básica do vento (m/s) — isopleta da região
        S1          : Fator topográfico (§5.2) — 1,0 para terreno plano
        categoria   : Categoria de rugosidade do terreno (I a V) — §5.3
        classe      : Classe da estrutura (A, B ou C) — §5.3
        S3          : Fator estatístico (§5.5) — grupo 2 = 1,0
        L           : Vão de cada pórtico (m)
        H1          : Variação de altura da cobertura = h_ap - h0 (m)
        h           : Pé-direito do pilar (m)
        dist_portico: Distância entre pórticos (m)
    """
    V0:           float = 45.0
    S1:           float = 1.0
    categoria:    str   = "IV"
    classe:       str   = "B"
    S3:           float = 1.0
    L:            float = 20.25
    H1:           float = 1.0
    h:            float = 7.0
    dist_portico: float = 5.75

    _S2_TABLE: dict = field(default=None, repr=False)

    def __post_init__(self):
        self._S2_TABLE = {
            ("I",   "A"): 1.10, ("I",   "B"): 1.11, ("I",   "C"): 1.12,
            ("II",  "A"): 1.00, ("II",  "B"): 1.00, ("II",  "C"): 1.00,
            ("III", "A"): 0.94, ("III", "B"): 0.94, ("III", "C"): 0.93,
            ("IV",  "A"): 0.86, ("IV",  "B"): 0.83, ("IV",  "C"): 0.82,
            ("V",   "A"): 0.74, ("V",   "B"): 0.70, ("V",   "C"): 0.68,
        }

    @property
    def S2(self) -> float:
        key = (self.categoria, self.classe)
        if key not in self._S2_TABLE:
            raise ValueError(
                f"Combinação categoria='{self.categoria}' classe='{self.classe}' "
                f"não encontrada. Categorias: I–V. Classes: A, B, C."
            )
        return self._S2_TABLE[key]

    @property
    def Vk(self) -> float:
        return self.V0 * self.S1 * self.S2 * self.S3

    @property
    def q(self) -> float:
        """Pressão dinâmica q (kN/m²) — NBR 6123 §6.2."""
        return 0.613e-3 * self.Vk ** 2

    @property
    def tg_beta(self) -> float:
        return self.H1 / (self.L / 2)

    @property
    def beta_deg(self) -> float:
        return math.degrees(math.atan(self.tg_beta))

    @property
    def H_max(self) -> float:
        return self.h + self.H1


# ── Tabela 25 — θ = 90° (perpendicular à cumeeira) ───────────────────────────

def coeficientes_tabela25(tg_beta: float) -> dict:
    """
    Coeficientes de pressão Cpb e Cps — NBR 6123 Tabela 25.

    Cobertura isolada a duas águas simétricas.
    Vento **perpendicular à cumeeira** (θ = 90°).

    Dois carregamentos obrigatórios (a norma exige avaliar ambos):
        Carregamento 1 — pressão / compressão dominante
        Carregamento 2 — sucção dominante

    Intervalos válidos: 0,07 ≤ tg β ≤ 0,6
    """
    if tg_beta < 0.07:
        raise ValueError(
            f"tg β = {tg_beta:.4f} abaixo do limite mínimo 0,07 da Tabela 25. "
            f"Revise a geometria da cobertura."
        )
    if tg_beta > 0.6:
        raise ValueError(
            f"tg β = {tg_beta:.4f} acima do limite máximo 0,6 da Tabela 25. "
            f"Revise a geometria da cobertura."
        )

    if 0.07 <= tg_beta <= 0.4:
        Cpb_1 = 2.4 * tg_beta + 0.6
        Cps_1 = 3.0 * tg_beta - 0.5
        Cpb_2 = 0.6 * tg_beta - 0.74
        Cps_2 = -1.0
    else:  # 0.4 < tg_beta <= 0.6
        Cpb_1 = min(2.4 * tg_beta + 0.6, 2.0)
        Cps_1 = +0.7
        Cpb_2 = 6.5 * tg_beta - 3.1
        Cps_2 = 5.0 * tg_beta - 3.0

    return {
        "C1": {"Cpb": Cpb_1, "Cps": Cps_1},
        "C2": {"Cpb": Cpb_2, "Cps": Cps_2},
    }


def padroes_cpe_tabela25(tg_beta: float) -> list[dict]:
    """
    Todos os padrões de Cpe da Tab. 25 a varrer no pórtico (θ = 90°).

    Para cada carregamento normativo (C1, C2) geram-se:
      • assimétrico: meia-água esq. = Cpb, dir. = Cps
      • reverso:     esq. = Cps, dir. = Cpb  (vento do outro lado)
      • uniforme bv: ambas as águas = Cpb  (envelope conservador)
      • uniforme st: ambas as águas = Cps  (envelope / sucção geral)

    Isto cobre barlavento, sotavento, sucção geral **e** a combinação
    simultânea Cpb+Cps exigida pela tabela — não só extremos uniformes.
    """
    coef = coeficientes_tabela25(tg_beta)
    padroes: list[dict] = []

    for caso in ("C1", "C2"):
        Cpb = coef[caso]["Cpb"]
        Cps = coef[caso]["Cps"]
        padroes.extend([
            {
                "id": f"{caso}_asim",
                "caso_tab": caso,
                "tipo": "assimetrico",
                "C_esq": Cpb,
                "C_dir": Cps,
                "descricao": f"Tab.25 {caso} assimétrico (esq=Cpb, dir=Cps)",
            },
            {
                "id": f"{caso}_rev",
                "caso_tab": caso,
                "tipo": "assimetrico_reverso",
                "C_esq": Cps,
                "C_dir": Cpb,
                "descricao": f"Tab.25 {caso} reverso (esq=Cps, dir=Cpb)",
            },
            {
                "id": f"{caso}_unif_bv",
                "caso_tab": caso,
                "tipo": "uniforme_barlavento",
                "C_esq": Cpb,
                "C_dir": Cpb,
                "descricao": f"Tab.25 {caso} uniforme Cpb (envelope)",
            },
            {
                "id": f"{caso}_unif_st",
                "caso_tab": caso,
                "tipo": "uniforme_sotavento",
                "C_esq": Cps,
                "C_dir": Cps,
                "descricao": f"Tab.25 {caso} uniforme Cps (sucção/pressão geral)",
            },
        ])
    return padroes


# ── θ = 0° — paralelo à cumeeira (estrutura aberta) ───────────────────────────

# Coeficiente de arrasto de elementos prismáticos livres — NBR 6123 §6.3 / Tab. 13
# Valor conservador para seção retangular (pilares MLC): Ca = 1,2
CA_PILAR_RET = 1.2

# Fricção no extradorso (vento paralelo) — ordem de grandeza NBR Cf ≈ 0,02–0,04
# Usa-se 0,04 (superfície «rugosa» / terças) sobre a área em planta da cobertura.
CF_COBERTURA = 0.04


def forca_vento_paralelo_cumeeira(
    params: ParametrosVento,
    b_pilar: float,
    h_pilar: float,
    n_pilares_linha: int,
    n_linhas_portico: int = 2,
    L_cob_m: float | None = None,
    B_cob_m: float | None = None,
) -> dict:
    """
    Força horizontal de vento **paralelo à cumeeira** (θ = 0°).

    Estrutura aberta (sem vedações): a Tab. 25 não governa esta direção.
    Modelo de projeto:
      1) Arrasto nos pilares (elementos livres): F = q · Ca · A_proj
         A_proj = b_pilar × H  (face perpendicular ao vento longitudinal)
      2) Fricção na cobertura: F_f = q · Cf · A_planta

    A força total alimenta:
      • contraventamento longitudinal (cruzes + terças-biela)
      • estabilidade lateral dos pilares (fora do plano do pórtico)

    Args:
        params           : ParametrosVento
        b_pilar, h_pilar : seção do pilar (m) — b face ao vento longitudinal
        n_pilares_linha  : pilares por alinhamento (ao longo do comprimento)
        n_linhas_portico : alinhamentos (tipicamente 2 por pórtico × n pórticos
                           em planta; para 2 pórticos lado a lado = 3 eixos se
                           compartilham central — ver main)
        L_cob_m          : comprimento da cobertura // cumeeira (default L_comp)
        B_cob_m          : largura total ⊥ cumeeira (default 2·L pórtico se n=2)
    """
    q = params.q
    H = params.h

    # Área projetada de um pilar (face ⊥ vento longitudinal)
    A_pil = b_pilar * H                          # m²
    F_pil_kN = q * CA_PILAR_RET * A_pil          # kN por pilar

    n_total = n_pilares_linha * n_linhas_portico
    F_pilares_kN = F_pil_kN * n_total

    # Fricção na cobertura
    if L_cob_m is None:
        L_cob_m = (n_pilares_linha - 1) * params.dist_portico
    if B_cob_m is None:
        B_cob_m = params.L                       # um vão; main pode passar 2·L
    A_planta = max(L_cob_m, 0.0) * max(B_cob_m, 0.0)
    F_fric_kN = q * CF_COBERTURA * A_planta

    F_total_kN = F_pilares_kN + F_fric_kN

    # Pressão linear equivalente no alinhamento de contraventamento (kN/m)
    L_trib = max(L_cob_m, 1e-6)
    w_long_kNpm = F_total_kN / L_trib

    return {
        "theta_deg":        0.0,
        "direcao":          "paralelo à cumeeira (longitudinal)",
        "q_kNm2":           round(q, 4),
        "Ca_pilar":         CA_PILAR_RET,
        "Cf_cobertura":     CF_COBERTURA,
        "A_pilar_m2":       round(A_pil, 4),
        "F_pilar_kN":       round(F_pil_kN, 3),
        "n_pilares":        n_total,
        "F_pilares_kN":     round(F_pilares_kN, 3),
        "A_planta_m2":      round(A_planta, 2),
        "F_friccao_kN":     round(F_fric_kN, 3),
        "F_total_kN":       round(F_total_kN, 3),
        "w_long_kNpm":      round(w_long_kNpm, 4),
        "L_trib_m":         round(L_trib, 3),
        "norma":            "NBR 6123 §6.3 (Ca) + Cf cobertura | estrutura aberta",
        "nota":             (
            "Tab.25 não se aplica a θ=0°. Arrasto em pilares livres + "
            "fricção no extradorso. Força → contraventamento e pilares."
        ),
    }


def forca_vento_pilar_90(
    params: ParametrosVento,
    b_pilar: float,
    h_pilar: float,
) -> dict:
    """
    Arrasto no pilar sob vento θ = 90° (perpendicular à cumeeira).

    Face projetada = h_pilar × H (dimensão no plano do pórtico).
    Em pórtico biarticulado a força horizontal no pilar vai para as
    rótulas (topo/base); a base transmite à sapata. Verifica-se também
    o pilar como elemento livre se o contraventamento de fachada for fraco.
    """
    q = params.q
    H = params.h
    A = h_pilar * H
    F = q * CA_PILAR_RET * A
    # Força repartida topo/base (biarticulado) → V_topo = V_base = F/2
    # Momento máximo no meio se considerar carga uniforme no fuste:
    #   w = F/H ; M_max = w·H²/8 = F·H/8  (biapoiado)
    M_mid = F * H / 8.0
    return {
        "theta_deg":   90.0,
        "direcao":     "perpendicular à cumeeira",
        "q_kNm2":      round(q, 4),
        "Ca":          CA_PILAR_RET,
        "A_proj_m2":   round(A, 4),
        "F_pilar_kN":  round(F, 3),
        "V_rotula_kN": round(F / 2.0, 3),
        "M_mid_kNm":   round(M_mid, 3),
        "norma":       "NBR 6123 §6.3 Ca=1,2 | pilar livre biapoiado",
    }


# ── Resultado agregado ────────────────────────────────────────────────────────

@dataclass
class ResultadoVento:
    """Resultados completos do cálculo de vento (θ=90° Tab.25 + θ=0°)."""
    params:     ParametrosVento
    coef:       dict
    pressoes:   dict          # legado C1/C2 bv/st
    cargas:     dict
    padroes_90: list          # todos os padrões Tab.25
    pressoes_padrao: dict     # id → {w_esq, w_dir} kN/m² e kN/m


def calcular_vento(params: ParametrosVento) -> ResultadoVento:
    """
    Calcula pressões e padrões de carga de vento (θ = 90°, Tab. 25).

    Convenção de sinais:
        Positivo → empurra para baixo (mesma direção do peso próprio)
        Negativo → puxa para cima (sucção)
    """
    tg_b = params.tg_beta
    q    = params.q
    d    = params.dist_portico

    coef = coeficientes_tabela25(tg_b)
    padroes = padroes_cpe_tabela25(tg_b)

    pressoes = {
        "C1": {
            "barlavento_kNm2": coef["C1"]["Cpb"] * q,
            "sotavento_kNm2":  coef["C1"]["Cps"] * q,
        },
        "C2": {
            "barlavento_kNm2": coef["C2"]["Cpb"] * q,
            "sotavento_kNm2":  coef["C2"]["Cps"] * q,
        },
    }
    cargas = {
        "C1": {
            "barlavento_kNm": coef["C1"]["Cpb"] * q * d,
            "sotavento_kNm":  coef["C1"]["Cps"] * q * d,
        },
        "C2": {
            "barlavento_kNm": coef["C2"]["Cpb"] * q * d,
            "sotavento_kNm":  coef["C2"]["Cps"] * q * d,
        },
    }

    pressoes_padrao = {}
    for p in padroes:
        pe = p["C_esq"] * q
        pd = p["C_dir"] * q
        pressoes_padrao[p["id"]] = {
            **p,
            "w_esq_kNm2": pe,
            "w_dir_kNm2": pd,
            "w_esq_kNm":  pe * d,
            "w_dir_kNm":  pd * d,
        }

    return ResultadoVento(
        params=params,
        coef=coef,
        pressoes=pressoes,
        cargas=cargas,
        padroes_90=padroes,
        pressoes_padrao=pressoes_padrao,
    )


def resumo_vento(resultado: ResultadoVento) -> None:
    """Imprime resumo formatado do cálculo de vento."""
    p = resultado.params
    c = resultado.coef
    pr = resultado.pressoes
    ca = resultado.cargas

    print("=" * 68)
    print("  CÁLCULO DE VENTO — NBR 6123 Tabela 25")
    print("  Cobertura isolada a duas águas | θ=90° ⊥ cumeeira")
    print("=" * 68)

    print(f"\n  V0={p.V0:.1f} m/s | S1={p.S1:.2f} | S2={p.S2:.2f} "
          f"(Cat.{p.categoria}/Cl.{p.classe}) | S3={p.S3:.2f}")
    print(f"  Vk={p.Vk:.2f} m/s | q={p.q:.4f} kN/m² | "
          f"tgβ={p.tg_beta:.4f} | β={p.beta_deg:.2f}°")

    print(f"\n  COEFICIENTES Tab.25:")
    print(f"  {'Caso':<6} {'Cpb':>8} {'Cps':>8}")
    for caso in ("C1", "C2"):
        print(f"  {caso:<6} {c[caso]['Cpb']:>+8.4f} {c[caso]['Cps']:>+8.4f}")

    print(f"\n  PADRÕES VARRIDOS ({len(resultado.padroes_90)}):")
    for pid, pp in resultado.pressoes_padrao.items():
        print(f"    {pid:<14} C=({pp['C_esq']:+.3f},{pp['C_dir']:+.3f})  "
              f"w=({pp['w_esq_kNm']:+.3f},{pp['w_dir_kNm']:+.3f}) kN/m  "
              f"— {pp['tipo']}")

    print(f"\n  Legado (pressões uniformes por zona):")
    for caso in ("C1", "C2"):
        print(f"    {caso} bv={pr[caso]['barlavento_kNm2']:+.4f}  "
              f"st={pr[caso]['sotavento_kNm2']:+.4f} kN/m²")
    print("=" * 68)


if __name__ == "__main__":
    params = ParametrosVento(
        V0=45.0, S1=1.0, categoria="IV", classe="B", S3=1.0,
        L=20.25, H1=1.785, h=7.0, dist_portico=5.75,
    )
    resultado = calcular_vento(params)
    resumo_vento(resultado)
    print("\n  θ=0° (exemplo 9 pilares × 3 eixos, b=0,22):")
    f0 = forca_vento_paralelo_cumeeira(
        params, b_pilar=0.22, h_pilar=0.26,
        n_pilares_linha=9, n_linhas_portico=3,
        L_cob_m=46.0, B_cob_m=40.5,
    )
    for k, v in f0.items():
        print(f"    {k}: {v}")
