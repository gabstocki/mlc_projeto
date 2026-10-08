# 44 — Diagonais: dimensionamento por capacidade (rosca rompe antes de escoar) e critério uniforme

- **Tema:** Contraventamento — aço
- **Prioridade:** P1 (argumento de ductilidade do §8.5.1 não se verifica; critérios incoerentes)
- **Normas:** EN 1993-1-8 Tab. 3.4 (F_t,Rd = 0,9·f_ub·A_s/γ_M2); EN 1993-1-1 §6.2.3 (N_pl,Rd = A·f_y/γ_M0; N_u,Rd); EN 1998-1 §6.7.3 (referência de capacity design, se útil)
- **Arquivos:** `mlc_projeto/checks/elu/contraventamento_vertical.py:73-90` (PASSO_ROSCA, área da rosca); `mlc_projeto/checks/elu/contraventamento.py` (cobertura Ø28 — seção bruta); `mlc_projeto/checks/elu/contraventamento_transversal.py` (frontões); `tese/cap08.tex:259-304` (§8.5.1, l. 265 “dúctil e avisa”)
- **Relaciona:** issues 14, 31, 41

## Origem (3ª revisão do orientador (2026-10))
N_t,Rd = 211,7 kN corresponde à ruptura na rosca (0,9·f_u·A_s/γ_M2, A_s = 817 mm² para M36) e é
**inferior** ao escoamento da seção bruta (A·f_y ≈ 239 kN). A barra **rompe na rosca antes de
escoar** → o argumento “o escoamento se dá na barra, que é dúctil e avisa” não vale. Só
valeria com **rosca sobre extremidade recalcada** (resistência da rosca > escoamento do fuste).
Além disso há **incoerência de critério**: diagonais da cobertura (Ø28) pela seção bruta;
verticais e frontões pela área da rosca.

## O que fazer
- [ ] Uniformizar: todas as diagonais verificadas por `min(N_pl,Rd bruta; F_t,Rd rosca)`.
- [ ] Decidir: (a) especificar **extremidade recalcada** (upset) e verificar
      F_t,Rd,rosca ≥ γ_ov·N_pl,Rd da barra (hierarquia), mantendo o argumento de ductilidade; ou
      (b) retirar o argumento de ductilidade e tratar a rosca como modo governante (frágil).
- [ ] Hierarquia também com ligações de extremidade (olhal/gousset/solda ≥ capacidade da barra).
- [ ] Reescrever §8.5.1; atualizar testes e re-dimensionar se necessário.

## Resolução ✅ (2026-10-06) — extremidades recalcadas (decisão do usuário)

**Critério único** para todas as diagonais (cobertura, verticais, frontões):
`N_t,Rd = min(N_pl,Rd = A·f_y/γM0 ; N_u,Rd = 0,9·A_s·f_u/γM2)` (EN 1993-1-1 §6.2.3(2) +
EN 1993-1-8 Tab. 3.4), com **rosca em extremidade recalcada** escolhida como a menor métrica
que cumpre §6.2.3(3) (N_u,Rd ≥ N_pl,Rd ⇔ A_s ≥ 0,907·A em S235) → governa o escoamento
(dúctil) e o argumento do §8.5.1 passa a valer.

**Código**
- `contraventamento_vertical.py`: `EXTREMIDADE_RECALCADA=True`, `rosca_recalcada_minima()`,
  `resistencia_tracao_diagonal(d, aco, recalcada=None)` (devolve d_rosca, ductil); roscas M68–M80
  acrescentadas (ISO 261); resultados publicam N_pl/N_u/d_rosca/ductil.
- `contraventamento.py` (cobertura): `verificar_diagonal_aco` passa a usar a mesma função
  (antes só seção bruta). Ø28 → rosca M30 (Ø28 não tem rosca grossa padrão).
- `main.py`: prints com a rosca; `report.py`: legenda de N_t,Rd.
- Testes F-11 reescritos para fixar o caso **rosca cortada** (`recalcada=False`, frágil: M36
  211,7 < 239,2 kN) + novos (rosca mínima, critério único na cobertura). Suíte 686 passed.

**Consequência (seleção automática η ≤ 0,90 — regra do projeto):**
| Diagonal | antes | depois | rosca | η |
|---|---|---|---|---|
| Vertical (fachadas e central) | Ø36 | **Ø33** | M36 | 0,835 (**governa**, η_max) |
| Frontão | Ø27 | **Ø24** | M27 | 0,824 |
| Cobertura | Ø28 | Ø28 | M30 | 0,790 |
Ligações de extremidade (por capacidade = N_pl): 0,811 / 0,809. α_cr transversal 20,88 → 16,50
(≥ 10); estab. global η 0,606. Aço: vertical 1.158 → 973 kg, transversal 163 → 129 kg; custo
R$ 2.786.419 → R$ 2.780.898.

**Tese:** §8.5 (parágrafo + Eq. da rosca recalcada; §8.5.1 sem “dúctil e avisa” incorreto;
tabela das ligações), §7.5, §6.5 (α_cr), §5.5.2, quantidades e custos, §9.

**Nota:** não se aplicou sobre-resistência do aço (γ_ov) na hierarquia — não exigida fora de
projeto sísmico; a manilha/rosca de catálogo deve resistir ≥ N_pl da barra (201,0 / 106,3 kN).
