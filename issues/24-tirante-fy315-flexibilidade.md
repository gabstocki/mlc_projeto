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
- [x] Adicionar um grau de aço com **fy = 315 MPa** e adotá-lo.
- [x] **Registrar no memorial** a hipótese de apoio horizontal indeslocável na obtenção
      de H (Castigliano), sem a flexibilidade axial do tirante.
- [x] Estimar o impacto da flexibilidade do tirante sobre H; decidir se precisa acoplar.

## Critério de aceite
Aço fy=315 MPa disponível/adotado; hipótese de rigidez do apoio documentada no
memorial; impacto da flexibilidade avaliado.

---

## ✅ Resolução (implementada)

Arquivo: [`checks/elu/tirante_base.py`](../mlc_projeto/checks/elu/tirante_base.py).

### 1) Aço f_y = 315 MPa (adotado)
Grau **MR315** adicionado a `ACO` (f_y=315 MPa; f_u=490 de referência — barra
redonda de média resistência, confirmar produto/norma). `main.py`:
`ACO_TIRANTE = "MR315"`. Tirante **∅80 mm MR315, η=0,693** (era S355).

### 2) Hipótese de apoio rígido — REGISTRADA
Campo `hipotese_H` no resultado + nota no memorial (§11.2): *"H obtido por
Castigliano assumindo apoio horizontal INDESLOCÁVEL; a flexibilidade axial do
tirante (δ=T·L/EA) não foi realimentada na análise — conservador para o tirante."*

### 3) Impacto da flexibilidade — AVALIADO (`impacto_flexibilidade_tirante`)
Diagnóstico por rigidezes horizontais:
- **k_arco = 608 kN/mm** (arco raso, muito rígido; f_p = ∫y_c²/EI) vs
  **k_tirante = 52 kN/mm** (f_t = L/E_sA); δ_tirante = 21,1 mm.
- Modelo de 2 molas em série (tirante como ÚNICO apoio) daria H≈87 kN — mas
  **ignora a restrição PARALELA** de ancoragem (chumbadores) + contraventamento
  vertical/transversal das bases. Na estrutura real essas rigidezes somam-se em
  paralelo → H permanece próximo do rígido.
- **Conclusão:** H_rígido é o máximo → **conservador para o tirante** (T=H). Não é
  necessário acoplar para o dimensionamento do tirante; um pórtico acoplado só
  refinaria a flexão da viga. Validação: o modelo reproduz H_real=1097,6 kN.

### Integração
- `main.py` Fase 4a: adota MR315, chama a avaliação e imprime o diagnóstico;
  `res_tirante["impacto_flexibilidade"]`.
- `output/report.py` §11.2: nota da hipótese de apoio rígido + avaliação da
  flexibilidade (rigidezes, limite de 2 molas e a ressalva da restrição paralela).
- **Testes:** [`tests/test_tirante_flexibilidade.py`](../tests/test_tirante_flexibilidade.py)
  (7 casos: MR315 disponível/adotado, hipótese registrada, rigidezes e 2 molas,
  δ=TL/EA, conclusão conservadora, sensibilidade ao diâmetro).

---

## ⚠ Reconciliação (issue 38 — auditoria)

**Números desta issue estão DEFASADOS** (anteriores à correção do termo axial do
Castigliano, `loads.py` v4, que reduziu `H` ~3,5×):
- Aqui: `k_tir=52 kN/mm`, `δ=21,1 mm`, **∅80 mm**, `H_real=1097,6 kN`.
- Vigente: `H=377 kN` (gravidade) ⇒ **∅48 mm**, `k_tir=19 kN/mm`, `δ=20,1 mm`
  (o `k_tir=52` correspondia ao ∅80; o `δ=21,1` usava o `T` inflado ≈1097 kN).

**Conclusão "H fica próximo do rígido" foi SUPERADA pela [issue 35](35-empuxo-pilar-caminho-carga.md)/[38](38-caminho-horizontal-transversal-coerencia.md):**
o diagnóstico de 2 molas comparou `k_arco` com o `k_tirante` (base), mas o tirante
está na **base** — entre o **springing** (topo, onde o empuxo atua) e a base há a
**flexão do pilar** (em série, ~10³× mais mole), que governa. Como o pilar
biarticulado é um mecanismo lateral (`k_pilar≈0`), o empuxo **não se desenvolve**
(`H_dev≈0`, [`empuxo_acoplado.py`](../mlc_projeto/checks/elu/empuxo_acoplado.py)).
O tirante permanece **conservador** (T=H rígido é o máximo), mas a justificativa da
restrição paralela **não** se aplica ao springing.
