# 80 — Furos da chapa de base: tolerância dos chumbadores moldados e espaço para aperto

- **Tema:** Base — chapa de base
- **Prioridade:** P1
- **Normas:** EN 1993-1-8 Tab. 3.3, §6.2.4 (T-stub), EN 1090-2 (tolerâncias de chumbadores)
- **Arquivos:** `connections/base_pilar.py` (`geometria_base`, `tstub_base`, `folga_arruela_pilar_mm`), `output/quadro_espacamentos.py`, desenhos das bases
- **Relaciona:** 74, 79, 87 (o pilarete muda a geometria da base)
- **Origem:** 4ª revisão, item 3.3

## O que fazer
- [ ] Adotar furo ampliado na chapa de base com arruela-chapa soldada na montagem.
- [ ] Reverificar e1/e2 com o furo ampliado e o T-stub (arruela-chapa, l_eff).
- [ ] Confirmar se os 18 mm entre arruela e pilar permitem o aperto com ferramenta (chave de boca /
      soquete para M24) — com o pilarete (87) esse espaço pode deixar de ser problema; reavaliar.

## Resolução ✅ (2026-11-09)
(`connections/base_pilar.py`: `d0_furo_base`, `verificar_arruela_chapa`, `TOL_POSICAO_CHU_MM`)
- **Tolerância** de posição dos chumbadores exigida da fundação: ±6 mm. **Furo alargado Ø36** (= d + 2·6) na chapa
  de base; **arruela-chapa 80 × 80 × 10 S275** com furo normal Ø26, posicionada e **soldada na montagem** (filete 5 mm
  no contorno). Cortante por chumbador (≤ 12 kN, choque) → contato no furo normal + solda: η 0,06.
- **e1/e2 e p com d0 = 36:** 1,2·36 = 43,2 ≤ 60; 2,4·36 = 86 ≤ 400 (quadro de espaçamentos).
- **T-stub:** inalterado — porca sobre a arruela-chapa, apoiada em todo o contorno do furo.
- **Aperto:** com o pilarete (87) o obstáculo é o tubo, não o pilar: eixo do chumbador → face do tubo 130 mm
  (soquete M24 ≈ 30 mm de raio), arruela-chapa → tubo 90 mm. Os 18 mm eram da geometria anterior.
Tese: parágrafo novo em §7.4.x. Testes `tests/test_issue80_furo_base.py` (3). 799 passed. η_max 0,90.
