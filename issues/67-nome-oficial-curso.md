# 67 — Nome oficial da especialização na capa, folha de rosto e termo de aprovação

- **Tema:** Pré-textuais
- **Prioridade:** P1 (simples, mas obrigatório para o envio)
- **Arquivos:** `tese/00-dados.tex` (`\ImprimirCurso` = “Curso de Engenharia Civil”, l. 75; natureza do trabalho “título de Especialista em Estruturas, Curso de Engenharia Civil”, l. 79); conferir capa, folha de rosto, termo de aprovação e ficha catalográfica
- **Origem:** 4ª revisão do orientador (2026-11), parágrafo inicial

## Problema
Capa, folha de rosto e termo de aprovação trazem “Curso de Engenharia Civil” e
“Especialista em Estruturas”, que não são o nome oficial da especialização.

## O que fazer
- [x] **Autor:** informar o nome oficial do curso e o título conferido (conforme o PPC/edital da UFPR).
- [x] Substituir em `00-dados.tex` e conferir todas as ocorrências no PDF (capa, rosto, termo, resumo/abstract se citarem).

## Resolução (2026-11-14)
Dados do autor: **Pós-Graduação *Lato Sensu* em Estruturas**, título de **Especialista em Estruturas**.

- `\ImprimirCurso` passou a "Pós-Graduação \textit{Lato Sensu} em Estruturas"; a capa sai em maiúsculas.
- Preâmbulo da folha de rosto e do termo: "…à obtenção do título de Especialista em Estruturas, Pós-Graduação *Lato Sensu* em Estruturas, Setor de Tecnologia, Universidade Federal do Paraná".
- Conferido no PDF, nas p. 1–3. O resumo e o abstract não citam o curso.
- Fora do escopo, ainda pendentes no termo e na ficha: nomes da banca (2º e 3º membros), data da defesa (sugerida 11/12/2026), CDU (atribuída pela biblioteca) e titulação do orientador (TODO em `00-dados.tex`).
