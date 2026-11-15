# 91 — Desenhos faltantes; soldas, aço e proteção em cada folha; sela e bases

- **Tema:** Desenhos
- **Prioridade:** P1 (necessário para o objetivo (c) — issue 101)
- **Arquivos:** `mlc_projeto/output/desenhos.py` (`FOLHAS`), `tese/apendiceE.tex`
- **Relaciona:** 69, 73, 78, 86, 87, 66 (nó de topo), 44 (terminais), 32 (corda do diafragma)
- **Origem:** 4ª revisão, itens 6.4, 6.5 e 6.6

## O que fazer
- [ ] Novas folhas:
  - [ ] ligação da chapa de topo e da sela ao pilar (issue 69);
  - [ ] nó de topo das baías contraventadas (escora, diagonal da cobertura e diagonal vertical);
  - [ ] terminais das diagonais (olhal, pino, manilha, rosca recalcada);
  - [ ] montante terça–viga;
  - [ ] emendas da corda do diafragma (3 emendas de 16,2 kN);
  - [ ] pilarete metálico (issue 87).
- [ ] Em cada desenho: tipo, garganta e comprimento de cada solda; aço de cada peça; proteção contra corrosão.
- [ ] Sela: enrijecedores (issue 73).
- [ ] Bases: plano da chapa vertical em relação ao pórtico, direção do impacto, cotas de nível (piso acabado, topo do pilarete, topo do bloco).

## Resolução ✅ (2026-11-10)

**Novas folhas** (`desenhos.py`, `FOLHAS` com 16 entradas; Apêndice E e cap. 8):
- **DES-11 — topo dos pilares (issue 69):**
  - chapa de topo L1 e sela L1c ao pilar, com a chapa vertical no plano do pórtico, as
    cavilhas (2×4 e 2×7) e um corte ⊥ ao pórtico (rasgo 24, chapa 20);
  - sela com 3 enrijecedores 125×125×12,5 e chapas laterais 250×12,5 (issue 73);
  - soldas a5–210 e a4.
- **DES-12 — terminais:** olhal (a, c, d0, t), pino S355, forquilha de catálogo com N_Rd
  mínimo, rosca recalcada e corte pelo pino, para CV-V, CV-T e CV-H.
- **DES-13 — junta das terças sobre a viga:** emenda da corda e montante, com a chapa em rasgo
  superior, as cavilhas, os parafusos a 45° e o corte da terça com a folga entre o rasgo e o
  parafuso mais alto.
- **DES-14 — pilarete:** elevação e planta da chapa de topo; soldas de contorno a6/a8 e a5;
  respiros; intumescente R60; choque F = 50 kN; níveis; quadro com as quatro bases.

**Em todas as folhas:**
- chamadas de solda (`_solda`, texto de `res["soldas"]` via `_solda_txt`) nas DES-05, 05B, 06,
  07, 08, 11, 12, 13 e 14;
- `NOTA_ACO` nas folhas novas;
- a proteção (`NOTA_CORROSAO`) já estava presente;
- `carimbo` agora recusa nota com mais de 7 linhas, em vez de cortá-la em silêncio.

**Bases (DES-06/07):**
- graute de 30 mm desenhado;
- cotas de nível no corte (±0,00 piso acabado = topo do bloco; +0,30 topo do pilarete);
- na planta, o plano do pórtico = plano da chapa vertical, e o choque F = 50 kN a 0,20 m "em
  qualquer direção".
- A DES-07 cresceu para mostrar as 13 fileiras do pé; o pilar central da DES-05B vai além da
  chapa vertical de 7 fileiras.

**O desenho expôs três lacunas de cálculo, corrigidas:**
1. **Emendas da corda.** As terças são biapoiadas, então a corda tem uma junta sobre cada viga
   intermediária: **7 por linha**, e não 3 emendas de barra de 11,75 m (`L_barra_m = L_T`).
   - Nova emenda em `ligacao_terca_viga`: chapa no rasgo superior, 2 cavilhas Ø20 de cada lado
     (2×1), chapa 360×146, rasgo 151, η 0,40.
2. **Rasgo superior × parafusos a 45°.** Os parafusos da junta corrente cruzam o plano médio da
   terça entre z = 41 e 217 mm, então o rasgo superior tem no máximo 173 mm
   (`rasgo_superior`), o que dá n_vert ≤ 2 e D⊥ ≤ 81,9.
   - O montante passou de 4×2 para **2×4** (a2 70; chapa 960×156; rasgo 161): η 0,70 → **0,75**
     (no limite) e bloco 0,31 → 0,74.
3. **Terminal da diagonal da cobertura (CV-H) não dimensionado.** Agora `lig_diag_cobertura`:
   pino Ø30, olhal t 16 S235, solda a4–105, η 0,84 (0,89 por capacidade).
   - Entrou no catálogo e no quadro de soldas.

**Tese:**
- cap. 8: figuras DES-11 a 14; texto do montante (rasgo e duas fileiras); bloco 0,74;
- corda: 19,8 kN, 7 juntas, emenda η 0,40, corda 0,12 (o texto dizia 16,2 kN, 3 emendas, 0,07);
- tabela das diagonais com a da cobertura e os números atuais (Ø36/36, Ø27/30, Ø28/30; 0,89);
- o TODO da manilha (239/135/145 kN);
- cap. 4: linha "Aço das cavilhas: S275, f_u,k ≥ 400 MPa".

**Fica para a [issue 104](104-no-topo-excentricidade-escora.md) (P0, aberta aqui):** o nó de topo
das baías contraventadas não foi desenhado. O caminho da issue 66 deixa um binário H·h0 ≈ 118
kN·m (236 na linha central) sem equilíbrio. Decisão do autor: abrir a issue e seguir com o resto.

**Verificação:** pipeline APROVADO, η_max 0,90; 834 testes passam (`test_issue91_desenhos_faltantes.py`,
9 novos); tese com 162 páginas, 0 overfull, nenhuma referência pendente.

**Para a issue 99:** subiram as contagens de verificações (catálogo + `lig_diag_cobertura`) e de
testes.
