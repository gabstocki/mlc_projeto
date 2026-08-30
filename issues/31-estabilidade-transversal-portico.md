# 31 — Estabilidade transversal do pórtico (mecanismo sway no plano)

- **Tema:** Estabilidade global
- **Prioridade:** P0
- **Normas:** EN 1995-1-1 §5.4; EN 1993-1-1 §5.2.1 (α_cr)
- **Arquivos:** `mlc_projeto/checks/elu/estabilidade_global.py`; modelo de apoios (`connections/`, `pilares.py`)

## Origem
Desdobramento da issue [14](14-contraventamento-vertical.md). A issue 14 resolveu o
caminho de carga lateral **longitudinal** (θ=0°) e corrigiu a classificação de
estabilidade. Resta a **direção transversal** (⊥ cumeeira, no plano do pórtico).

## Problema
Com pilares biarticulados (topo e base) e ligações viga-pilar rotuladas, o pórtico é
um **mecanismo sway** no seu próprio plano para carga lateral transversal
(α_cr,sway → 0). O tirante de base não estabiliza o modo sway (as bases não
transladam entre si; o modo é a rotação dos pilares em torno das bases). Hoje
`estabilidade_global.py` sinaliza isso (`alpha_cr_sway=0`, nota transversal), mas a
**solução** não está implementada.

## Opções (decisão de modelo de suporte)
1. **Bases engastadas** nos pilares → pórtico transforma-se em sistema estável no
   plano. Impacta: `pilares.py` (l_ef ≠ 1,0·H), sapata L3 (momento na base, não só
   H+N), armadura/ancoragem, e o próprio Castigliano (a base deixa de ser rótula).
2. **Contraventamento transversal** (baías transversais contraventadas / diafragma de
   cobertura levando a força a pórticos de extremidade contraventados). Mantém bases
   rotuladas, mas exige diafragma/treliça transversal.
3. **Ligações viga-pilar rígidas** (pórtico rígido) — muda o modelo estrutural.

## O que precisa ser feito
- [x] Escolher a estratégia → **Opção 2 (contraventamento transversal)**, confirmada
      com o orientador. Justificativa crítica: a Opção 1 (bases engastadas) é inviável
      com as seções atuais — o pilar central com `l_ef=2H` (cantilever sway) dá λ=180,
      k_c=0,116, **η_N≈9,7** (falha); os pilares só funcionam *non-sway* (`l_ef=1H`),
      que a Opção 2 valida.
- [x] Quantificar a demanda transversal: vento θ=90° (arrasto nos pilares, reação de
      topo) + forças nocionais (EN 1993-1-1 §5.3.2).
- [x] Implementar/verificar o sistema e o caminho de carga à fundação.
- [x] Propagar as consequências: **nenhuma mudança em pilares.py/L3/Castigliano** —
      a Opção 2 preserva bases rotuladas e `l_ef=1H`; o diafragma trava os topos,
      tornando legítimo o dimensionamento atual dos pilares e o `pilar_vento_90`.

## Resolução (implementado)
- **Novo módulo** [contraventamento_transversal.py](../mlc_projeto/checks/elu/contraventamento_transversal.py):
  diafragma de cobertura (viga horizontal entre frontões) + **frontões contraventados**
  (cruzes de St. André). Demanda = arrasto θ=90° nos pilares (reação de topo) + nocional;
  diagonal à tração (EN 1993-1-1 §6.2.3, ∅ comercial automático); **caminho de carga à
  fundação** (`H_base` + `N_uplift`); drift δ ≤ H/300; força de corda do diafragma
  reportada (→ beiral). Resultado: H_tr≈60,5 kN, ∅20 mm S235, η_N≈0,65.
- **`estabilidade_global.py`**: novo parâmetro `contravento_transversal_ok`; o sistema
  só é *non-sway* se **ambas** as direções (long. §14 + transv. §31) estiverem
  verificadas; `alpha_cr_sway`, `non_sway_long`, `non_sway_transv` no retorno.
- **`main.py`**: chama o módulo transversal (Fase 2) e passa o `ok` à estabilidade global.
- **`report.py`**: nova §8b.2 (memória do contraventamento transversal) + linha no
  resumo §12; item 1 da §8b agora cita as duas direções; nota da §9 atualizada.
- **Testes**: [test_contraventamento_transversal.py](../tests/test_contraventamento_transversal.py)
  e atualização de [test_estabilidade_global.py](../tests/test_estabilidade_global.py)
  (agora exige as duas direções para *non-sway*).

## Critério de aceite
Direção transversal com sistema lateral definido e verificado (diafragma + frontões,
caminho de carga à fundação) **✓**; estabilidade lateral avaliada pelo modo sway nas
duas direções (non-sway só com ambos os contraventamentos) **✓**; consequências no
modelo propagadas de forma consistente (pilares `l_ef=1H` validado, sem mudança de
apoios) **✓**.
