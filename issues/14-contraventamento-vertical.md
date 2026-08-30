# 14 — Contraventamento vertical/frontões ausente — mecanismo lateral; αcr de arco ≠ sway

- **Tema:** Estabilidade global
- **Prioridade:** P0
- **Normas:** EC5 §5.4; EN 1993-1-1 §5.2.1 (α_cr, analogia)
- **Arquivos:** `mlc_projeto/checks/elu/estabilidade_global.py:189-223`, `:30-42`

## Apontamento do orientador
> Faltam os contraventamentos vertical e de frontões (força de 125,8 kN sem caminho
> até a fundação). Um pórtico com pilares biarticulados e sem contraventamento
> vertical é um mecanismo hipoestático para carga lateral, não um sistema
> indeslocável. O valor αcr = 14,7 refere-se ao modo de arco, não ao modo de
> deslocamento lateral do pórtico.

## Estado atual no código
- [estabilidade_global.py:189-197](../mlc_projeto/checks/elu/estabilidade_global.py)
  classifica o sistema como **non-sway** por ser biarticulado ("empuxo H de 1.ª ordem
  à fundação; sem momentos de nó").
- O α_cr reportado (~14,7) é o **modo de arco** com `L_ef = L/2`
  ([:217-223](../mlc_projeto/checks/elu/estabilidade_global.py)) — **não** o modo de
  deslocamento lateral (sway) do pórtico.
- A força longitudinal de vento θ=0° (`F_total`, ~125,8 kN) é calculada em
  [wind.py:204-280](../mlc_projeto/core/wind.py), mas **não há um sistema vertical de
  contraventamento** que a conduza do nível da cobertura até a fundação.

## Análise
Com pilares biarticulados topo e base e sem contraventamento vertical, o pórtico é um
**mecanismo** para carga lateral no plano — não pode ser tratado como indeslocável. O
α_cr de arco não representa a estabilidade lateral. É preciso um caminho de carga
lateral real: contraventamento vertical nas fachadas/frontões (cruzes de St. André,
pórtico de contraventamento, ou parede de cisalhamento).

## O que precisa ser feito
- [x] Definir o **sistema de contraventamento vertical** (nas paredes longitudinais),
      com caminho de carga completo até a fundação.
- [x] Verificar esse sistema para a força lateral θ=0° (~125,8 kN) e para as forças
      nocionais/imperfeições (EN 1993-1-1 §5.3.2).
- [x] Corrigir a classificação de estabilidade: não classificar *non-sway*
      incondicionalmente; o α_cr de arco foi rotulado como **modo de snap-through**
      (informativo), separado do **modo sway** (α_cr,sway).
- [x] Reavaliar 1.ª vs 2.ª ordem com base no modo correto (condicionado ao
      contraventamento vertical).
- [ ] **Direção transversal (⊥ cumeeira):** resolver o mecanismo sway no plano do
      pórtico → ver issue [31](31-estabilidade-transversal-portico.md) (muda o modelo
      de suporte; fora do escopo desta issue para não refatorar as bases).

## Resolução (implementado)
- **Novo módulo** [contraventamento_vertical.py](../mlc_projeto/checks/elu/contraventamento_vertical.py):
  cruzes de St. André nas paredes longitudinais; demanda = vento θ=0° + nocional;
  diagonal à tração (EN 1993-1-1 §6.2.3, diâmetro comercial automático); **caminho de
  carga à fundação explícito** (`H_base` cortante + `N_uplift` arrancamento); drift
  δ ≤ H/300. Resultado atual: ∅42 mm S235, η_N≈0,82, δ ok.
- **`estabilidade_global.py`**: novo parâmetro `contravento_vertical_ok` condiciona a
  classificação sway/non-sway; adicionados `alpha_cr_sway` e nota da direção
  transversal; `metodo_analise="instavel_lateralmente"` quando não há sistema lateral.
- **`main.py`**: chama o contraventamento vertical (Fase 2) e passa o `ok` à
  estabilidade global.
- **`report.py`**: nova §8b.1 (memória do contraventamento vertical) + linha no
  resumo §12; corrigida a afirmação "non-sway (biarticulado)".
- **Testes**: [test_contraventamento_vertical.py](../tests/test_contraventamento_vertical.py)
  e atualização de [test_estabilidade_global.py](../tests/test_estabilidade_global.py)
  (a premissa antiga "biarticulado ⇒ non-sway" era o erro apontado).

## Critério de aceite
Sistema de contraventamento vertical dimensionado com caminho de carga à fundação
(**longitudinal: atendido**); estabilidade lateral avaliada pelo modo sway
(arco separado do sway; **transversal: avaliada e sinalizada** como mecanismo →
issue 31).
