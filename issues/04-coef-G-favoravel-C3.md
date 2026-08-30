# 04 — Coeficiente G favorável: 0,9G (NBR) → EN 1990 Tab. A1.2(B)

- **Tema:** Ações e combinações
- **Prioridade:** P1
- **Normas:** EN 1990 Tab. A1.2(B)
- **Arquivos:** `mlc_projeto/core/loads.py:53`, `:479-487`, `:547-556`

## Apontamento do orientador
> ELU_C3 com 0,9G: verificar o valor correto na EN 1990 Tab. A1.2(B), não usar da NBR.

## Estado atual no código
- `GAMMA_G_inf = 0.90` em [loads.py:53](../mlc_projeto/core/loads.py).
- Usado na combinação de sucção `0,9G + 1,5W` (ELU_S_*), [loads.py:479-487](../mlc_projeto/core/loads.py),
  e replicado no alias `ELU_C3`, [loads.py:547-556](../mlc_projeto/core/loads.py).

## Análise
O fator **0,90** para ação permanente favorável é da **NBR 8681**. Na **EN 1990**,
a abordagem depende do conjunto de equações adotado:
- Eq. 6.10 (Tab. A1.2(B)): γ_G,inf = **1,00** para permanente favorável.
- Eq. 6.10a/6.10b: com fator de redução ξ aplicado a G desfavorável (ξ·γ_G,sup),
  não a G favorável.

O `0,9` mistura critérios da NBR na estrutura EN 1990 adotada no restante do projeto.

## O que precisa ser feito
- [ ] Definir e documentar o conjunto de equações EN 1990 adotado (6.10 ou 6.10a/b).
- [ ] Corrigir o coeficiente de G favorável para o valor da EN 1990 Tab. A1.2(B).
- [ ] Reavaliar a combinação de sucção — ver interação com issue [01](01-gk-peso-proprio-superestimado.md)
      (gk superestimado agrava o mascaramento do uplift).

## Critério de aceite
Coeficiente de G favorável coerente com a EN 1990 (não NBR), com a equação adotada
declarada no memorial.
