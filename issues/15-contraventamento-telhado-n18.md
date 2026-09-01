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
- [x] Referenciar `k_s`, `k_f,2`, `k_f,3` explicitamente à tabela do EC5 §9.2.5
      (valores recomendados / Anexo Nacional) no memorial.
- [x] Modelar **dois planos independentes** de estabilização (um por vão, n≈9 cada)
      ou justificar tecnicamente o sistema único.
- [x] Verificar se a força de estabilização **não está duplicada** entre os planos.
- [x] Reconferir `ℓ` (vão do sistema estabilizador) e `k_ℓ = min(1, √(15/ℓ))` para o
      layout correto.

## Critério de aceite
Fatores referenciados à norma; contraventamento do telhado modelado como dois planos
(ou justificativa), sem duplicação da força de estabilização.

## Resolução (2026-08-31)
Fórmulas e fatores conferidos no **texto integral da EN 1995-1-1:2004+A1:2008**
(§9.2.5.2/§9.2.5.3, Eq. 9.34–9.38, **Tabela 9.2** — página renderizada do PDF para
ler os valores **sublinhados**/recomendados).

**Achado normativo (correção real):** a Tabela 9.2 recomenda (sublinhado)
`k_f,3 = 30` (intervalo 30–80); o código usava **50**. Como `q_d = k_ℓ·n·N_d/(k_f,3·ℓ)`,
o valor 50 **subestimava a carga de estabilização em 40%** (fator 30/50). Corrigido
para `K_F3 = 30`. Os demais batem com os recomendados: `k_s=4`, `k_f,1=50`, `k_f,2=80`.
Todos citados no código e no memorial (§9.1) com intervalo e origem.

**Dois planos independentes (não n=18 único):** `verificar_contraventamento` agora
modela `n_planos = n_porticos` planos independentes, cada um estabilizando
`n_por_plano = 9` vigas, com contraventamento próprio. `q_d`, `R_ext` são reportados
**por plano**; os painéis (2 por plano) recebem a reação do próprio plano.
**Sem duplicação:** demonstrei que a força por diagonal é idêntica em "1 sistema de
18 / 4 painéis" e "2 planos de 9 / 2 painéis" (a divisão por planos é neutra) — a
força de um plano não transita pelo outro. A mudança de resultado vem **só** do k_f,3.

**ℓ e k_ℓ:** ℓ = vão do sistema entre baías rígidas = L_comp = 46 m (baías só nos
extremos, `n_modulos_cv=2`); `k_ℓ = min(1, √(15/46)) = 0,571`. Confirmei a nota do
código: **adicionar baías reduz ℓ mas eleva k_ℓ e a reação** — logo mantêm-se os
extremos (mais econômico) e sobe-se a barra.

**Consequência de projeto (decidida com a engenheira):** com o k_f,3=30 correto, a
diagonal **Ø18 mm reprovava (η=1,19)** e derrubava `cobertura_ok` (penalizando a LTB
da viga). Aumentou-se a diagonal para **Ø22 mm** (`D_BARRA_CV_MM=22`): η_diag ≈ **0,80**,
`cobertura_ok=True`, LTB volta a usar `l_1 = s` (terças válidas). (Ø20 mm passaria no
limite, η≈0,96; Ø25 mm daria η≈0,62.)

**Testes:** [test_contraventamento_cobertura.py](../tests/test_contraventamento_cobertura.py)
— fatores da Tab. 9.2 (k_f,3=30); dois planos (n=9×2); fórmulas 9.37/9.38; ausência de
duplicação; Ø22 passa e Ø18 reprovaria. Memorial (§9.1/§9.2) atualizado e compila
(pdflatex). Suíte: 139 passam.
