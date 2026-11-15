# 78 — Soldas: especificar e verificar todas (EN 1993-1-8 §4)

- **Tema:** Ligações — aço
- **Prioridade:** P1
- **Normas:** EN 1993-1-8 §4.5 (método direcional ou simplificado), garganta mínima
- **Arquivos:** `connections/` (hoje só a L1 tem solda, como valor “declarado”), `connections/base_pilar.py`, `checks/elu/no_contraventamento.py`, chaveta; `output/desenhos.py`
- **Relaciona:** 69, 73, 87, 91
- **Origem:** 4ª revisão, itens 2.12 e 6.5

## O que fazer
- [ ] Especificar tipo, garganta e comprimento e verificar as soldas de:
  - [ ] chapa embutida × chapa de topo e × sela;
  - [ ] chapa vertical × chapa de base (até 284 kN);
  - [ ] nó de topo (escora, diagonais);
  - [ ] chaveta (164 kN);
  - [ ] novas: ligação topo–pilar (69), enrijecedores da sela (73), pilarete (87).
- [ ] Substituir o valor “declarado” da L1 por verificação.
- [ ] Indicar as soldas em cada desenho (issue 91).

## Resolução ✅ (2026-11-09)
`connections/soldas.py` (`filete`, `gerar_tex`): método simplificado EN 1993-1-8 §4.5.3.3, F_w,Ed = √(f_par² + f_norm²)
com momento fora do plano pelo binário entre cordões (z); garganta = menor da série 4–12 mm com η ≤ 0,90, a ≤ 0,7·t_min
(§4.5.2). Nova verificação “Soldas de filete (todas)” (catálogo) reunindo **todas** as soldas:
- novas: chapa embutida × chapa de topo (L1, a 4, η 0,20) e × sela (L1c, 0,22); L1f (0,14); chapa vertical do pé × chapa de
  topo do pilarete (5 bases, até 0,81); nó de topo × chapa de topo (beiral 0,33 / central 0,49, l = 300 mm); chavetas
  (canto a 8 → 0,72; central montante 0,90; cruz das correntes 0,54; t_chaveta = 30 mm, V a meia altura embutida);
- já existentes, agora no quadro: tubo do pilarete × base/topo, chapa vertical do topo × chapa de topo (69), enrijecedores
  da sela (73), arruela-chapa (80), olhais das diagonais (sob capacidade, 0,80/0,77).
η governante 0,90 (tubo × base L3a); η_max 0,90. A antiga solda “declarada” de chapas_aco (geometria errada, cordões ao
longo da altura) saiu da verificação da chapa da L1. Tese: nova §7.x «SOLDAS» com as duas tabelas geradas
(tese/tab_soldas.tex). Testes `tests/test_issue78_soldas.py` (3) + 1 ajustado. 805 passed.
**Fica para a 91:** indicar tipo/garganta/comprimento nos desenhos.
