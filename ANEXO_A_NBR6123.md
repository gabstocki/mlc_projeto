# ANEXO A — Proveniência dos valores da ABNT NBR 6123:2023

> **Folha de conferência do achado [F-18].** Gerada por
> `auditoria_v2/gerar_anexo_nbr.py` a partir de `CATALOGO_NBR6123`
> (`mlc_projeto/core/normativo.py`). **Não editar à mão** — corrigir o
> catálogo e regenerar.

## O que este anexo é, e o que não é

**Não reproduz a NBR 6123:2023.** A norma é obra protegida por direito autoral
e o repositório tem remoto público; `NBR6123-2023.pdf` está deliberadamente
fora do git (ver `.gitignore`). O controle documental exige uma cópia
controlada disponível ao projetista, não a sua redistribuição — e um memorial
cita cláusulas, não reimprime a norma.

É o registo de **todos** os números do projeto que dependem da NBR 6123, com o
local exato no código, a cláusula, o estado de verificação e a evidência.

## Como foi verificado

`auditoria_v2/bm_nbr_texto.py` (BM-17) **lê o PDF** com `pdftotext`, extrai as
tabelas e confronta valor a valor com o que o repositório implementa. Extrai,
compara, descarta: nada da norma fica no repositório. Sem o PDF, aborta com
instrução — nunca degrada em silêncio para uma verificação mais fraca.

| Verificação | Resultado |
|---|---|
| Tabela 1 — parâmetros meteorológicos | **45/45** valores |
| Tabela 2 — fator de rajada | **3/3** valores |
| **Tabela 3 — S2 tabelado contra a fórmula de §5.3.3** | **279 células**, pior Δ = 0,0050 |
| Tabela 10 — telhados múltiplos | **40/40** valores |
| Tabela 25 — cobertura isolada duas águas | **8 expressões**, 216 amostras |
| §4.2 c), §5.2 a), §7.2.1, §7.2.2, §7.2.6, nota da Tab. 10 | à letra |

A **Tabela 3** é a verificação forte. A norma dá o S2 tabelado *e* a fórmula
que o gera; confrontar uma com a outra testa `b`, `p`, `z_g`, `F_r` e a regra
especial da Categoria V de uma só vez, contra dados externos ao repositório. O
pior desvio em 279 células é 0,0050 — exatamente o arredondamento a duas casas.

## Porque isto importa em obra

O vento governa **toda** a estrutura metálica de contraventamento e a
verificação da telha. Um erro numa destas tabelas não produz um aviso: produz
um dimensionamento errado que passa em todos os testes.

## Estado

| | |
|---|---|
| Itens catalogados | 15 |
| Confirmados contra o texto | **11** |
| **Por resolver** | **4** |

Dois estados apenas, deliberadamente: `CONFIRMADO` significa que o texto
literal foi lido e confrontado. Tudo o resto é `NAO_CONFIRMADO`.

**Nenhum dos que sobram é uma tabela.** São um valor que depende de um dado que
o projeto não declara, duas decisões que só o projetista toma, e uma lacuna.

---

## A. Itens por resolver



### A.1 — Velocidade básica V0 = 45 m/s

| | |
|---|---|
| Cláusula alegada | `NBR 6123:2023 §5.1, Figura 1` |
| Local no código | `core/normativo.py:137, main.py VENTO_PARAMS` |
| Símbolos | `V0` |
| Chave no catálogo | `v0_isopleta` |

**Verificação independente:** BM-17 confirmou a DEFINIÇÃO de §5.1 (rajada de 3 s a 10 m, campo aberto e plano, excedida em média uma vez em 50 anos, lida no gráfico de isopletas da Figura 1). O VALOR continua sem verificação possível: a Figura 1 é um mapa, e o projeto não declara a localidade da obra em lado nenhum.

**A confirmar:** Qual é a localidade da obra? Sem ela, V0 = 45 m/s não é rastreável — é o único valor de vento do projeto que permanece sem fonte, e nem uma invariante lhe é aplicável.

### A.2 — Fator estatístico S3 = 1,0

| | |
|---|---|
| Cláusula alegada | `NBR 6123:2023 §5.4 Tab. 4` |
| Local no código | `core/normativo.py:139` |
| Símbolos | `S3` |
| Chave no catálogo | `s3_estatistico` |

**Verificação independente:** **[F-21] CONTRADIÇÃO ENTRE O VALOR E O SEU RÓTULO.** A Tab. 4 da :2023 dá grupo 2 → S3 = 1,06 (Tp 75 anos) e grupo 3 → S3 = 1,00 (Tp 50 anos). O código adota 1,00 — que é o do GRUPO 3 — rotulado «grupo 2». Se a classificação correta for o grupo 2, toda a ação de vento sobe 1,06² = +12,4 %, e o defeito é NÃO CONSERVATIVO.

**A confirmar:** A que grupo da Tab. 4 pertence o galpão? Grupo 3 abrange «residências, hotéis, comércio, indústrias»; grupo 2 é para estruturas cuja ruína represente substancial risco à vida, com aglomerações. Um estacionamento coberto parece grupo 3 — mas é o projetista que classifica, e o rótulo atual afirma o contrário do valor usado.

### A.3 — Colunas b1/b2/b3 da Tab. 10 (vento α = 90°) e c_pe médio

| | |
|---|---|
| Cláusula alegada | `NBR 6123:2023 Tab. 10` |
| Local no código | `NÃO IMPLEMENTADO` |
| Símbolos |  |
| Chave no catálogo | `tabela_10_alpha_90` |

**Verificação independente:** Apanhado ao ler a tabela: a Tab. 10 tem, além das zonas a*..z* para α = 0°, as colunas b1/b2/b3 para α = 90° (−0,8 / −0,6 / −0,2) e uma linha de c_pe médio para elementos localizados. O repositório só transcreveu α = 0°.

**A confirmar:** Na rota de edificação fechada (§7.2.1), o vento paralelo às cumeeiras devia usar b1/b2/b3 da Tab. 10. O projeto trata θ = 0° pela rota de cobertura isolada (§7.2.2 + arrasto dos pilares). As duas rotas estão a ser misturadas de forma coerente? Só o projetista fecha esta.

### A.4 — Coeficiente de arrasto C_a = 1,2 de pilar prismático livre

| | |
|---|---|
| Cláusula alegada | `NBR 6123:2023 §6.3 / Tab. 13 — CITAÇÃO ERRADA` |
| Local no código | `core/wind.py:507-509` |
| Símbolos | `CA_PILAR_RET` |
| Chave no catálogo | `ca_pilar` |

**Verificação independente:** **[F-20] A CITAÇÃO NÃO EXISTE PARA ESTE FIM.** Na :2023, §6.3 é «Pressões internas em edificações» e a Tab. 13 é «Distribuição das pressões externas em edificações cilíndricas de seção circular». Nenhuma trata do arrasto de uma barra prismática livre. A rota certa é §8.1.1: Cx/Cy da Tab. 26 (barras de faces planas, comprimento infinito) multiplicados pelo fator K de comprimento finito da Tab. 28 (0,62 a 0,95 para ℓ/c de 2 a 100). A Tab. 26 dá Cx ≥ +1,6 em α = 0°, o que com K ≈ 0,7 dá ≈ 1,1–1,4: o valor 1,2 cai dentro do intervalo, mas não foi obtido por esta rota e não está demonstrado como conservador. Peso: o arrasto dos pilares é 60,5 kN em 837,3 kN do vento θ=0° (7,2 %).

**A confirmar:** Refazer C_a por §8.1.1: qual a relação ℓ1/ℓ2 da secção do pilar e qual o ℓ/c para entrar na Tab. 28? As figuras da Tab. 26 são imagens no PDF e não se leem por extração de texto — exigem consulta visual.

---

## B. Itens confirmados contra o texto

### Parâmetros meteorológicos b, p, z_g por categoria e classe

| | |
|---|---|
| Cláusula | `NBR 6123:2023 §5.3.3 Tab. 1` |
| Local | `core/wind.py:32-41` |


BM-17: os 45 valores conferem um a um com a Tab. 1 do texto da :2023. Verificação cruzada mais forte: as 279 células da Tab. 3 (S2 tabelado pela própria norma) são reproduzidas pela fórmula de §5.3.3 com estes parâmetros, pior desvio 0,0050 — exatamente o arredondamento a 2 casas. Isto testa b, p, z_g, F_r e a regra especial da Categoria V de uma só vez, contra dados que não saíram do repositório.

### Fator de rajada F_r por classe (A=1,00 B=0,98 C=0,95)

| | |
|---|---|
| Cláusula | `NBR 6123:2023 §5.3.3 Tab. 2` |
| Local | `core/wind.py:42-43` |


BM-17: os 3 valores conferem com a Tab. 2 do texto. A dúvida de numeração levantada em Z.18 estava errada: a :2023 tem mesmo Tab. 1 (parâmetros), Tab. 2 (rajada) e Tab. 3 (S2 tabelado), tal como o código sempre citou.

### q = 0,613·Vk² (N/m², Vk em m/s)

| | |
|---|---|
| Cláusula | `NBR 6123:2023 §4.2 c)` |
| Local | `core/wind.py:45-47` |


BM-17: §4.2 c) confirmado à letra — q = ½ρVk² com ρ = 1,226 kg/m³, «q = 0,613 Vk2, expresso em Newton por metro ao quadrado». Também dedutível da física (BM-01, Δ = 0,000 %).

### Fator topográfico S1 = 1,0

| | |
|---|---|
| Cláusula | `NBR 6123:2023 §5.2 a)` |
| Local | `core/normativo.py:138` |


BM-17: §5.2 a) «terreno plano ou fracamente acidentado: S1 = 1,0» confirmado à letra. Que o terreno seja plano é premissa de projeto, a conferir no levantamento.

### c_pi = +0,8 (obstrução a sotavento) / −0,3 (a barlavento)

| | |
|---|---|
| Cláusula | `NBR 6123:2023 §7.2.1, último parágrafo` |
| Local | `core/wind.py:236-243` |


BM-17: parágrafo confirmado à letra, incluindo os dois sinais e o gatilho («Para os casos em que a altura h for inferior aos limites de 7.2.1, ou em que obstruções possam ser colocadas sob ou junto à cobertura»).

### Domínio das Tab. 24/25: 0,07 ≤ tg θ ≤ 0,6 e h ≥ 0,5·ℓ2

| | |
|---|---|
| Cláusula | `NBR 6123:2023 §7.2.1` |
| Local | `core/wind.py:354-405` |


BM-17: condição confirmada à letra para as duas águas. É esta condição que expulsa a geometria do projeto (h = 7,0 m < 0,5·ℓ2) da Tab. 25 e obriga à rota alternativa de edificação fechada — a recusa do código está certa.

### C_pe externos de telhados múltiplos, zonas a*..z*, θ=5..45°

| | |
|---|---|
| Cláusula | `NBR 6123:2023 Tab. 10` |
| Local | `core/wind.py:245-265` |


BM-17: os 40 valores conferem um a um. A NOTA de que «para α = 0° as forças horizontais de atrito já estão consideradas nos valores da Tabela 10» também está confirmada — é o que impede a dupla contagem com §7.2.2.

### Cpb/Cps de cobertura isolada a duas águas, carregamentos 1 e 2

| | |
|---|---|
| Cláusula | `NBR 6123:2023 Tab. 25` |
| Local | `core/wind.py:410-450` |


BM-17: as 8 expressões conferem à letra, e 216 amostras numéricas em 0,07 ≤ tg θ ≤ 0,60 batem com zero desvio. O teto «2,4 tgθ + 0,6 ≤ 2,0», que Z.18 suspeitava ser interpolação do autor, ESTÁ na norma. A numeração Tab. 25 confere.

### c_p = ±2,0 por elemento de vedação (fixação da telha)

| | |
|---|---|
| Cláusula | `NBR 6123:2023 §7.2.6` |
| Local | `checks/elu/fixacao_telha.py:70-75` |


BM-17: §7.2.6 confirmado à letra — «Cada elemento de vedação deve ser calculado com cp = ±2,0». O docstring obsoleto do módulo, que descrevia a rota antiga por zonas da Tab. 5 com c_pi de §6.2.5, foi removido agora que a cláusula está confirmada.

### Ft = 0,5·q·a·b — força horizontal, vento paralelo à geratriz

| | |
|---|---|
| Cláusula | `NBR 6123:2023 §7.2.2` |
| Local | `core/wind.py:518-548` |


Texto fornecido pelo utilizador e agora reconfirmado por BM-17 contra o PDF. É uma ação ENVOLVENTE («englobam a ação do vento sobre as duas faces»), não uma estimativa de atrito de superfície — foi por confundir as duas coisas que a auditoria propôs 0,05 e teve de se retratar.

### c_d = 1,2 do diagnóstico de arrasto de silhueta

| | |
|---|---|
| Cláusula | `NBR 6123:2023 — NÃO se reclama cláusula` |
| Local | `core/wind.py:550-552` |


Não é valor de projeto: entra apenas na razão informativa que compara Ft com o arrasto de um corpo maciço de igual silhueta, para apanhar erro de ENTRADA. Nada dimensionado depende dele — daí não haver o que confirmar.


---

## C. O que mudou, e porquê importa

A primeira versão deste anexo declarava
`NOT VERIFIABLE — REQUIRES EXTERNAL NORMATIVE SOURCE` para as onze tabelas e
cláusulas, e construiu o BM-15 — sete invariantes de coerência interna — como o
melhor que se podia fazer sem a norma.

**A norma estava na raiz do projeto o tempo todo.** A auditoria nunca listou a
árvore à procura dela: inventariou os `.py` e ignorou o resto. É falha de
cobertura da própria auditoria, e o episódio do [F-13] — em que se argumentou
que `Ft = 0,5·q·a·b` era fisicamente impossível, com retratação depois — teria
sido evitado abrindo o ficheiro.

O BM-15 continua a correr, agora no papel certo: guarda de regressão barata
que não precisa do PDF. Quem clonar o repositório sem a cópia licenciada tem
as sete invariantes; quem a tiver corre o BM-17 e verifica contra o texto.

## D. Achados abertos pela leitura da norma

Verificar contra a fonte confirmou onze itens **e destapou dois defeitos** que
nenhuma verificação de coerência interna podia apanhar:

**[F-20] `C_a = 1,2` sob citação inexistente.** Estava citado como
«§6.3 / Tab. 13». Na :2023, §6.3 é *Pressões internas em edificações* e a
Tab. 13 é *edificações cilíndricas de seção circular*. A rota correta é §8.1.1
(Tab. 26, `Cx`/`Cy`) com o fator `K` de comprimento finito (Tab. 28). O valor
cai dentro do intervalo plausível mas não foi obtido por essa rota. Peso:
7,2 % da ação de vento θ = 0°.

**[F-21] `S3 = 1,00` rotulado «grupo 2».** A Tab. 4 dá grupo 2 → 1,06
(Tp 75 anos) e grupo 3 → 1,00 (Tp 50 anos). O valor usado é o do grupo 3; o
rótulo diz grupo 2. Se a classificação correta for o grupo 2, **toda** a ação
de vento sobe 1,06² = **+12,4 %** — defeito não conservativo. Só o projetista
classifica a edificação.

Nenhum dos dois foi corrigido: ambos exigem dados que o projeto não tem
(a secção do pilar para a Tab. 28; a classificação da edificação). Estão
declarados no código, no catálogo e nas saídas.

## E. Como fechar o que resta

1. **`v0_isopleta`** — declarar a localidade da obra e ler a isopleta na
   Figura 1.
2. **`s3_estatistico`** — classificar a edificação na Tab. 4 e acertar valor e
   rótulo entre si.
3. **`ca_pilar`** — refazer `C_a` por §8.1.1 com a secção real do pilar.
4. **`tabela_10_alpha_90`** — decidir se a rota de edificação fechada exige as
   colunas b1/b2/b3 para vento paralelo às cumeeiras.

Para cada um: `estado="CONFIRMADO"` no catálogo com a evidência escrita, ou
abrir achado se divergir. Depois regenerar este anexo e correr
`pytest tests/test_f18_proveniencia_nbr.py`.

---

*Gerado de `CATALOGO_NBR6123` em 4e77401.*
