# 86 — Proteção contra corrosão de todas as peças de aço (EC5 §4.2, Tab. 4.1, CS3)

- **Tema:** Durabilidade — aço
- **Prioridade:** P1
- **Normas:** EN 1995-1-1 §4.2 Tab. 4.1 (CS3), EN ISO 1461 (galvanização a fogo), EN ISO 12944 (categoria de corrosividade)
- **Arquivos:** `tese/cap04.tex` (materiais), `tese/cap08.tex` §7.8, desenhos (issue 91)
- **Origem:** 4ª revisão, itens 4.6 e 6.5

## O que fazer
- [x] Especificar a proteção de chapas, pinos, cavilhas, parafusos autoatarraxantes, chumbadores,
      diagonais, olhais, manilhas e pilarete para CS3 (ex.: galvanização a fogo com espessura
      mínima; inox para parafusos ≤ 4 mm de Tab. 4.1, se aplicável).
- [x] Mencionar que aço sem proteção mancha a madeira exposta.
- [x] Indicar a proteção nos desenhos.

## Resolução ✅

- **Nova seção** `sec:protecao-corrosao` (cap08, antes da fundação) com a
  `tab:protecao-corrosao` por componente. Base: EC5 §4.2 Tab. 4.1 (CS3: Fe/Zn 25c
  mínimo para d > 4 mm e chapas > 5 mm) + nota b (cobre do CCA/CCB e zona de
  respingo pedem margem).
- **Categoria** C3 (EN ISO 12944-2), com ressalva para litoral/industrial (C4/C5).
- **Especificação:**
  - Chapas: galvanização a fogo EN ISO 1461 após corte/furo/solda (85 µm méd., 70 µm local, t > 6 mm).
  - Pinos/cavilhas: galvanizados.
  - M24 8.8 e chumbadores: EN ISO 10684, centrifugados, porca sobredimensionada.
  - Barras das diagonais: EN ISO 10684. Manilhas: galvanizadas de fábrica.
  - Autoatarraxantes Ø8: Fe/Zn 25c conforme ETA. O inox exigiria reverificar a ligação.
  - Bases (chapa, pilarete, chaveta, arruela-chapa, chumbador exposto): dúplex EN ISO 12944-5.
- **Durabilidade:** zinco C3 0,7–2,1 µm/a (EN ISO 14713-1) → ≥ 40 anos nas chapas, ≥ 26 nas roscas.
- **Pilarete:** 4 furos de respiro Ø16 (EN ISO 14713-2); nova verificação
  `secao_liquida_respiro` (0,9·A_net·f_u/γM2 + M/(r·M_pl), linear). Governa o tubo
  (até 0,63); o tubo não muda.
- **Solda de obra da arruela-chapa:** remoção do zinco + reparo com tinta rica em zinco (EN ISO 1461 §6.3).
- **Manchas na madeira:** ferrugem escorrida e limalha (ferro × extrativos); proibido furar aço sobre a madeira.
- **Desenhos:** `Folha.NOTA_CORROSAO` em DES-05 a DES-09. Rodapé 15 → 19 mm e até 7
  linhas de nota; a nota do DES-06 já era truncada antes.
- **cap04:** linha "Proteção do aço" na tabela de materiais e remissão.
- **Bib:** EN ISO 1461, 10684, 12944-2, 12944-5, 14713-1, 14713-2.
- **Testes:** `tests/test_issue86_corrosao.py`. 808 passed. Tese 141 p., 0 overfull.
- **Pendente:** custo do aço não inclui galvanização/dúplex explicitamente (issue 99).
