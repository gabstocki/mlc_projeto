# 110 — Caminho transversal até os frontões e diafragma nas baías intermediárias

- **Tema:** Estabilidade global — direção transversal
- **Prioridade:** P0 — sem diafragma demonstrado, os pórticos intermediários (viga e pilares birrotulados) são mecanismo
- **Origem:** Revisão técnica (comentários tipo banca), 2026-11-14, item 2

## Diagnóstico — CONFIRMADO
- Os pórticos intermediários não têm rigidez lateral própria: todas as ligações são rotuladas e o pilar é birrotulado. A força transversal no topo do pórtico 5 só chega aos frontões por um diafragma horizontal ao longo dos 46 m.
- As cruzes da cobertura (CV-H) estão só nas baías 1–2 e 8–9. Nas baías 2–8 não há alma resistente ao cisalhamento: vigas e terças rotuladas formam retângulos.
- `estabilidade_global.py`: `K_lat_transv` vem só dos painéis CV-T dos frontões. O α_cr transversal = 19,6 supõe implicitamente um diafragma rígido.
- A corda de beiral (N = 19,8 kN) é verificada, mas a alma do diafragma não é.

## O que fazer
- [x] Decidir o mecanismo (decisão do autor):
  - (a) telha como diafragma: rigidez, cisalhamento, fixações, emendas e coletores, com produto definido;
  - (b) treliçamento horizontal em todo o comprimento, ou nas fachadas, entre os frontões;
  - (c) outra solução, como contraventamento transversal em pórticos intermediários.
- [x] Modelo espacial (OpenSees) com as liberações reais: força transversal no pórtico 5 → fundações dos frontões; deslocamentos e esforços.
- [x] Recalcular o α_cr transversal com a rigidez demonstrada.
- [x] Desenhos, quantitativos e texto (§5.5, §6.x, cap. 7).

## Resolução (2026-11-14) — opção B, cruzes em todas as baías (decisão do autor)

**Estudo** (`issues/110-estudo-diafragma.py`)
- H_tr = 139,6 kN de cálculo, w = 3,04 kN/m, fluxo de cisalhamento ≤ 1,72 kN/m.
- Opções: A (telha como diafragma), B (cruzes nas baías 2–8, dois vãos: 192 Ø12, ≈ 1,07 t), B1 (só o vão A–B: 96 barras, cordas de 40 kN).

**Modelo em planta** (`opensees/diafragma_espacial.py`)
- Nós nos cruzamentos de terças e vigas (9 eixos × 17 linhas); vigas e terças como barras rotuladas.
- Cruzes só à tração (Elastic com E_neg = 0, análise não linear em 10 passos).
- Painéis CV-T (transversal) e CV-V (longitudinal) como molas com a rigidez C_h.
- Sem as CV-D, o modelo é singular: o **mecanismo fica demonstrado**.
- Com as CV-D: os frontões recebem 69,85 / 69,80 kN; 100 kN no pórtico 5 chegam com 50,0 / 50,0 kN; δ_max = 21,7 mm (13,2 do painel do frontão).

**Verificação** (`checks/elu/diafragma_cobertura.py`, chave `diafragma_cobertura`)
- CV-D: menor diâmetro ≥ 12 com η ≤ 0,90 → Ø12, F_diag máx 6,1 kN, η 0,23.
- CV-H ao vento transversal: η 0,04.
- Deslocamento ≤ H/300 = 23,3 mm: η 0,93, que passa a ser o η_max do projeto.
- `lig_diag_diafragma`: terminal por capacidade, η 0,52.
- **Rigidez equivalente** K_eq = 6.439 kN/m, contra 10.695 kN/m dos painéis com diafragma rígido; passou a alimentar o α_cr transversal: 19,6 → **11,8** (≥ 10, 1ª ordem; k_II = 1,09 não aplicado). Estabilidade global η 0,85.

**Desenho e quantitativo**
- DES-02 com as CV-D (traço fino cinza) e nota.
- Custo: +1,07 t de aço (`m_cv_diafragma`).
- Nova figura `fig/diafragma_caminho.pdf`, gerada pelo pipeline: deslocamento do topo de cada pórtico nos dois casos, com as reações nos frontões.

**Tese**
- Cap. 6 (§ ordem da análise): mecanismo, modelo, caminho de carga, figura e α_cr 11,8 (e o longitudinal corrigido para 162, após a 109).
- Cap. 7: tabela de contraventamentos (diafragma 0,93, ligação 0,52, estabilidade 0,85), texto e síntese (η_max no deslocamento).
- Cap. 8: parágrafo das CV-D.
- Cap. 5: menção às CV-D.
- Tab. de nomenclatura e lista de siglas: CV-D.
- Abstract: 0,93.

**Testes:** `tests/test_issue110_diafragma.py` (4). Resultado: 867 passed.

**Fica para outras issues**
- 113: rigidez ao afastamento dos apoios de uma viga, com este modelo estendido.
- 121: este modelo serve de verificação independente da hipótese de diafragma.
- A margem do α_cr (11,8) é governada pelos painéis dos frontões. Se for preciso mais folga, engrossar a CV-T (4 barras) é a medida mais barata.

**Varredura global (110 + 114, 2026-11-14):** 1.110 de 3.213 aprovadas, mesmo número de antes, mas com motivos diferentes nas geometrias pesadas.
- 4 reprovam na estabilidade global (b = 0,36, h₀ ≥ 1,15, α = 8,0–8,5°): o α_cr transversal com o diafragma flexível cai pouco abaixo de 10 (η 1,00–1,02).
- 1 reprova no pilar central montante (16°, 1,20 m).
- O deslocamento do diafragma fica entre 0,83 e 0,99.
- A fronteira de volume e a geometria adotada não mudam.
- Cap. 5 atualizado (alínea das reprovações e faixa do diafragma). ✅

**Diagonais dos frontões engrossadas (decisão do autor, 2026-11-15)**
- A CV-T é dimensionada também pela rigidez do sistema: é o menor diâmetro com o deslocamento do conjunto (painel + diafragma) ≤ 0,75·H/300 (`ETA_DESLOC_TRANSV`, laço `_cvt`/`_diaf` no main).
- Ø27 → **Ø33/M36**: δ 21,7 → 17,3 mm (η 0,74); K_eq 6.440 → 8.040 kN/m; α_cr transversal 12,1 → **15,1** (estabilidade η 0,67). Diagonal η 0,55; ligação 0,69 (pino Ø33).
- η_max do projeto volta a 0,91 (lâmina do central montante). Tese: cap. 6 (§ ordem da análise), cap. 7 (tabela, CV-T, síntese), cap. 8 (diâmetros, olhal), abstract.

**Varredura global após o engrossamento da CV-T (2026-11-15):** 1.114 de 3.213 aprovadas (antes 1.110).
- As 4 reprovações por α_cr transversal desaparecem: com a CV-T dimensionada pela rigidez em cada geometria, o α_cr fica acima de 10 em todas as aprovadas.
- Resta 1 reprovação de sistema: lâmina do pilar central montante (16°, 1,20 m, b = 0,36).
- O deslocamento do diafragma fica entre 0,66 e 0,75 do limite (o laço da CV-T leva cada geometria a ≤ 0,75).
- A faixa do central montante bipartido nas aprovadas é 0,85–1,00.
- Fronteira de volume e geometria adotada sem mudança. Cap. 5 atualizado. Rodada com as causas completas (issue 124). ✅
