# 61 — Cap. 4: ajustes de redação (abertura, espaço espúrio, “molhamento”)

- **Tema:** Texto — cap. 4
- **Prioridade:** P2
- **Arquivos:** `tese/cap04.tex:7` (“Este capítulo fixa o objeto do dimensionamento.”); `tese/cap04.tex` §4.2.1 (espaço espúrio); `tese/cap04.tex:123` (“molhamento”)

## Origem (3ª revisão do orientador (2026-10), pp. 22–24)
- p. 22: “Este capítulo fixa o objeto do dimensionamento.” — redação imprecisa; reescrever.
- p. 23, §4.2.1: espaço espúrio no texto — a nota está no PDF (p. 24 do arquivo) ao fim do
  parágrafo “…a característica, nas verificações de ligação.” (`tese/cap04.tex:92`);
  provavelmente o vazio vertical antes da Tabela 5 (float).
- p. 24, §4.2.2: “molhamento” → outro termo (ex.: “umedecimento”, “exposição eventual à chuva”).
(Itens da Tabela 4 → issue 56.)

## O que fazer
- [x] Aplicar as três correções; localizar o espaço espúrio no PDF compilado.

## Resolução (2026-10-08) ✅
- Abertura do cap. 4 reescrita: «Este capítulo define a estrutura a ser dimensionada e as
  condições sob as quais o dimensionamento é feito…».
- «molhamento» → «exposição eventual à chuva conduzida pelo vento» (§ Classe de serviço).
- **Espaço espúrio — causa encontrada no macro `\tabela`** (`00-pacotesOpcionais.tex`): o
  `\noindent` antes de `\begin{table}` abria um parágrafo vazio contendo o float; quando a tabela
  não cabia, a página era encerrada ali e o texto seguinte ia para depois do float (p. 27: ~⅓ de
  página em branco após «…nas verificações de ligação.»). Removido o `\noindent` (com `%` no fim da
  linha anterior): o texto agora preenche a página. A correção vale para **todas** as tabelas.
  Testado também `[!htbp]`: resultado igual ao `[!ht]`, mantido o original.
