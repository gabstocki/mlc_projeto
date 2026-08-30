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
- [ ] Rastrear e unificar a definição de N usada em cada pilar (reação vertical da
      viga vs normal no eixo) — ver issue [12](12-sistema-eixos-N-V.md).
- [ ] Confirmar que o **pilar central** recebe `N = R_v(vão esq.) + R_v(vão dir.)`
      da(s) combinação(ões) governante(s), incluindo casos assimétricos de vento
      (as reações dos dois vãos podem não ser iguais).
- [ ] Reverificar o dimensionamento do pilar central (η, k_c, eixo de flambagem;
      atenção ao `eixo="min"` em [pilares.py:91-93](../mlc_projeto/checks/elu/pilares.py)).
- [ ] Garantir que os valores batem com a tabela do memorial.

## Critério de aceite
Definição única de N por pilar, rastreável; pilar central reverificado e coerente com
a tabela; a origem dos valores 87,3 e 209,59 kN explicada no memorial.
