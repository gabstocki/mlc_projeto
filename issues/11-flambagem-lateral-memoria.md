# 11 — Memória de cálculo da flambagem lateral (lef, σm,crit, λrel,m, kcrit)

- **Tema:** Viga — flambagem lateral (LTB)
- **Prioridade:** P2
- **Normas:** EC5 §6.3.3
- **Arquivos:** `mlc_projeto/checks/elu/flambagem_lateral.py`

## Apontamento do orientador
> [Bloco de reprodutibilidade] Memória de cálculo da flambagem lateral: lef,
> σm,crit, λrel,m e kcrit.

## Estado atual no código
- [flambagem_lateral.py](../mlc_projeto/checks/elu/flambagem_lateral.py) implementa
  `calcular_l_ef`, `calcular_sigma_m_crit`, `calcular_lambda_rel_m`,
  `calcular_k_crit` (usados em [main.py:407-409](../mlc_projeto/main.py) e
  [apoio.py:141-144](../mlc_projeto/checks/elu/apoio.py)).
- O cálculo **existe**, mas o **memorial não publica** os valores intermediários nem a
  hipótese de restrição lateral (`l_1` vindo do contraventamento/terças).

## O que precisa ser feito
- [ ] Publicar no memorial: `l_ef` (e a hipótese de restrição adotada), `σ_m,crit`,
      `λ_rel,m` e `k_crit`, com a seção de referência (h_ap) e E0,05.
- [ ] Explicitar a dependência de `l_1` = espaçamento efetivo das terças e sua
      validação pelo contraventamento (ver issues [15](15-contraventamento-telhado-n18.md)
      e [16](16-terca-flexo-compressao.md)).

## Critério de aceite
Memória completa de LTB no memorial (lef, σm,crit, λrel,m, kcrit) com hipóteses.
