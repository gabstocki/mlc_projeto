# 26 — Situação de içamento da viga (combinação de montagem)

- **Tema:** Modelo — situações transitórias
- **Prioridade:** P1
- **Normas:** EN 1991-1-6 (ações durante a execução); EC5 (verificação da peça)
- **Arquivos:** verificação inexistente (novo módulo em `checks/elu/`)

## Apontamento do orientador
> Falta verificação de situação de içamento da viga maciça — combinação ao menos.

## Estado atual no código
- O pipeline verifica apenas a estrutura **em serviço**; não há nenhuma verificação
  da fase **transitória de montagem/içamento** da viga de MLC.

## Por que importa
No içamento, a viga é apoiada/suspensa em pontos diferentes dos apoios definitivos,
gerando **momentos e cortantes com sinais e posições distintos** (momento negativo nos
pontos de içamento, viga em balanço, possível flambagem lateral com contenção mínima).
É uma situação de projeto por si.

## O que precisa ser feito
- [ ] Definir o esquema de içamento (nº e posição dos pontos de suspensão, ângulo dos
      cabos) — ou o esquema previsto pela fabricação.
- [ ] Montar **pelo menos uma combinação** de içamento (peso próprio × γ + efeitos
      dinâmicos de montagem, EN 1991-1-6).
- [ ] Verificar flexão (incl. momento negativo), cortante, e **flambagem lateral com a
      contenção real durante o içamento** (crítica — viga longa e esbelta).
- [ ] Registrar no memorial.

## Critério de aceite
Ao menos uma combinação de içamento verificada (flexão/cortante/LTB), com o esquema de
suspensão documentado.
