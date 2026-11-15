# 95 — Referências: letras de desambiguação, autoria da EN 1992-4, “Citado n vezes”, destaque do título

- **Tema:** Citações e referências
- **Prioridade:** P1
- **Normas:** ABNT NBR 6023:2018, NBR 10520:2023
- **Arquivos:** `tese/*.bib`, configuração do biblatex/abntex2cite em `tese/00-pacotes*.tex`
- **Origem:** 4ª revisão, itens 8.1, 8.3 e 8.4

## O que fazer
- [x] 8.1 — O texto cita “(CEN, 2002a)”, “(CEN, 2004b)”, “(CEN, 2013a)”, mas as entradas não trazem a
      letra: incluir as letras nas entradas da lista (cada citação ↔ uma referência).
- [x] 8.3 — EN 1992-4 está como “EUROPEAN COMMITTEE FOR STANDARDIZATION. BS EN 1992-4”: usar a EN do
      CEN (coerente com “(CEN, 2018)”) ou atribuir a BS à BSI.
- [x] 8.4 — Retirar as remissões “Citado n vezes nas páginas [...]” (backref do abnTeX2).
- [x] 8.4 — Destaque do título (negrito/itálico) conforme a NBR 6023, uniforme em todas as entradas.

## Resolução (2026-11-12)
- 8.1: opção `extradate=true` do biblatex-abnt. A lista agora traz a mesma letra da citação (CEN 2002a/b/c, 2004a/b, 2005a–f, 2013a–d, 2017a/b, 2018a/b), conferida no PDF.
- 8.3: a EN 1992-4 passou a ser a EN do CEN (`Title = {EN} 1992-4: 2018`), coerente com "(CEN, 2018b)".
- 8.4: `backref=false` e `citecounter=false`; nenhum "Citado n vezes" no PDF.
- 8.4: o destaque já era uniforme pela NBR 6023, conferido nas páginas renderizadas. O título fica em negrito em normas, livros, dissertações e manuais, e o periódico em negrito nos artigos; o subtítulo vai sem destaque.
- Efeito colateral: com o backref desligado, o aviso persistente "Please (re)run Biber" e "There were undefined references" (issue 99) sumiu.
