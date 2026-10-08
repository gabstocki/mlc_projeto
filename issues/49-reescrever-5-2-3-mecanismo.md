# 49 — Reescrever §5.2.3: mecanismo real da variação das taxas na varredura

- **Tema:** Pré-dimensionamento — texto
- **Prioridade:** P2
- **Arquivos:** `tese/cap05.tex:95-122` (§5.2.3 “O que governa”, l. 113 “centro de pressões”); `mlc_projeto/` (varredura; vínculo largura do pilar = b da viga; auto-dimensionamento da diagonal η ≤ 0,90)
- **Relaciona:** —

## Origem (3ª revisão do orientador (2026-10))
“Reduzir a seção da viga eleva a altura relativa do centro de pressões” não tem fundamento.
O aumento da taxa no **pilar de canto** decorre de a **largura do pilar estar vinculada à
largura b da viga**. A variação no **contraventamento vertical** provavelmente decorre do
**dimensionamento automático da diagonal para η ≤ 0,90**.

## O que fazer
- [ ] Confirmar no código os dois mecanismos (vínculo b_pilar = b_viga; laço de escolha de Ø).
- [ ] Reescrever §5.2.3 com o mecanismo identificado (se útil, gráfico η × b da varredura).

## Resolução ✅ (2026-10-06)

Mecanismos confirmados nos dados da varredura que gerou a Tabela (`output/varredura_global_consolidada.csv`,
1.391 geometrias, 1.104 aprovadas) e no código (`predim/varredura_global.py`):

1. **Pilar de canto** — `_ATRIBUTOS_LIGADOS_A_B = ("B_PILAR", "B_PILAR_C", "B_PILAR_CANTO")`: a largura
   dos pilares acompanha b. O download dos painéis independe de b; reduzir b reduz a área e aumenta a
   esbeltez no eixo fraco. η médio: 0,858 (b = 0,24) → 0,588 (0,28) → 0,431 (0,32); com b fixo,
   desvio-padrão 0,027 em h₀ e α.
2. **Contraventamento vertical** — diâmetro auto-dimensionado ao menor comercial com η ≤ 0,90:
   dente de serra. Ex.: b = 0,24, h₀ = 0,80: η 0,894 → 0,899 (α 6,5° → 7,5°) e cai para 0,765 em
   α = 8,0° (troca de diâmetro). Em todas as aprovadas, 0,76 ≤ η ≤ 0,90.

A explicação anterior (“reduzir a seção eleva a altura relativa do centro de pressões”) foi removida.

**Tese:** §5.2.3 — segunda constatação reescrita (dois parágrafos, com os números).

**Observação:** a varredura (Tabela da fronteira de volume e figura) é anterior às correções das
issues 41/44/46/64/42 etc.; os mecanismos não mudam, mas os valores absolutos sim. Regenerá-la
custa ~1 h de pipeline (1.391 pontos) — fica a critério.
