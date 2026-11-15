# 109 — Vento longitudinal entra sem γ_Q nos contraventamentos

- **Tema:** Ações — vento paralelo à cumeeira
- **Prioridade:** P0 — muda diagonais, escoras, montantes, ligações e ancoragens
- **Origem:** Revisão técnica (comentários tipo banca), 2026-11-14, item 1

## Diagnóstico — CONFIRMADO no código
- `core/wind.py::forca_vento_paralelo_cumeeira`: `F_fric = 0,5·q·a·b` com `q = 0,613·V_k²`, **característico**. F_total = 65 + 862 = 927 kN.
- `checks/elu/contraventamento_vertical.py:432`: `V_lat_total = frac·(F_vento0 + H_imp)`, **sem γ_Q**.
- `checks/elu/contraventamento.py:534`: `R_vento0 = F_vento0_baia/2` (115,8 kN), **sem γ_Q**, somado à estabilização.
- Inconsistência interna: `contraventamento_transversal.py:117` aplica `F_col_d = γ_Q·F_col_k`.
- q do atrito = 927 − 65 = 862 kN = 0,5·q·2.067 → q ≈ 0,834 kN/m² (z_ref do atrito). A fixação da telha usa q = 0,890 kN/m² (z = 8,79 m). As duas podem estar certas, mas o texto não as distingue.
- Estimativa do revisor: com 1,5·F_k, a diagonal CV-V passa de 0,88 para ~1,30.

## O que fazer
- [x] Aplicar γ_Q = 1,5 ao vento longitudinal nos contraventamentos vertical, central e da cobertura (R_vento0), no nó/escoras e no download dos montantes. Rever também se `H_imp` (nocional, origem gravitacional) leva γ_G.
- [x] Rastrear quem consome `vento_0`: pilares (vento θ=0°), terça-biela, ancoragens, bipartido, cargas de fundação (W_k característico deve continuar característico).
- [x] Teste de regressão: V_lat = γ_Q·(F_pil + F_t) + H_imp.
- [x] Redimensionar o que reprovar (diagonais Ø36/Ø28, olhais, escoras, nó, lâminas, bases L3a, chumbadores) e refazer a varredura global.
- [x] Tese: sequência explícita q_k → F_t,k → F_t,d → V_Ed → N_Ed (cap. 6, cap. 7, Apêndice B, eq. B.10), e tabela das pressões dinâmicas usadas (global × local, z de cada uma).

## Resolução ✅ (2026-11-14)

**Código**
- `contraventamento_vertical.py` e `contraventamento.py` aplicam `F_vento0_kN = γ_Q·F_k` e guardam `F_vento0_k_kN`. A nocional H_imp não leva γ_Q, porque já sai da reação vertical de cálculo.
- Diagonal da cobertura: a escolha passou a ser automática (`_cv_cobertura` no main): o menor diâmetro comercial com η ≤ 0,90, como na vertical. `D_BARRA_CV_MM` virou o diâmetro mínimo.
- Escora central (T9 nas 4 baías contraventadas da linha B): seção própria de 0,24 × 0,40 (`B_ESCORA_CENTRAL`), por decisão do autor. Com 0,20, a flambagem no eixo fraco dava η 1,03.
- Concreto frágil limitado a 0,75 no veredito (`ETA_CONCRETO_FRAGIL`, `ancoragem.py`). A tese já declarava isso, mas o código aprovava até 1,0.
- Bases L3a dos montantes: h_ef 400 → 500 mm, c ≥ 750 mm, bloco ≥ 1,00 m e chaveta de 200 → 260 mm (`DADOS_ANCORAGEM_MONT`). As bases correntes ficam inalteradas.
- O check "Sucção/uplift" (resistência lumped de 80 kN/chumbador) saiu do quadro (`report._DEMANDAS`); o cálculo do arrancamento continua alimentando as ancoragens EN 1992-4.
- DES-07: h_ef, borda, bloco e chaveta próprios dos montantes, e corte mais próximo da planta. DES-09B em 1:25. Solda da chaveta L3a com l = 260 mm.
- Memorial: equação B.10 com γ_Q·F_w,k explícito.
- Testes: `tests/test_issue109_vento_longitudinal_gamma.py` (3); `test_contraventamento_cobertura` (Ø36) e `test_contraventamento_vertical` (faixa nova) atualizados; o teste de desenhos usa a ancoragem dos montantes. Resultado: 863 passed.

**Resultados**
- F_w,d = 1,5 × 926,7 = 1.390 kN; V por painel 118 → 176 kN.
- Diagonal CV-V Ø36 → **Ø45/M48** (η 0,84). Diagonal CV-H Ø28 → **Ø36/M39** (η 0,80). Aço de contraventamento: 3.040 → 5.280 kg.
- Escoras 176/351 kN: beiral 0,52, central 0,65; ligações 10 e 20 cavilhas (0,73/0,74). Montante terça–viga: 14 cavilhas (0,73).
- Lâminas do bipartido: D = 258 kN; compressão 0,89 (canto), 0,78 (lateral), **0,91** (central) — passa a ser o η_max do projeto (madeira, limite 1,0).
- Ancoragens: canto 442/245 kN, cone 0,69, chaveta 0,71; central montante 427/176 kN, cone 0,67.
- Pipeline APROVADO, η_max 0,91, 74 verificações (72 executadas).
- Varredura global refeita: 1.110 aprovadas (antes 1.115); 5 geometrias pesadas (α ≥ 15°, h₀ ≥ 1,15 m, b ≥ 0,34 m) reprovam no pilar central montante.
- Varredura das terças: 0,18 × 0,44 passou a ser a menor área; o autor manteve 0,20 × 0,40 (1 % maior). Estudo da distribuição dos painéis refeito (`issues/109-estudo-distribuicao-paineis.py`): 4 + 4 continua adotado.

**Tese**
- Cap. 6: tabela de ações de vento com os valores característicos rotulados, mais a linha de cálculo (1.390 kN). Novo parágrafo com q_v da classe B (0,834, global) × classe A (0,890, fixação) e a cadeia F_w,k → F_w,d → V_Ed → N_Ed (eq. `cadeia-vento-longitudinal`).
- Cap. 5: varredura da diagonal da cobertura (28 → 39 mm), tabela de distribuição dos painéis, terças candidatas e escora central, varredura global (1.110, faixas do bipartido e do CV-V).
- Cap. 7: tabelas de pilares, terças e contraventamentos, texto do CV e síntese (η_max pela macro).
- Cap. 8: tabela de modos (ancoragem L3a e chaveta como frágeis), bases, arrancamento (η da ancoragem EN 1992-4), ancoragem de canto (h_ef 500, c 750, chaveta 260), nó de topo (escoras, tabela, nota sobre o estudo da 104), bipartido, contraventamento (Ø36/Ø45, M39/M48), calha T9 e custo.
- Cap. 9, resumo e abstract: taxas dos contraventamentos e η_max.

**Observação:** as cargas de fundação características (issue 102) dividem a parcela do painel por γ_Q. Agora que ela é de fato de cálculo, essa divisão ficou correta.
