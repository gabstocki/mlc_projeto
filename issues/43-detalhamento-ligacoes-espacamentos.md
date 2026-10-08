# 43 — Detalhamento das ligações com atendimento dos espaçamentos

- **Tema:** Ligações — detalhamento
- **Prioridade:** P1
- **Normas:** EN 1995-1-1 §8.5–§8.7 (Tab. 8.4/8.5 — a1, a2, a3,t, a3,c, a4,t, a4,c), EN 1993-1-8 Tab. 3.3 (e1, e2, p1, p2 em chapas), EN 1992-4 (distâncias de borda dos chumbadores)
- **Arquivos:** `mlc_projeto/connections/*.py`; `tese/cap08.tex`
- **Relaciona:** issues 29, 42, 48, 52

## Origem (3ª revisão do orientador (2026-10))
“Após o cálculo, apresentar o detalhamento das ligações mostrando o atendimento dos
requisitos (espaçamentos) de detalhamento.”

## O que fazer
- [ ] Para cada ligação (L1, L1c, L3, L3c, ancoragem, extremidades das diagonais, terça–viga):
      tabela **requerido × adotado** de todos os espaçamentos e distâncias (madeira, chapa, concreto).
- [ ] Desenho cotado de cada ligação mostrando esses valores (integra a issue 52).
- [ ] Garantir que o código exporta os espaçamentos adotados (já parcialmente no dict da L1).
