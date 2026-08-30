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

## O que precisa ser feito
- [ ] Incluir a ação variável **vento** na composição da flecha final conforme
      EC5 §2.3.2.2 / EN 1990 §6.5.3, com o ψ apropriado
      (ψ₀ para acompanhante na característica; ψ₂ na quase-permanente).
- [ ] **Explicitar no memorial** todos os ψ₀/ψ₂ adotados por ação (G, Q, W) e a
      categoria (H) que os justifica — ver issue [05](05-psi1-combinacao-frequente.md).
- [ ] Se o vento dominante gerar sucção (flecha para cima), tratar o sinal/caso
      corretamente e verificar contra o limite adequado.

## Critério de aceite
Expressão de w_fin com todas as ações e ψ explícitos; memorial lista ψ por ação.
