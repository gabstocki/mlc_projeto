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

from mlc_projeto.core.validacao import (
    DominioInvalidoError,
    exigir_inteiro_minimo,
    exigir_positivo,
)


# ── Tabelas normativas — NBR 6123:2023 §5.3 ──────────────────────────────────
#
# Tabela 1 — Parâmetros meteorológicos: (b_m, p, z_g) por categoria e classe.
# z_g (m) é o contorno superior da camada limite atmosférica, comum às classes.
PARAM_METEOROLOGICOS: dict[str, dict[str, tuple[float, float, float]]] = {
    "I":   {"A": (1.10, 0.060, 250.0), "B": (1.11, 0.065, 250.0), "C": (1.12, 0.070, 250.0)},
    "II":  {"A": (1.00, 0.085, 300.0), "B": (1.00, 0.090, 300.0), "C": (1.00, 0.100, 300.0)},
    "III": {"A": (0.94, 0.100, 350.0), "B": (0.94, 0.105, 350.0), "C": (0.93, 0.115, 350.0)},
    "IV":  {"A": (0.86, 0.120, 420.0), "B": (0.85, 0.125, 420.0), "C": (0.84, 0.135, 420.0)},
    "V":   {"A": (0.74, 0.150, 500.0), "B": (0.73, 0.160, 500.0), "C": (0.71, 0.175, 500.0)},
}

# Tabela 2 — Fator de rajada F_r, por classe (sempre referido à Categoria II).
FATOR_RAJADA: dict[str, float] = {"A": 1.00, "B": 0.98, "C": 0.95}

# §4.2 c) — q = ½·ρ·Vk², com ρ = 1,226 kg/m³ (ar a 15 °C, 1 atm) ⇒ q = 0,613·Vk²
# em N/m². O fator 1e-3 leva a kN/m², unidade interna do projeto.
COEF_PRESSAO_DINAMICA = 0.613e-3


def q_de_Vk(Vk: float) -> float:
    """Pressão dinâmica q (kN/m²) a partir de Vk (m/s) — NBR 6123:2023 §4.2 c)."""
    return COEF_PRESSAO_DINAMICA * Vk ** 2


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
    # Profundidade ℓ2 da cobertura (m) — dimensão horizontal PERPENDICULAR à
    # cumeeira, medida na direção do vento de θ=90° (ver figura da Tabela 25).
    # None → adota-se ℓ2 = L (um vão). Com vãos múltiplos lado a lado, ℓ2 deve
    # ser informado explicitamente, pois é a profundidade TOTAL da cobertura.
    l2:           float | None = None
    # Número de tramos (águas duplas) lado a lado ao longo de ℓ2. n=1 é a
    # cobertura isolada a duas águas da Tabela 25; n≥2 é telhado múltiplo.
    n_tramos:     int = 1
    # §7.2.1: obstruções que possam ser colocadas SOB ou junto à cobertura
    # (p.ex. veículos num estacionamento coberto) acionam, por si só, a rota
    # de edificação fechada — independentemente de a altura h ser suficiente.
    obstrucoes_sob_cobertura: bool = False

    def __post_init__(self):
        if self.categoria not in PARAM_METEOROLOGICOS:
            raise ValueError(
                f"categoria='{self.categoria}' inválida. Categorias: I–V "
                f"(NBR 6123:2023 §5.3.1)."
            )
        if self.classe not in FATOR_RAJADA:
            raise ValueError(
                f"classe='{self.classe}' inválida. Classes: A, B, C "
                f"(NBR 6123:2023 §5.3.2)."
            )

    # ── Fator S2 — NBR 6123:2023 §5.3.3 ──────────────────────────────────────

    @property
    def l2_efetivo(self) -> float:
        """Profundidade ℓ2 adotada (m)."""
        return float(self.L if self.l2 is None else self.l2)

    def S2_em(self, z: float) -> float:
        """
        Fator S2 na altura z acima do nível geral do terreno — §5.3.3:

            S2 = b_m · F_r · (z/10)^p

        b_m e p vêm da Tabela 1 (por categoria e classe); F_r da Tabela 2
        (por classe, sempre referido à Categoria II). Válido até z = z_g,
        contorno superior da camada limite atmosférica.

        AUD-001: a versão anterior devolvia uma constante por
        (categoria, classe), que equivale a congelar S2 em z = 10 m — os
        valores tabelados batiam exatamente com a linha z=10 da Tabela 3.
        O efeito da altura sobre a pressão dinâmica estava suprimido.
        """
        z = exigir_positivo("z", z, unidade="m")
        b_m, p, z_g = PARAM_METEOROLOGICOS[self.categoria][self.classe]
        F_r = FATOR_RAJADA[self.classe]

        if z > z_g:
            raise DominioInvalidoError(
                f"z = {z:.3f} m acima de z_g = {z_g:.0f} m (categoria "
                f"{self.categoria}). A expressão de §5.3.3 só é aplicável "
                f"dentro da camada limite atmosférica."
            )
        # §5.3.3: "o fator S2 é considerado constante até 10 m de altura na
        # categoria V" — coerente com a Tabela 3, cujas linhas z<5 e z=10
        # coincidem apenas nessa categoria.
        z_ef = max(z, 10.0) if self.categoria == "V" else z
        return b_m * F_r * (z_ef / 10.0) ** p

    @property
    def z_ref(self) -> float:
        """
        Altura de referência da estrutura (m) — topo da cobertura.

        §5.3.3 recomenda o S2 do topo da edificação para o estudo dos
        elementos de vedação; adota-se a mesma cota como referência global
        das forças da cobertura, por ser a mais desfavorável do perfil.
        """
        return self.H_max

    @property
    def S2(self) -> float:
        """S2 na altura de referência da estrutura (topo da cobertura)."""
        return self.S2_em(self.z_ref)

    @property
    def Vk(self) -> float:
        return self.V0 * self.S1 * self.S2 * self.S3

    def Vk_em(self, z: float) -> float:
        """Velocidade característica na altura z — §4.2 b)."""
        return self.V0 * self.S1 * self.S2_em(z) * self.S3

    @property
    def q(self) -> float:
        """Pressão dinâmica q (kN/m²) na altura de referência — §4.2 c)."""
        return q_de_Vk(self.Vk)

    def q_em(self, z: float) -> float:
        """Pressão dinâmica q (kN/m²) na altura z — §4.2 c)."""
        return q_de_Vk(self.Vk_em(z))

    @property
    def tg_beta(self) -> float:
        return self.H1 / (self.L / 2)

    @property
    def beta_deg(self) -> float:
        return math.degrees(math.atan(self.tg_beta))

    @property
    def H_max(self) -> float:
        return self.h + self.H1

    # ── Seleção da rota normativa — §7.2 ─────────────────────────────────────

    @property
    def a_linha(self) -> float:
        """Largura a' de cada tramo (m) = ℓ2 / n_tramos."""
        return self.l2_efetivo / self.n_tramos

    @property
    def rota_normativa(self) -> str:
        """
        Qual disposição do §7.2 governa os coeficientes de pressão.

        "tabela25"            — cobertura isolada a duas águas, dentro do
                                domínio geométrico e sem obstruções previstas.
        "edificacao_fechada"  — rota do último parágrafo de §7.2.1: h < 0,5·ℓ2,
                                OU obstruções sob/junto à cobertura, OU telhado
                                múltiplo (que as Tabelas 24/25 não cobrem).
        """
        if self.obstrucoes_sob_cobertura:
            return "edificacao_fechada"
        if self.n_tramos > 1:
            return "edificacao_fechada"
        if self.h < 0.5 * self.l2_efetivo:
            return "edificacao_fechada"
        return "tabela25"


# ── Rota alternativa do §7.2.1 — edificação fechada de mesma cobertura ───────
#
# Quando h < 0,5·ℓ2, OU quando obstruções possam ser colocadas sob ou junto à
# cobertura, §7.2.1 determina: "esta deve resistir à ação do vento, na zona de
# obstrução, calculada para uma edificação fechada e de mesma cobertura, com
# cpi = +0,8, para obstruções na borda de sotavento, e com cpi = −0,3, para
# obstruções na borda de barlavento."
CPI_OBSTRUCAO_SOTAVENTO  = +0.8
CPI_OBSTRUCAO_BARLAVENTO = -0.3

# Tabela 10 — Coeficientes de pressão e de forma, externos, para telhados
# múltiplos, simétricos, de tramos iguais, com h ≤ a'. Vento α = 0°
# (perpendicular às cumeeiras). Zonas ao longo da profundidade, do barlavento
# para o sotavento: (a*,b*) 1.º tramo, (c*,d*) 2.º, (m*,n*) intermédios,
# (x*,z*) último. Em cada par, o primeiro rótulo é a água de BARLAVENTO.
#
# NOTA da tabela: "para α = 0°, as forças horizontais de atrito já estão
# consideradas nos valores da Tabela 10".
TABELA_10_THETA = (5.0, 10.0, 20.0, 30.0, 45.0)
TABELA_10_CE: dict[str, tuple[float, ...]] = {
    #        θ =   5°     10°     20°     30°     45°
    "a": (-0.9, -1.1, -0.7, -0.2, +0.3),
    "b": (-0.6, -0.6, -0.6, -0.6, -0.6),
    "c": (-0.4, -0.4, -0.4, -0.4, -0.6),
    "d": (-0.3, -0.3, -0.3, -0.3, -0.4),
    "m": (-0.3, -0.3, -0.3, -0.2, -0.2),
    "n": (-0.3, -0.3, -0.3, -0.3, -0.4),
    "x": (-0.3, -0.3, -0.3, -0.2, -0.2),
    "z": (-0.3, -0.4, -0.5, -0.5, -0.5),
}


def coeficientes_tabela10(theta_deg: float) -> dict[str, float]:
    """
    Coeficientes externos Ce da Tabela 10 (α = 0°), interpolados em θ.

    A tabela é discreta em θ = 5°, 10°, 20°, 30° e 45°; adota-se interpolação
    linear entre linhas, prática corrente para as tabelas da NBR 6123. Fora
    desse intervalo não há extrapolação: a tabela é recusada.
    """
    theta_deg = exigir_positivo("theta_deg", theta_deg, unidade="graus")
    lo, hi = TABELA_10_THETA[0], TABELA_10_THETA[-1]
    if not (lo <= theta_deg <= hi):
        raise ValueError(
            f"θ = {theta_deg:.3f}° fora do intervalo tabelado da Tabela 10 "
            f"({lo:.0f}° a {hi:.0f}°). A norma não autoriza extrapolação."
        )
    xs = TABELA_10_THETA
    i = next(k for k in range(len(xs) - 1) if xs[k] <= theta_deg <= xs[k + 1])
    t = (theta_deg - xs[i]) / (xs[i + 1] - xs[i])
    return {
        zona: vals[i] + t * (vals[i + 1] - vals[i])
        for zona, vals in TABELA_10_CE.items()
    }


def zonas_por_tramo(n_tramos: int) -> list[tuple[str, str]]:
    """
    Rótulos (barlavento, sotavento) de cada tramo, do barlavento ao sotavento.

    1.º tramo → (a*, b*); 2.º → (c*, d*); intermédios → (m*, n*);
    último → (x*, z*).

    Com exatamente DOIS tramos o segundo é simultaneamente "2.º" e "último".
    Adota-se (c*, d*) — decisão de projeto registrada, por ser a atribuição
    posicional direta da tabela.
    """
    n = exigir_inteiro_minimo("n_tramos", n_tramos, minimo=1)
    if n == 1:
        return [("a", "b")]
    if n == 2:
        return [("a", "b"), ("c", "d")]
    return [("a", "b"), ("c", "d")] + [("m", "n")] * (n - 3) + [("x", "z")]


def padroes_cpe_edificacao_fechada(theta_deg: float, n_tramos: int) -> list[dict]:
    """
    Padrões de coeficiente LÍQUIDO para um pórtico, pela rota do §7.2.1.

        c_net = c_pe (Tabela 10) − c_pi (+0,8 ou −0,3)

    Um mesmo pórtico é dimensionado para qualquer posição que ocupe na
    cobertura e para o vento incidindo por qualquer dos dois lados; as
    obstruções (veículos) podem estar tanto na borda de barlavento como na de
    sotavento. Varrem-se, portanto, todas as combinações
    tramo × sentido do vento × posição da obstrução.
    """
    ce = coeficientes_tabela10(theta_deg)
    zonas = zonas_por_tramo(n_tramos)
    padroes: list[dict] = []

    for t, (zb, zs) in enumerate(zonas, start=1):
        ce_bar, ce_sot = ce[zb], ce[zs]
        for sentido, (c_esq_pe, c_dir_pe) in (
            ("esq",  (ce_bar, ce_sot)),   # vento incidindo pela esquerda
            ("dir",  (ce_sot, ce_bar)),   # vento incidindo pela direita
        ):
            for rotulo_cpi, cpi in (
                ("cpi+0.8", CPI_OBSTRUCAO_SOTAVENTO),
                ("cpi-0.3", CPI_OBSTRUCAO_BARLAVENTO),
            ):
                padroes.append({
                    "id": f"T10_t{t}_{sentido}_{rotulo_cpi}",
                    "caso_tab": f"Tab.10 tramo {t} ({zb}*/{zs}*)",
                    "tipo": "edificacao_fechada_com_cpi",
                    "C_esq": c_esq_pe - cpi,
                    "C_dir": c_dir_pe - cpi,
                    "c_pe_esq": c_esq_pe,
                    "c_pe_dir": c_dir_pe,
                    "c_pi": cpi,
                    "descricao": (
                        f"§7.2.1 rota de edificação fechada — Tab.10 tramo {t}, "
                        f"vento pela {'esquerda' if sentido == 'esq' else 'direita'}, "
                        f"c_pi={cpi:+.1f}"
                    ),
                })
    return padroes


# ── Domínio de validade das Tabelas 24/25 — §7.2.1 ───────────────────────────

def validar_dominio_cobertura_isolada(params: ParametrosVento) -> None:
    """
    Verifica as condições de aplicabilidade da Tabela 25 — NBR 6123:2023 §7.2.1.

    A norma é explícita: "Os coeficientes das Tabelas 24 e 25 se aplicam somente
    quando forem satisfeitas as seguintes condições: Coberturas a duas águas
    (ver a Tabela 25): 0,07 ≤ tg θ ≤ 0,6 **e h ≥ 0,5 ℓ2**", onde

        h  é a altura livre entre o piso e o nível da aresta horizontal mais
           baixa da cobertura (beiral);
        ℓ2 é a profundidade da cobertura — dimensão horizontal medida
           PERPENDICULARMENTE à cumeeira (direção do vento de θ=90°).

    A condição `h ≥ 0,5·ℓ2` garante que a cobertura está sobre "suportes de
    reduzidas dimensões" e não constitui obstáculo significativo ao escoamento,
    de modo que o vento atue livremente sobre as faces superior E inferior.

    Fora desse domínio a norma NÃO permite extrapolar a tabela: §7.2.1 prescreve
    outra rota — "Para os casos em que a altura h for inferior aos limites de
    7.2.1, ou em que obstruções possam ser colocadas sob ou junto à cobertura,
    esta deve resistir à ação do vento, na zona de obstrução, calculada para uma
    edificação fechada e de mesma cobertura, com cpi = +0,8, para obstruções na
    borda de sotavento, e com cpi = −0,3, para obstruções na borda de
    barlavento."

    Essa rota alternativa exige coeficientes de forma de edificação fechada
    (§6.1) e não está implementada neste módulo — daí a recusa explícita em vez
    de um resultado silenciosamente inválido (AUD-002).

    Raises:
        ValueError: geometria fora do domínio declarado da Tabela 25.
    """
    h  = params.h
    l2 = params.l2_efetivo
    h_min = 0.5 * l2

    if h < h_min:
        raise ValueError(
            f"Fora do domínio da Tabela 25 (NBR 6123:2023 §7.2.1): exige-se "
            f"h ≥ 0,5·ℓ2, ou seja h ≥ {h_min:.3f} m para ℓ2 = {l2:.3f} m, mas "
            f"h = {h:.3f} m.\n"
            f"h é a altura livre até a aresta horizontal mais baixa da cobertura "
            f"e ℓ2 é a profundidade da cobertura medida ⊥ à cumeeira.\n"
            f"A norma não autoriza extrapolar a tabela. Nesse caso §7.2.1 "
            f"prescreve calcular a cobertura, na zona de obstrução, como "
            f"EDIFICAÇÃO FECHADA de mesma cobertura, com cpi = +0,8 (obstruções "
            f"na borda de sotavento) ou cpi = −0,3 (borda de barlavento). "
            f"Essa rota não está implementada.\n"
            f"Se a profundidade adotada estiver errada, informe "
            f"ParametrosVento(l2=...) — o default é ℓ2 = L (um vão), e uma "
            f"cobertura de vãos múltiplos tem ℓ2 igual à profundidade TOTAL."
        )


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

    A Tabela 25 fornece, para cada carregamento (1 e 2), um PAR simultâneo
    (Cpb, Cps): Cpb atua na água de barlavento e Cps na de sotavento, ao mesmo
    tempo, como mostra a figura "sentidos positivos" da tabela. §7.2.1: "Nos
    casos em que são indicados dois carregamentos, as duas situações
    respectivas de forças devem ser consideradas independentemente."

    Geram-se, portanto, apenas:
      • assimétrico: meia-água esq. = Cpb, dir. = Cps  (vento pela esquerda)
      • reverso:     esq. = Cps, dir. = Cpb            (vento pela direita)

    O reverso é o espelhamento geométrico do mesmo caso normativo — a cobertura
    é simétrica e o vento de θ=90° pode incidir por qualquer dos dois lados.

    AUD-004: a versão anterior acrescentava padrões UNIFORMES (Cpb em ambas as
    águas, Cps em ambas), rotulados "envelope conservador". Não são
    carregamentos da Tabela 25: recombinam extremos de faces distintas e
    destroem a correlação espacial que o caso de carga define. O caso que
    governava a flexão no projeto (`C1_unif_bv`) era um desses padrões
    fabricados. Um envelope só pode ser formado por campos de pressão que a
    norma admite existirem simultaneamente.
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
                "descricao": f"Tab.25 {caso}: Cpb barlavento (esq) + Cps sotavento (dir)",
            },
            {
                "id": f"{caso}_rev",
                "caso_tab": caso,
                "tipo": "assimetrico_reverso",
                "C_esq": Cps,
                "C_dir": Cpb,
                "descricao": f"Tab.25 {caso} espelhado: vento incidindo pela direita",
            },
        ])
    return padroes


# ── θ = 0° — paralelo à cumeeira (estrutura aberta) ───────────────────────────

# Coeficiente de arrasto de elementos prismáticos livres — NBR 6123 §6.3 / Tab. 13
# Valor conservador para seção retangular (pilares MLC): Ca = 1,2
CA_PILAR_RET = 1.2

# NBR 6123:2023 §7.2.2 — Forças de atrito na cobertura isolada, para vento
# paralelo à geratriz: Ft = 0,5·q·a·b, com a e b as dimensões EM PLANTA da
# cobertura. "Estas forças englobam a ação do vento sobre as duas faces da
# cobertura" — não é um coeficiente de atrito superficial aplicado a uma face.
COEF_ATRITO_COBERTURA_ISOLADA = 0.5


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
      2) Atrito na cobertura isolada (§7.2.2): Ft = 0,5 · q · a · b
         — equação específica, já englobando as duas faces da cobertura

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
    # ── §7.2.2 — Ft = 0,5·q·a·b (AUD-003) ────────────────────────────────
    # A versão anterior usava F = q·Cf·A_planta com Cf=0,04, um coeficiente de
    # atrito superficial genérico cujo próprio comentário admitia ser "ordem de
    # grandeza". A norma prescreve equação específica para cobertura isolada,
    # já integrando as DUAS faces: o resultado era 12,5× menor que o normativo.
    a_m = max(L_cob_m, 0.0)
    b_m = max(B_cob_m, 0.0)
    A_planta = a_m * b_m
    F_fric_kN = COEF_ATRITO_COBERTURA_ISOLADA * q * a_m * b_m

    F_total_kN = F_pilares_kN + F_fric_kN

    # Pressão linear equivalente no alinhamento de contraventamento (kN/m)
    L_trib = max(L_cob_m, 1e-6)
    w_long_kNpm = F_total_kN / L_trib

    return {
        "theta_deg":        0.0,
        "direcao":          "paralelo à cumeeira (longitudinal)",
        "q_kNm2":           round(q, 4),
        "Ca_pilar":         CA_PILAR_RET,
        "coef_atrito_7_2_2": COEF_ATRITO_COBERTURA_ISOLADA,
        "A_pilar_m2":       round(A_pil, 4),
        "F_pilar_kN":       round(F_pil_kN, 3),
        "n_pilares":        n_total,
        "F_pilares_kN":     round(F_pilares_kN, 3),
        "A_planta_m2":      round(A_planta, 2),
        "F_friccao_kN":     round(F_fric_kN, 3),
        "F_total_kN":       round(F_total_kN, 3),
        "w_long_kNpm":      round(w_long_kNpm, 4),
        "L_trib_m":         round(L_trib, 3),
        "norma":            (
            "NBR 6123:2023 §6.3 (Ca dos pilares) + §7.2.2 (Ft = 0,5·q·a·b)"
        ),
        "nota":             (
            "Tab.25 não se aplica a θ=0°. Arrasto em pilares livres + força de "
            "atrito da cobertura isolada por §7.2.2, que engloba as duas faces. "
            "Força → contraventamento longitudinal, frontões e pilares."
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
    rota = params.rota_normativa

    if rota == "tabela25":
        # Cobertura isolada a duas águas dentro do domínio declarado (§7.2.1).
        validar_dominio_cobertura_isolada(params)
        tg_b    = params.tg_beta
        coef    = coeficientes_tabela25(tg_b)
        padroes = padroes_cpe_tabela25(tg_b)
    else:
        # Rota do último parágrafo de §7.2.1 — edificação fechada de mesma
        # cobertura, com c_pi de obstrução. Ver `rota_normativa` para os
        # gatilhos. A Tabela 10 exige h ≤ a'.
        if params.h > params.a_linha:
            raise ValueError(
                f"Tabela 10 exige h ≤ a' (largura do tramo): h = {params.h:.3f} m "
                f"contra a' = {params.a_linha:.3f} m. Fora do domínio tabelado."
            )
        coef    = coeficientes_tabela10(params.beta_deg)
        padroes = padroes_cpe_edificacao_fechada(params.beta_deg, params.n_tramos)

    q = params.q
    d = params.dist_portico

    # Campos legados C1/C2: na rota da Tabela 25 são os dois carregamentos
    # normativos. Na rota de edificação fechada não existe essa dupla — usa-se
    # o envelope dos padrões (C1 = menos severo, C2 = sucção governante) apenas
    # para preservar o contrato de dados a jusante.
    if rota == "tabela25":
        _c1 = (coef["C1"]["Cpb"], coef["C1"]["Cps"])
        _c2 = (coef["C2"]["Cpb"], coef["C2"]["Cps"])
    else:
        _menos = min(padroes, key=lambda p: abs(min(p["C_esq"], p["C_dir"])))
        _mais  = min(padroes, key=lambda p: min(p["C_esq"], p["C_dir"]))
        _c1 = (_menos["C_esq"], _menos["C_dir"])
        _c2 = (_mais["C_esq"],  _mais["C_dir"])

    pressoes = {
        "C1": {"barlavento_kNm2": _c1[0] * q, "sotavento_kNm2": _c1[1] * q},
        "C2": {"barlavento_kNm2": _c2[0] * q, "sotavento_kNm2": _c2[1] * q},
    }
    cargas = {
        "C1": {"barlavento_kNm": _c1[0] * q * d, "sotavento_kNm": _c1[1] * q * d},
        "C2": {"barlavento_kNm": _c2[0] * q * d, "sotavento_kNm": _c2[1] * q * d},
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
