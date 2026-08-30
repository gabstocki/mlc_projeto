# 01 — Peso próprio gk superestimado

- **Tema:** Ações e combinações
- **Prioridade:** P1
- **Normas:** EN 1991-1-1
- **Arquivos:** `mlc_projeto/main.py:109`, `mlc_projeto/core/loads.py:321`

## Apontamento do orientador
> Confira o valor de gk. Eu esperava algo como peso próprio da MLC ≈ 0,43 kN/m² +
> terças, telha e instalações ≈ 0,25 kN/m², total ≈ 0,70 kN/m². O valor adotado é
> mais que o dobro do que esperava, mas pode ser que você tenha adotado um telhado
> mais pesado; isso é importante porque superestimar o peso próprio pode prejudicar
> a análise quando o esforço é inverso — ver combinação ELU-C3.

## Estado atual no código
- `G_AREA = 1.50` kN/m² em [main.py:109](../mlc_projeto/main.py) (default também em
  `Carregamentos.g_area = 1.50`, [loads.py:321](../mlc_projeto/core/loads.py)).
- Valor > 2× o esperado (~0,70 kN/m²).

## Por que importa
Nas combinações de **sucção/uplift** (ELU_S / ELU_C3, `0,9G + 1,5W`), superestimar G
mascara o esforço inverso (levantamento) — o caso G desfavorável quando o vento
alivia. Um gk alto torna a verificação de sucção artificialmente confortável.

## O que precisa ser feito
- [ ] Levantar a composição real de G: peso próprio MLC + terças + telha + instalações.
- [ ] Se o telhado for realmente pesado, **documentar** a discriminação no memorial;
      caso contrário, ajustar `G_AREA` para o valor correto (~0,70 kN/m²).
- [ ] Reexecutar o pipeline e conferir especialmente a issue [04](04-coef-G-favoravel-C3.md)
      (combinação de sucção).

## Critério de aceite
gk discriminado por parcela no memorial e coerente com o telhado especificado; a
combinação de sucção reavaliada com o G correto.
