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

## Análise (com dados normativos)
O **0,90** é, de fato, um valor do **EN 1990** — mas da **Tab. A1.2(A) (EQU**, perda
de equilíbrio estático / uplift), não da NBR. Na **Tab. A1.2(B) (STR/GEO)** o
permanente favorável é **1,00**. A combinação de sucção do código serve à verificação
de **uplift/ancoragem** (issue [33](33-succao-uplift-ancoragem-tirante.md)) — que é uma
situação de **EQU** — logo o γ_G,estab = 0,90 (Tab. A1.2(A)) está **correto** para essa
finalidade. Para **resistência do membro (STR)** o favorável seria 1,00 (Tab. A1.2(B)),
mas a sucção não governa a resistência (a gravidade/vento-pressão governam).

## O que precisa ser feito
- [x] Fundamentar cada valor na tabela correta do EN 1990 (não NBR):
      STR favorável = **1,00** (Tab. A1.2(B)); EQU estabilizante = **0,90**,
      desestabilizante = **1,10** (Tab. A1.2(A)).
- [x] Corrigir/distinguir no código: `GAMMA_G_inf = 1,00` (STR); novos
      `GAMMA_G_EQU_estab = 0,90` e `GAMMA_G_EQU_desestab = 1,10` (EQU).
- [x] Combinação de sucção (uplift) passa a usar explicitamente o γ_G,estab de EQU
      (0,90, Tab. A1.2(A)); `succao_uplift.py` idem.
- [x] Documentar no memorial (§11.2, nota de rodapé) e reavaliar a sucção.

## Resolução (implementado)
- **`loads.py`**: `GAMMA_G_inf = 1.00` (STR favorável, Tab. A1.2(B)); adicionados
  `GAMMA_G_EQU_estab = 0.90` e `GAMMA_G_EQU_desestab = 1.10` (Tab. A1.2(A) EQU). A
  combinação de sucção `ELU_S`/`ELU_C3` usa `GAMMA_G_EQU_estab` (uplift = EQU), com
  descrição "0,9G+1,5W (EQU Tab.A1.2(A))".
- **`succao_uplift.py`**: usa `GAMMA_G_EQU_estab`; docstring referencia Tab. A1.2(A) EQU.
- **`report.py`**: §11.2 com nota de rodapé fundamentando o 0,90 no EN 1990 (não NBR).
- **Testes**: `test_combinacoes_catH.py` (coeficientes + sucção usa 0,90 EQU).

## Efeito numérico
**Nenhuma mudança nos esforços de projeto** — o 0,90 (correto para uplift/EQU) foi
preservado; o uplift/ancoragem (issue 33) permanece η=0,859. A correção é de
**fundamentação normativa** (grounding no EN 1990) e de **distinção EQU/STR**, não de
valor. `GAMMA_G_inf = 1,00` (STR) fica explícito para qualquer situação futura de G
favorável em STR.

## Critério de aceite
Coeficiente de G favorável coerente com a EN 1990 (não NBR), com a tabela/situação de
projeto (EQU vs STR) declarada no memorial **✓**.
