"""
core/normativo.py — Base normativa e proveniência dos NDP.

Achado AUD-015 da auditoria
---------------------------
"O projeto não declara `EUROCODE_BASE + NATIONAL_ANNEX`. [...] `γG`, `γQ`, `ψ`,
`γM`, `kcr` e limites são constantes de módulo, sem objeto de configuração,
edição normativa ou origem EN/NA. [...] O repositório não diferencia
*Recommended value from EN* de *Nationally Determined Parameter*."

A questão de fundo deste projeto
--------------------------------
A estrutura fica no **Brasil**: o vento é calculado pela ABNT NBR 6123:2023 e o
dimensionamento da madeira pelos Eurocódigos. Ora, o Brasil **não publica Anexo
Nacional aos Eurocódigos** — eles não são normas nacionais brasileiras. Não
existe, portanto, NA a adotar.

A saída honesta não é inventar um NA nem escolher o de um país europeu ao
acaso: é declarar explicitamente que **todos os NDP usam o valor RECOMENDADO
do próprio EN**, por decisão de projeto, e registar isso em cada parâmetro. O
JRC é claro em que os valores recomendados podem ser adotados, desde que a
adoção seja explícita — é exatamente o que este módulo torna auditável.

Consequência que deve constar do memorial: os resultados são conformes ao texto
EN com valores recomendados, e **não** a uma adoção nacional. Se a obra vier a
ser submetida sob um NA concreto, os parâmetros marcados `NDP` têm de ser
revistos um a um.

Classificação usada em `origem`
-------------------------------
    "EN"            — valor prescrito pelo EN, não sujeito a escolha nacional.
    "EN-recomendado"— NDP: o EN recomenda, o NA pode alterar. Aqui adota-se o
                      recomendado, por ausência de NA.
    "PROJETO"       — especificação do projeto (não normalizada); a norma não
                      fixa valor e a escolha é do projetista.
    "ABNT"          — valor da norma brasileira aplicável (ações de vento).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True)
class ParametroNormativo:
    """Um parâmetro com valor, cláusula de origem e natureza (NDP ou não)."""
    valor:    float | str | bool
    clausula: str
    origem:   str
    nota:     str = ""

    @property
    def e_ndp(self) -> bool:
        """True quando o valor é um Nationally Determined Parameter."""
        return self.origem == "EN-recomendado"


EUROCODE_BASE = "EN 1990:2002 + EN 1991-1-1:2002 + EN 1995-1-1:2004/A1:2008"

NATIONAL_ANNEX = (
    "NENHUM — o Brasil não publica Anexo Nacional aos Eurocódigos. "
    "Adotam-se os VALORES RECOMENDADOS do EN, por decisão de projeto "
    "declarada. Resultados dependentes de NDP devem ser revistos caso a obra "
    "seja submetida sob um Anexo Nacional concreto."
)

NORMA_VENTO = "ABNT NBR 6123:2023"


def _p(valor, clausula, origem, nota=""):
    return ParametroNormativo(valor=valor, clausula=clausula, origem=origem, nota=nota)


#: Proveniência de cada parâmetro que entra no cálculo.
NDP_SOURCE: Mapping[str, ParametroNormativo] = MappingProxyType({
    # ── EN 1990 — coeficientes parciais de ações ──────────────────────────
    "gamma_G_sup": _p(1.35, "EN 1990 Tab. A1.2(B), STR/GEO", "EN-recomendado",
                      "permanente desfavorável"),
    "gamma_G_inf": _p(1.00, "EN 1990 Tab. A1.2(B), STR/GEO", "EN-recomendado",
                      "permanente favorável; NÃO 0,90 da prática ABNT"),
    "gamma_G_EQU_estab":    _p(0.90, "EN 1990 Tab. A1.2(A), EQU", "EN-recomendado",
                               "permanente estabilizante (uplift)"),
    "gamma_G_EQU_desestab": _p(1.10, "EN 1990 Tab. A1.2(A), EQU", "EN-recomendado",
                               "permanente desestabilizante"),
    "gamma_Q":     _p(1.50, "EN 1990 Tab. A1.2(B), STR/GEO", "EN-recomendado",
                      "ação variável desfavorável"),

    # ── EN 1990 / EN 1991-1-1 — fatores ψ ────────────────────────────────
    "psi_0_Q": _p(0.00, "EN 1990 Tab. A1.1, categoria H", "EN-recomendado",
                  "cobertura não acessível (só manutenção)"),
    "psi_1_Q": _p(0.00, "EN 1990 Tab. A1.1, categoria H", "EN-recomendado"),
    "psi_2_Q": _p(0.00, "EN 1990 Tab. A1.1, categoria H", "EN-recomendado"),
    "psi_0_W": _p(0.60, "EN 1990 Tab. A1.1, vento", "EN-recomendado"),
    "psi_2_W": _p(0.00, "EN 1990 Tab. A1.1, vento", "EN-recomendado"),
    "Q_e_W_nao_concomitantes": _p(
        True, "EN 1991-1-1 §3.3.2(1)", "EN",
        "sobrecarga de cobertura cat. H não atua com vento nem neve"),

    # ── EN 1995-1-1 — material ───────────────────────────────────────────
    "gamma_M_madeira": _p(1.25, "EN 1995-1-1 Tab. 2.3", "EN-recomendado",
                          "MLC — peças"),
    "gamma_M_ligacao": _p(1.30, "EN 1995-1-1 Tab. 2.3", "EN-recomendado"),
    "k_cr":            _p(0.67, "EN 1995-1-1 §6.1.7 (A1:2008)", "EN-recomendado",
                          "fator de fissuração; b_ef = k_cr·b"),
    "k_mod":  _p("Tab. 3.1", "EN 1995-1-1 Tab. 3.1", "EN",
                 "tabelado por classe de serviço e duração"),
    "k_def":  _p("Tab. 3.2", "EN 1995-1-1 Tab. 3.2", "EN",
                 "CS3 = 2,00 — fluência elevada, estrutura exterior"),
    "k_m":    _p(0.70, "EN 1995-1-1 §6.1.6(2)", "EN", "seção retangular"),
    "beta_c": _p(0.10, "EN 1995-1-1 §6.3.2(1)", "EN", "MLC"),

    # ── EN 1995-1-1 — serviço ────────────────────────────────────────────
    "lim_w_inst":    _p("L/300", "EN 1995-1-1 Tab. 7.2", "EN-recomendado"),
    "lim_w_net_fin": _p("L/250", "EN 1995-1-1 Tab. 7.2", "EN-recomendado"),
    "lim_abertura_springings": _p(
        "L/500", "não normalizado", "PROJETO",
        "o EC5 não fixa limite para a abertura dos apoios; ver AUD-006"),

    # ── Ações de vento ───────────────────────────────────────────────────
    "norma_vento": _p(NORMA_VENTO, "ABNT NBR 6123:2023", "ABNT",
                      "edição única adotada; ver AUD-001 a AUD-005"),
    "V0":  _p(45.0, "NBR 6123:2023 §5.1", "ABNT", "isopleta do local — m/s"),
    "S1":  _p(1.0,  "NBR 6123:2023 §5.2", "ABNT", "terreno plano"),
    "S3":  _p(1.0,  "NBR 6123:2023 §5.4", "ABNT", "grupo 2"),

    # ── Limiares de estabilidade (analogia EN 1993) ──────────────────────
    "alpha_cr_min":     _p(10.0, "EN 1993-1-1 §5.2.1(3)", "EN-recomendado",
                           "análise elástica; adotado por analogia em MLC"),
    "phi_0":            _p(1.0 / 200.0, "EN 1993-1-1 §5.3.2", "EN-recomendado",
                           "imperfeição global"),
    "H_imp_over_H_max": _p(0.10, "critério de dispensa", "PROJETO",
                           "não normalizado; ver AUD-006/AUD-008"),
    "w_over_f_max":     _p(0.05, "critério de dispensa", "PROJETO",
                           "abaixamento relativo do freche"),
})


def parametros_ndp() -> dict[str, ParametroNormativo]:
    """Só os parâmetros que um Anexo Nacional poderia alterar."""
    return {k: v for k, v in NDP_SOURCE.items() if v.e_ndp}


def parametros_de_projeto() -> dict[str, ParametroNormativo]:
    """Só as escolhas de projeto — não normalizadas, responsabilidade do autor."""
    return {k: v for k, v in NDP_SOURCE.items() if v.origem == "PROJETO"}


@dataclass(frozen=True)
class ConfiguracaoNormativa:
    """Base normativa declarada de uma análise, anexável a qualquer resultado."""
    eurocode_base:  str = EUROCODE_BASE
    national_annex: str = NATIONAL_ANNEX
    norma_vento:    str = NORMA_VENTO
    ndp_source: Mapping[str, ParametroNormativo] = field(default=NDP_SOURCE)

    @property
    def na_definido(self) -> bool:
        """False enquanto nenhum Anexo Nacional concreto for adotado."""
        return not self.national_annex.startswith("NENHUM")

    def aviso(self) -> str:
        """Texto obrigatório em qualquer saída dependente de NDP."""
        if self.na_definido:
            return f"NDP conforme {self.national_annex}."
        n = len(parametros_ndp())
        return (
            f"NDP NÃO DEFINIDO POR ANEXO NACIONAL — {n} parâmetros adotam o "
            f"valor recomendado do EN por decisão de projeto. "
            f"RESULTADO DEPENDENTE DE NATIONAL ANNEX."
        )


CONFIG_NORMATIVA = ConfiguracaoNormativa()
