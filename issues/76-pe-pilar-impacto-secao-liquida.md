# 76 — Pé do pilar: seção líquida, F90,Rd sob impacto, direção do choque e a4,t

- **Tema:** Base — pé do pilar
- **Prioridade:** P0
- **Normas:** EC5 §6.1.2 (seção líquida), §8.1.4 (F90,Rd), Tab. 8.5 (a4,t = max[(2+2 sen α)d; 3d] = 4d = 80 mm para Ø20 a 90°)
- **Arquivos:** `connections/base_pilar.py`, `output/quadro_espacamentos.py` (`_cavilhas_axiais` só lista a4,c), `tese/cap08.tex` §7.4, Tabela 35
- **Relaciona:** 74, 81, 87 (o pilarete muda a altura do impacto e o detalhe do pé)
- **Origem:** 4ª revisão, itens 2.10 e 3.1

## O que fazer
- [ ] Verificar a seção líquida do pilar à tração (§6.1.2), descontando o rasgo e os furos.
- [ ] Apresentar F90,Rd (§8.1.4) para o cortante do impacto de 46,4 kN.
- [ ] Declarar a direção do choque em relação ao plano da chapa vertical; força ⊥ ao plano da chapa
      não é resistida pelas cavilhas em corte — definir o caminho dela (ou orientar a chapa / prever
      dois planos).
- [ ] Sob o impacto a borda passa a ser carregada: a4,t ≥ 80 mm. L3, L3c e L3a central têm 75 mm →
      corrigir a geometria e incluir a4,t na Tabela 35 / quadro de espaçamentos.

## Resolução ✅ (2026-11-07)
(`connections/base_pilar.py`, `connections/retracao.n_perp_max_borda_carregada`)
- **a4,t:** o choque (⊥ às fibras, direção qualquer) torna as duas faces bordas carregadas → a4,t = 4d = 80 mm.
  Com 3 fileiras no pilar de 270 mm, a4 = 75 < 80 (não atendia). Malha limitada a **2 fileiras ⊥** no pilar de
  270 mm (a4 = 105 mm) e a 3 no de 320 (pela retração, 3) — no pé e no topo. Grupos alongam: L3c 14 cav (2×7),
  L3a 26 (2×13, 1,34 m). Quadro de espaçamentos com a linha a4,t; tabela pé/topo dividida em duas (altura da página).
- **F90,Rd (§8.1.4)** sob 48,5 kN, grupo centrado: h_e = 165 mm, k_mod 0,90 (instantânea CS3), **γ_M = 1,0
  (acidental, EC5 Tab. 2.3)** → F90,Rd = 83 kN, η 0,58 (canto 0,56).
- **Seção líquida (§6.1.2):** A_net = b·h − t_r·w_rasgo − n_⊥·d·(b − t_r); σ_t ≤ 4,5 MPa, η ≤ 0,45.
- **Direção do choque:** componente no plano da chapa → cavilhas ao corte (⊥) + F90; componente ⊥ ao plano →
  vencida a folga de 2 mm do rasgo, faces da chapa contra as paredes do rasgo, σ_c,90 ≤ 0,59 MPa, η ≤ 0,26. O
  pilarete circular (issue 87) é isotrópico.
- **L3a sob choque (pendência da 87):** binário do pilarete ≈ 73 kN equivalentes ≪ 327 kN persistentes — declarado.

η_max 0,90 inalterado. Testes `tests/test_issue76_pe_impacto.py` (6). 793 passed. Tese: §7.4.x com o parágrafo do
choque (a4,t, F90, fora do plano, seção líquida), tabelas das bases, do topo e da retração atualizadas.
