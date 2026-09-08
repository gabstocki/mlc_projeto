# ANEXO A — Proveniência dos valores da ABNT NBR 6123:2023

> **Folha de conferência do achado [F-18].** Gerada por
> `auditoria_v2/gerar_anexo_nbr.py` a partir de `CATALOGO_NBR6123`
> (`mlc_projeto/core/normativo.py`). **Não editar à mão** — corrigir o
> catálogo e regenerar.

## O que este anexo é, e o que não é

Não é uma reprodução da NBR 6123:2023. A auditoria **não dispõe do texto da
norma** e a carta de auditoria proíbe preencher a lacuna de memória ou por
analogia com a edição de 1988.

É a lista fechada de **todos** os números do projeto que dependem da NBR 6123,
com o local exato no código, a cláusula que o código alega e — para cada item
por confirmar — a pergunta a fazer. Com a norma em mãos, fecha-se numa sessão.

## Porque isto importa em obra

O vento governa **toda** a estrutura metálica de contraventamento e a
verificação da telha. Um erro numa destas tabelas não produz um aviso: produz
um dimensionamento errado que passa em todos os testes. Daí a lista existir em
código (`itens_nbr_nao_confirmados()`), fazer falhar a suíte se um valor NBR
novo entrar sem registo, e ser impressa no cabeçalho do pipeline.

## Estado

| | |
|---|---|
| Itens catalogados | 13 |
| **Por confirmar** | **11** |
| Confirmados | 2 |

Dois estados apenas, deliberadamente: `CONFIRMADO` significa que o texto
literal foi obtido e transcrito. Tudo o resto é `NAO_CONFIRMADO` — «é o valor
de sempre» e «bate com a edição de 1988» não são fontes.

---

## A. Itens por confirmar

Para cada um: ler a cláusula na norma, comparar com o valor transcrito, e
depois marcar `estado="CONFIRMADO"` no catálogo (ou abrir achado, se divergir).


### A.1 — Parâmetros meteorológicos b, p, z_g por categoria e classe

| | |
|---|---|
| Cláusula alegada | `NBR 6123:2023 §5.3.3 Tab. 1` |
| Local no código | `core/wind.py:32-41` |
| Símbolos | `PARAM_METEOROLOGICOS` |
| Chave no catálogo | `param_meteorologicos` |

**Verificação independente:** BM-15 V1/V2/V3/V5 — monotonia e convergência ao vento gradiente com dispersão de 0,72 % (limite 2 %). A tabela é internamente coerente; z_g é a coluna mal policiada por esta invariante (um erro de +100 m dá só 1,75 %).

**A confirmar:** Os 45 valores da Tab. 1 da :2023 coincidem com os transcritos? A auditoria RECONHECE-OS como sendo os da edição :1988, mas esse reconhecimento é de memória e não é fonte — é ele próprio parte do que há a confirmar. A :2023 renumerou a tabela?

### A.2 — Fator de rajada F_r por classe (A=1,00 B=0,98 C=0,95)

| | |
|---|---|
| Cláusula alegada | `NBR 6123:2023 §5.3.3 Tab. 2` |
| Local no código | `core/wind.py:42-43` |
| Símbolos | `FATOR_RAJADA` |
| Chave no catálogo | `fator_rajada` |

**Verificação independente:** BM-15 V4/V5 — decresce A→C e entra coerentemente na convergência ao vento gradiente.

**A confirmar:** Na :1988 b, p e F_r estão TODOS na Tab. 1 e a Tab. 2 é o S2 tabelado. O código separa-os em Tab. 1 e Tab. 2 e chama Tab. 3 ao S2 tabelado (core/wind.py:144). Qual das duas numerações é a da :2023?

### A.3 — q = 0,613·Vk² (N/m², Vk em m/s)

| | |
|---|---|
| Cláusula alegada | `NBR 6123:2023 §4.2 c)` |
| Local no código | `core/wind.py:45-47` |
| Símbolos | `COEF_PRESSAO_DINAMICA` |
| Chave no catálogo | `pressao_dinamica` |

**Verificação independente:** Valor INDEPENDENTEMENTE FUNDADO: ½·ρ·V² com ρ = 1,226 kg/m³ (ar a 15 °C, 1 atm) dá 0,613 exatamente; BM-01 reproduziu a cadeia V0→S2→Vk→q com Δ = 0,000 %. Só a NUMERAÇÃO da cláusula fica por confirmar.

**A confirmar:** A expressão de q é o §4.2 c) na :2023?

### A.4 — Velocidade básica V0 = 45 m/s

| | |
|---|---|
| Cláusula alegada | `NBR 6123:2023 §5.1` |
| Local no código | `core/normativo.py:137, main.py VENTO_PARAMS` |
| Símbolos | `V0` |
| Chave no catálogo | `v0_isopleta` |

**A confirmar:** Qual é a LOCALIDADE da obra e que isopleta lhe corresponde no mapa da :2023? O projeto não declara o local, logo V0 = 45 m/s não é rastreável — é o valor mais desamparado do conjunto.

### A.5 — Fator topográfico S1 = 1,0 e fator estatístico S3 = 1,0

| | |
|---|---|
| Cláusula alegada | `NBR 6123:2023 §5.2 e §5.4` |
| Local no código | `core/normativo.py:138-139` |
| Símbolos | `S1`, `S3` |
| Chave no catálogo | `s1_s3` |

**A confirmar:** S1 = 1,0 exige terreno plano ou fracamente acidentado — confirmar contra o levantamento. S3 = 1,0 é o grupo 2; um estacionamento coberto pertence ao grupo 2 na :2023?

### A.6 — c_pi = +0,8 (obstrução a sotavento) / −0,3 (a barlavento)

| | |
|---|---|
| Cláusula alegada | `NBR 6123:2023 §7.2.1, último parágrafo` |
| Local no código | `core/wind.py:236-243` |
| Símbolos | `CPI_OBSTRUCAO_SOTAVENTO`, `CPI_OBSTRUCAO_BARLAVENTO` |
| Chave no catálogo | `cpi_obstrucao` |

**Verificação independente:** O código transcreve a cláusula entre aspas (wind.py:237-241), mas uma citação no próprio repositório não é fonte: é a mesma alegação por outras palavras.

**A confirmar:** Confirmar o texto e os dois sinais. É esta a rota que a norma manda seguir quando h < 0,5·ℓ2?

### A.7 — Domínio de validade das Tab. 24/25: 0,07 ≤ tg θ ≤ 0,6 e h ≥ 0,5·ℓ2

| | |
|---|---|
| Cláusula alegada | `NBR 6123:2023 §7.2.1` |
| Local no código | `core/wind.py:354-405` |
| Símbolos | `validar_dominio_cobertura_isolada` |
| Chave no catálogo | `dominio_tab_24_25` |

**Verificação independente:** ADV-C — é esta condição que expulsa a geometria do projeto (h = 7,0 m < 0,5·ℓ2) da Tab. 25 e obriga à rota alternativa. Governa QUAL tabela se aplica: por confirmar em primeiro lugar.

**A confirmar:** Reproduzir a condição de aplicabilidade tal como redigida.

### A.8 — C_pe externos de telhados múltiplos, zonas a*..z*, θ=5..45°

| | |
|---|---|
| Cláusula alegada | `NBR 6123:2023 Tab. 10` |
| Local no código | `core/wind.py:245-265` |
| Símbolos | `TABELA_10_CE`, `TABELA_10_THETA` |
| Chave no catálogo | `tabela_10_ce` |

**Verificação independente:** BM-15 V7 — sinais coerentes (sucções em todas as zonas de sotavento; pico de sucção do barlavento em θ = 10°, que é a bolha de separação; inversão para pressão a 45°). É uma verificação FRACA: não deteta troca de valores dentro do mesmo sinal.

**A confirmar:** Reproduzir a Tab. 10 completa. Confirmar também a nota de que «para α = 0° as forças horizontais de atrito já estão consideradas» — dela depende não haver dupla contagem com §7.2.2.

### A.9 — Cpb/Cps de cobertura isolada a duas águas, carregamentos 1 e 2

| | |
|---|---|
| Cláusula alegada | `NBR 6123:2023 Tab. 25 (equiv. Tab. 18 na :1988)` |
| Local no código | `core/wind.py:410-450` |
| Símbolos | `coeficientes_tabela25` |
| Chave no catálogo | `tabela_25_cp` |

**Verificação independente:** BM-15 V6 — os quatro ramos lineares juntam-se em tg β = 0,4 com salto nulo nos quatro. Um ajuste linear a pontos tabelados que fecha exatamente no ponto de quebra é forte indício de transcrição fiel.

**A confirmar:** Reproduzir a Tab. 25. Confirmar em especial o teto Cpb,1 ≤ 2,0 (morde só para tg β > 0,583) — é da norma ou é interpolação do autor?

### A.10 — Coeficiente de arrasto C_a = 1,2 de pilar prismático livre

| | |
|---|---|
| Cláusula alegada | `NBR 6123:2023 §6.3 / Tab. 13` |
| Local no código | `core/wind.py:507-509` |
| Símbolos | `CA_PILAR_RET` |
| Chave no catálogo | `ca_pilar` |

**A confirmar:** C_a de secção retangular depende da esbelteza e da relação dos lados. 1,2 é conservador para o pilar deste projeto?

### A.11 — c_p = ±2,0 por elemento de vedação (fixação da telha)

| | |
|---|---|
| Cláusula alegada | `NBR 6123:2023 §7.2.6` |
| Local no código | `checks/elu/fixacao_telha.py:70-75` |
| Símbolos | `CP_VEDACAO_ISOLADA` |
| Chave no catálogo | `cp_vedacao_isolada` |

**A confirmar:** Confirmar §7.2.6 e o valor. ATENÇÃO: o docstring do módulo (fixacao_telha.py:27-34) ainda descreve a rota antiga por zonas da «Tab. 5» com c_pi de §6.2.5, que NÃO é a usada. Confirmada a cláusula, apagar o docstring obsoleto.

---

## B. Itens confirmados

### Ft = 0,5·q·a·b — força horizontal, vento paralelo à geratriz

| | |
|---|---|
| Cláusula | `NBR 6123:2023 §7.2.2` |
| Local | `core/wind.py:518-548` |


Texto literal fornecido e transcrito integralmente em core/wind.py. Encerra a parte de F-13/F-18 relativa a esta cláusula: é uma ação ENVOLVENTE («englobam a ação do vento sobre as duas faces»), não uma estimativa de atrito de superfície — foi por confundir as duas coisas que a auditoria propôs 0,05 e teve de se retratar.

### c_d = 1,2 do diagnóstico de arrasto de silhueta

| | |
|---|---|
| Cláusula | `NBR 6123:2023 — NÃO se reclama cláusula` |
| Local | `core/wind.py:550-552` |


Não é valor de projeto: entra apenas na razão informativa que compara Ft com o arrasto de um corpo maciço de igual silhueta, para apanhar erro de ENTRADA (área em planta, q). Nada dimensionado depende dele — daí não haver o que confirmar.


---

## C. Verificação independente já realizada — BM-15

`auditoria_v2/bm_nbr_tabelas.py` lê as tabelas do código-fonte por análise
sintática (sem importar o repositório) e testa sete invariantes que um erro de
transcrição quebraria:

| | Invariante | Resultado |
|---|---|---|
| V1 | Tab. 1: b decresce e p cresce de I para V | OK |
| V2 | Tab. 1: p cresce de A para C | OK |
| V3 | Tab. 1: z_g cresce com a categoria, constante entre classes | OK |
| V4 | Tab. 2: F_r decresce de A para C | OK |
| V5 | **S2(z_g) igual nas cinco categorias** (vento gradiente) | **dispersão 0,72 %** |
| V6 | Tab. 25: os quatro ramos juntam-se em tg β = 0,4 sem salto | salto = 0 |
| V7 | Tab. 10: coerência de sinais e pico de sucção em θ = 10° | OK |

**V5 é a invariante forte.** Acima da camada limite o escoamento é geostrófico:
a velocidade não depende do terreno. Logo `S2(z_g) = b·F_r·(z_g/10)^p` tem de
dar o mesmo nas cinco categorias — o que liga três colunas independentes da
tabela. Dá 1,331 a 1,347, dispersão máxima 0,72 %.

Poder de deteção medido, perturbando um único valor:

| Perturbação | Dispersão resultante | |
|---|---|---|
| b(IV) +0,10 | 8,69 % | detetado |
| p(III) +0,020 | 6,02 % | detetado |
| z_g(II) +100 m | 1,75 % | **não detetado** (limite 2 %) |

**Limitação declarada:** z_g é a coluna mal policiada. b e p entram na
convergência com peso alto; z_g entra elevado a p (≈ 0,1) e um erro grosseiro
de 100 m ainda cabe dentro do limite. Confirmar z_g à vista, não por invariante.

### O que V1–V7 provam e o que não provam

**Provam** que a transcrição é uma tabela de camada-limite consistente: os
valores não foram inventados nem baralhados, e um erro futuro de edição não
passa em silêncio (as invariantes estão congeladas em
`tests/test_f18_proveniencia_nbr.py`).

**Não provam** fidelidade à edição :2023. Se a ABNT tiver revisto os
parâmetros em 2023, uma tabela revista seria igualmente coerente — e o
benchmark diria OK à mesma. A coerência interna não distingue edições.

## D. Numeração das tabelas — a inconsistência a esclarecer

O deslocamento de numeração alegado entre :1988 e :2023 não é uniforme:

| Conteúdo | Nº na :1988 (alegado) | Nº usado no código | Δ |
|---|---|---|---|
| Cobertura isolada duas águas | Tab. 18 | Tab. 25 | +7 |
| Telhados múltiplos | Tab. 6 | Tab. 10 | +4 |
| Parâmetros meteorológicos | Tab. 1 (com F_r) | Tab. 1 (sem F_r) + Tab. 2 | — |

O terceiro caso é o mais delicado: na :1988 b, p **e F_r** estão todos na
Tab. 1, e a Tab. 2 é o S2 tabelado. O código separa F_r numa «Tab. 2» e trata o
S2 tabelado por «Tab. 3» (`core/wind.py:144`). Ou a :2023 reorganizou a
apresentação, ou a citação está errada. **Só o texto decide.**

## E. Como fechar

1. Obter a NBR 6123:2023.
2. Percorrer a secção A deste anexo, item a item.
3. Para cada um que confira: `estado="CONFIRMADO"` no catálogo, com o texto
   literal na `evidencia`, à maneira do que já foi feito para o §7.2.2.
4. Para cada um que divirja: **abrir achado** — é um erro de dimensionamento,
   não um erro de documentação.
5. Regenerar este anexo e correr `pytest tests/test_f18_proveniencia_nbr.py`.
6. Quando a lista esvaziar, `aviso_nbr()` deixa de emitir a reserva sozinho.

---

*Gerado de `CATALOGO_NBR6123` em ea94841.*
