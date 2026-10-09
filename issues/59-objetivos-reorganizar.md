# 59 — Objetivos: mover para subseção do cap. 1; suprimir “Objetivo geral”; objetivos específicos ≠ metodologia

- **Tema:** Estrutura do documento — cap. 1/2
- **Prioridade:** P2
- **Arquivos:** `tese/cap02.tex` (inteiro: §2.1 l. 12, §2.2 l. 19, §2.3 Delimitação l. 86); `tese/cap01.tex`; `tese/main.tex`; `tese/cap01.tex:74` (§ Estrutura do trabalho — atualizar)

## Origem (3ª revisão do orientador (2026-10), p. 15)
- Colocar os objetivos como **subseção do capítulo 1**.
- Título “2.1 Objetivo geral” está riscado → **suprimir o título**.
- §2.2 Objetivos específicos parece **metodologia**. Se não forem obrigatórios, retirar; se forem, manter **apenas objetivos**.

## O que fazer
- [x] Verificar se o modelo UFPR/curso exige objetivos específicos.
- [x] Fundir cap. 2 no cap. 1; mover conteúdo metodológico para o capítulo de metodologia; realocar a Delimitação.
- [x] Renumerar capítulos e corrigir todas as referências cruzadas (`\ref`) e o texto “Estrutura do trabalho”.

## Resolução (2026-10-08) ✅
- `cap02.tex` removido (git rm); conteúdo no cap. 1: §1.3 OBJETIVOS (objetivo geral em
  parágrafo, **sem o título** “Objetivo geral”) e §1.4 DELIMITAÇÃO DO TRABALHO (texto mantido).
- Objetivos específicos **mantidos, só como objetivos** (escolha do usuário — vale exija ou não a
  UFPR): 5 alíneas de resultado (geometria e seções; contraventamentos; ligações/ancoragem em
  desenho + esforços para a fundação; custo; programa aberto e testado). Os 8 itens antigos eram
  passos de método (caracterizar, levantar ações, verificar…) e a tabela alínea × capítulo saiu.
- Labels antigos mantidos como âncoras (`sec:objetivo-geral`, `sec:objetivos-especificos`,
  `sec:delimitacao`); `cap:objetivos` deixou de existir. “Estrutura do trabalho”: oito capítulos.
- cap. 9 (Quanto aos objetivos) reescrito para os 5 objetivos novos. Capítulos renumerados
  automaticamente (Revisão = cap. 2 … Considerações finais = cap. 8); nenhum número fixo no texto.
- A exigência de objetivos específicos pelo modelo UFPR não foi verificada (sem acesso à regra).
