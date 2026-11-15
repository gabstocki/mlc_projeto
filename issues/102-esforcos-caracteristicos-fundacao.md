# 102 — Esforços característicos entregues à fundação (Tabela 37)

- **Tema:** Coerência — delimitação × entrega
- **Prioridade:** P1
- **Arquivos:** gerador da tabela de esforços na fundação, `tese/cap08.tex` §7.9 (Tabela 37), `tese/cap01.tex` §1.4
- **Origem:** 4ª revisão, item 10.4

## O que fazer
- [ ] O §1.4 promete “os esforços característicos e de cálculo em cada base”, mas a Tabela 37 traz só
      os de cálculo. Incluir os característicos por ação (G, Q, W por padrão, impacto) por base — o
      projeto geotécnico precisa deles —, ou corrigir o texto. (Preferência: incluir.)

## Resolução ✅ (2026-11-09) — incluídos os característicos (o texto do §1.4 passa a ser verdadeiro)
`output/cargas_fundacao.py`: `esforcos_caracteristicos` + `gerar_tex_caracteristicos` → **tese/tab_cargas_fundacao_k.tex**
(gerada pelo pipeline): por base (extremidade, central, central montante, canto, PF) e por ação —
G_k (reação da viga com beiral + peso do pilar), Q_k, W_k (maior compressão e maior arrancamento entre os padrões
de Cpe + horizontal), A_d (choque, 48,5 kN). Parcela dos painéis de contraventamento em W_k = cálculo/γ_Q
(inclui a pequena força de imperfeição gravitacional — a favor da segurança). Conferência: extremidade
1,5·96,8 − 0,9·52,0 = 98,4 ≈ 98,3 kN de cálculo.
Também a tabela de **cálculo** passou a ser gerada (`gerar_tex_calculo` → tese/tab_cargas_fundacao.tex), com os
valores atuais (antes digitada, com valores antigos). Totais horizontais: 943 kN longitudinal, 69,8 kN por frontão.
`verificar_refs.py` passa a ler também tese/tab_*.tex. 802 passed.

Obs. para a 99: a compilação emite “There were undefined references” genérico (sem rótulo identificado), já presente
antes desta issue.
