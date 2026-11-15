# 82 — Ausência de beiral: criar beirais/oitões ou justificar e proteger

- **Tema:** Durabilidade — concepção
- **Prioridade:** P1 — **decisão do autor**
- **Arquivos:** se criar: geometria/modelo da viga (balanço além do pilar em A e C), terças nos frontões (eixos 1 e 9), cargas, desenhos, custo; se não: `tese/cap08.tex` §7.8
- **Relaciona:** 83, 84
- **Origem:** 4ª revisão, item 4.2

## Problema
O contorno da cobertura coincide com os pilares de perímetro (alinhamentos A e C, eixos 1 e 9),
sem projeção: topos, ligações e faces ficam expostos à chuva.

## Opções
- (a) Criar beirais em balanço (A e C: prolongar a viga além do pilar e revisar o modelo — momento
      negativo no apoio, L1, vento no balanço) e oitões (1 e 9: prolongar as terças), sem alterar a área interna.
- (b) Não criar, por prazo: justificar no texto e adotar as proteções das issues 83 e 84.

## O que fazer
- [ ] **Autor:** escolher (a) ou (b).
- [ ] Implementar a opção escolhida.

## Resolução ✅ (2026-11-07) — opção (a): beiral em A/C + oitões, projeção 1,00 m (decisão do autor)

**Geometria:** projeção de 1,00 m além da face dos pilares de perímetro. Balanços medidos do eixo:
viga a = 1,00 + 0,27/2 = **1,135 m** (h 1,00 → 0,800 m na ponta, extradorso continua a água);
terça a_t = 1,00 + 0,32/2 = **1,16 m**. Cobertura 42,77 × 48,32 m = 2.067 m² (área interna
1.863 m² inalterada). Terças de ponta **T0 e T18** na extremidade dos beirais (mesma seção).

**Modelo** (`core/loads.py`, `core/geometry.py`): `GeometriaViga.a_bal`, `h_ponta`, `h_balanco`;
`analisar_biarticulada(a_bal=)` por superposição, balanço **só no apoio externo A** (em B a viga
termina na sela; V2 é o espelho e os padrões de vento cobrem as duas incidências):
M(x) = M0 + M_A(1 − x/L), M_A = −q_esq·a²/2, R_A = R_A0 − M_A/L + q_esq·a, R_B = R_B0 + M_A/L.
V_apoio/N_apoio = lado do vão; R_A/R_B = reações totais. `componente_horizontal_cobertura(a_bal=)`.
Propagado a ELS, fogo, flexão, mísula, sucção/uplift, LTB sob sucção (`momento_biapoiada`),
diagramas/apêndice C. Vento: atrito §7.2.2 com a × b = 48,32 × 42,77; ℓ2 = 2L + 2a.

**Nova verificação** (`checks/elu/beiral.py`): balanço da viga (flexão na raiz com k_m,α da borda
inclinada §6.4.2, cisalhamento, LTB Tab. 6.1, flecha da ponta Tab. 7.2 = balanço + rotação do
apoio; validada contra Roark) η = 0,13 (ELS governa); balanço da terça η = 0,07. Q só no vão:
+2,2 kN·m (0,4 %) — informado.

**Efeito nos resultados (todos APROVADO):** η_max 0,85 → **0,89** (diagonal da cobertura Ø28 fixa,
0,80 → 0,88, atrito +11 %); M_d 504 → 501 kN·m; R_v 99,6 → 111 kN; arrancamento L1 86,1 → 96,9 kN
→ **L1 passa a 6 pinos** (η 0,65), fendilhamento 0,34 → 0,39; CV-V auto Ø33 → **Ø36**, CV-T Ø24 →
**Ø27**; sela 0,75 → 0,83; base L3f 0,73 → 0,84; pilar central montante 0,75 → 0,83.
66 verificações. Testes: `tests/test_issue82_beiral.py` (9) + 4 ajustados. 761 passed.

**Desenhos:** DES-01 (contorno da cobertura, T0/T18, cotas), DES-03 (terças em balanço),
DES-04 (vigas com beiral), DES-05 (viga continua além do pilar), ESQ-02 (balanços no modelo).
Quadro: a3,t da L1 = 168 + 1000 mm.

**Tese:** §3.1 (beirais e oitões, dimensões), Tab. de geometria e de nomenclatura (T0, T18);
§5.1 Eq. de superposição; área do atrito; nova §6.x.y «Balanços do beiral e do oitão» + tabela;
§7.8 abre com o beiral como medida de concepção.

**Pendências criadas (registradas nas issues):**
- **99** — os números digitados nas tabelas e no texto (cap. 4–9, resumo, custo) ainda são os
  anteriores ao beiral: atualizar todos (diâmetros CV-V/CV-T, η, forças, L1 6 pinos, quantidades).
- **99** — figuras do modelo OpenSees/VTK (`modelo_3d`, `portico_elevacao`, `modelo_momento`) e a
  comparação FEM × analítico não têm o balanço: atualizar o modelo FEM ou declarar.
- **93** — varredura global sem `a_bal` (`predim/varredura_global.py`): incluir o beiral.
- **83/84/85** — o beiral resolve topo do pilar e L1/rasgo; restam topos na ponta dos balanços e
  faces dos pilares; UC das peças de perímetro a reavaliar.
- **91** — detalhe da terça de ponta e da ligação terça de ponta–viga.
