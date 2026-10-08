# 46 — Imperfeições geométricas: usar EN 1995-1-1 §5.4.4 (não EN 1993-1-1 §5.3.2)

- **Tema:** Estabilidade global / Análise
- **Prioridade:** P1
- **Normas:** EN 1995-1-1 §5.4.4 (φ = 0,005 p/ h ≤ 5 m; φ = 0,005·√(5/h) p/ h > 5 m; e = 0,0025·ℓ); EN 1993-1-1 §5.2.1 (α_cr) e §5.3.2
- **Arquivos:** `mlc_projeto/checks/elu/contraventamento_vertical.py:90` (“EN 1993-1-1 §5.3.2 — imperfeição global”); `mlc_projeto/checks/elu/contraventamento_transversal.py:17,46`; `mlc_projeto/checks/elu/estabilidade_global.py:23,59`; `tese/cap06.tex:255-…` (§6.5, l. 269)
- **Relaciona:** issues 14, 31; memória [[aud006-dois-graus-de-liberdade]]

## Origem (3ª revisão do orientador (2026-10))
Verificar se a EN 1993-1-1 §5.3.2 é a norma adequada. A EN 1995-1-1 §5.4.4 tem prescrição
própria para madeira: inclinação inicial φ = 0,005 (h ≤ 5 m) ou 0,005·√(5/h) (h > 5 m) e
curvatura inicial e = 0,0025·ℓ. Se mantiver o critério α_cr da EN 1993-1-1 §5.2.1,
**declarar que é usado por analogia** (o EC5 não tem esse critério).

## O que fazer
- [ ] Substituir a força nocional por φ do EC5 §5.4.4 (h ≈ 7 m → φ = 0,005·√(5/7) ≈ 0,0042);
      comparar com o valor atual e reprocessar contraventamentos.
- [ ] Avaliar se a curvatura inicial e = 0,0025ℓ precisa entrar em algum elemento (pilares/diagonais).
- [ ] Declarar no código e na tese que o critério α_cr ≥ 10 da EN 1993-1-1 §5.2.1 é **analogia**.

## Resolução ✅ (2026-10-06)

**Código**
- `checks/elu/estabilidade_global.py`: novas `inclinacao_inicial_ec5(h)` (EC5 §5.4.4(2) Eq. 5.1:
  φ = 0,005 p/ h ≤ 5 m; 0,005·√(5/h) p/ h > 5 m) e `curvatura_inicial_ec5(ℓ)` (Eq. 5.2:
  e = 0,0025·ℓ). `forca_nocional` passa a usar φ do EC5, **sem redução por nº de colunas**
  (o φ da EN 1993-1-1 §5.3.2 fica só como `phi_en1993_comparacao`). Docstring/norma declaram o
  α_cr ≥ 10 da EN 1993-1-1 §5.2.1 como **analogia**.
- `contraventamento_vertical.forca_nocional` delega na mesma fonte (antes eram duas fórmulas
  duplicadas); `contraventamento_transversal` herda. Cláusulas trocadas em docstrings/prints.
- `core/normativo.py`: `phi_0` → EC5 §5.4.4 com origem "EN" (não é NDP — NDP 21 → 20);
  novo `e_bow_rel`; `alpha_cr_min` anotado “por analogia”.
- `output/report.py`: fórmula φ, rótulos do catálogo, nota de estabilidade global.
- Curvatura inicial e = 0,0025ℓ: **não somada** — já incorporada em k_c (EC5 §6.3.2, β_c).
- Testes: +4 em `tests/test_estabilidade_global.py`. Suíte 669 passed; pipeline APROVADO.

**Resultados:** h = 7,0 m → φ = 0,00423 (EN 1993 dava 0,00282 com α_m de 9 colunas; 0,00327
com 2). H_imp 10,1 → 15,2 kN. Contravento vertical η 0,7883 → **0,7930 — passa a governar o
projeto** (cobertura 0,7902 vira a 2ª); transversal 0,7024 → 0,7358; canto 0,4283 → 0,4333;
central montante 0,7444 → 0,7460; e_0 pilar 22,91 → 29,58 mm (η 0,06).

**Tese:** §4.4.1 (tabela NDP: φ0 removido, α_cr “por analogia”, 19 → 18), §6.5 (reescrito, Eq.
de φ do EC5, curvatura em k_c, α_cr por analogia), §5.5.2 (nota sobre a varredura histórica),
§7 (tabelas e textos de pilares/contraventamento, síntese 0,7930), §8 (ancoragem, arrancamento,
fundação, corda 15,8 kN), §9 e resumo/abstract (0,7930; 49 verificações; 669 testes).
