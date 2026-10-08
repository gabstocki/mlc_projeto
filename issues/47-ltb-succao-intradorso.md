# 47 — Flambagem lateral sob sucção: intradorso comprimido sem contenção das terças

- **Tema:** Viga — estabilidade lateral
- **Prioridade:** P1 (verificação ausente)
- **Normas:** EN 1995-1-1 §6.3.3 (Eq. 6.33–6.35, Tab. 6.1), §9.2.5
- **Arquivos:** `mlc_projeto/checks/elu/flambagem_lateral.py`; `mlc_projeto/checks/elu/flexao.py`; combinações `ELU_S_*` em `core/loads.py`; `tese/cap07.tex:32-73` (§7.2)
- **Relaciona:** issues 11, 33, 41

## Origem (3ª revisão do orientador (2026-10))
Na combinação de sucção o momento inverte: o **intradorso** fica comprimido e **não é contido
pelas terças** (que travam o extradorso). Apresentar a verificação com o **comprimento efetivo
correspondente**.

## O que fazer
- [ ] Definir l_ef para banzo inferior comprimido: entre pontos de contenção do intradorso
      (mãos-francesas/escoras, se houver) ou vão inteiro; considerar carga aplicada no banzo
      tracionado (Tab. 6.1 nota) e seção variável.
- [ ] Implementar a verificação para a combinação de sucção governante (M_neg, k_mod da ação de curta duração).
- [ ] Se não passar: prever contenção do intradorso (escoras terça–intradorso) e verificá-las.
- [ ] Incluir no §7.2 da tese e no relatório; testes.

## Resolução ✅ (2026-10-06)

**Achado:** a verificação de LTB já varria as combinações de sucção, mas com l_1 = s (terças)
e carga na borda comprimida — hipóteses que só valem com o extradorso comprimido. Sob sucção
M chega a −394,4 kN·m (0,9G+1,5W, c_pi=+0,8; 15 de 17 combinações têm trecho negativo).

**Código** — `checks/elu/flambagem_lateral.py`
- `momento_biapoiada(x, L, q_esq, q_dir)`: M(x) da viga biapoiada (confere com a análise).
- `verifica_flambagem_lateral_succao()`: só trechos com M < 0; l_1 = L (contenção só nos
  apoios, garfo em L1/L1c); l_ef = 0,9·L = 18,23 m (Tab. 6.1); **conservador**: não credita a
  contenção da borda tracionada pelas terças nem a redução −0,5h; **varredura em x** (altura
  variável).
- `verifica_flambagem_lateral` (principal) passa a considerar só M > 0.
- `main.py` (Fase 2), catálogo do relatório; memória no relatório LaTeX. Corrigida a exibição
  do l_ef da LTB principal (mostrava 0,9·l_1 mas o código soma +2h → 7,85 m).
- Testes: `tests/test_flambagem_succao.py` (5). Suíte 674 passed; pipeline APROVADO
  (50 verificações).

**Resultado:** governa ELU_S_T10_t1_dir_cpi+0.8 em x = 15,80 m (h = 1,786 m, M = −290,4 kN·m,
**não** a seção de |M| máximo): σ_m,crit = 23,56 MPa, λ_rel = 1,01, k_crit = 0,80,
σ_m,d = 1,71 ≤ 10,79 MPa → **η = 0,158**. Escoras terça–intradorso **não são necessárias**.

**Tese:** §7.2 (tabela da viga + parágrafo com equações simbólicas; correção do l_ef = 7,85 m),
contagens (50 verificações, 674 testes).
