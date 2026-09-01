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
- [x] Publicar no memorial: `l_ef` (e a hipótese de restrição adotada), `σ_m,crit`,
      `λ_rel,m` e `k_crit`, com a seção de referência (h_ap) e E0,05.
- [x] Explicitar a dependência de `l_1` = espaçamento efetivo das terças e sua
      validação pelo contraventamento (ver issues [15](15-contraventamento-telhado-n18.md)
      e [16](16-terca-flexo-compressao.md)).

## Critério de aceite
Memória completa de LTB no memorial (lef, σm,crit, λrel,m, kcrit) com hipóteses.

## Resolução (2026-08-31)
Emenda de reprodutibilidade — o cálculo já existia; o que faltava era **publicar**
a memória. Nada da física do LTB mudou.

**[flambagem_lateral.py](../mlc_projeto/checks/elu/flambagem_lateral.py):**
`verifica_flambagem_lateral` agora também retorna os dados de reprodutibilidade:
`fator_l_ef` (0,9), `restricao`, `tipo_carga`, `l_ef_formula`, `l_1_origem`
(dependência do contraventamento §9.2.5 / terças), `E0_05_MPa`,
`sigma_m_crit_formula`, `lambda_rel_formula` — além dos valores que já existiam
(`l_1_m`, `l_ef_m`, `sigma_m_crit_MPa`, `lambda_rel_m`, `k_crit`, `regime`).

**[report.py](../mlc_projeto/output/report.py):** nova subseção "Detalhes --
Flambagem lateral / LTB (§6.3.3)" no memorial, com:
- hipótese de restrição e `l_ef = 0,9·l_1` (EC5 Tab. 6.1), com a origem de `l_1`
  (espaçamento efetivo das terças validado pelo contraventamento §9.2.5 — issues
  15/16);
- seção de referência (h no ponto de M_max, b) e `E0,05`;
- `σ_m,crit = 0,78·b²·E0,05/(h·l_ef)` (Eq. 6.32), `λ_rel,m = √(f_m,k/σ_m,crit)`;
- `k_crit` com os três regimes (Eq. 6.34) e a verificação `σ_m,d ≤ k_crit·f_m,d`.

**Valores (GL24h, l_1 = 2,53 m):** l_ef = 2,28 m; E0,05 = 9600 MPa (valor corrigido
na issue 8); σ_m,crit ≈ 121 MPa; λ_rel,m ≈ 0,45 (≤ 0,75 ⇒ **k_crit = 1,0**, sem
redução — seção alta e curto l_1 validado pelas terças); η ≈ 0,07.

**Testes:** [test_flambagem_memoria.py](../tests/test_flambagem_memoria.py)
(exposição dos campos; l_ef = 0,9·l_1; σ_m,crit e λ_rel,m consistentes com as
fórmulas; três regimes de k_crit). LaTeX compila (pdflatex). Suíte: 128 passam.
