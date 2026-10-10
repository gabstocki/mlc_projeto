# 43 — Detalhamento das ligações com atendimento dos espaçamentos

- **Tema:** Ligações — detalhamento
- **Prioridade:** P1
- **Normas:** EN 1995-1-1 §8.5–§8.7 (Tab. 8.4/8.5 — a1, a2, a3,t, a3,c, a4,t, a4,c), EN 1993-1-8 Tab. 3.3 (e1, e2, p1, p2 em chapas), EN 1992-4 (distâncias de borda dos chumbadores)
- **Arquivos:** `mlc_projeto/connections/*.py`; `tese/cap08.tex`
- **Relaciona:** issues 29, 42, 48, 52

## Origem (3ª revisão do orientador (2026-10))
“Após o cálculo, apresentar o detalhamento das ligações mostrando o atendimento dos
requisitos (espaçamentos) de detalhamento.”

## O que fazer
- [x] Para cada ligação (L1, L1c, L3, L3c, ancoragem, extremidades das diagonais, terça–viga):
      tabela **requerido × adotado** de todos os espaçamentos e distâncias (madeira, chapa, concreto).
- [x] Desenho cotado de cada ligação mostrando esses valores (integra a issue 52).
- [x] Garantir que o código exporta os espaçamentos adotados (já parcialmente no dict da L1).

## Resolução (2026-10-09) ✅
**Quadro requerido × adotado** — `mlc_projeto/output/quadro_espacamentos.py`, gerado pelo
pipeline em `tese/tab_espacamentos.tex` (3 tabelas: madeira topo/cobertura; madeira pé dos
pilares; chapas e concreto) e incluído no cap. 8, nova §«Atendimento dos espaçamentos». 79 itens:
L1, L1c (EC5 Tab. 8.5 a θ = 84,2°; chapa: p1, e3, e4 de furo ovalizado), L1f, escoras do nó de topo,
terça–viga (corrente: EC5 Tab. 8.6; montante), pé do pilar das 5 bases + chapa vertical, chapas de
base (e1, e2, p, folga da arruela), concreto (s ≥ 4·d_nom, c ≥ 1,5·h_ef, h ≥ 2·h_ef — EN 1992-4) e
olhais (EN 1993-1-8 Tab. 3.9). Requerido vem das funções de norma do programa; adotado, do detalhe.
- **Falha encontrada e corrigida:** chapa embutida da L1/L1c terminava 26 mm acima da extremidade
  do furo ovalizado do pino mais alto (< 1,5·d0 = 36 mm). Altura 964 → 974 mm (`main.py`,
  esquadro); teste de regressão que reproduz o caso.
- **Ligação terça–viga** (não existia — escolha do usuário: dimensionar agora):
  `connections/terca_viga.py`. Junta corrente: parafusos autoatarraxantes de rosca total Ø8 a 45°,
  cruzados, 4 por face empilhados (8 por extremidade de terça), EC5 §8.7.2 (Eq. 8.38/8.39, A1),
  §8.7.1 + Johansen Eq. 8.6, interação §8.7.3; esforços V_up = 14,7 kN, H_viga = 3,4 kN (diafragma),
  H_terça = 0,2 kN (§9.2.5.2); η 0,56. Geometria: terças biapoiadas se encontram sobre o eixo da
  viga (meia largura cada); faces deslocadas ±2d para os pares não colidirem. Junta de montante nas
  baías rígidas (N = 93,3 kN): 5×Ø20 em chapa embutida, η 0,75. **Declarados (catálogo, sem ETA):**
  f_tens,k = 20 kN, d_núcleo = 5,4 mm, M_y,Rk = 20 N·m.
- Desenho DES-09 (terça–viga, 1:15) no cap. 8 e no Apêndice E.
- 64 verificações; testes `tests/test_issue43_espacamentos.py` (5); suíte 736.
- Não desenhados: olhais e nó de topo (peças de catálogo / chapa de nó) — espaçamentos no quadro.
