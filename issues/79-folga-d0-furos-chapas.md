# 79 — Diâmetro dos furos nas chapas (d0 com folga) e recálculo dos mínimos

- **Tema:** Ligações — chapas
- **Prioridade:** P0 (e4 da L1/L1c deixa de atender)
- **Normas:** EN 1993-1-8 Tab. 3.3 (e1, e2, e3, e4, p1, p2 em função de d0), EN 1090-2 (folgas nominais)
- **Arquivos:** `output/quadro_espacamentos.py` (`d0 = d  # cavilha ajustada`), `connections/*.py`, `main.py` (altura do esquadro), Tabela 36
- **Relaciona:** 71, 72, 80, 90
- **Origem:** 4ª revisão, item 3.2

## Problema
Os mínimos da Tabela 36 foram calculados com d0 = d (sem folga). Com d0 = 25–26 mm para Ø24,
o e4 = 36 mm da L1/L1c fica abaixo de 1,5 d0 (37,5–39 mm).

## O que fazer
- [ ] Definir a folga dos furos por tipo de conector (cavilha na chapa, parafuso, chumbador) e
      declará-la (EN 1090-2 / prática).
- [ ] Propagar d0 a todos os cálculos de chapa (e, p, seção líquida, esmagamento) e ao quadro.
- [ ] Recalcular a geometria das chapas (L1/L1c 974 mm muda; coordenar com 71/72).

## Resolução ✅ (2026-11-07)
**Critério:** furo redondo normal na chapa, d0 = d + Δ, Δ da EN 1090-2:2018 Tab. 11 — 1 mm até
Ø14, 2 mm de Ø16 a Ø24, 3 mm a partir de Ø27 (atende o limite max(2; 0,1d) do EC5 §10.4.3). Na
madeira o furo continua ajustado. Nos oblongos, d0 é a largura do rasgo. Fonte única:
`connections/chapas_aco.py` → `folga_furo_mm`, `d0_furo`.

**Propagado a:** `verificar_chapas_aco` e `espessura_chapa_embutida` (α_b, k1, seção líquida),
altura/largura do esquadro L1/L1c (`main.py`), detalhe L1f (`desenhos.detalhe_topo_pf` agora
publica `d0_mm` e `H_chapa_mm`, usados no DES-08 e no quadro), quadro de espaçamentos (L1, L1c,
L1f, e2 da chapa vertical do pé, chapa de base) e furação das bases.

**Resultados:** chapa L1/L1c 974 → **977 mm** (e4 = 1,5·26 = 39 mm); L1f p1 req. 88,4 ≤ 90;
e2 do pé 26,4 ≤ 45; nenhum η muda (chapa L1 η 0,10); APROVADO, η_max 0,85. Quadro sem “(!)”.
Escoras, montante e pé: distâncias na chapa ficam muito acima dos mínimos do aço (as da madeira
governam: a3,t ≥ 7d = 140 mm × e1 ≥ 1,2·d0 = 26,4 mm).

**Tese:** §7.2.3 declara d0 = 26 mm (texto + linha na tabela do arranjo); §7.7 declara o critério
e a altura 977 mm (sem narrativa de correção); referência EN 1090-2:2018 adicionada.
Testes: `tests/test_issue79_d0.py` (16); `test_chapas_aco.py` ajustado. 752 passed.

**Fica para:** furo ampliado da chapa de base (issue 80); curso do oblongo abaixo do pino (72)
e altura do rasgo (71) — ambos mexem de novo na altura da chapa.
