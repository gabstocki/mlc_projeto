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
    "ABNT-A-CONFIRMAR" — atribuído a uma cláusula da ABNT que NÃO foi
                      reproduzida nem verificada (achado F-13). Não é um valor
                      normativo enquanto a cláusula não for anexada ao memorial.
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

    # ── EN 1992-1-1 — concreto sob a chapa de base ───────────────────────
    "alpha_cc": _p(1.00, "EN 1992-1-1 §3.1.6(1)", "EN-recomendado",
                   "efeitos de longa duração na resistência à compressão"),
    "gamma_C":  _p(1.50, "EN 1992-1-1 Tab. 2.1N", "EN-recomendado",
                   "coeficiente parcial do concreto, situações persistentes"),
    "k_confinamento_apoio": _p(
        1.00, "EN 1992-1-1 §6.7", "PROJETO",
        "√(A_c1/A_c0) ≤ 3,0; adotado 1,0 (sem ganho) por não se conhecer a "
        "geometria da sapata — elevá-lo exige dimensionar a fundação"),

    # ── Ações de vento ───────────────────────────────────────────────────
    "norma_vento": _p(NORMA_VENTO, "ABNT NBR 6123:2023", "ABNT",
                      "edição única adotada; ver AUD-001 a AUD-005"),
    "V0":  _p(45.0, "NBR 6123:2023 §5.1", "ABNT", "isopleta do local — m/s"),
    "S1":  _p(1.0,  "NBR 6123:2023 §5.2", "ABNT", "terreno plano"),
    "S3":  _p(1.0,  "NBR 6123:2023 §5.4", "ABNT", "grupo 2"),
    # Governa toda a estrutura metálica de contraventamento (achado F-13,
    # ENCERRADO: cláusula transcrita em core/wind.py e confirmada em 0,50).
    "coef_atrito_cobertura_isolada": _p(
        0.50, "NBR 6123:2023 §7.2.2", "ABNT",
        "Ft = 0,5·q·a·b (θ=0°), a e b as dimensões EM PLANTA da cobertura. "
        "«Estas forças englobam a ação do vento sobre as duas faces da "
        "cobertura» — é uma ação ENVOLVENTE, não uma estimativa de atrito "
        "superficial: vale 2,35× o arrasto de bloqueio da silhueta deste "
        "galpão. Texto integral transcrito em core/wind.py."),

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


# ── [F-18] Catálogo de proveniência dos valores de origem NBR 6123 ───────────
#
# O achado F-18 não é um erro de cálculo. É a constatação de que NENHUMA tabela
# da NBR 6123:2023 está reproduzida com citação verificável neste repositório:
# os números podem estar certos, mas a conformidade à edição declarada não é
# demonstrável com o material disponível à auditoria.
#
# A resposta possível em código não é inventar a fonte — é tornar a lacuna
# ENUMERÁVEL. Cada valor de origem NBR fica aqui registado com a cláusula que o
# código ALEGA, o local exato, o estado de confirmação e — quando por confirmar
# — a pergunta concreta a fazer à norma em papel. `ANEXO_A_NBR6123.md` é a
# folha de conferência gerada a partir deste catálogo.
#
# `estado` só admite dois valores, deliberadamente:
#   "CONFIRMADO"     — o texto literal da cláusula foi obtido e transcrito.
#   "NAO_CONFIRMADO" — tudo o resto. Não há estado intermédio: "é o valor de
#                      sempre" e "bate com a edição de 1988" não são fontes.
#
# `evidencia` regista verificação INDEPENDENTE que exista sobre o valor, que é
# coisa distinta de confirmar a cláusula. Um valor pode estar fisicamente
# fundado (BM-01, BM-15) e continuar com a citação por confirmar.

@dataclass(frozen=True)
class ItemNBR:
    """Um valor de origem NBR 6123 e o estado da sua proveniência."""
    chave:      str
    designacao: str
    clausula:   str            # o que o código ALEGA ser a fonte
    local:      str            # ficheiro:linha
    simbolos:   tuple[str, ...]  # constantes/funções que o materializam
    estado:     str            # "CONFIRMADO" | "NAO_CONFIRMADO"
    evidencia:  str = ""       # verificação independente, se houver
    questao:    str = ""       # a pergunta exata a fazer à norma em papel


CATALOGO_NBR6123: tuple[ItemNBR, ...] = (
    ItemNBR(
        chave="param_meteorologicos",
        designacao="Parâmetros meteorológicos b, p, z_g por categoria e classe",
        clausula="NBR 6123:2023 §5.3.3 Tab. 1",
        local="core/wind.py:32-41",
        simbolos=("PARAM_METEOROLOGICOS",),
        estado="NAO_CONFIRMADO",
        evidencia="BM-15 V1/V2/V3/V5 — monotonia e convergência ao vento "
                  "gradiente com dispersão de 0,72 % (limite 2 %). A tabela é "
                  "internamente coerente; z_g é a coluna mal policiada por "
                  "esta invariante (um erro de +100 m dá só 1,75 %).",
        questao="Os 45 valores da Tab. 1 da :2023 coincidem com os "
                "transcritos? A auditoria RECONHECE-OS como sendo os da edição "
                ":1988, mas esse reconhecimento é de memória e não é fonte — é "
                "ele próprio parte do que há a confirmar. A :2023 renumerou a "
                "tabela?",
    ),
    ItemNBR(
        chave="fator_rajada",
        designacao="Fator de rajada F_r por classe (A=1,00 B=0,98 C=0,95)",
        clausula="NBR 6123:2023 §5.3.3 Tab. 2",
        local="core/wind.py:42-43",
        simbolos=("FATOR_RAJADA",),
        estado="NAO_CONFIRMADO",
        evidencia="BM-15 V4/V5 — decresce A→C e entra coerentemente na "
                  "convergência ao vento gradiente.",
        questao="Na :1988 b, p e F_r estão TODOS na Tab. 1 e a Tab. 2 é o S2 "
                "tabelado. O código separa-os em Tab. 1 e Tab. 2 e chama Tab. 3 "
                "ao S2 tabelado (core/wind.py:144). Qual das duas numerações é "
                "a da :2023?",
    ),
    ItemNBR(
        chave="pressao_dinamica",
        designacao="q = 0,613·Vk² (N/m², Vk em m/s)",
        clausula="NBR 6123:2023 §4.2 c)",
        local="core/wind.py:45-47",
        simbolos=("COEF_PRESSAO_DINAMICA",),
        estado="NAO_CONFIRMADO",
        evidencia="Valor INDEPENDENTEMENTE FUNDADO: ½·ρ·V² com ρ = 1,226 kg/m³ "
                  "(ar a 15 °C, 1 atm) dá 0,613 exatamente; BM-01 reproduziu a "
                  "cadeia V0→S2→Vk→q com Δ = 0,000 %. Só a NUMERAÇÃO da "
                  "cláusula fica por confirmar.",
        questao="A expressão de q é o §4.2 c) na :2023?",
    ),
    ItemNBR(
        chave="v0_isopleta",
        designacao="Velocidade básica V0 = 45 m/s",
        clausula="NBR 6123:2023 §5.1",
        local="core/normativo.py:137, main.py VENTO_PARAMS",
        simbolos=("V0",),
        estado="NAO_CONFIRMADO",
        evidencia="",
        questao="Qual é a LOCALIDADE da obra e que isopleta lhe corresponde no "
                "mapa da :2023? O projeto não declara o local, logo V0 = 45 m/s "
                "não é rastreável — é o valor mais desamparado do conjunto.",
    ),
    ItemNBR(
        chave="s1_s3",
        designacao="Fator topográfico S1 = 1,0 e fator estatístico S3 = 1,0",
        clausula="NBR 6123:2023 §5.2 e §5.4",
        local="core/normativo.py:138-139",
        simbolos=("S1", "S3"),
        estado="NAO_CONFIRMADO",
        evidencia="",
        questao="S1 = 1,0 exige terreno plano ou fracamente acidentado — "
                "confirmar contra o levantamento. S3 = 1,0 é o grupo 2; um "
                "estacionamento coberto pertence ao grupo 2 na :2023?",
    ),
    ItemNBR(
        chave="cpi_obstrucao",
        designacao="c_pi = +0,8 (obstrução a sotavento) / −0,3 (a barlavento)",
        clausula="NBR 6123:2023 §7.2.1, último parágrafo",
        local="core/wind.py:236-243",
        simbolos=("CPI_OBSTRUCAO_SOTAVENTO", "CPI_OBSTRUCAO_BARLAVENTO"),
        estado="NAO_CONFIRMADO",
        evidencia="O código transcreve a cláusula entre aspas (wind.py:237-241), "
                  "mas uma citação no próprio repositório não é fonte: é a "
                  "mesma alegação por outras palavras.",
        questao="Confirmar o texto e os dois sinais. É esta a rota que a norma "
                "manda seguir quando h < 0,5·ℓ2?",
    ),
    ItemNBR(
        chave="dominio_tab_24_25",
        designacao="Domínio de validade das Tab. 24/25: 0,07 ≤ tg θ ≤ 0,6 e "
                   "h ≥ 0,5·ℓ2",
        clausula="NBR 6123:2023 §7.2.1",
        local="core/wind.py:354-405",
        simbolos=("validar_dominio_cobertura_isolada",),
        estado="NAO_CONFIRMADO",
        evidencia="ADV-C — é esta condição que expulsa a geometria do projeto "
                  "(h = 7,0 m < 0,5·ℓ2) da Tab. 25 e obriga à rota alternativa. "
                  "Governa QUAL tabela se aplica: por confirmar em primeiro "
                  "lugar.",
        questao="Reproduzir a condição de aplicabilidade tal como redigida.",
    ),
    ItemNBR(
        chave="tabela_10_ce",
        designacao="C_pe externos de telhados múltiplos, zonas a*..z*, θ=5..45°",
        clausula="NBR 6123:2023 Tab. 10",
        local="core/wind.py:245-265",
        simbolos=("TABELA_10_CE", "TABELA_10_THETA"),
        estado="NAO_CONFIRMADO",
        evidencia="BM-15 V7 — sinais coerentes (sucções em todas as zonas de "
                  "sotavento; pico de sucção do barlavento em θ = 10°, que é a "
                  "bolha de separação; inversão para pressão a 45°). É uma "
                  "verificação FRACA: não deteta troca de valores dentro do "
                  "mesmo sinal.",
        questao="Reproduzir a Tab. 10 completa. Confirmar também a nota de que "
                "«para α = 0° as forças horizontais de atrito já estão "
                "consideradas» — dela depende não haver dupla contagem com "
                "§7.2.2.",
    ),
    ItemNBR(
        chave="tabela_25_cp",
        designacao="Cpb/Cps de cobertura isolada a duas águas, carregamentos 1 e 2",
        clausula="NBR 6123:2023 Tab. 25 (equiv. Tab. 18 na :1988)",
        local="core/wind.py:410-450",
        simbolos=("coeficientes_tabela25",),
        estado="NAO_CONFIRMADO",
        evidencia="BM-15 V6 — os quatro ramos lineares juntam-se em tg β = 0,4 "
                  "com salto nulo nos quatro. Um ajuste linear a pontos "
                  "tabelados que fecha exatamente no ponto de quebra é forte "
                  "indício de transcrição fiel.",
        questao="Reproduzir a Tab. 25. Confirmar em especial o teto Cpb,1 ≤ 2,0 "
                "(morde só para tg β > 0,583) — é da norma ou é interpolação "
                "do autor?",
    ),
    ItemNBR(
        chave="ca_pilar",
        designacao="Coeficiente de arrasto C_a = 1,2 de pilar prismático livre",
        clausula="NBR 6123:2023 §6.3 / Tab. 13",
        local="core/wind.py:507-509",
        simbolos=("CA_PILAR_RET",),
        estado="NAO_CONFIRMADO",
        evidencia="",
        questao="C_a de secção retangular depende da esbelteza e da relação "
                "dos lados. 1,2 é conservador para o pilar deste projeto?",
    ),
    ItemNBR(
        chave="cp_vedacao_isolada",
        designacao="c_p = ±2,0 por elemento de vedação (fixação da telha)",
        clausula="NBR 6123:2023 §7.2.6",
        local="checks/elu/fixacao_telha.py:70-75",
        simbolos=("CP_VEDACAO_ISOLADA",),
        estado="NAO_CONFIRMADO",
        evidencia="",
        questao="Confirmar §7.2.6 e o valor. ATENÇÃO: o docstring do módulo "
                "(fixacao_telha.py:27-34) ainda descreve a rota antiga por "
                "zonas da «Tab. 5» com c_pi de §6.2.5, que NÃO é a usada. "
                "Confirmada a cláusula, apagar o docstring obsoleto.",
    ),
    ItemNBR(
        chave="atrito_cobertura",
        designacao="Ft = 0,5·q·a·b — força horizontal, vento paralelo à geratriz",
        clausula="NBR 6123:2023 §7.2.2",
        local="core/wind.py:518-548",
        simbolos=("COEF_ATRITO_COBERTURA_ISOLADA", "CLAUSULA_ATRITO",
                  "ORIGEM_ATRITO"),
        estado="CONFIRMADO",
        evidencia="Texto literal fornecido e transcrito integralmente em "
                  "core/wind.py. Encerra a parte de F-13/F-18 relativa a esta "
                  "cláusula: é uma ação ENVOLVENTE («englobam a ação do vento "
                  "sobre as duas faces»), não uma estimativa de atrito de "
                  "superfície — foi por confundir as duas coisas que a "
                  "auditoria propôs 0,05 e teve de se retratar.",
        questao="",
    ),
    ItemNBR(
        chave="bloqueio_silhueta",
        designacao="c_d = 1,2 do diagnóstico de arrasto de silhueta",
        clausula="NBR 6123:2023 — NÃO se reclama cláusula",
        local="core/wind.py:550-552",
        simbolos=("CA_BLOQUEIO_SILHUETA",),
        estado="CONFIRMADO",
        evidencia="Não é valor de projeto: entra apenas na razão informativa "
                  "que compara Ft com o arrasto de um corpo maciço de igual "
                  "silhueta, para apanhar erro de ENTRADA (área em planta, q). "
                  "Nada dimensionado depende dele — daí não haver o que "
                  "confirmar.",
        questao="",
    ),
)


def itens_nbr() -> tuple[ItemNBR, ...]:
    """Todos os valores de origem NBR 6123 usados no projeto — achado F-18."""
    return CATALOGO_NBR6123


def item_nbr(chave: str) -> ItemNBR:
    """Um item do catálogo pela chave; falha alto se a chave não existir."""
    for item in CATALOGO_NBR6123:
        if item.chave == chave:
            return item
    raise KeyError(
        f"'{chave}' não está no catálogo NBR 6123. Chaves: "
        f"{[i.chave for i in CATALOGO_NBR6123]}"
    )


def itens_nbr_nao_confirmados() -> tuple[ItemNBR, ...]:
    """
    Os valores NBR cuja cláusula NÃO foi verificada contra o texto da norma.

    Enquanto esta lista não estiver vazia, o memorial não pode declarar
    conformidade à NBR 6123:2023 — só ao método que dela se alega.
    """
    return tuple(i for i in CATALOGO_NBR6123 if i.estado == "NAO_CONFIRMADO")


def parametros_a_confirmar() -> dict[str, ParametroNormativo]:
    """
    Parâmetros cuja cláusula de origem NÃO foi verificada — achado F-13.

    Bloqueiam a emissão do memorial: um valor sem fonte não é um valor
    normativo, mesmo quando está do lado conservador.
    """
    return {k: v for k, v in NDP_SOURCE.items()
            if v.origem.endswith("A-CONFIRMAR")}


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

    def aviso_nbr(self) -> str:
        """
        Reserva obrigatória sobre a NBR 6123 — achado F-18.

        Enquanto houver valores de origem NBR com a cláusula por confirmar, o
        memorial declara o MÉTODO alegado, não a conformidade à edição.
        """
        pendentes = itens_nbr_nao_confirmados()
        if not pendentes:
            return f"Valores de {NORMA_VENTO} confirmados contra o texto da norma."
        return (
            f"[F-18] {len(pendentes)} de {len(CATALOGO_NBR6123)} valores de "
            f"origem NBR 6123 têm a CLÁUSULA POR CONFIRMAR contra o texto da "
            f"{NORMA_VENTO}. A coerência interna das tabelas está verificada "
            f"(BM-15), a fidelidade à edição declarada NÃO. "
            f"Folha de conferência: ANEXO_A_NBR6123.md."
        )


CONFIG_NORMATIVA = ConfiguracaoNormativa()
