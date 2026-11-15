# 117 — Quantitativo por lista explícita de peças (terças, espaçadores)

- **Tema:** Quantidades e custo
- **Prioridade:** P2 (afeta também g_terças)
- **Origem:** Revisão técnica (comentários tipo banca), 2026-11-14, item 9

## Diagnóstico — CONFIRMADO
- Terças: 19 linhas (T0–T18) × 48,32 m × 0,20 × 0,40 = 73,4 m³. O `custo.py` dá 65,4 m³ (g_terças·área/γ, que supõe o espaçamento 2,53 m uniforme até os beirais). Diferença ~12 %.
- A mesma aproximação subestima g_terças (0,130 kN/m²) no peso próprio.
- Os espaçadores dos bipartidos (~4,1 m³ nos 14 pilares, segundo a lista da Fig. 20) não entram.

## O que fazer
- [x] `custo.py`: volume por lista de peças (vigas, terças por linha e comprimento, pilares, lâminas, espaçadores, escoras).
- [x] g_terças pela mesma contagem (verificar o efeito no peso próprio).
- [x] Texto §7.10.1.

## Resolução (2026-11-15) ✅
- Volume por lista (`custo.volume_tercas_m3`, `volume_espacadores_m3`): terças 19 linhas × 48,3 m + escoras = 73,8 m³ (era 65,4); espaçadores 4,11 m³; MLC 324 m³.
- Terças como linhas de carga no modelo da viga (`analisar_biarticulada(P_terca_kN, s_terca_m)`): M do vão igual ao uniforme (8·s·P); +0,5·P na reação A e terça de ponta como força no beiral. R_d 103,9 → 106,7 kN; M 505,7 → 504,5 kN·m; R_up,k 48,7 → 46,6 kN. `reacao_arrancamento_max` passa a usar fator_G.
- Tese: cap. 6 (parágrafo novo; M 505, R 107, V 95,0, N 8,37, α_cr 161/14,7, δ 17,4), cap. 5/7/8/9 e resumo (sela 0,58, apoio 0,49, pilar central 0,42, canto 0,89, estabilidade 0,69). Testes: `tests/test_issue117_quantitativo_tercas.py`.
- **Varredura final (após 111, 112, 115, 116 e 117):** 1.111 de 3.213 aprovadas (antes 1.114). As 3 a mais reprovadas são do pilar central montante (b = 0,36, α ≥ 15°, h₀ ≥ 1,15). Margem 0,50 da fronteira passa a b = 0,36 m (era 0,34). Cap. 5 atualizado (contagens, alínea do montante, faixa do diafragma 0,67–0,75, b = 0,30 com 0,73 nos modos frágeis da L1, taxa da viga 0,98 → 0,53 → 0,56). Tese: 178 p., 0 overfull, 0 indefinidas; 897 testes.
