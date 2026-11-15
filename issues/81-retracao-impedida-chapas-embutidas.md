# 81 — Retração impedida pelas chapas embutidas: ovalizar furos ⊥ às fibras ou dividir a chapa

- **Tema:** Durabilidade — ligações
- **Prioridade:** P1
- **Normas:** EN 1995-1-1 §8 (comentário), Dietsch & Winter (2018) — fissuração por retração impedida; retração ⊥ da MLC
- **Arquivos:** `checks/elu/no_contraventamento.py` (escoras), `connections/terca_viga.py` (montante), `connections/base_pilar.py` (pé), `output/desenhos.py`, `tese/cap08.tex`
- **Relaciona:** 69 (adotar o critério desde a concepção), 76
- **Origem:** 4ª revisão, item 4.1

## Problema
Chapa rígida ligando cavilhas afastadas ⊥ às fibras impede a retração e provoca fissuras ao longo
das fibras. Distâncias entre cavilhas extremas ⊥ às fibras: 420 mm (escora central), 300 mm
(escora de beiral), 240 mm (montante terça–viga), 120 mm (pé dos pilares).

## O que fazer
- [ ] Estimar a variação dimensional ⊥ para a faixa de umidade esperada (CS3) em cada distância.
- [ ] Escoras e montante: ovalizar os furos da chapa ⊥ às fibras (força // às fibras → resistência
      mantida) com curso cotado, ou dividir a chapa.
- [ ] Pé dos pilares (120 mm): justificar a distância ou separar o caminho do cortante do impacto
      para poder ovalizar.
- [ ] Registrar o critério no texto (concepção) e nos desenhos.

## Resolução ✅ (2026-11-07)
**Critério** (`connections/retracao.py`): δ = α⊥·Δu·D⊥/2 na cavilha extrema (Δu = 6 pontos, faixa da issue 72).
A folga do furo na chapa (d0 − d = 2 mm, issue 79) absorve ±1 mm → **D⊥,max = 133 mm** (3 fileiras de Ø20 a 60).
- Acima disso, força // fibras (escoras, montante): **furos ovalizados ⊥ fibras**, curso ±⌈(δ + 1)/0,90⌉; aço em
  furo ovalizado ⊥ à força a 0,6·F_b,Rd (EN 1993-1-8 Tab. 3.4), folgado com t = d; ligamento ≥ 1,2·d0.
- Pé dos pilares (cortante do choque cruza as cavilhas ⊥): não ovalizável → **malha limitada a 3 fileiras**
  (`dimensionar_ligacao_axial_escora(n_vert_limite)`, n_horiz até 12); o grupo cresce ao longo das fibras.

**Resultado** (malhas atuais; diferentes das 420/300/240/120 citadas pelo orientador, de versão anterior):
escora de beiral 120 mm → redondo (η 0,90); escora central 240 → ovalizado ±4 mm; montante 180 → ovalizado ±3 mm;
L1f 270 → já ovalizado ±20 mm (flecha); pé L3 60 / L3c, L3f, L3a 120 → redondo. Pé da L3a canto 4×6 → **3×9 =
27 cavilhas**, 940 mm (η 0,69). Nova verificação “Retração impedida (chapas)” η 0,90. η_max 0,90. 68
verificações. Testes `tests/test_issue81_retracao.py` (4). 781 passed.

**Tese:** nova §7.8.x «Retração impedida pelas chapas embutidas» com tabela; tabela das bases (canto 27 cav.).

**Achado para a issue 69/91:** a viga sobe em relação ao pilar até ~12 mm sob arrancamento (issue 72) e o
extradorso desloca-se α⊥·Δu·h0 ≈ 15 mm com a umidade — o nó de topo, que liga a escora (sobre a viga) ao topo do
pilar, precisa acomodar esse movimento vertical relativo.
