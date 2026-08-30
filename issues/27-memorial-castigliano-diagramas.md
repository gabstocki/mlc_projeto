# 27 — Derivação de Castigliano + diagramas M/V/N (anexo de análise)

- **Tema:** Reprodutibilidade do memorial
- **Prioridade:** P1
- **Normas:** boa prática de memorial de cálculo
- **Arquivos:** `mlc_projeto/core/loads.py:84-234`; `mlc_projeto/output/report.py`

## Apontamento do orientador
> Omissões do memorial que tornam não reprodutíveis os resultados:
> 1 — Definição de yc(x) e I(x), sistema de eixos, convenção de sinais de momento e o
> desenvolvimento da integral de Castigliano com seus limites. Não pode apenas
> publicar o resultado.
> 2 — Diagramas de momento fletor, esforço cortante e esforço normal ao longo da viga.
> A análise tem que estar em um anexo.

## Estado atual no código
- A análise biarticulada está em [loads.py:118-234](../mlc_projeto/core/loads.py):
  `y_c(x) = x_sim·tan(α)/2`, `I(x) = b·h(x)³/12`,
  `H = ∫ M0·y_c/I dx / ∫ y_c²/I dx`, `M(x) = M0 − H·y_c`.
- Os arrays `M_x`, `M0_x`, `y_c`, `x` são calculados, mas o **memorial** publica apenas
  resultados-síntese; falta o **desenvolvimento** e faltam os **diagramas**.

## O que precisa ser feito
- [ ] Escrever no memorial (anexo de análise): definição de `y_c(x)` e `I(x)`, o
      **sistema de eixos** e a **convenção de sinais** (coerente com issue
      [12](12-sistema-eixos-N-V.md)), e a **integral de Castigliano com seus limites**
      (0→L), incluindo a hipótese de apoio indeslocável (issue [24](24-tirante-fy315-flexibilidade.md)).
- [ ] Gerar e incluir os **diagramas M(x), V(x) e N(x)** ao longo da viga (usar os
      arrays já disponíveis; exportar figura no `report.py`).
- [ ] Conferir que `V_ELU()` ([loads.py:694-697](../mlc_projeto/core/loads.py)), hoje
      aproximado, seja substituído/derivado do M(x) real para o diagrama.

## Critério de aceite
Anexo de análise reprodutível (definições, eixos, sinais, integral com limites) +
diagramas M/V/N publicados.
