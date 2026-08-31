# 13 — Esforços nos pilares: dois valores de N; pilar central subdimensionado

- **Tema:** Sistema de eixos e esforços / Pilares
- **Prioridade:** P0
- **Normas:** EC5 §6.3.2
- **Arquivos:** `mlc_projeto/main.py:454`, `:469-476`; `mlc_projeto/checks/elu/pilares.py:232`, `:49-141`

## Apontamento do orientador
> Verificar os esforços nos pilares. Me parece que há ao menos dois valores distintos
> de esforço normal circulando no código, e nenhum deles reproduz a tabela. O pilar
> central parece estar subdimensionado — verifique novamente as contas.
> [Bloco de reprodutibilidade] Origem dos dois valores distintos de esforço normal
> nos pilares (87,3 e 209,59 kN).

## Estado atual no código
- Pilar **lateral**: `N_d = load.V_max_ELU()` (reação vertical de um vão),
  [pilares.py:232](../mlc_projeto/checks/elu/pilares.py) e
  [main.py:469-476](../mlc_projeto/main.py) (`_N_lat = load.V_max_ELU()`).
- Pilar **central**: `_N_central = 2 * load.V_max_ELU()`,
  [main.py:454-460](../mlc_projeto/main.py) — soma dos dois vãos.
- `V_max_ELU()` devolve `R_v_gov` (reação vertical) da combinação governante; há ainda
  `N_viga_kN` (esforço no eixo) — daí **dois "N" diferentes** circulando
  (reação vertical vs normal no eixo).
- O valor 209,59 kN corresponde à reação vertical; 87,3 kN provavelmente a outra
  combinação/definição — **conferir a origem de cada um**.

## O que precisa ser feito
- [x] Rastrear e unificar a definição de N usada em cada pilar (reação vertical da
      viga vs normal no eixo) — ver issue [12](12-sistema-eixos-N-V.md).
- [x] Confirmar que o **pilar central** recebe `N = fator·R_v` (fator=2 = soma dos
      dois vãos). Para vento assimétrico adota-se `2·max(|R_A|,|R_B|)` (limite
      superior conservador; o padrão inter-vãos não é modelado explicitamente).
- [x] Reverificar o dimensionamento do pilar central (η, k_c, eixo de flambagem;
      `eixo="min"` = eixo fraco no plano do pórtico, `l_ef=1H` validado pelas issues
      14/31 — non-sway nas duas direções).
- [x] Garantir que os valores batem com a tabela do memorial (nova §8 do relatório).

## Origem dos dois valores de N (esclarecida com dados)
Executando o modelo (reações de todas as combinações):
- **209,59 kN** = `R_v` de **ELU_C2/C4** (`1,35G+1,5W+1,05Q`), a reação vertical ELU
  → é o **N do pilar** de extremidade. `2·R_v` = 419,2 kN seria o central por essa
  combinação.
- **87,33 kN** = `R_v` de **ELS_S3** (quase-permanente, só `G`, sem majoração) — um
  valor de **ELS/serviço**, que **não** pode ser usado como esforço de projeto ELU.
- (Além disso, `N_viga_kN` ≈ **1,6 MN** é o normal no **eixo da viga**, que inclui o
  empuxo `H` — vai ao tirante/sapata, não ao pilar.)

## Resolução (implementado)
- **Nova função** `verifica_pilar_governante` em
  [pilares.py](../mlc_projeto/checks/elu/pilares.py): verifica o pilar contra
  **todas** as combinações ELU, **cada uma com o seu k_mod** (EC5 §3.1.3 / §2.4.1), e
  reporta a **governante** (η máximo) + detalhamento por combinação. N definido de
  forma única: `N_d = fator_reacao·R_v` (fator=1 extremidade, 2 central).
- **`flexo_compressao.py`** (pilar lateral) e **`main.py`** (pilar central) passam a
  usar a nova função. O `main` imprime a origem dos N e a combinação governante.
- **Recheque revelou subdimensionamento na conta anterior**: o código avaliava só a
  combinação de |M| (ELU_C2, k_mod=0,70) → η_central=**0,683**. O correto (máximo
  sobre todas as combinações) é governado por **ELU_Q** (Q dom., k_mod=0,55) →
  η_central=**0,868** (lateral: 0,171 → 0,217). Ambos < 1,0 → **pilares adequados**,
  mas as taxas corretas são maiores que as reportadas antes.
- **`report.py`**: nova nota na §8 com a definição de N, as combinações governantes e
  o esclarecimento dos dois valores.
- **Testes**: [test_pilares.py](../tests/test_pilares.py).

## Dependência cruzada (transparência)
A governante ELU_Q está rotulada como duração **"longa"** (k_mod=0,55). Pelo
EC5 §3.1.3, uma combinação **com vento** deveria usar o k_mod da ação de menor
duração (vento → "curta"). Portanto η=0,868 é **conservador**; se a duração for
corrigida (issue [5](05-psi1-combinacao-frequente.md) / combinações), governa ELU_C2
(curta) com η≈0,68. A verificação do pilar (iterar todas as combinações) está correta
em ambos os casos; a classificação de duração é escopo das issues de combinação.

## Critério de aceite
Definição única de N por pilar, rastreável **✓**; pilar central reverificado
(governante entre todas as combinações, k_mod correto) e coerente com a tabela **✓**;
origem dos valores 87,3 (ELS) e 209,59 (ELU) kN explicada no memorial **✓**.
