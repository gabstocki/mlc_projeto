# 99 — Coerência numérica entre resumo, capítulos e apêndices; regra de precisão; Apêndice D

- **Tema:** Coerência
- **Prioridade:** P1 — fazer **por último**, depois de todas as issues que mudam resultados
- **Arquivos:** resumo/abstract (`00-pretextual.tex`), todos os `capNN.tex`, apêndices B–D (gerados), `output/formatacao.py`
- **Relaciona:** 53 (regra de precisão)
- **Origem:** 4ª revisão, itens 10.1 e 10.8

## Divergências apontadas
| Grandeza | Onde | Valores |
|---|---|---|
| Verificações | Resumo, §6.1 / §4.1, §8.3 | 64 / 55 |
| Testes automatizados | Resumo, §8.3 / §8.1 | 736 / 730 |
| NDP | §3.5.1 / §8.4.1 (conferir Tab. 7) | 18 / 19 |
| η contraventamento vertical | §4.3 / §4.2.3, Tab. 22, §8.2 | 0,79 / 0,84 |
| Arrancamento pilar de canto | §6.3 / Tab. 30, 31, 37 | 193 / 284 kN |
| η pinos da L1 | §7.2.3 / Tab. 25, 27 | 0,69 / 0,70 |
| Fendilhamento | §8.2 / §7.2.3 | 0,339 / 0,34 |

## O que fazer
- [x] Eliminar todas as divergências acima (preferir gerar os números do pipeline em vez de digitar).
- [x] Aplicar a regra de precisão do §6.1 também a: α_cr = 124,75 e 16,50; excentricidade 29,58 mm;
      massa 1.943,4 kg; rigidez 208.462 kN/m.
- [x] Varredura final por números repetidos entre capítulos.
- [x] 10.8 — Apêndice D gerado pela **mesma execução** que produziu o texto final (regenerar ao fim).

## Acrescentado pela issue 82 (beiral)
- [x] Todos os números digitados nos cap. 4–9, resumo e custo são anteriores ao beiral: η, forças,
      diâmetros (CV-V Ø36, CV-T Ø27), L1 com 6 pinos, arrancamento 96,9 kN, R_v 111 kN, η_max 0,89
      (governa a diagonal da cobertura), quantidades (vigas + 5,9 m³; terças ≈ 94,8 m³) e custo.
      **Preferir gerar** os valores do pipeline (macros em um `.tex` gerado) em vez de digitar.
- [x] Figuras OpenSees/VTK e comparação FEM × analítico sem o balanço.
- [x] (issue 101) terça 0,20 × 0,40: volume das terças (≈ 65 m³ em vez de 94,8), peso próprio
      (g_terças 0,130 kN/m²), arrancamento L1 100,5 kN e custo.
- [x] Aviso genérico “There were undefined references” na compilação (sem rótulo identificado; pré-existente).

## Resolução (2026-11-12)

**Números gerados pelo pipeline, não digitados.**
- `output/valores_tese.py` escreve `tese/valores_pipeline.tex` na mesma execução que gera os apêndices. As macros são:
  - `\nVerif` 75, `\nVerifExec` 73, `\nVerifNA` 2, com variantes por extenso no gênero certo (setenta e cinco, setenta e três, duas);
  - `\nNDP` 20;
  - `\nTestes`, contado por `pytest --collect-only`;
  - `\etaMaxGlobal`.
- O mesmo módulo escreve `tese/tab_ndp.tex` a partir de `core.normativo.parametros_ndp()`, com 20 linhas. A tabela antiga tinha 18: faltavam k_s, k_f,2, k_f,3 e γ_M,fi, e listava os limites de flecha, que no código são escolha de projeto (a Tab. 7.2 dá intervalos). O cap. 4, o cap. 7 (§ ELS), o cap. 9 e o Apêndice A foram corrigidos.
- Usam as macros: resumo, abstract, cap. 5, 7 e 9 e Apêndice A. Isso substitui 64, 55, 62, 736, 835, 18 e 19.
- `output/custo.py` gera `tab_custo_quantidades`, `tab_custo_composicao` e `tab_custo_sensibilidade`, mais as macros de custo (`\custoTotal`, `\custoPorMetro`, `\custoPctMadeira` etc.). As quantidades saem do pipeline:
  - vigas: 227 m³ com os beirais (volume da varredura);
  - terças: 65,4 m³ (g_terças × área ÷ γ);
  - pilares: 19,7 m³, 15 maciços e 14 bipartidos;
  - aço: 3.330 kg (Ø36/Ø28/Ø27).
- Total de R$ 2,69 milhões, ou R$ 1.300/m² sobre 2.067 m². As vigas aprovadas de menor volume têm 57% do volume adotado, uma diferença de cerca de R$ 506 mil.

**Precisão.** Valores em reais e quantidades com 3 algarismos significativos. Também: α_cr 104 / 19,6, e₀ 29,6 mm, massa 1.940 kg, rigidez 208.000 kN/m. Carga de incêndio da estrutura: 312 m³, cerca de 1.200 MJ/m².

**Divergências apontadas.** Todas foram eliminadas, aqui ou na issue 106:
- CV-V 0,88;
- arrancamento do canto 357 kN;
- pinos da L1 0,68;
- fendilhamento 0,67.

O Apêndice D lê `output/pipeline_console.txt` da última execução do pipeline, que deve continuar sendo o último passo antes de compilar.

**Pendente: o aviso “There were undefined references”.**
- Não há rótulo nem citação nomeados no log, nem “??” no PDF.
- O biblatex pede “(re)run Biber” mesmo com o `.bcf` estável entre execuções.
- Provável origem: o estilo `biblatex-abnt` (falta `brazilian-abnt-abnt.lbx`) ou a lista vazia `keyword=consulta`.
- Pré-existente e sem efeito visível.

Testes: `tests/test_issue99_valores_tese.py`.

**Atualização (issue 95):** o aviso de undefined references vinha do backref/citecounter do biblatex. Desligados, o log fica limpo (0 avisos, sem pedido de novo Biber). ✅
