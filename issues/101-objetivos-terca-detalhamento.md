# 101 — Objetivos × resultados: seção das terças e objetivo (c)

- **Tema:** Coerência — objetivos
- **Prioridade:** P1 — **decisão do autor** no item das terças
- **Arquivos:** `tese/cap01.tex` §1.3 (objetivos), `tese/cap05.tex` §4.6, `tese/cap09.tex` §8.1
- **Relaciona:** 69, 91 (objetivo (c))
- **Origem:** 4ª revisão, item 10.3

## O que fazer
- [ ] Objetivo (a) inclui “obter [...] as seções [...] das terças”, mas §4.6 diz que seção e espaçamento
      das terças são dados de entrada. **Autor:** ajustar o objetivo ou dimensionar a terça (varredura
      de seção/espaçamento).
- [ ] Objetivo (c) “detalhar as ligações e a ancoragem em desenhos cotados” só se cumpre após 69 e 91:
      revisar o §8.1 depois delas.

## Resolução — parte (a) ✅ (2026-11-07): terça DIMENSIONADA (decisão do autor: seção única)
`mlc_projeto/predim/varredura_terca.py`: s fixo = L/8 (painéis do CV-H, l_1 da viga); larguras
0,115–0,20 m × alturas 0,24–0,60 m (múltiplos de 40 mm); pipeline completo por candidata (a
seção muda g_k e as ligações). Critério: APROVADO e η ≤ 0,75 em flexão, biela, Q_k, corda,
balanço do oitão, nó de topo (escoras + ligações) e terça–viga. Menor área aprovada:
**0,20 × 0,40 m** (antes 0,20 × 0,58 como dado de entrada; −31 % de seção). Governa a ligação da
escora central ao nó (η 0,74; altura para as fileiras de cavilhas); barra: biela 0,44, flexão 0,20.
Vizinhas: 0,20×0,36 → 0,83; 0,18×0,40 → 0,97; 0,16×0,44 → 1,19.
Efeitos: g_k terças 0,189 → 0,130 kN/m²; arrancamento L1 96,9 → 100,5 kN (L1 6 pinos, η 0,68);
η_max 0,89 inalterado (diagonal da cobertura). Testes `tests/test_issue101_terca.py` (3). 764 passed.
Tese: nova §4.x «Terças» com tabela de candidatas; síntese do pré-dim. e Tab. de critérios;
terça retirada dos dados de entrada (Tab. de geometria).

**Pendente — parte (c):** revisar o §8.1 depois das issues 69 e 91.

## Resolução — parte (c) ✅ (2026-11-11)
`cap09` §`sec:quanto-objetivos`: o parágrafo corrido virou uma alínea por objetivo específico, cada uma com a remissão ao lugar onde o objetivo é cumprido.
- **(a)** viga por varredura; terças 0,20×0,40 por varredura própria (`sec:predim-tercas`); pilares.
- **(c)** 16 folhas descritas: soldas, aço e proteção em cada uma. Declarado com franqueza: o **nó de topo das baías contraventadas não está detalhado em desenho** (issue 104), com um `%% TODO (issue 104)` para revisar quando o nó for resolvido.
- **(e)** 835 testes (era 730). A recontagem final fica para a 99.

A §4.6 já não trata a terça como dado de entrada: só o espaçamento L/8 é fixado, com justificativa.

**Atenção (issue 104):** a seção da terça é governada pela ligação da escora central ao nó de topo (η 0,74). Se a 104 mudar o nó, a varredura da terça deve ser refeita.
