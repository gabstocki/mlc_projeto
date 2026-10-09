# 56 — Lista de símbolos + coluna de símbolo na Tabela 4 (e “–” para adimensionais)

- **Tema:** Formatação / Notação
- **Prioridade:** P1 (indispensável dado o volume de notação; articula com 50)
- **Arquivos:** `tese/00-pretextual.tex` (lista de símbolos abnTeX2); `tese/cap04.tex:60-85` (Tabela 4 — Parâmetro | Valor | Unidade)
- **Relaciona:** issues 50, 52

## Origem (3ª revisão do orientador (2026-10))
Elaborar a **lista de símbolos**. Na **Tabela 4** (p. 24): incluir coluna com o **símbolo**
adotado para cada variável; quando a grandeza não tiver unidade, colocar **“–”**.

## O que fazer
- [x] Levantar todos os símbolos usados (tese + relatório) e fixar notação única (EC5 como base).
- [x] Lista de símbolos no pré-textual (ambiente `siglas`/`simbolos` do abnTeX2).
- [x] Tabela 4: coluna “Símbolo”; “–” para adimensionais. Estender a todas as tabelas de dados de entrada (issue 51).

## Resolução (2026-10-08) ✅
- `tese/00-simbolos.tex` (novo): lista curada (~110 símbolos) em três grupos — latinas maiúsculas,
  minúsculas e gregas —, notação EN 1995-1-1; levantada por varredura de `$…$` e das equações
  dos caps. 1–9 e apêndices B/C. Ativada em `00-dados.tex` (`\terSimbolos{Sim}`); o
  `\criarsimbolo` do modelo não foi usado porque ordena pela descrição.
- Tabela 4 (`tab:geometria-edificacao`): coluna Símbolo ($B_{tot}$, $L_{tot}$, $L$, $L_T$, $H$,
  $b_t\times h_t$, $s$) e “--” para adimensionais (nº de vãos e de pórticos).
- Estendido às tabelas de entrada: `tab:valores-declarados` ($g_{tel}$, $g_{ins}$, $q_k$, $Q_k$,
  $V_0$, $S_1$, $S_3$, $F_{d,x}$, $F_{d,y}$; “--” em categoria/classe e unidades adimensionais) e
  `tab:ligacao-l1-arranjo`. GL24h e NDP já traziam o símbolo.
- Símbolos novos introduzidos: $B_{tot}$, $L_{tot}$, $g_{tel}$, $g_{ins}$, $F_{d,x}$, $F_{d,y}$.
