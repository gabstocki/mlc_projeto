# 23 — Dimensões das chapas não publicadas (incl. base do pilar central)

- **Tema:** Ligações / memorial
- **Prioridade:** P2
- **Normas:** —
- **Arquivos:** `mlc_projeto/connections/connections.py:832-910`; `mlc_projeto/output/report.py`

## Apontamento do orientador
> Dimensões de algumas chapas não publicadas no memorial.
> [Bloco de reprodutibilidade] Dimensões da chapa de base do pilar central.

## Estado atual no código
- A sapata calcula `A_chapa_cm2` e `lado_chapa_cm`
  ([connections.py:600-601](../mlc_projeto/connections/connections.py),
  [:867-868](../mlc_projeto/connections/connections.py)), mas **espessuras** das chapas
  e as dimensões das **chapas embutidas** de L1/L2 não são calculadas nem publicadas.
- A chapa de base do **pilar central** (L3c) tem área, mas falta detalhamento completo
  no memorial.

## O que precisa ser feito
- [ ] Publicar no memorial todas as dimensões das chapas: base (L3/L3c), embutidas
      (L1/L2), incluindo **espessura**, largura, altura e furação.
- [ ] Ligar às verificações metálicas da issue [21](21-chapas-aco-en1993.md)
      (a espessura sai do dimensionamento, não pode ser arbitrada).
- [ ] Incluir a chapa de base do pilar central explicitamente.

## Critério de aceite
Todas as chapas dimensionadas e publicadas (com espessura) no memorial, incluindo a do
pilar central.
