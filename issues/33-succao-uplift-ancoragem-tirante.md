# 33 — Verificações de sucção/uplift: ancoragem ao arrancamento e tirante frouxo

- **Tema:** Ações e combinações / Ligações e fundação
- **Prioridade:** P1
- **Normas:** EN 1990 (comb. de sucção); EC5 §8 / EN 1993-1-8 / EN 1992-4 (ancoragem); EN 1993-1-1 (tirante)
- **Arquivos:** `mlc_projeto/connections/connections.py` (L3 sapata); `mlc_projeto/checks/elu/tirante_base.py`; `mlc_projeto/core/loads.py`

## Origem
Desdobramento da issue [1](01-gk-peso-proprio-superestimado.md). Ao corrigir o peso
próprio (`g_k` de 1,50 → ≈ 0,82 kN/m²), a combinação de **sucção** deixou de ficar
mascarada e passou a apresentar **uplift líquido real** — exatamente o que o
orientador alertou ("superestimar o peso próprio pode prejudicar a análise quando o
esforço é inverso — ver combinação ELU-C3").

## Dados (com g_k correto)
Combinação governante de sucção **ELU_C3 / ELU_S_C2_unif_st** (`0,9G + 1,5W_suc`):
- `q = −3,12 kN/m` (uplift), antes ≈ +0,39 (mascarado).
- **R_v = −31,6 kN por apoio** → reação líquida **para cima** (arrancamento).
- **H = −245,5 kN** → empuxo **invertido** (para dentro).

## Problema (verificações ausentes)
1. **Ancoragem ao arrancamento** nos apoios: sob sucção há tração líquida (~31,6 kN)
   na base do pilar. O dimensionamento de L3 (sapata) só considera compressão + H;
   falta verificar os chumbadores/ancoragem à **tração** (EN 1993-1-8 / EN 1992-4).
2. **Tirante frouxo sob sucção**: o tirante é dimensionado à tração (empuxo de
   gravidade). Sob sucção o empuxo inverte (H ≈ −245,5 kN) → a barra iria à
   **compressão** e **flamba/afrouxa** (não resiste). O empuxo invertido deve então
   ir à **fundação** (H_sapata ≠ 0 nesse caso) — caminho de carga a verificar.
3. **Pilar sob uplift**: sob sucção o pilar fica **tracionado** (não é caso de
   flambagem); a verificação relevante passa a ser a ligação/ancoragem, não o k_c.

> Nota: as magnitudes são modestas (a sapata tem 4×80 kN de chumbadores e a base
> transfere cortante), portanto **não** há falha oculta — mas as verificações
> precisam ser formalizadas para a situação de sucção.

## O que precisa ser feito
- [x] Verificar a ancoragem ao arrancamento (tração) nas bases sob a combinação de
      sucção (R_v,uplift), descontando o peso próprio favorável (γ_G,inf·W_pilar).
- [x] Tratar o tirante frouxo: sob sucção o empuxo inverte → tirante frouxo → o
      empuxo invertido |H| vai à fundação (cortante na base de extremidade), e a
      base é verificada para a interação N (uplift) + V (empuxo invertido).
- [x] Registrar a combinação de sucção e seus efeitos no memorial (§11.2 do relatório).
- [x] Coerência com issues [4](04-coef-G-favoravel-C3.md) (γ_G,inf) e
      [24](24-tirante-fy315-flexibilidade.md) (tirante).

## Resolução (implementado)
- **Novo módulo** [succao_uplift.py](../mlc_projeto/checks/elu/succao_uplift.py):
  extrai a combinação de sucção (`combinacao_ELU_succao`, sinais reais), e verifica:
  - **Apoio de extremidade** (governa): N_uplift = |R_v| − γ_G,inf·W_pilar
    (tração na ancoragem) + V_base = |H| (empuxo invertido, tirante frouxo → sem
    atrito, base tracionada) → interação N–V linear (conservadora).
  - **Apoio central**: N_uplift = soma dos dois vãos, V≈0 (empuxos cancelam).
  - Densidade do pilar por EN 14080; γ_G,inf da combinação favorável (EN 1990).
- **`main.py`**: nova Fase 4c chama a verificação (usa n_chu de L3) e imprime o
  caminho de carga.
- **`report.py`**: §11.2 (memória da sucção) + linha no resumo §12.
- **Testes**: [test_succao_uplift.py](../tests/test_succao_uplift.py).

## Resultados (com g_k correto — issue 1)
Combinação `ELU_C3` (`0,9G + 1,5W_suc`): q=−3,12 kN/m, R_v=−31,6 kN (uplift),
H=−245,5 kN (invertido → tirante frouxo).
- **Extremidade**: N_uplift=29,3 kN (η_N=0,092) + V_base=245,5 kN (η_V=0,767) →
  **η=0,859** (ancoragem 4×80 kN).
- **Central**: N_uplift=60,9 kN → η=0,190.
- **Governa a extremidade (η=0,859 < 1,0 → adequado)**, confirmando que a ancoragem
  sob sucção **não é meramente construtiva** — precisava mesmo ser verificada.

## Limites (transparência)
- A interação N–V é **linear conservadora**; o dimensionamento definitivo dos
  chumbadores (aço + cone de concreto + arrancamento + interação) segue
  **EN 1992-4 / EN 1993-1-8** (fica para o projeto de fundação/ligação metálica —
  ver issues [21](21-chapas-aco-en1993.md) e [22](22-criterio-eta-alvo.md)).
- O **peso da fundação** (bloco/sapata), favorável ao uplift global (EN 1997), não
  está modelado — a considerar no projeto de fundação.
- `F_chu` é uma resistência *lumped* por chumbador (usada para tração e cortante);
  a distinção rigorosa é da EN 1992-4.

## Critério de aceite
Combinação de sucção verificada quanto ao arrancamento (ancoragem) e ao empuxo
invertido (tirante frouxo → fundação) **✓**, com o caminho de carga completo e
registro no memorial (§11.2) **✓**.
