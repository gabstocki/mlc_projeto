"""
core/wind.py — Carregamento de vento conforme NBR 6123.

Cobertura isolada a duas águas simétricas — Tabela 25.
Vento perpendicular à cumeeira.

Estrutura: 2 pórticos independentes, cada um com vão L = 20,25 m.
Vão total do galpão = 40,50 m.

Referência: ABNT NBR 6123:2023
"""

from dataclasses import dataclass
import math


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
    V0:           float = 45.0   # m/s — Londrina, PR
    S1:           float = 1.0    # terreno plano
    categoria:    str   = "IV"   # rugosidade urbana
    classe:       str   = "B"    # maior dimensão entre 20 e 50 m
    S3:           float = 1.0    # grupo 2 — edificações em geral
    L:            float = 20.25  # m — vão de cada pórtico
    H1:           float = 1.0    # m — variação de altura da cobertura
    h:            float = 7.0    # m — pé-direito
    dist_portico: float = 5.75   # m — espaçamento entre pórticos

    # Tabela de S2 — NBR 6123 Tabela 3
    # chave: (categoria, classe)
    _S2_TABLE: dict = None

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
        """Fator de rugosidade S2 — NBR 6123 Tabela 3."""
        key = (self.categoria, self.classe)
        if key not in self._S2_TABLE:
            raise ValueError(
                f"Combinação categoria='{self.categoria}' classe='{self.classe}' "
                f"não encontrada. Categorias: I–V. Classes: A, B, C."
            )
        return self._S2_TABLE[key]

    @property
    def Vk(self) -> float:
        """Velocidade característica Vk (m/s) — NBR 6123 §5.1."""
        return self.V0 * self.S1 * self.S2 * self.S3

    @property
    def q(self) -> float:
        """Pressão dinâmica q (kN/m²) — NBR 6123 §6.2."""
        return 0.613e-3 * self.Vk ** 2   # 0,613 Pa·s²/m² → kN/m²

    @property
    def tg_beta(self) -> float:
        """
        Tangente do ângulo de inclinação β.

        O ângulo é definido pela variação de altura H1 sobre o quarto
        do vão (L/2), pois a cumeeira está no centro do pórtico:
        tg β = H1 / (L/2)
        """
        return self.H1 / (self.L / 2)

    @property
    def beta_deg(self) -> float:
        """Ângulo de inclinação β (graus)."""
        return math.degrees(math.atan(self.tg_beta))

    @property
    def H_max(self) -> float:
        """Altura máxima da estrutura (m) — pé-direito + variação."""
        return self.h + self.H1


def coeficientes_tabela25(tg_beta: float) -> dict:
    """
    Coeficientes de pressão Cpb e Cps — NBR 6123 Tabela 25.

    Cobertura isolada a duas águas simétricas.
    Vento perpendicular à cumeeira.

    Intervalos válidos: 0,07 ≤ tg β ≤ 0,6

    Args:
        tg_beta: Tangente do ângulo de inclinação

    Returns:
        dict com Cpb e Cps para Carregamento 1 e Carregamento 2
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
        # Carregamento 1
        Cpb_1 = 2.4 * tg_beta + 0.6
        Cps_1 = 3.0 * tg_beta - 0.5
        # Carregamento 2
        Cpb_2 = 0.6 * tg_beta - 0.74
        Cps_2 = -1.0

    else:  # 0.4 < tg_beta <= 0.6
        # Carregamento 1
        Cpb_1 = min(2.4 * tg_beta + 0.6, 2.0)
        Cps_1 = +0.7
        # Carregamento 2
        Cpb_2 = 6.5 * tg_beta - 3.1
        Cps_2 = 5.0 * tg_beta - 3.0

    return {
        "C1": {"Cpb": Cpb_1, "Cps": Cps_1},
        "C2": {"Cpb": Cpb_2, "Cps": Cps_2},
    }


@dataclass
class ResultadoVento:
    """Resultados completos do cálculo de vento."""
    params:    ParametrosVento
    coef:      dict
    pressoes:  dict   # pressões em kN/m²
    cargas:    dict   # cargas lineares na viga em kN/m


def calcular_vento(params: ParametrosVento) -> ResultadoVento:
    """
    Calcula as pressões e cargas de vento sobre a viga.

    Convenção de sinais (Tabela 25):
        Positivo → empurra para baixo (mesma direção do peso próprio)
        Negativo → puxa para cima (sucção — contrário ao peso próprio)

    Para o dimensionamento, avalia os dois carregamentos e
    retorna os valores em módulo para cada situação.

    Args:
        params: Parâmetros geométricos e de vento

    Returns:
        ResultadoVento com coeficientes, pressões e cargas lineares
    """
    tg_b = params.tg_beta
    q    = params.q
    d    = params.dist_portico  # espaçamento entre pórticos

    coef = coeficientes_tabela25(tg_b)

    # ── Pressões por zona (kN/m²) ─────────────────────────────
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

    # ── Cargas lineares na viga (kN/m) ────────────────────────
    # Cada meia água recebe carga de uma zona (barlavento ou sotavento)
    # A carga linear = pressão × distância entre pórticos
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

    return ResultadoVento(
        params=params,
        coef=coef,
        pressoes=pressoes,
        cargas=cargas,
    )


def resumo_vento(resultado: ResultadoVento) -> None:
    """Imprime resumo formatado do cálculo de vento."""
    p = resultado.params
    c = resultado.coef
    pr = resultado.pressoes
    ca = resultado.cargas

    print("=" * 58)
    print("  CÁLCULO DE VENTO — NBR 6123 Tabela 25")
    print("  Cobertura isolada a duas águas — vento perpendicular")
    print("=" * 58)

    print(f"\n{'PARÂMETROS GERAIS':}")
    print(f"  V0          = {p.V0:.1f} m/s")
    print(f"  S1          = {p.S1:.2f}")
    print(f"  S2          = {p.S2:.2f}  (Cat. {p.categoria}, Classe {p.classe})")
    print(f"  S3          = {p.S3:.2f}")
    print(f"  Vk          = {p.Vk:.2f} m/s")
    print(f"  q           = {p.q:.4f} kN/m²")

    print(f"\n{'GEOMETRIA':}")
    print(f"  Vão (L)     = {p.L:.2f} m  (cada pórtico)")
    print(f"  H1          = {p.H1:.2f} m  (variação de altura)")
    print(f"  h           = {p.h:.2f} m  (pé-direito)")
    print(f"  H_max       = {p.H_max:.2f} m")
    print(f"  tg β        = {p.tg_beta:.4f}")
    print(f"  β           = {p.beta_deg:.2f}°")

    print(f"\n{'COEFICIENTES — TABELA 25':}")
    print(f"  {'Caso':<14} {'Cpb':>8} {'Cps':>8}")
    print(f"  {'-'*30}")
    for caso in ["C1", "C2"]:
        label = "Carregamento 1" if caso == "C1" else "Carregamento 2"
        print(f"  {label:<14} {c[caso]['Cpb']:>8.4f} {c[caso]['Cps']:>8.4f}")

    print(f"\n{'PRESSÕES RESULTANTES (kN/m²)':}")
    print(f"  {'Caso':<14} {'Barlavento':>12} {'Sotavento':>12}")
    print(f"  {'-'*40}")
    for caso in ["C1", "C2"]:
        label = "Carregamento 1" if caso == "C1" else "Carregamento 2"
        bv = pr[caso]["barlavento_kNm2"]
        sv = pr[caso]["sotavento_kNm2"]
        print(f"  {label:<14} {bv:>+12.4f} {sv:>+12.4f}")

    print(f"\n{'CARGAS LINEARES NA VIGA (kN/m)  d = '+str(p.dist_portico)+' m':}")
    print(f"  {'Caso':<14} {'Barlavento':>12} {'Sotavento':>12}")
    print(f"  {'-'*40}")
    for caso in ["C1", "C2"]:
        label = "Carregamento 1" if caso == "C1" else "Carregamento 2"
        bv = ca[caso]["barlavento_kNm"]
        sv = ca[caso]["sotavento_kNm"]
        print(f"  {label:<14} {bv:>+12.4f} {sv:>+12.4f}")

    print(f"\n{'NOTA':}")
    print("  Positivo = empurra para baixo (mesma direção do peso próprio)")
    print("  Negativo = puxa para cima (sucção)")
    print("  Para o dimensionamento, avaliar cada carregamento")
    print("  e verificar qual combinação é mais desfavorável.")
    print("=" * 58)


# ── Execução direta para teste ────────────────────────────────
if __name__ == "__main__":
    params = ParametrosVento(
        V0=45.0, S1=1.0, categoria="IV", classe="B", S3=1.0,
        L=20.25, H1=1.0, h=7.0, dist_portico=5.75,
    )
    resultado = calcular_vento(params)
    resumo_vento(resultado)
