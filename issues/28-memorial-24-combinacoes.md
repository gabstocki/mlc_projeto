# 28 — Tabela das 24 combinações + Cpe dos 8 padrões

- **Tema:** Reprodutibilidade do memorial
- **Prioridade:** P1
- **Normas:** EN 1990 (combinações); NBR 6123 Tab.25 (Cpe)
- **Arquivos:** `mlc_projeto/core/loads.py:458-624`; `mlc_projeto/core/wind.py:137-190`; `mlc_projeto/output/report.py`

## Apontamento do orientador
> Para completude do memorial falta a tabela completa das vinte e quatro combinações
> com os coeficientes de pressão de cada um dos oito padrões: publica-se apenas o
> envelope.
> [Bloco de reprodutibilidade] Tabela das vinte e quatro combinações com os
> coeficientes de pressão de cada um dos oito padrões. A primeira versão trazia Cpb e
> Cps; a segunda os removeu.

## Estado atual no código
- 8 padrões Cpe (Tab.25) são gerados em
  [wind.py:137-190](../mlc_projeto/core/wind.py) (C1/C2 × assimétrico/reverso/unif.bv/unif.st).
- Para cada padrão, 3 combinações ELU (W dom., sucção, Q dom.) → ~24 combinações em
  [loads.py:458-499](../mlc_projeto/core/loads.py). Mas o relatório publica só o
  **envelope** (aliases ELU_C1..C4).

## O que precisa ser feito
- [ ] Publicar a **tabela completa** das 24 combinações, com: id do padrão, Cpb e Cps
      (ou C_esq/C_dir), q_esq/q_dir, M_max, H, duração, e a marcação da governante.
- [ ] Reintroduzir **Cpb e Cps** por padrão (presentes em `coeficientes_tabela25`,
      [wind.py:96-134](../mlc_projeto/core/wind.py)) — a 2ª versão os removeu.
- [ ] Gerar a tabela no `report.py` (todas as combinações, não só os aliases).

## Critério de aceite
Tabela das 24 combinações com Cpb/Cps dos 8 padrões publicada no memorial;
governante(s) destacada(s).
