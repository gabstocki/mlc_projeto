# 70 — Rasgo da chapa embutida reduz a largura de apoio e de cisalhamento (b − t_rasgo)

- **Tema:** Viga — apoio
- **Prioridade:** P1 (muda η)
- **Normas:** EC5 §6.1.5 (Eq. 6.3 / “eq. 7.1” do texto), §6.1.7
- **Arquivos:** verificação de compressão ⊥ no apoio (L1 e sela L1c) e cisalhamento no apoio; `tese/cap08.tex` §7.2.2
- **Origem:** 4ª revisão, item 2.2

## Problema
O rasgo para a chapa embutida retira t_rasgo da largura b = 320 mm na região do apoio. A
compressão perpendicular e o cisalhamento no apoio estão calculados com b inteira.

## O que fazer
- [ ] Definir t_rasgo (espessura da chapa + folga de montagem) — coerente com a issue 79.
- [ ] Recalcular compressão ⊥ (L1 e L1c) com b_ef = b − t_rasgo (orientador estima η ≈ 0,50).
- [ ] Recalcular cisalhamento no apoio com b_ef = b − t_rasgo (estimativa η ≈ 0,42), atenção a k_cr.
- [ ] Atualizar texto, tabelas e Apêndice B.

## Resolução ✅ (2026-11-07)
**Rasgo:** t_r = t_chapa + 2 × 2 mm = 25 + 4 = **29 mm** (`FOLGA_RASGO_MM = 2`; chapa t ≥ d na série
comercial, conferida contra o esquadro — erro se a chapa adotada não couber no rasgo previsto).

**Código:** `verifica_apoio_contato(t_rasgo_m=)` → σ = R/((b − t_r)·l_ef); `verifica_cisalhamento(t_rasgo_m=)`
→ b_ef = k_cr·(b − t_r). Também corrigido com o beiral (issue 82): na L1 a viga continua além do apoio, então
l_ef = l + 30 + 30 mm (EC5 §6.1.5) = 0,33 m (antes 0,30).

**Resultados:** compressão ⊥ L1 0,46 → **0,49** (sem k_c,90 0,85); L1c (sela) 0,52 → **0,58**; cisalhamento
0,37 → **0,41** (estimativas do orientador: ~0,50 e ~0,42); sela 0,79 → 0,87 (t_req 14,9 mm, adota 16 —
enrijecedores na issue 73). η_max 0,90 inalterado. Teste `test_apoio_contato` ajustado. 773 passed.

**Tese:** §7.2.2 reescrita (Eq. com b − t_r e l_ef 0,33; sela “projeta-se em balanço”/“não tem balanço” —
item 7.2 da issue 94; sem a narrativa do 0,27 — item 7.1 da issue 92); §6.2 cisalhamento com as duas reduções;
tabela da viga; símbolo t_r na lista.
