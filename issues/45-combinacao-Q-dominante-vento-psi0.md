# 45 — Combinação com sobrecarga dominante: vento acompanhante com ψ₀ = 0,6?

- **Tema:** Ações e combinações
- **Prioridade:** P1 (pode faltar uma combinação ELU)
- **Normas:** EN 1990 Tab. A1.1 (ψ₀,W = 0,6; cat. H ψ = 0) e Eq. 6.10; EN 1991-1-1 §3.3.2(1)
- **Arquivos:** `mlc_projeto/core/loads.py` (`ELU_Q` = 1,35G + 1,5Q sem vento; `PSI_0_Q`); `tese/cap06.tex:113-125, 172-205` (§6.2.2, §6.3, l. 178); `tests/test_combinacoes_catH.py`
- **Relaciona:** issue 3 (decisão anterior de não concomitância)

## Origem (3ª revisão do orientador (2026-10))
Confirmar se não deve ser usada a combinação **1,35G + 1,5Q + 1,5×0,6W**. Os ψ nulos da
categoria H eliminam a **sobrecarga como acompanhante**, **mas não o vento**. Se mantida a não
concomitância, a justificativa deve vir de cláusula específica — possivelmente a
**EN 1991-1-1 §3.3.2(1)** — verificada e citada.

## O que fazer
- [ ] Ler EN 1991-1-1 §3.3.2(1) (e notas) no texto normativo e decidir: a cláusula cobre
      vento + sobrecarga de cobertura (cat. H)? (Ela trata de neve/vento com cargas de uso em
      coberturas — confirmar redação exata.)
- [ ] Se **não** cobrir: acrescentar a combinação `ELU_Q_W` = 1,35G + 1,5Q + 0,9W (para os
      padrões de vento pertinentes, k_mod da ação de menor duração) e reprocessar.
- [ ] Se cobrir: citar a cláusula *verbatim* (≤ 15 palavras) na tese §6.3 e no relatório.
- [ ] Atualizar testes de combinações.

## Resolução ✅ (2026-10-06) — mantida a não concomitância, com a cláusula citada

**Cláusula confirmada:** EN 1991-1-1:2002/**AC:2009** §3.3.2(1) — em coberturas, em particular
de categoria H, a sobrecarga não precisa ser combinada com neve nem com vento (a errata
reescreveu o texto original de 2002). Fontes: errata CEN; NSC AD 541
(newsteelconstruction.com). O orientador tem razão quanto ao argumento: ψ0,Q=0 só elimina Q
como **acompanhante**; não elimina W acompanhando Q dominante. A justificativa antiga da tese
(“por serem nulos os ψ da categoria H”) estava errada e foi corrigida.

**Demonstração de que a dispensa não altera o dimensionamento**
- Novo `Carregamentos.combinacao_Q_com_vento_acompanhante()` (loads.py): 1,35G+1,5Q+1,5·0,6·W
  por padrão, com W só se desfavorável. **Os 8 padrões θ=90° são de sucção** (cobertura como
  edificação fechada, §7.2.1) → W favorável → γ=0 (EN 1990 Tab. A1.2(B)) → M = 504,3 kN·m =
  ELU_Q. Impresso na Fase 1 do pipeline; guardado em `meta["combinacao_Q_W"]`.
- A omissão é **conservadora**: ELU_Q é de duração média (k_mod 0,65); com o vento passaria a
  curta (k_mod 0,70 em CS3), EC5 §3.1.3.
- Pilares: as verificações já somam a máxima reação gravítica (ELU_Q) ao vento integral
  (1,5W) — envoltória que cobre 0,9W.

**Arquivos:** `core/loads.py` (método + comentário ψ), `main.py` (print + meta), `output/report.py`
(nota de concomitância reescrita, com os números), `tests/test_combinacoes_catH.py` (+2: dispensa
não altera a viga; padrão de pressão fictício passa a governar — guarda de regressão),
`tese/cap06.tex` (§6.2.2 e §6.3 + Eq. da combinação omitida), `tese/referencias.bib` (nota AC:2009).
Suíte 665 passed; pipeline APROVADO.

**Atualização (issue 39, 2026-10-06):** com os padrões α = 90° da Tab. 10, a faixa b3 com c_pi −0,3
é de pressão leve (C_net = +0,1). Q+0,6W passa a dar M = 526,4 kN·m (+4,4 %), mas com k_mod 0,70
(curta) contra 0,65 (média) a utilização relativa é 0,97 < 1: a dispensa continua conservadora.
O método recebe `mat` e compara M/k_mod; teste ajustado.
