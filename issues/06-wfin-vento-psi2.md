# 06 — wfin omite a parcela de vento (ψ₀=0,6) e ψ₂ não explícito

- **Tema:** ELS / flechas
- **Prioridade:** P1
- **Normas:** EC5 §2.3.2.2; EN 1990 §6.5.3 (Tab. A1.1)
- **Arquivos:** `mlc_projeto/checks/els/deflection_els.py:93`, `:124`; `mlc_projeto/checks/els/creep.py:114`

## Apontamento do orientador
> A expressão de wfin omite a parcela de vento (ψ₀ = 0,6) e não explicita os ψ₂ adotados.

## Estado atual no código
- Flecha final: `w_fin = w_G·(1+k_def) + w_Q1·(1+ψ₂·k_def)` com `psi_2 = 0.0`
  fixo em [deflection_els.py:93](../mlc_projeto/checks/els/deflection_els.py) e
  [:124](../mlc_projeto/checks/els/deflection_els.py); idem [creep.py:114](../mlc_projeto/checks/els/creep.py).
- A combinação característica `ELS_S1` **inclui** vento (`G+Q+0,6W`,
  [loads.py:579-585](../mlc_projeto/core/loads.py)), mas a **flecha final** (`w_fin`)
  só soma G e Q — o vento some no cálculo de fluência.

## Reenquadramento (após issue 3)
A issue 3 corrigiu a concomitância: para **categoria H**, Q e vento **não** atuam
juntos (EN 1991-1-1 §3.3.2(1)). Logo o wfin **não** tem 0,6W *acompanhante* de Q — o
vento entra como **ação dominante** (combinação alternativa G+W). O achado substantivo:
no característico, a **pressão de vento (NBR 6123) supera a sobrecarga Q**, então
**G+W governa a flecha descendente** — o módulo antigo só considerava G+Q.

## O que precisa ser feito
- [x] Incluir o **vento (NBR 6123)** como ação dominante do ELS característico e da
      flecha final (EC5 §2.3.2.2 / EN 1990 §6.5.3), por superposição elástica das
      parcelas (G, Q, cada padrão Cpe).
- [x] Explicitar ψ₀/ψ₂ (categoria H: ψ₂,Q = ψ₂,W = 0) no resultado e no memorial (§10).
- [x] Tratar o sinal: flecha **descendente** governante = max(G+Q, G+W_pressão); a
      **sucção** (G+W_sucção, ↑/uplift) é reportada como **informativa** (o EC5 Tab.7.2
      limita a flecha descendente).

## Resolução (implementado)
- **`deflection_els.py`**: `verificar_ELS` reescrito — flechas assinadas por parcela
  (superposição), vento por padrão (NBR 6123); característico governante = max(G+Q,
  G+W); w_fin = w_G·(1+k_def) + w_var (variável dominante, ψ₂=0). Novos campos:
  `w_W_press_mm`, `w_W_suc_mm`, `w_char_Q_mm`, `w_char_W_mm`, `w_char_up_mm`,
  `gov_caracteristico`, `w_var_fin_mm`, `psi_2_Q`, `psi_2_W`.
- **`report.py`**: §10 mostra o característico governante (G+Q vs G+W, NBR 6123), o
  uplift informativo e a fluência com a variável dominante e ψ₂=0.
- **Testes**: [test_els_deflection.py](../tests/test_els_deflection.py).

## Resultados (R2)
Vento **governa** o característico: G+Q=0,55 mm; **G+W=0,76 mm** (NBR 6123). Uplift
G+W_sucção=−0,01 mm (informativo). w_fin=0,37·(1+2,0)+0,39=**1,50 mm** (variável
dominante: vento). η_S1=0,011; η_net,fin=0,019 — folgado (viga muito rígida,
h_ap≈2,8 m), mas **agora correto** (vento incluído).

## Critério de aceite
Expressão de w_fin com todas as ações (incl. vento NBR 6123) e ψ₀/ψ₂ explícitos;
memorial (§10) lista os casos e a variável dominante **✓**.
