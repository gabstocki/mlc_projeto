# 63 — Figuras: variáveis da varredura (§5.2) e modelo estrutural (§6.1)

- **Tema:** Memorial — figuras
- **Prioridade:** P2
- **Fonte:** anotações no PDF `main (1)gavassoni.pdf` (não constavam do e-mail)
- **Arquivos:** `tese/cap05.tex:26-42` (§5.2 Varredura global da viga / §5.2.1 Grade percorrida); `tese/cap06.tex:7-20` (§6.1 Sistema estrutural, “Cada pórtico transversal…”); `tese/fig/`; `mlc_projeto/visualization/`
- **Relaciona:** issue 52 (desenhos e nomenclatura)

## Origem (3ª revisão do orientador, anotações no PDF)
- p. 29 (impressa 28), título “5.2 VARREDURA GLOBAL”: *“precisa uma figura mostrando essas
  variáveis”* — inclinação do extradorso α, altura no apoio h₀ e largura b da seção.
- p. 36 (impressa 35), §6.1 “Cada pórtico transversal…”: *“por uma figura do modelo”*.
  Há ainda uma nota sem texto ao lado do parágrafo do §6.1.1 sobre arco abatido × viga
  biapoiada (provavelmente pede ilustrar os dois extremos de apoio horizontal).

## O que fazer
- [x] Figura esquemática da viga de duplo-bisel com α, h₀, h_ap, b e L cotados (símbolos da lista — issue 56).
- [x] Figura do modelo estrutural do pórtico: vigas, 3 pilares, rótulas, apoios, cargas,
      eixos; nomes dos elementos coerentes com a issue 52. Opcional: o modelo FEM (OpenSeesPy).
- [x] Opcional: esquema do apoio horizontal (indeslocável → arco; livre → biapoiada; mola k).

## Resolução (2026-10-08) ✅
Novo módulo `mlc_projeto/output/esquemas.py`, gerado pelo pipeline a partir da GeometriaViga
(→ `tese/fig/esq0*.pdf`; sem escala, altura ampliada e declarada na figura):
- ESQ-01 `fig:esq-variaveis` (§5.2.1): viga com $L$, $h_0$, $h_{ap}$, $\alpha$, seção $b\times h(x)$
  e as faixas da varredura.
- ESQ-02 `fig:esq-modelo` (§6.1): pórtico intermediário — eixo da viga, cargas $q_{esq}$/$q_{dir}$,
  pilares articulados no topo e na base, eixos A–C, nomes V(2i−1), V(2i), P(3i−2)… (issue 52),
  nota da estabilidade no plano (diafragma → CV-T).
- ESQ-03 `fig:esq-apoio` (§6.1.1): (a) apoio indeslocável → arco, H > 0; (b) mola $k_h$;
  (c) apoio livre → biapoiada, H = 0 (a nota sem texto do orientador).
Símbolo $k_h$ acrescentado à lista. Teste `tests/test_esquemas.py`; suíte 731.
