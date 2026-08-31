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
- [x] Levantar a composição real de G (peso próprio MLC + terças + telha + instalações).
- [x] Ajustar `G_AREA` para o valor correto — agora **calculado**, não mais o lump 1,50.
- [x] Reexecutar o pipeline e reavaliar a combinação de sucção (ver issue
      [4](04-coef-G-favoravel-C3.md) e o desdobramento [33](33-succao-uplift-ancoragem-tirante.md)).

## Composição real de g_k (calculada com dados — EN 1991-1-1 §4 + EN 14080)
γ_glulam = ρ_mean·g = 420·9,81/1000 = **4,12 kN/m³** (GL24h, EN 14080).

| Parcela | kN/m² | Origem |
|---|---|---|
| Viga MLC (duplo-bisel) | **0,434** | ∫A(x)dx·γ / L_viga / L_t (integração exata) — bate com os "≈0,43" do orientador |
| Terças (0,20×0,58 @ 2,53 m) | 0,189 | γ·b_t·h_t / s |
| Telha (metálica) | 0,10 | declarado (ficha técnica) |
| Instalações | 0,10 | estimativa de projeto |
| **Total viga g_k** | **0,823** | vs 1,50 anterior (~2×) |
| Total terça g_k | 0,389 | terças + cobertura (a terça NÃO carrega a viga) |

## Resolução (implementado)
- **Nova função** `peso_proprio_gk` em [loads.py](../mlc_projeto/core/loads.py):
  g_k discriminado por parcela (viga por integração de A(x)·ρ_mean; terças; cobertura
  declarada). Devolve `g_k_viga` (viga) e `g_k_terca` (terça — sem o peso da viga).
- **`main.py`**: `G_AREA=1,50` removido; g_k calculado e impresso discriminado.
  Corrigido também o g passado às **terças** (era 1,50 = incluía indevidamente o peso
  da viga MLC; agora 0,389 = cobertura + peso próprio da terça).
- **`report.py`**: §4 com a tabela de parcelas de g_k (fonte EN 1991-1-1 §4).
- **Testes**: [test_peso_proprio.py](../tests/test_peso_proprio.py).

## Combinação de sucção reavaliada (efeito principal)
Com g_k correto, a sucção deixa de ser mascarada e revela **uplift real**:
`ELU_C3` passa de q≈+0,39 (mascarado) para **q=−3,12 kN/m** → **R_v=−31,6 kN**
(arrancamento) e **H=−245,5 kN** (empuxo invertido). As verificações de uplift daí
decorrentes (ancoragem ao arrancamento; tirante frouxo → fundação) foram abertas na
issue [33](33-succao-uplift-ancoragem-tirante.md). Efeito colateral positivo: todas as
verificações de gravidade caíram (ex.: cisalhamento 0,748→0,558; tirante ∅90→∅80;
L1 8×8→6×8).

## Critério de aceite
gk discriminado por parcela no memorial **✓** e coerente com o telhado (0,82 vs 1,50)
**✓**; combinação de sucção reavaliada com o G correto (uplift revelado e quantificado;
verificações de uplift → issue 33) **✓**.
