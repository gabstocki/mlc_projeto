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
- [x] Publicar a **tabela completa** das combinações, com: padrão, C_esq/C_dir
      (Cpb/Cps), q_esq/q_dir, M_max, H, duração e a marcação da(s) governante(s).
- [x] Reintroduzir **C_esq/C_dir (Cpb/Cps)** por padrão.
- [x] Gerar a tabela no `report.py` (todas as combinações, não só os aliases).

## Critério de aceite
Tabela das combinações com Cpb/Cps dos 8 padrões publicada no memorial;
governante(s) destacada(s).

---

## ✅ Resolução (implementada)

**Nota:** são **17** combinações, não 24 — a categoria H reduziu de 24→17 (Q e
vento não concomitantes, issue 3). A tabela publica as 17 e registra essa redução.

### 1) Método `tabela_combinacoes()` (loads.py)
Novo método em `Carregamentos`: monta as 17 linhas — para cada um dos **8 padrões
Cpe da Tab.25** (C1/C2 × asim/rev/unif.bv/unif.st), as combinações **ELU_W**
(1,35G+1,5W) e **ELU_S** (0,9G+1,5W); mais **ELU_Q** (1,35G+1,5Q, sem vento). Cada
linha: padrão, caso, **C_esq/C_dir** (Cpe em cada meia-água, = Cpb/Cps conforme o
padrão), q_esq/q_dir, M_max, H, duração e marcação **governante** (|M|, uplift, |H|).
Os C_esq/C_dir vêm de `padroes_vento` (que preserva os coef. de `padroes_cpe_tabela25`).

### 2) Governantes (mesmos critérios dos aliases ELU_C2/C3/C4)
- **|M|**: ELU_W_C1_unif_bv (M=−265,5 kN·m) — também **|H|** (H=1097,7 kN);
- **uplift**: ELU_S_C2_unif_st (H=−245,5 kN, sucção).

### 3) Anexo B no memorial (report.py)
"Anexo B — Combinações completas por padrão de vento": tabela das 17 combinações
agrupadas por caso (C1/C2), com C_esq/C_dir, q's, M_max e as governantes em negrito;
nota da redução 24→17 e das durações (vento=curta, Q=média).

### Verificação
- 17 combinações (8 W + 8 S + 1 Q); assimétricos têm C_esq≠C_dir, uniformes iguais.
- Pipeline gera o Anexo B no PDF sem erros.
- **Testes:** [`tests/test_tabela_combinacoes.py`](../tests/test_tabela_combinacoes.py)
  (6 casos: 17 combos, Cpe por padrão, governantes, |M| bate, assim.≠unif., durações).
