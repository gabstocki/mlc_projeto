# 62 — Revisão textual do restante do documento (após p. 35) com os mesmos critérios

- **Tema:** Texto — geral
- **Prioridade:** P2 (fazer por último, após as issues de conteúdo)
- **Arquivos:** `tese/cap05.tex` … `tese/cap09.tex`, `tese/apendiceA.tex`

## Origem (3ª revisão do orientador (2026-10))
O orientador anotou o PDF **até a p. 35** e pediu: “aplique a todo o texto”.

## O que fazer
- [x] Passar pelo restante aplicando os critérios das anotações: redação precisa nas aberturas
      de capítulo, termos técnicos adequados, espaços espúrios, separar metodologia × resultado,
      símbolos coerentes com a lista (56), precisão numérica (53), nomes dos elementos (52).
- [x] Recompilar e conferir referências cruzadas, listas de figuras/tabelas.

## Resolução (2026-10-08) ✅
- **Aberturas de capítulo:** caps. 5–9 começavam direto numa seção; ganharam parágrafo de abertura
  (o que o capítulo faz e como se organiza), no padrão do cap. 4 (issue 61).
- **Espaços espúrios:** a causa geral (`\noindent` no macro `\tabela`) já fora corrigida na 61 e
  vale para todas as tabelas.
- **Precisão (53):** varredura por valores de 4 casas e >3 alg. sig. nos caps. 5–9 e Apêndice A,
  inclusive no texto movido pela issue 60 — restam só coeficientes legítimos (tg θ = 0,0882) e o
  exemplo da convenção (0,7492).
- **Símbolos (56):** símbolos usados nos caps. 5–9 comparados com `00-simbolos.tex`; acrescidos
  $b_1$–$b_3$, $\ell_2$, $\lambda_{rel,m}$, $\sigma_{m,crit}$ e $\psi_{0,W}$.
- **Apêndice A:** estatísticas do programa atualizadas (60 arquivos, 27.096 linhas; pacotes
  `checks/elu` 25, `connections` 8, `output` 9) e tabela de fases (nó de topo, fogo, pilar de
  frontão, detalhe das bases, desenhos e apêndices gerados).
- **Metodologia × resultado (51)** e **nomes dos elementos (52)**: já aplicados nas respectivas
  issues; sem pendências novas encontradas.
- Compilação: sem referências indefinidas nem overfull hbox; 15 figuras e 41 tabelas listadas;
  únicos rótulos sem citação são equações. 115 páginas.
- **TODOs que dependem do autor** (não resolvíveis aqui): URL do repositório (`VALIDAR`,
  Apêndice A), ficha catalográfica, CDU, data da defesa, titulação do orientador, banca,
  regra da UFPR sobre IA, fontes de preços e percentuais do custo, V0/S3 e forças de impacto,
  fixador da telha, manilhas, tempo de resistência ao fogo, conferência das referências das
  issues 57 e 60.
