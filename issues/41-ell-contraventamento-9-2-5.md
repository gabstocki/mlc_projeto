# 41 — ℓ do EC5 §9.2.5 é o vão do sistema de contraventamento (20,25 m), não 46,0 m

- **Tema:** Estabilidade / Contraventamento da cobertura
- **Prioridade:** P1 (altera k_ℓ de 0,57 para 0,86 → altera a força de estabilização e o dimensionamento das diagonais)
- **Normas:** EN 1995-1-1 §9.2.5.3 (Eq. 9.37, Fig. 9.9), §6.3.3 (l_ef da LTB)
- **Arquivos:** `mlc_projeto/checks/elu/contraventamento.py:100-114` (`ell_m` = L_comp / docstring “aumentar baías agrava”); `mlc_projeto/main.py:240-255` (comentários “ℓ = 46 m”, “l_1 saltava para ℓ=46 m”); `mlc_projeto/output/report.py:1567`; `tese/cap03.tex:159` (§3.5 “efeito contraintuitivo”); `tese/cap05.tex:184-215` (§5.5.1, “salta … para 46,0 m”, “aspecto contraintuitivo”); `tese/cap07.tex:71` (§7.2)
- **Relaciona:** issue 15; flambagem lateral (issue 11, nova 47)

## Origem (3ª revisão do orientador (2026-10))
Na EN 1995-1-1, **ℓ é o vão do sistema de contraventamento**, paralelo às vigas: **20,25 m**
(não o comprimento da edificação 46,0 m). Logo `k_ℓ = min(1; √(15/ℓ))` passa de **0,57 → 0,86**.
Pelo mesmo motivo é incorreto dizer (§5.5.1, §7.2) que, sem contraventamento, o comprimento
efetivo de flambagem lateral “salta para 46,0 m” — ele passa a ser referido ao **vão da própria
viga**. Também não se sustenta o “efeito contraintuitivo” (§3.5, §5.5.1): mais baías
contraventadas reduzem o número **n** de elementos estabilizados por sistema, mas **não alteram ℓ**.

## O que fazer
- [ ] Corrigir `ell_m` para o vão do sistema (= vão da viga, 20,25 m), independente de
      `n_modulos_cv`; `n_modulos_cv` passa a atuar só em **n** (vigas por sistema).
- [ ] Recalcular k_ℓ, F_d / q_d de estabilização, diagonais (Ø28) e restrição das terças;
      rever se o diâmetro ainda atende e atualizar a varredura de comentários do `main.py`.
- [ ] Corrigir o l_ef da LTB “sem contraventamento” (referido ao vão da viga, não 46 m).
- [ ] Reescrever §3.5, §5.5.1 e §7.2 (remover o “efeito contraintuitivo” e o “salta para 46,0 m”).
- [ ] Atualizar testes de contraventamento (valores de k_ℓ e forças).

## Critério de aceite
k_ℓ = 0,86 no relatório; texto coerente; suíte de testes verde; pipeline reexecutado.

## Resolução ✅ (2026-10-06)

**Código** — `mlc_projeto/checks/elu/contraventamento.py`
- `LayoutContraventamento.ell_m` = `L_vao` (vão da viga, 20,25 m), independente de
  `L_comp` e de `n_modulos_cv`. Novo `n_por_sistema = ⌈n_vigas_por_linha / n_modulos_cv⌉`
  (= ⌈9/2⌉ = 5): é só aqui que o nº de baías entra.
- Modelo de treliça (EC5 Fig. 9.10): banzos = 2 vigas da baía, montantes = terças,
  diagonais = cruzes em **todos os 8 painéis do vão** (antes só 2 painéis junto aos
  apoios → mecanismo). Diagonal crítica = painel extremo, cortante
  `V = máx(q_d·ℓ/2; F_vento0,baía/2)`.
- Flecha da treliça: `δ = q·ℓ²/(8·C_h·s) + 5qℓ⁴/(384·EI_eq)` (antes `R/K_baía`).
- `l_1` penalizado (cobertura falha) = vão da viga, não 46 m.
- `main.py`: comentários/print corrigidos; coerência com o contraventamento vertical
  passa a usar a força total coletada (`F_cobertura_total_kN`).
- `report.py`: tabela §9.1 (n por sistema, ℓ = vão da viga), nota sem “efeito contraintuitivo”.
- Testes: `tests/test_contraventamento_cobertura.py` (11; novos: ℓ independe de
  L_comp/n_cv, mais baías ⇒ menor n e menor força, n por sistema, flecha da treliça,
  l_1 penalizado = vão). Suíte: 656 passed. Pipeline APROVADO.

**Resultados** (pipeline): k_ℓ 0,57 → **0,861**; n 9 → **5**; a diagonal continua governada
pelo **vento θ=0°** (R por apoio 104,7 kN ≫ estabilização 1,4 kN) → **η_diag = 0,79
inalterado** (Ø28); η_δ 0,13 → 0,30; aço da cobertura **486 → 1.943 kg** (64 barras).
Com l_1 = 20,25 m a LTB daria η = 0,20 — não governaria.

**Tese**: §3.5 (cap03), §5.5.1 (cap05: ℓ, treliça, n=5, “contraintuitivo” substituído pelo
mecanismo real), §7.2 e §7.5 (cap07), §8.5 e §8.7 (cap08: massa, quantidades, custo
R$ 2.749.687 → R$ 2.786.419, R$ 1.496/m²). Compila sem erros.

**Desdobramentos:** [64](64-caminho-longitudinal-linha-central.md) (reação da treliça na
linha central sem contraventamento vertical — P0/P1) e
[65](65-qd-mais-vento-9-2-5-3.md) (q_d “além” do vento externo).
