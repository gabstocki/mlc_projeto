# 98 — Lista de siglas completa

- **Tema:** Pré-textuais
- **Prioridade:** P2
- **Arquivos:** `tese/00-pretextual.tex` (lista de siglas: hoje só BDI, MLC, NDP)
- **Origem:** 4ª revisão, item 9.4

## O que fazer
- [x] Incluir ELU, ELS, CS, UC, EC5, CEN, ABNT, CV-H, CV-V, CV-T (e CBPMPR, TRRF, NPT se a issue 88 entrar).
- [x] Designações das ligações (L1, L1c, L1f, L3, L3c, L3f, L3a): incluir ou remeter à Tabela 2.

## Resolução (2026-11-12)
A lista passou de 3 para 23 entradas.

**Por extenso na primeira ocorrência** (`\criarsigla*`), além de MLC, NDP e BDI, que já estavam assim:
- ABNT (cap. 1, NBR 7190:1997);
- CEN, junto com EC5 (cap. 1, "norma do Comitê Europeu de Normalização (CEN) conhecida como Eurocódigo 5 (EC5)");
- NPT e CBPMPR (cap. 1);
- CCA e CCB (cap. 4, tratamento preservativo).

**Só registradas**, em `tese/00-siglas.tex`, lido no início do cap. 1:
- EC5, EN, NBR, ISO, UC e NP;
- CV-H, CV-V e CV-T;
- L1/L1c/L1f, L3/L3c e L3f/L3a;
- P, PF, T e V, que remetem à tabela "Nomenclatura dos elementos" (cap. 4), onde as designações já estão definidas.

**Não incluídas:** ELU, ELS e CS não são usadas como sigla, porque o texto escreve "estado-limite último", "de serviço" e "classe de serviço" por extenso. TRRF também não aparece como sigla (o texto diz "tempo requerido de resistência ao fogo").
