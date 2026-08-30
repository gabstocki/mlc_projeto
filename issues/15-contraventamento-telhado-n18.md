# 15 — Contraventamento do telhado: n=18 vs dois planos de 9; kf/ks e duplicação

- **Tema:** Contraventamento (cobertura)
- **Prioridade:** P1
- **Normas:** EC5 §9.2.5 (§9.2.5.2 e §9.2.5.3)
- **Arquivos:** `mlc_projeto/checks/elu/contraventamento.py:50-57`, `:87-94`, `:214-226`; `mlc_projeto/main.py:129-139`, `:293-305`

## Apontamento do orientador
> Fiquei com dúvida no contraventamento do telhado. Os fatores kf,2 = 80, kf,3 = 50 e
> ks = 4 devem ser referenciados à tabela do EC5 §9.2.5. Além disso, o cálculo
> considera n = 18 vigas em sistema único de 46 m, quando existem dois planos de
> cobertura independentes, um por vão, cada qual estabilizando nove vigas. É
> necessário verificar se a força de estabilização não está duplicada, ou se não
> deveriam ser dimensionados dois sistemas distintos.

## Estado atual no código
- Fatores em [contraventamento.py:50-57](../mlc_projeto/checks/elu/contraventamento.py):
  `K_S=4.0`, `K_F2=80.0`, `K_F3=50.0` (com nota dos intervalos NDP, mas sem citação
  explícita da tabela/linha no memorial).
- `n_vigas = n_vigas_por_linha × n_porticos`
  ([contraventamento.py:87-94](../mlc_projeto/checks/elu/contraventamento.py)); o main
  passa `n_porticos=2` e `L_comp=46 m` ([main.py:388-395](../mlc_projeto/main.py)) —
  tratando **um sistema único** ao longo dos 46 m.
- Há dois vãos (dois planos de cobertura), cada um com ~9 vigas.

## O que precisa ser feito
- [ ] Referenciar `k_s`, `k_f,2`, `k_f,3` explicitamente à tabela do EC5 §9.2.5
      (valores recomendados / Anexo Nacional) no memorial.
- [ ] Modelar **dois planos independentes** de estabilização (um por vão, n≈9 cada)
      ou justificar tecnicamente o sistema único.
- [ ] Verificar se a força de estabilização **não está duplicada** entre os planos.
- [ ] Reconferir `ℓ` (vão do sistema estabilizador) e `k_ℓ = min(1, √(15/ℓ))` para o
      layout correto — ver a nota em
      [contraventamento.py:99-116](../mlc_projeto/checks/elu/contraventamento.py).

## Critério de aceite
Fatores referenciados à norma; contraventamento do telhado modelado como dois planos
(ou justificativa), sem duplicação da força de estabilização.
