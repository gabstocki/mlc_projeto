# 74 — Chumbadores: corrigir “soldada a chumbadores 8.8” e cortante com braço de alavanca

- **Tema:** Base — ancoragem
- **Prioridade:** P1
- **Normas:** EN 1993-1-8 (aço 8.8 não soldável), EN 1992-4 §6.2.2.3 / §7.2.2.3 (cortante com braço de alavanca — stand-off com graute/porca de nivelamento)
- **Arquivos:** `tese/cap08.tex` §7.4; `mlc_projeto/connections/base_pilar.py` / ancoragem
- **Relaciona:** 76 (impacto), 80 (furo ampliado), 87 (pilarete)
- **Origem:** 4ª revisão, item 2.6

## O que fazer
- [ ] Corrigir no §7.4 a expressão “chapa soldada a chumbadores classe 8.8”: a ligação é por porca e arruela (como no desenho).
- [ ] Declarar se há porca de nivelamento e graute; se houver, verificar o cortante do impacto nos
      chumbadores **com braço de alavanca** (EN 1992-4) — ou justificar a transmissão do cortante
      pela chaveta/atrito com graute.

## Resolução ✅ (2026-11-09) — chaveta cruciforme nas bases correntes (decisão do autor)
- **Texto (§7.4):** “chapa soldada a chumbadores 8.8” → chapa fixada por porca sobre arruela-chapa (8.8 não soldável),
  nivelada por porcas de nivelamento e assente sobre graute.
- **Braço de alavanca (EN 1992-4 §6.2.2.3, lida no PDF do projeto):** com graute > d/2 = 12 mm, cortante nos
  chumbadores agiria com l_a = 0,5d + e1 ≈ 60 mm; M24 8.8 sob o choque (12,1 kN/chumbador): η 0,56 com α_M = 2 e
  **1,11 com α_M = 1** — resultado dependente de premissa. **Solução:** chaveta **em cruz** (2 braços 200 × 80 mm,
  qualquer direção do choque) soldada sob a chapa das bases L3, L3c e L3f: cortante → concreto (esmagamento EN 1992-1-1
  §6.7), chumbadores só à tração. `verificar_base_corrente(chaveta=CHAVETA_CRUZ)`; L3f idem.
- **Resultados:** chaveta η 0,19 no choque, 0,27 na L3f (cortante do painel CV-T + vento); ancoragem L3 0,24 / L3c 0,41
  (cone; binário do pilarete incluído). η_max 0,90.
DES-06 com a chaveta em cruz (planta e corte) e nota. Tese: §7.4 reescrita (texto + tabela com η chaveta). Testes
`tests/test_issue74_chaveta_corrente.py` (3). 802 passed.
