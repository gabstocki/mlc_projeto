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
    # [F-21] O valor 1,00 é o do GRUPO 3 da Tab. 4 (Tp 50 anos); o grupo 2
    # exige 1,06 (Tp 75 anos) e elevaria toda a ação de vento em +12,4 %. O
    # rótulo antigo dizia «grupo 2» com o valor do grupo 3 — contradição
    # apanhada por BM-17 contra o texto da norma. Fica declarada até o
    # projetista classificar a edificação; NÃO se alterou o valor.
    "S3":  _p(1.0,  "NBR 6123:2023 §5.4 Tab. 4", "ABNT-A-CONFIRMAR",
              "[F-21] 1,00 é o valor do GRUPO 3 (Tp 50 anos). O rótulo anterior "
              "dizia «grupo 2», que exige 1,06 — contradição por resolver. "
              "Grupo 3 = residências, hotéis, comércio, indústrias; grupo 2 = "
              "ruína com substancial risco à vida / aglomerações. Se for grupo "
              "2, toda a ação de vento sobe +12,4 % (NÃO CONSERVATIVO)."),
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
        estado="CONFIRMADO",
        evidencia="BM-17: os 45 valores conferem um a um com a Tab. 1 do texto "
                  "da :2023. Verificação cruzada mais forte: as 279 células da "
                  "Tab. 3 (S2 tabelado pela própria norma) são reproduzidas "
                  "pela fórmula de §5.3.3 com estes parâmetros, pior desvio "
                  "0,0050 — exatamente o arredondamento a 2 casas. Isto testa "
                  "b, p, z_g, F_r e a regra especial da Categoria V de uma só "
                  "vez, contra dados que não saíram do repositório.",
        questao="",
    ),
    ItemNBR(
        chave="fator_rajada",
        designacao="Fator de rajada F_r por classe (A=1,00 B=0,98 C=0,95)",
        clausula="NBR 6123:2023 §5.3.3 Tab. 2",
        local="core/wind.py:42-43",
        simbolos=("FATOR_RAJADA",),
        estado="CONFIRMADO",
        evidencia="BM-17: os 3 valores conferem com a Tab. 2 do texto. A dúvida "
                  "de numeração levantada em Z.18 estava errada: a :2023 tem "
                  "mesmo Tab. 1 (parâmetros), Tab. 2 (rajada) e Tab. 3 (S2 "
                  "tabelado), tal como o código sempre citou.",
        questao="",
    ),
    ItemNBR(
        chave="pressao_dinamica",
        designacao="q = 0,613·Vk² (N/m², Vk em m/s)",
        clausula="NBR 6123:2023 §4.2 c)",
        local="core/wind.py:45-47",
        simbolos=("COEF_PRESSAO_DINAMICA",),
        estado="CONFIRMADO",
        evidencia="BM-17: §4.2 c) confirmado à letra — q = ½ρVk² com "
                  "ρ = 1,226 kg/m³, «q = 0,613 Vk2, expresso em Newton por "
                  "metro ao quadrado». Também dedutível da física (BM-01, "
                  "Δ = 0,000 %).",
        questao="",
    ),
    ItemNBR(
        chave="v0_isopleta",
        designacao="Velocidade básica V0 = 45 m/s",
        clausula="NBR 6123:2023 §5.1, Figura 1",
        local="core/normativo.py:137, main.py VENTO_PARAMS",
        simbolos=("V0",),
        estado="NAO_CONFIRMADO",
        evidencia="BM-17 confirmou a DEFINIÇÃO de §5.1 (rajada de 3 s a 10 m, "
                  "campo aberto e plano, excedida em média uma vez em 50 anos, "
                  "lida no gráfico de isopletas da Figura 1). O VALOR continua "
                  "sem verificação possível: a Figura 1 é um mapa, e o projeto "
                  "não declara a localidade da obra em lado nenhum.",
        questao="Qual é a localidade da obra? Sem ela, V0 = 45 m/s não é "
                "rastreável — é o único valor de vento do projeto que "
                "permanece sem fonte, e nem uma invariante lhe é aplicável.",
    ),
    ItemNBR(
        chave="s1_topografico",
        designacao="Fator topográfico S1 = 1,0",
        clausula="NBR 6123:2023 §5.2 a)",
        local="core/normativo.py:138",
        simbolos=("S1",),
        estado="CONFIRMADO",
        evidencia="BM-17: §5.2 a) «terreno plano ou fracamente acidentado: "
                  "S1 = 1,0» confirmado à letra. Que o terreno seja plano é "
                  "premissa de projeto, a conferir no levantamento.",
        questao="",
    ),
    ItemNBR(
        chave="s3_estatistico",
        designacao="Fator estatístico S3 = 1,0",
        clausula="NBR 6123:2023 §5.4 Tab. 4",
        local="core/normativo.py:139",
        simbolos=("S3",),
        estado="NAO_CONFIRMADO",
        evidencia="**[F-21] CONTRADIÇÃO ENTRE O VALOR E O SEU RÓTULO.** A "
                  "Tab. 4 da :2023 dá grupo 2 → S3 = 1,06 (Tp 75 anos) e "
                  "grupo 3 → S3 = 1,00 (Tp 50 anos). O código adota 1,00 — que "
                  "é o do GRUPO 3 — rotulado «grupo 2». Se a classificação "
                  "correta for o grupo 2, toda a ação de vento sobe 1,06² = "
                  "+12,4 %, e o defeito é NÃO CONSERVATIVO.",
        questao="A que grupo da Tab. 4 pertence o galpão? Grupo 3 abrange "
                "«residências, hotéis, comércio, indústrias»; grupo 2 é para "
                "estruturas cuja ruína represente substancial risco à vida, "
                "com aglomerações. Um estacionamento coberto parece grupo 3 — "
                "mas é o projetista que classifica, e o rótulo atual afirma o "
                "contrário do valor usado.",
    ),
    ItemNBR(
        chave="cpi_obstrucao",
        designacao="c_pi = +0,8 (obstrução a sotavento) / −0,3 (a barlavento)",
        clausula="NBR 6123:2023 §7.2.1, último parágrafo",
        local="core/wind.py:236-243",
        simbolos=("CPI_OBSTRUCAO_SOTAVENTO", "CPI_OBSTRUCAO_BARLAVENTO"),
        estado="CONFIRMADO",
        evidencia="BM-17: parágrafo confirmado à letra, incluindo os dois "
                  "sinais e o gatilho («Para os casos em que a altura h for "
                  "inferior aos limites de 7.2.1, ou em que obstruções possam "
                  "ser colocadas sob ou junto à cobertura»).",
        questao="",
    ),
    ItemNBR(
        chave="dominio_tab_24_25",
        designacao="Domínio das Tab. 24/25: 0,07 ≤ tg θ ≤ 0,6 e h ≥ 0,5·ℓ2",
        clausula="NBR 6123:2023 §7.2.1",
        local="core/wind.py:354-405",
        simbolos=("validar_dominio_cobertura_isolada",),
        estado="CONFIRMADO",
        evidencia="BM-17: condição confirmada à letra para as duas águas. É "
                  "esta condição que expulsa a geometria do projeto "
                  "(h = 7,0 m < 0,5·ℓ2) da Tab. 25 e obriga à rota alternativa "
                  "de edificação fechada — a recusa do código está certa.",
        questao="",
    ),
    ItemNBR(
        chave="tabela_10_ce",
        designacao="C_pe externos de telhados múltiplos, zonas a*..z*, θ=5..45°",
        clausula="NBR 6123:2023 Tab. 10",
        local="core/wind.py:245-265",
        simbolos=("TABELA_10_CE", "TABELA_10_THETA"),
        estado="CONFIRMADO",
        evidencia="BM-17: os 40 valores conferem um a um. A NOTA de que «para "
                  "α = 0° as forças horizontais de atrito já estão consideradas "
                  "nos valores da Tabela 10» também está confirmada — é o que "
                  "impede a dupla contagem com §7.2.2.",
        questao="",
    ),
    ItemNBR(
        chave="tabela_10_alpha_90",
        designacao="Colunas b1/b2/b3 da Tab. 10 (vento α = 90°) e c_pe médio",
        clausula="NBR 6123:2023 Tab. 10",
        local="NÃO IMPLEMENTADO",
        simbolos=(),
        estado="NAO_CONFIRMADO",
        evidencia="Apanhado ao ler a tabela: a Tab. 10 tem, além das zonas "
                  "a*..z* para α = 0°, as colunas b1/b2/b3 para α = 90° "
                  "(−0,8 / −0,6 / −0,2) e uma linha de c_pe médio para "
                  "elementos localizados. O repositório só transcreveu α = 0°.",
        questao="Na rota de edificação fechada (§7.2.1), o vento paralelo às "
                "cumeeiras devia usar b1/b2/b3 da Tab. 10. O projeto trata "
                "θ = 0° pela rota de cobertura isolada (§7.2.2 + arrasto dos "
                "pilares). As duas rotas estão a ser misturadas de forma "
                "coerente? Só o projetista fecha esta.",
    ),
    ItemNBR(
        chave="tabela_25_cp",
        designacao="Cpb/Cps de cobertura isolada a duas águas, carregamentos 1 e 2",
        clausula="NBR 6123:2023 Tab. 25",
        local="core/wind.py:410-450",
        simbolos=("coeficientes_tabela25",),
        estado="CONFIRMADO",
        evidencia="BM-17: as 8 expressões conferem à letra, e 216 amostras "
                  "numéricas em 0,07 ≤ tg θ ≤ 0,60 batem com zero desvio. O "
                  "teto «2,4 tgθ + 0,6 ≤ 2,0», que Z.18 suspeitava ser "
                  "interpolação do autor, ESTÁ na norma. A numeração Tab. 25 "
                  "confere.",
        questao="",
    ),
    ItemNBR(
        chave="ca_pilar",
        designacao="Coeficiente de arrasto C_a = 1,2 de pilar prismático livre",
        clausula="NBR 6123:2023 §6.3 / Tab. 13 — CITAÇÃO ERRADA",
        local="core/wind.py:507-509",
        simbolos=("CA_PILAR_RET",),
        estado="NAO_CONFIRMADO",
        evidencia="**[F-20] A CITAÇÃO NÃO EXISTE PARA ESTE FIM.** Na :2023, "
                  "§6.3 é «Pressões internas em edificações» e a Tab. 13 é "
                  "«Distribuição das pressões externas em edificações "
                  "cilíndricas de seção circular». Nenhuma trata do arrasto de "
                  "uma barra prismática livre. A rota certa é §8.1.1: Cx/Cy da "
                  "Tab. 26 (barras de faces planas, comprimento infinito) "
                  "multiplicados pelo fator K de comprimento finito da Tab. 28 "
                  "(0,62 a 0,95 para ℓ/c de 2 a 100). A Tab. 26 dá Cx ≥ +1,6 "
                  "em α = 0°, o que com K ≈ 0,7 dá ≈ 1,1–1,4: o valor 1,2 cai "
                  "dentro do intervalo, mas não foi obtido por esta rota e não "
                  "está demonstrado como conservador. Peso: o arrasto dos "
                  "pilares é 60,5 kN em 837,3 kN do vento θ=0° (7,2 %).",
        questao="Refazer C_a por §8.1.1: qual a relação ℓ1/ℓ2 da secção do "
                "pilar e qual o ℓ/c para entrar na Tab. 28? As figuras da "
                "Tab. 26 são imagens no PDF e não se leem por extração de "
                "texto — exigem consulta visual.",
    ),
    ItemNBR(
        chave="cp_vedacao_isolada",
        designacao="c_p = ±2,0 por elemento de vedação (fixação da telha)",
        clausula="NBR 6123:2023 §7.2.6",
        local="checks/elu/fixacao_telha.py:70-75",
        simbolos=("CP_VEDACAO_ISOLADA",),
        estado="CONFIRMADO",
        evidencia="BM-17: §7.2.6 confirmado à letra — «Cada elemento de "
                  "vedação deve ser calculado com cp = ±2,0». O docstring "
                  "obsoleto do módulo, que descrevia a rota antiga por zonas "
                  "da Tab. 5 com c_pi de §6.2.5, foi removido agora que a "
                  "cláusula está confirmada.",
        questao="",
    ),
    ItemNBR(
        chave="atrito_cobertura",
        designacao="Ft = 0,5·q·a·b — força horizontal, vento paralelo à geratriz",
        clausula="NBR 6123:2023 §7.2.2",
        local="core/wind.py:518-548",
        simbolos=("COEF_ATRITO_COBERTURA_ISOLADA", "CLAUSULA_ATRITO",
                  "ORIGEM_ATRITO"),
        estado="CONFIRMADO",
        evidencia="Texto fornecido pelo utilizador e agora reconfirmado por "
                  "BM-17 contra o PDF. É uma ação ENVOLVENTE («englobam a ação "
                  "do vento sobre as duas faces»), não uma estimativa de "
                  "atrito de superfície — foi por confundir as duas coisas que "
                  "a auditoria propôs 0,05 e teve de se retratar.",
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
                  "silhueta, para apanhar erro de ENTRADA. Nada dimensionado "
                  "depende dele — daí não haver o que confirmar.",
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
        total = len(CATALOGO_NBR6123)
        if not pendentes:
            return (f"Todos os {total} valores de origem {NORMA_VENTO} "
                    f"confirmados contra o texto da norma (BM-17).")
        return (
            f"[F-18] {total - len(pendentes)} de {total} valores de origem NBR "
            f"6123 confirmados contra o TEXTO da {NORMA_VENTO} (BM-17: Tab. 1 "
            f"45/45, Tab. 2 3/3, Tab. 3 279 células, Tab. 10 40/40, Tab. 25 8 "
            f"expressões, §4.2/§5.2/§7.2.1/§7.2.2/§7.2.6 à letra). "
            f"{len(pendentes)} POR RESOLVER: "
            + "; ".join(i.chave for i in pendentes)
            + ". Ver ANEXO_A_NBR6123.md."
        )


CONFIG_NORMATIVA = ConfiguracaoNormativa()
