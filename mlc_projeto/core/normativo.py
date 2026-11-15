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
    "PROJETO-A-CONFIRMAR" — escolha de projeto que o projetista ainda não fez
                      (classe de consequência, tempo requerido de resistência ao
                      fogo). Difere de "PROJETO" precisamente nisto: ali há uma
                      decisão tomada e justificada; aqui há um valor a usar
                      provisoriamente e uma decisão em falta. Ambos os sufixos
                      "-A-CONFIRMAR" caem em `parametros_a_confirmar()`.
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


EUROCODE_BASE = (
    "EN 1990:2002 + EN 1991-1-1:2002 + EN 1995-1-1:2004/A1:2008 "
    "+ EN 1995-1-2:2004"
)

#: Declaração do HÍBRIDO NBR 6123 × EN 1990 (achado B2 da auditoria de
#: conformidade). Os coeficientes parciais e ψ da EN 1990 Tab. A1.1/A1.2 foram
#: calibrados contra a ação de vento característica da **EN 1991-1-4**. Este
#: projeto substitui essa ação pela da NBR 6123:2023 e mantém o formato de
#: segurança do EN 1990. Não é ilegítimo — é uma DECISÃO DE PROJETO, e como tal
#: tem de estar escrita: quem lê o memorial não pode inferi-la dos números.
HIBRIDO_VENTO = (
    "A ação de vento é obtida pela ABNT NBR 6123:2023 (rajada de 3 s, "
    "Tr = 50 anos via S3) e introduzida no formato de segurança da EN 1990 "
    "(γ_Q = 1,50; ψ_0,W = 0,60; ψ_2,W = 0). Esses coeficientes foram calibrados "
    "pelo CEN contra a ação característica da EN 1991-1-4 (velocidade média de "
    "10 min com c_s·c_d e pressão de pico q_p), NÃO contra a rajada de 3 s da "
    "NBR. A equivalência entre as duas ações características não é demonstrada "
    "neste memorial: adota-se o par (NBR 6123 para a ação, EN 1990 para a "
    "combinação) por decisão de projeto, por ser a prática corrente quando a "
    "obra é brasileira e o dimensionamento da madeira segue o EC5. Consequência "
    "a declarar: a fiabilidade resultante é a da NBR para a AÇÃO e a do EN 1990 "
    "para a COMBINAÇÃO, e não a fiabilidade calibrada de nenhum dos dois "
    "sistemas completos."
)

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
    # [F-20] A Tab. 7.2 do EC5 dá INTERVALOS (w_inst: ℓ/300–ℓ/500;
    # w_net,fin: ℓ/250–ℓ/350), não um "valor recomendado" — não há aqui um NDP
    # a herdar do EN. Adotar a extremidade MAIS PERMISSIVA de cada intervalo é
    # escolha do projetista e fica classificada como tal. (η_ELS = 0,19: a
    # extremidade rígida seria igualmente atendida — a reclassificação é de
    # rastreabilidade, não de dimensionamento.)
    "lim_w_inst":    _p("L/300", "EN 1995-1-1 Tab. 7.2 (intervalo ℓ/300–ℓ/500)",
                        "PROJETO",
                        "extremidade permissiva do intervalo; cobertura "
                        "industrial sem forro nem elementos frágeis apoiados"),
    "lim_w_net_fin": _p("L/250", "EN 1995-1-1 Tab. 7.2 (intervalo ℓ/250–ℓ/350)",
                        "PROJETO",
                        "idem; a flecha final verificada é 0,19 do limite"),
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
                           "análise elástica; adotado POR ANALOGIA em MLC — o "
                           "EC5 não fixa limiar (issue 46)"),
    "phi_0":            _p(0.005, "EN 1995-1-1 §5.4.4(2) Eq. (5.1)", "EN",
                           "inclinação inicial; φ = 0,005·√(5/h) para h > 5 m"),
    "e_bow_rel":        _p(0.0025, "EN 1995-1-1 §5.4.4(3) Eq. (5.2)", "EN",
                           "curvatura inicial e = 0,0025·ℓ (incorporada em k_c)"),
    "H_imp_over_H_max": _p(0.10, "critério de dispensa", "PROJETO",
                           "não normalizado; ver AUD-006/AUD-008"),
    "w_over_f_max":     _p(0.05, "critério de dispensa", "PROJETO",
                           "abaixamento relativo do freche"),

    # ── Contraventamento: parâmetros que GOVERNAM e não constavam [F-23] ──
    # O limite de deslocamento dos painéis de cruz governa o Ø das diagonais em
    # ELS (η_δ ≈ 0,61) e estava só como default de assinatura, sem cláusula e
    # fora deste catálogo. O EC5 não fixa drift para painéis de contraventamento
    # de cobertura; H/300 é a prática corrente para estruturas industriais e é,
    # portanto, escolha do projetista.
    "drift_lim_paineis": _p(
        300.0, "não normalizado (δ ≤ H_col/300)", "PROJETO",
        "limite de deslocamento horizontal dos painéis de contraventamento "
        "vertical e transversal; governa o diâmetro das diagonais em ELS"),
    "k_s_contravento":  _p(4.0, "EN 1995-1-1 Tab. 9.2 (§9.2.5.3)", "EN-recomendado",
                           "fator de modificação por n.º de vãos"),
    "k_f_2":            _p(80.0, "EN 1995-1-1 Tab. 9.2 (§9.2.5.3)", "EN-recomendado",
                           "rigidez do contraventamento — Eq. (9.36)"),
    "k_f_3":            _p(30.0, "EN 1995-1-1 Tab. 9.2 (§9.2.5.3)", "EN-recomendado",
                           "rigidez do contraventamento — Eq. (9.37)"),

    # ── Fiabilidade: classe de consequência (EN 1990 Anexo B) ────────────
    # Achado B1: a classe de consequência NÃO estava declarada em lado nenhum,
    # e é a MESMA pergunta que o S3 da NBR 6123 (grupo 2 vs 3) em aberto no
    # [F-21]. Uma classificação, duas normas: têm de responder o mesmo.
    #
    # A EN 1990 §B3.3 permite modificar γ por K_FI (CC1: 0,9 | CC2: 1,0 |
    # CC3: 1,1). A aplicação de K_FI é ela própria um NDP e a EN 1990 §B1(3)
    # nota que a diferenciação por K_FI pode ser dispensada quando outras
    # medidas (controlo de projeto e execução) a substituem.
    "classe_consequencia": _p(
        "CC2", "EN 1990 Anexo B Tab. B1", "PROJETO-A-CONFIRMAR",
        "Estacionamento coberto: CC2 («consequência MÉDIA — edifícios "
        "residenciais e de escritórios, públicos com consequências médias»). "
        "PENDENTE DE CONFIRMAÇÃO pelo projetista, e a decisão é solidária com "
        "o grupo da Tab. 4 da NBR 6123 [F-21]: CC3 (aglomerações, ruína com "
        "risco elevado) corresponde ao grupo 2 (S3 = 1,06) e implicaria "
        "K_FI = 1,10 sobre as ações desfavoráveis MAIS +12,4 % na ação de "
        "vento. Enquanto o par não for confirmado, o memorial não pode "
        "afirmar a classe."),
    "K_FI": _p(
        1.00, "EN 1990 Anexo B §B3.3 Tab. B3", "PROJETO-A-CONFIRMAR",
        "K_FI = 1,00 é o valor de CC2. Solidário com 'classe_consequencia': "
        "se a edificação for CC3, K_FI = 1,10 multiplica γ_G e γ_Q "
        "desfavoráveis (EN 1990 §B3.3(2)) e TODAS as verificações ELU sobem "
        "10 %. Não aplicado enquanto a classe não estiver confirmada."),

    # ── Incêndio (EN 1995-1-2) ───────────────────────────────────────────
    # O Eurocódigo dá o método, não o tempo requerido: R vem do regulamento
    # nacional de segurança contra incêndio (ABNT NBR 14432 / IT do CBM
    # estadual). É por isso "PROJETO", e não "EN-recomendado".
    "R_fogo_req_min": _p(
        30.0, "NPT 008 CBPMPR (2012) Anexo A, itens A2.3.10 b) e A2.4 c); método "
              "por EN 1995-1-2:2004 §4.2.2", "PROJETO",
        "TRRF EXIGIDO = 0 (issue 88): edificação térrea, G-1/G-2 aberta "
        "lateralmente — isenta por A2.3.10 b) (q_fi = 200 MJ/m², NPT 014) e, "
        "se a CTPI somar a madeira da estrutura à carga de incêndio (~1.250 "
        "MJ/m²), TRRF da Tabela A de 30 min reduzido em 30 min por A2.4 c). A "
        "verificação a R30 (e a margem a R60) é INFORMATIVA. Independe disso o "
        "item 5.17: área > 750 m² com madeira exige retardante ao fogo."),
    "beta_n_MLC": _p(
        0.70, "EN 1995-1-2:2004 Tab. 3.1", "EN",
        "taxa de carbonização NOCIONAL (mm/min) para MLC de coníferas com "
        "ρ_k ≥ 290 kg/m³; GL24h tem ρ_k = 385"),
    "k_fi_MLC": _p(
        1.15, "EN 1995-1-2:2004 Tab. 2.1", "EN",
        "converte o 5 % fractil no 20 % fractil em situação de incêndio"),
    "gamma_M_fi": _p(
        1.00, "EN 1995-1-2:2004 §2.3(1)", "EN-recomendado",
        "coeficiente parcial da madeira em situação acidental de incêndio"),
})


#: Fatores de MAJORAÇÃO da resistência que o EC5 permite e que este projeto NÃO
#: aplica (achado A6). Omiti-los é conservador — e por isso passam despercebidos
#: numa auditoria de segurança. Mas um memorial que não os declara deixa o leitor
#: sem saber se foram descartados por decisão ou por esquecimento, e essa é uma
#: diferença que só o autor pode resolver. Ficam escritos, com o ganho perdido.
OMISSOES_CONSERVADORAS: Mapping[str, str] = MappingProxyType({
    "k_h": (
        "EN 1995-1-1 §3.3 Eq. (3.2) — para MLC com h < 600 mm, "
        "k_h = min((600/h)^0,1 ; 1,1) majora f_m,k e f_t,0,k. NÃO implementado. "
        "Aplicar-se-ia às terças (h = 580 mm → k_h = 1,003): ganho de 0,3 %."
    ),
    "k_sys": (
        "EN 1995-1-1 §6.6 — k_sys ≤ 1,1 para elementos contínuos com "
        "distribuição transversal de carga garantida. NÃO aplicado: a telha "
        "metálica não constitui distribuição transversal garantida no sentido "
        "da cláusula. Omissão correta para o caso, e não só conservadora."
    ),
    "k_c_90": (
        "EN 1995-1-1 §6.1.5(4) — para MLC sobre apoio descontínuo, k_c,90 pode "
        "chegar a 1,75, majorando f_c,90,d. NÃO aplicado (k_c,90 = 1,0). "
        "É a verificação de apoio que governa em η = 0,266."
    ),
    "psi_M_N": (
        "EN 1992-4:2018 Fórmula (7.7) — ψ_M,N é favorável e foi adotado 1,0."
    ),
    "k8_pryout": (
        "EN 1992-4:2018 Fórmula (7.39a) — k8 é remetido ao ETA; adotado o "
        "valor conservador 1,0."
    ),
    "A_c1_sobre_A_c0": (
        "EN 1992-1-1 §6.7 — o confinamento sob a chaveta pode chegar a "
        "√(A_c1/A_c0) ≤ 3,0. Adotado 1,0: elevá-lo exige a geometria da "
        "sapata, fora de escopo."
    ),
})


def parametros_ndp() -> dict[str, ParametroNormativo]:
    """Só os parâmetros que um Anexo Nacional poderia alterar."""
    return {k: v for k, v in NDP_SOURCE.items() if v.e_ndp}


def parametros_de_projeto() -> dict[str, ParametroNormativo]:
    """
    Só as escolhas de projeto — não normalizadas, responsabilidade do autor.

    Inclui as ainda por confirmar (`PROJETO-A-CONFIRMAR`): uma decisão em falta
    continua a ser responsabilidade do projetista, e omiti-la desta lista fá-la
    desaparecer do memorial.
    """
    return {k: v for k, v in NDP_SOURCE.items()
            if v.origem.startswith("PROJETO")}


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
        clausula="NBR 6123:2023 Tab. 10 (figura e linha α = 90°)",
        local="core/wind.py:292-294",
        simbolos=("TABELA_10_ALPHA90", "TABELA_10_CPE_MEDIO"),
        estado="CONFIRMADO",
        evidencia="Issue 39 (3.ª revisão): lido no PDF (pág. 24 da norma) — "
                  "α = 90°, θ ≤ 45°: b1 = −0,8, b2 = −0,6, b3 = −0,2, com "
                  "b1 = b2 = h a partir do frontão de barlavento (figura); "
                  "c_pe médio das bordas −1,5 / −2,0, y = mín(h; 0,1b). "
                  "Implementado como 6 padrões de pórtico (3 faixas × 2 c_pi).",
        questao="Decisão registrada: atrito para α = 90° pelo §7.2.2 "
                "(cobertura isolada, envolvente) em vez de §6.1.5, conforme "
                "orientação do orientador (mesma seção §7.2 da cobertura "
                "isolada); bordas de vedação por §7.2.6 (±2,0).",
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

    def aviso_hibrido(self) -> str:
        """
        Declaração do híbrido NBR 6123 (ação) × EN 1990 (combinação) — achado B2.

        `aviso_ndp` cobre a ausência de Anexo Nacional e `aviso_nbr` a
        proveniência dos valores da NBR. Nenhum dos dois dizia que os γ e ψ do
        EN 1990 foram calibrados contra OUTRA ação de vento — que é a decisão
        de projeto com maior alcance neste memorial.
        """
        return HIBRIDO_VENTO

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
