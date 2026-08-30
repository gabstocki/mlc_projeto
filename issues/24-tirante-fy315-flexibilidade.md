# 24 — Tirante: fy 315 MPa e hipótese de apoio horizontal indeslocável

- **Tema:** Tirante de base
- **Prioridade:** P2
- **Normas:** EN 1993-1-1 §6.2.3 (tração); modelagem do apoio
- **Arquivos:** `mlc_projeto/checks/elu/tirante_base.py:31-52`, `:117-122`; `mlc_projeto/main.py:152`; `mlc_projeto/core/loads.py:191-196`

## Apontamento do orientador
> O mais adequado para o tamanho do tirante é um fy de 315 MPa.
> Registrar no modelo de cálculo que o empuxo foi obtido sob hipótese de apoio
> horizontal indeslocável, sem consideração da flexibilidade axial do tirante.

## Estado atual no código
- Aços disponíveis: apenas `S235` e `S355`
  ([tirante_base.py:35-38](../mlc_projeto/checks/elu/tirante_base.py)); o projeto usa
  `ACO_TIRANTE = "S355"` ([main.py:152](../mlc_projeto/main.py)).
- O empuxo `H` é obtido por Castigliano **assumindo apoio horizontal rígido**
  (`∫ M0·y_c/I / ∫ y_c²/I`, [loads.py:191-196](../mlc_projeto/core/loads.py)); a
  flexibilidade axial do tirante **não** entra na análise.
- O alongamento elástico do tirante `δ = T·L/(E·A)` é calculado **a posteriori**
  ([tirante_base.py:117-122](../mlc_projeto/checks/elu/tirante_base.py)), mas não
  realimenta H.

## O que precisa ser feito
- [ ] Adicionar um grau de aço com **fy = 315 MPa** (barra redonda adequada ao tirante)
      e adotá-lo, ou justificar o aço escolhido.
- [ ] **Registrar no memorial** a hipótese de apoio horizontal indeslocável na obtenção
      de H (Castigliano), explicitando que a flexibilidade axial do tirante não foi
      considerada.
- [ ] (Opcional/avaliar) Estimar o impacto da flexibilidade do tirante (δ/L já
      calculado) sobre H e sobre a flecha; decidir se precisa acoplar.

## Critério de aceite
Aço fy=315 MPa disponível/adotado; hipótese de rigidez do apoio documentada no
memorial; impacto da flexibilidade avaliado.
