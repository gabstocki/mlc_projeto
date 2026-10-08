# 51 — Organização: tabelas de entrada separadas das de resultado; anexos de análise e saída do pipeline

- **Tema:** Memorial / Estrutura do documento
- **Prioridade:** P2
- **Arquivos:** `tese/cap04.tex` … `tese/cap08.tex`; `tese/apendiceA.tex`; `tese/main.tex`; `output/pipeline_console.txt`; `output/relatorio_mlc_diagrama_MVN.pdf`
- **Relaciona:** issues 27, 28, 52

## Origem (3ª revisão do orientador (2026-10))
Organizar os **dados de entrada** em tabelas próprias e os **resultados** em outras, separadas.
Colocar em **anexo** a análise estática (diagramas e esforços por combinação) e a **saída
completa do pipeline**.

## O que fazer
- [x] Inventariar tabelas que misturam entrada e resultado; separar.
- [x] Anexo: análise estática — diagramas M/V/N e tabela de esforços por combinação (17 combos).
- [x] Anexo: saída completa do pipeline (listing do `pipeline_console.txt` ou relatório PDF incluído).

## Resolução (2026-10-07) ✅
São **apêndices** (C e D), não anexos: pela ABNT NBR 14724, anexo é material de terceiros.

**Inventário das tabelas (cap. 3–8).** Critério: *entrada* = valor fixado antes da análise e
recebido pelo programa sem cálculo; *resultado* = tudo o que o programa calcula (inclusive
dimensões auto-dimensionadas). Tabelas mistas encontradas e separadas:
- cap. 4 `geometria-edificacao`: misturava arquitetura com seções resultantes do pré-dim.
  (α, h0, h_ap, b, pilares) → fica só a entrada; as seções já estão em `criterios-predim`
  (cap. 5), que ganhou a linha h_ap = h0 + (L/2)·tanα.
- cap. 6 `peso-proprio`: telha e instalações (declaradas) repetidas → uma linha remetendo a
  `valores-declarados`; título "Ação permanente característica calculada".
- cap. 6 `acoes-vento`: contagens (14 padrões, 29 combinações) saem da tabela (já estão no texto).
- cap. 8 `ligacao-l1` → `ligacao-l1-arranjo` (d, n, planos, a2, a3,t, a4,c, h) + `ligacao-l1`
  (força, ângulo, resistências, η).
- cap. 8 custo: nova `custo-entrada` (R$/m³, R$/kg, 15 %, 12 %, 25 %); `custo-composicao`
  passa a citar a origem em vez de repetir os preços.
- Demais tabelas já eram puras (cap. 4 entrada; cap. 5–8 resultado). Tabelas de verificação com
  a solução adotada + η (nó de topo, diagonais) foram mantidas: a solução é resultado do
  auto-dimensionamento.
- cap. 1 (estrutura do trabalho) declara o critério e lista os apêndices A–D; cap. 4 idem.

**Apêndice C — análise estática** (`mlc_projeto/output/apendice_analise.py` → `tese/apendiceC.tex`
+ `tese/fig/analise_MVN_*.pdf`, gerado pelo pipeline junto do apêndice B): diagramas M/V/N da
governante; M/V/N das **29** combinações sobrepostos (não 17: issue 39 levou a 14 padrões);
tabela por combinação (q_esq, q_dir, M_max, x, M_cum, R_A, R_B, V, N). V e N nos apoios pela
decomposição analítica no eixo (o gradiente numérico subestimava ~0,5 %: 99,0 × 99,2 kN).
`Carregamentos.diagramas_MVN_ELU(comb=None)` aceita qualquer combinação e devolve R_A/R_B.

**Apêndice D — saída do pipeline**: `\lstinputlisting` de `../output/pipeline_console.txt`
(estilo `consoleUFPR`); `literate` ganhou § █ ⊥ − ℓ ⁺ ⁻ ⇒.

Testes: `tests/test_apendices_analise.py` (5), incluindo guarda de que todo caractere não ASCII
do console está mapeado no listings (senão o pdflatex aborta). Suíte 703 passed; tese 94 p.
