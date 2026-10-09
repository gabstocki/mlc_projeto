# 55 — Declarar softwares (Python, bibliotecas, LaTeX) e uso de IA na metodologia e nas referências

- **Tema:** Metodologia / Referências
- **Prioridade:** P2
- **Arquivos:** capítulo de metodologia (cap. 5/6 ou nova seção); `tese/apendiceA.tex`; `tese/referencias.bib`; `pyproject.toml` (versões)

## Origem (3ª revisão do orientador (2026-10))
Declarar: Python e bibliotecas (NumPy, SciPy, OpenSeesPy, PyVista, matplotlib, pandas…),
LaTeX/abnTeX2 e demais ferramentas; incluí-los nas referências. Declarar também o **uso de IA
(nome e ano)**.

## O que fazer
- [x] Tabela de software (nome, versão, uso) na metodologia, versões tiradas do ambiente (`pip freeze`).
- [x] Entradas `.bib` para cada software (citação recomendada de cada projeto).
- [x] Parágrafo de declaração de uso de IA (ferramenta, versão/ano, finalidade, revisão humana) — conferir regras da UFPR.

## Resolução (2026-10-08) ✅
- cap. 5, nova §5.1.1 «Ferramentas computacionais» (`ssec:ferramentas`) com `tab:software`:
  Python 3.12.7, NumPy 2.4.6, SciPy 1.17.1, pandas 3.0.3, openpyxl 3.1.5, Matplotlib 3.11.0,
  OpenSeesPy 3.8.0.0, PyVista 0.48.4 + VTK 9.6.2, pytest 9.1.0, TeX Live 2023 + abnTeX2 1.9.7
  (versões do `.venv`). SymPy está no `pyproject.toml` mas não é importado — não listado.
- `referencias.bib`: 13 entradas com a citação recomendada de cada projeto (artigos da Nature,
  SoftwareX, JOSS etc.) e `@manual` com campo `version` para as ferramentas.
- Declaração de IA (texto do usuário): Claude Opus 5 e 5.5 (Anthropic, 2026, via Claude Code)
  na **complementação e ajuste do código** escrito inicialmente pelo autor; **toda a concepção é
  humana**. Nomes dos modelos conforme os co-autores registrados nos commits.
- Pendente com o autor: conferir a regra da UFPR sobre a declaração (TODO no cap05.tex).
