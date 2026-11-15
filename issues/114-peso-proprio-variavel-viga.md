# 114 — Peso próprio da viga com altura variável (hoje uniforme médio)

- **Tema:** Ações — peso próprio
- **Prioridade:** P1 — +27 kN·m de cálculo na cumeeira (~5,7 %)
- **Origem:** Revisão técnica (comentários tipo banca), 2026-11-14, item 6

## Diagnóstico — CONFIRMADO
- `core/loads.py:142`: `q_viga_lin = V_viga·γ/L`, uniforme. O momento no meio do vão fica subestimado, porque a madeira está concentrada no centro.
- Para h linear de h₀ a h_ap: ΔM_k = b·γ·Δh·L²/48 = 0,32·4,12·1,785·20,25²/48 ≈ 20 kN·m (×1,35 ≈ 27 kN·m). Bate com o revisor.
- A comparação MEF 481 × analítico 478 não valida o carregamento, porque os dois usam carga uniforme.

## O que fazer
- [x] Peso próprio g(x) = γ·b·h(x) no integrador de esforços (M, V, N, reações) e no modelo OpenSees (carga por elemento).
- [x] Refazer M_Ed, as verificações da viga, a varredura global e as figuras; comparar com o atual.
- [x] Texto: cap. 6 (Tab. 18 e de rigidez), Apêndices B e C.

## Resolução (2026-11-14)

**Código**
- `analisar_biarticulada(..., g_var_kNm3)`: soma Δg(x) = g_var·b·(h(x) − h̄) às cargas médias.
  - No vão, a resultante é nula: as reações do vão não mudam; o momento ganha b·γ·Δh·L²/48 no meio.
  - No beiral, a altura (0,80–1,00 m) fica abaixo da média de 1,89 m: o balanço fica mais leve e o alívio do vão diminui (antes isso estava contra a segurança).
- `Combinacao.fator_G` (γ_G da combinação, ou 1 no ELS) é passado em `_analisar`, nos aliases ELU_C2/C3/C4, em Q+0,6W, nos diagramas, em M_g e em M_ELS. `Carregamentos.peso_viga_variavel` (padrão True) e `gamma_mlc_kNm3`.
- Também recebem o fator: ELS (`deflection_els._parcelas_signed` com fG nas parcelas com G), cargas de fundação (`_R(..., fG)`) e flambagem sob sucção (passa a usar o integrador em vez de `momento_biapoiada`).
- OpenSees (`opensees_vtk.analisar_viga(q, fG)`):
  - carga por elemento segundo h(x); M, V e N saem dos próprios elementos (`localForce`) e colorem a malha 3D;
  - aferição: M_FEM 507,9 × integrador 508,1 kN·m (0,04 %) sem o beiral;
  - figuras do modelo 3D regeneradas.

**Resultados**
- M_Ed na cumeeira: 477,9 → **505,7 kN·m** (+27,8: +27 do peso variável, e o restante do beiral mais leve).
- R_v: 106,0 → 103,9 kN. Q+0,6W: 527,6 kN·m, utilização relativa 0,97.
- Viga: cumeeira 0,34 → 0,36, LTB 0,10 → 0,11, sucção 0,17 → 0,16, L1 0,49 → 0,48, L1c 0,58 → 0,57.
- ELS: w_fin 14,34 → 15,18 mm (0,19); w_inst 6,48 mm.
- Pilar central 212 → 208 kN (0,40).
- α_cr: longitudinal 165, transversal 12,1. Estabilidade 0,83.
- η_max continua 0,93 (diafragma).

**Tese**
- Cap. 6: parágrafo do peso próprio variável (fórmula, 20 kN·m característicos / 27 de cálculo, efeito no beiral); tabela de rigidez com nota (peso uniforme, sem beiral); "modelo conservador" → "o que produz o maior momento positivo no cenário gravitacional" (item 5 da revisão); Q+0,6W; Tab. 18; esforço normal; comparação FEM × integrador reescrita (afere o integrador, não a carga); α_cr.
- Cap. 7: tabelas da viga, dos pilares e do ELS; LTB sob sucção (15,90 m, h 1,768, M −288, σ_crit 23,8, k_crit 0,81); pilar central; estabilidade.
- Cap. 8: apoio L1/L1c e sela. Cap. 5, cap. 9 e resumo/abstract: 0,57.

**Testes:** `tests/test_issue114_peso_variavel.py` (2); regressões atualizadas (`test_f06`, `test_f07`, `test_flambagem_succao`, `test_tirante_base`). Resultado: 869 passed.


**Varredura global (110 + 114, 2026-11-14):** 1.110 de 3.213 aprovadas, mesmo número de antes, mas com motivos diferentes nas geometrias pesadas.
- 4 reprovam na estabilidade global (b = 0,36, h₀ ≥ 1,15, α = 8,0–8,5°): o α_cr transversal com o diafragma flexível cai pouco abaixo de 10 (η 1,00–1,02).
- 1 reprova no pilar central montante (16°, 1,20 m).
- O deslocamento do diafragma fica entre 0,83 e 0,99.
- A fronteira de volume e a geometria adotada não mudam.
- Cap. 5 atualizado (alínea das reprovações e faixa do diafragma). ✅
