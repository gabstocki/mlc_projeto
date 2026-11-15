# 104 — Nó de topo das baías contraventadas: excentricidade h0 entre a escora e o topo do pilar

- **Tema:** Ligações — caminho longitudinal nas baías rígidas
- **Prioridade:** P0 (o caminho de carga da issue 66 não fecha em equilíbrio)
- **Arquivos:** `mlc_projeto/checks/elu/no_contraventamento.py`, `mlc_projeto/connections/ligacao_topo_pilar.py` (`movimento_vertical_escora`, `verificar_interface_deslizante`), `mlc_projeto/main.py` (soldas do nó), `tese/cap08.tex` (`ssec:no-topo`)
- **Relaciona:** 66 (concepção do nó), 64 (escora central), 69 (topo do pilar), 91 (achado ao desenhar), 44 (terminais)
- **Origem:** achado ao desenhar o nó na [issue 91](91-desenhos-faltantes.md) (2026-11-10)

## Problema
A issue 66 adotou o caminho: treliça da cobertura → **escora** = terça T1/T9/T17 sobre o apoio →
**nó metálico no topo do pilar** → painel vertical → fundação.

Ao desenhar, a geometria não fecha:
- a escora está **sobre o extradorso da viga**;
- o nó do painel vertical está no **topo do pilar**, h0 = 1,00 m abaixo.

A força H (118 kN no beiral, 236 kN na linha central) entra na terça e sai no topo do pilar. Isso
deixa um binário **H·h0 ≈ 118 kN·m (236 kN·m)** no plano da fachada que nenhuma peça equilibra:
- **A chapa da escora** liga-se ao nó por 2 M24 em furos ovalizados verticais (interface
  deslizante, de propósito para o movimento vertical viga × pilar). Portanto, não leva força
  vertical, e o binário não pode sair por ela.
- **As cavilhas da escora na terça** precisariam de ±H·h0/z ≈ ±390 kN na vertical, para z ≈ 0,3 m.
- **A viga** não resiste a esse giro no apoio. O garfo da L1 é verificado só para M_d/k_f,2.

Também em aberto, pela mesma razão:
- a chapa do nó em si (espessura, flexão, furação);
- a ligação dos terminais CV-V e CV-H ao nó (o olhal é dimensionado na DES-12, mas a posição
  no nó não);
- o modo como a diagonal da cobertura chega à chapa do montante (DES-13).

As soldas "nó de topo (beiral/central): chapa do nó × chapa de topo" (l = 300 mm) foram
verificadas sem o momento.

## Rotas possíveis (decisão do autor)
1. **Nó no nível da escora.** A diagonal CV-V termina numa chapa embutida na terça, ao lado da
   face da viga.
   - A favor: o binário some, e a componente vertical (sempre para baixo no topo) desce por
     contato terça → viga → pilar.
   - A tratar: o movimento vertical da viga em relação ao pilar e à fundação (até 15 mm de
     umidade e 12 mm de levantamento) alonga a diagonal em ≈ 0,77·δ ≈ 12 mm, o que a escoaria.
     Pede esticador regulado, ou outro meio.
2. **Escora no nível do topo dos pilares.** Uma peça própria entre os topos, nas baías rígidas.
   - A tratar: a reação da treliça (no extradorso) precisa descer h0 pela viga até o topo do
     pilar, e é o mesmo binário, agora na viga.
3. **Treliça de cobertura ancorada nos pilares por mão-francesa.** Uma barra inclinada da terça
   ao topo do pilar, no plano da fachada, triangula o binário.
   - A tratar: forças verticais grandes na terça e na chapa de topo.

## O que fazer
- [x] Escolher a rota.
- [x] Recalcular o nó (chapa, soldas com momento, parafusos) e a interface deslizante, se ficar.
- [x] Desenhar a folha do nó (escora + diagonal da cobertura + diagonal vertical) e incluí-la em
      `FOLHAS` e no Apêndice E.
- [x] Revisar `ssec:no-topo` na tese.

**Dependências registradas (2026-11-11):**
- A seção da terça (0,20×0,40, issue 101) é governada pela ligação da escora central ao nó. Mudando o nó, refazer `varredura_terca.py`.
- O objetivo (c) no cap. 9 declara o nó como não detalhado (`%% TODO (issue 104)`).

## Estudo da rota 1 (2026-11-11) — **inviável como concebida**
Script reprodutível: `issues/104-estudo-rota1.py` (lê o pipeline atual). Hipóteses:
- nó sob a terça, ao lado da face da viga (y = 250 mm do eixo do pilar, 100 mm abaixo do extradorso);
- base da diagonal na chapa de base do pilar vizinho;
- E90,mean = 300 MPa;
- α⊥ = 0,25 %/% e umidades de montagem e de serviço do `oblongo_L1`.

| Grandeza | Hoje (nó no topo do pilar) | Rota 1 |
|---|---|---|
| Inclinação da diagonal | 50,6° | 55,2° (9,63 m) |
| N na diagonal Ø36 (V_painel 118 kN) | 186 kN, η 0,78 | 206 kN, η 0,86 |
| Componente vertical no nó | 143 kN | 169 kN |
| Deslocamento do painel (lim. H/300 = 23,3 mm) | 12,4 mm | **26,5 mm** = 16,3 (barra) + 10,2 (viga ⊥ sob 169 kN, K = 23,7 kN/mm) |

O deslocamento de 26,5 mm reprova com o limite de 23,3 mm. Com o limite referido à altura de 8 m, seria 26,7 mm, o que dá η 0,99.

**Por que falha:** a componente vertical da diagonal passa a descer pela **viga, perpendicular às fibras**, na altura h0 = 1 m. Isso tem três consequências.
1. **Rigidez:** a compressão ⊥ da viga soma 10 mm ao deslocamento do painel. Engrossar a barra não resolve essa parcela.
2. **Umidade:** a diagonal impede o inchamento da viga.
   - Com Δu = 6 % (montagem a 13 %, serviço até 19 %), o inchamento livre é de 15 mm, e a rigidez em série é 9,2 kN/mm (barra na vertical 15,0 com a viga 23,7). Daí F_v = 138 kN, ou **+168 kN na diagonal**: 374 kN contra 239 kN de resistência, e a barra escoa.
   - Mesmo montando úmido (17 %, Δu = 2 %), são +56 kN e 262 kN, que também passam de 239.
   - Barra mais grossa é mais rígida e recebe *mais* força.
3. **Terça:** se os 169 kN entrassem pelas cavilhas no rasgo inferior da terça, o fendilhamento resistiria a cerca de 30 kN, com a borda carregada embaixo e h_e ≈ 150 mm. Seria preciso um selim metálico sobre a viga, com parafusos passantes, para levar a força ao topo da viga.

**Favorável:** sob sucção sem vento longitudinal, a diagonal segura a viga. São 122 kN (η 0,51), com 6,7 mm de subida, e os pinos da L1 nem entram em carga nas baías rígidas.

**Variante testada — pórtico metálico sobre o topo do pilar:** dois montantes de aço ao lado da viga, da chapa de topo até a escora, com a escora ligada por furos verticais.
- Elimina a madeira ⊥ do caminho vertical, e com isso as consequências 1 e 2.
- Mas a componente vertical chega ao pilar com excentricidade de cerca de 0,25 m: M ≈ 42 kN·m no topo do pilar, ou σ_m ≈ 9,2 MPa no central montante (0,32 × 0,27) e 7,8 MPa no de canto, num pilar birrotulado já com η 0,75.
- Só se viabiliza aumentando os pilares montantes das baías rígidas, ou tornando o topo capaz de receber momento.

**Constatação de fundo:** a força nasce no nível das terças, h0 acima do topo do pilar. Para fechar o equilíbrio, alguma peça precisa levar força **vertical** entre esses dois níveis. Se essa peça for a madeira da viga (⊥), o movimento de umidade carrega a diagonal. Se for aço ao lado da viga, surge excentricidade no pilar. A escolha é entre essas duas penalidades, ou outra concepção do caminho longitudinal.

## Estudo do pórtico metálico (2026-11-11) — viável com pilares montantes maiores
Script reprodutível: `issues/104-estudo-portico.py`.

**Concepção:**
- Montantes de aço ao lado da viga, da chapa de topo até a escora.
- A escora liga-se ao topo deles com furos verticais e leva só a força horizontal; a viga fica livre para inchar e subir.
- A diagonal CV-V prende-se no topo do montante, ao lado da viga (y ≈ 250 mm do eixo), no nível da escora.
- No nó, a força da escora e a componente horizontal da diagonal se equilibram: **não sobra binário**.
- A componente vertical D desce pelo aço até a chapa de topo, com excentricidade e ≈ 0,25 m.

**Esforços no topo do pilar montante:**
- D = 169 kN (era 143, pela diagonal mais inclinada).
- M = D·e = 42 kN·m. Varia linearmente até zero na base, que é rotulada, e soma-se ao vento θ = 0° na face (2,7 kN·m, concomitante).
- Verificação: `verifica_pilar_contraventado`, flexocompressão EC5 §6.3.2, com o momento no plano da fachada (eixo "z", alavanca b).

**Taxas por seção (b ⊥ ao pórtico, ao longo da fachada × h no plano do pórtico):**

| Pilar | Hoje (sem M) | 0,32×0,27 | 0,32×0,32 | 0,36×0,32 | **0,40×0,32** | 0,44×0,32 |
|---|---|---|---|---|---|---|
| Canto P1, P3, P25, P27 (N 360 kN) | 0,42 | 1,17 | 0,99 | 0,77 | **0,62** | 0,52 |
| Lateral montante P4, P6, P22, P24 (N 275) | 0,48 | 1,06 | 0,89 | 0,69 | **0,56** | 0,47 |
| Central montante P2, P5, P8, P20, P23, P26 (N 381) | 0,67 | 1,20 | 1,01 | 0,79 | **0,64** | 0,54 |

Seção sugerida: **0,40 × 0,32 m nos 14 pilares montantes das baías rígidas**. O acréscimo de MLC é de cerca de 3,5 m³, ≈ 1,5 % do volume da viga.

**Ainda por dimensionar se esta rota for adotada:**
1. **Topo do pilar com momento.** A chapa vertical atual, no plano do pórtico, não tem braço na direção da fachada. São precisas chapas laterais nas faces y do pilar, com cavilhas paralelas às fibras, para a tração do binário: T ≈ M/z ≈ 140 kN. É o mesmo detalhe das chapas laterais da sela.
2. **Montantes de aço, travessa e chapa de topo.**
   - A chapa de topo estende-se além da face do pilar.
   - A escora apoia-se na travessa, com folga vertical sobre a viga.
   - Furos verticais na ligação escora × montante (a interface deslizante atual, reaproveitada).
3. **Pilar com b maior que a viga:** a chapa de topo e a base passam a 0,40 m, e as bases L3a e L3 dos montantes precisam ser revistas.
4. **Reação horizontal no topo do pilar:** M/H ≈ 6 kN, levada pela escora e pelo diafragma (pequena).
5. **Diagonal CV-V:** 206 kN, η 0,86 com Ø36, e deslocamento de 16,3 mm (só a barra, sem madeira ⊥), dentro do limite de 23,3 mm.
6. **Terça:** deixa de ser governada pelas cavilhas da escora no nó, porque a escora passa a ligar-se ao montante de aço. Refazer a varredura da terça.
7. **Desenhos:** nova folha do nó; DES-03, 06 e 07 nos montantes; texto da `ssec:no-topo`.

## Estudo do pilar bipartido (2026-11-11) — viável, ≈ mesma madeira do pórtico, sem aço no nó
Script reprodutível: `issues/104-estudo-bipartido.py`.

**Concepção:**
- Nos 14 pilares montantes, o pilar é composto por **duas lâminas de MLC**, uma de cada lado da viga (distância livre de 340 mm = b_viga + 2 × 10), da base até a escora (7,7 m). As lâminas são unidas por espaçadores, como pilar composto do EN 1995-1-1 Anexo C.3, com distância livre ≤ 3 × a espessura da lâmina.
- A viga apoia-se numa peça de aço entre as lâminas, no nível atual do topo do pilar.
- A escora (terça) apoia-se no topo das lâminas. O topo da viga fica com folga sob a terça, livre para inchar.
- A diagonal CV-V prende-se no topo da lâmina do seu lado.

**Por que fecha:**
- Escora e diagonal no mesmo nível: sem binário.
- A componente vertical D (≈ 171 kN) desce pela lâmina **paralela às fibras**, sem madeira ⊥ e, portanto, sem conflito com a umidade.
- Cada lâmina descarrega num pilarete próprio. O momento D·e vira só um binário axial entre as lâminas, sem flexão no pilar.

**Verificação** (lâmina do lado do nó, N = R/2 + D + parcela do vento):
- Plano do pórtico: lâmina isolada, l = 6,7 m (travada pela viga).
- Fachada: composto, λ_ef = √(λ² + η·λ1²) (C.10), η = 3,5 (espaçadores parafusados, longa duração, conservador), espaçadores a 1,5 m.

| Lâmina (b × h) | Largura total | Canto | Lateral montante | Central montante | Área de madeira (m²) |
|---|---|---|---|---|---|
| 0,14 × 0,27 | 0,62 m | 1,11 | 0,94 | 1,16 | 0,076 |
| 0,14 × 0,32 | 0,62 m | 0,77 | 0,65 | 0,80 | 0,090 |
| 0,16 × 0,27 | 0,66 m | 0,98 | 0,82 | 1,01 | 0,086 |
| **0,16 × 0,32** | **0,66 m** | **0,62** | **0,53** | **0,65** | **0,102** |

**Comparação com o pórtico metálico (por pilar):**
- Pórtico: 0,40 × 0,32 em 6,7 m ≈ 0,86 m³, η 0,56–0,64, mais o pórtico de aço e as chapas laterais de momento no topo.
- Bipartido: 2 × (0,16 × 0,32) em 7,7 m ≈ 0,79 m³, η 0,53–0,65, sem pórtico de aço e sem momento no pilar.

**Ainda por dimensionar se esta rota for adotada:**
1. **Apoio da viga entre as lâminas:** peça de aço (sela) com abas embutidas nas lâminas, com cavilhas paralelas às fibras: R/2 por lâmina, 53 kN na lateral e 106 kN na central (duas vigas). Isso **substitui a L1/L1c** nesses 14 pilares. O arrancamento sobe pelas mesmas cavilhas.
2. **Espaçadores e as suas ligações** (C.3.3), inclusive o do topo, que recebe a escora.
3. **Base com dois pilaretes**, um por lâmina, numa chapa de base de cerca de 0,70 m. Rever ancoragem e chaveta.
4. **Nó no topo da lâmina:** escora × chapa × olhal da diagonal, com cavilhas ∥ fibras na lâmina. Reaproveita a ligação da escora (9/20 cavilhas).
5. **Terça:** deixa de ser governada pela ligação ao nó. Refazer a varredura.
6. **Desenhos:** nova folha do pilar bipartido. Rever DES-03, 05, 05B, 06, 07 e o texto (cap. 5 e 8).

## Resolução ✅ (2026-11-11) — pilar bipartido (decisão do autor)

**Cálculo** (`checks/elu/pilar_bipartido.py`, novo):
- Nos 14 montantes (cantos P1, P3, P25, P27; laterais P4, P6, P22, P24; centrais P2, P5, P8, P20, P23, P26), o pilar tem duas lâminas de 0,16×0,32 m, uma de cada lado da viga (a = 340 mm ≤ 3·b_l), da base até a escora (7,7 m). Espaçadores de MLC a cada 1,5 m e no pé.
- Lâmina do nó: N = R/2 + D (+ parcela do frontão no canto). k_c pelo plano do pórtico (lâmina isolada, 6,7 m) e pela fachada (λ_ef, C.10–C.12, η = 3,5).
- Espaçadores: C.5 e C.13, com M16 8.8 em corte duplo madeira–madeira (Eq. 8.7, f_h pela 8.32).
- Nó e sela: cavilhas ∥ fibras, com furos ovalizados ⊥ nas chapas para a retração.
- Resultados (lâmina do nó):

| | Canto | Lateral montante | Central montante |
|---|---|---|---|
| N | 274 kN | 232 kN | 285 kN |
| η compressão | 0,68 | 0,57 | 0,70 |
| Espaçadores | 0,69 | 0,53 | 0,73 |
| Nó, 18 Ø20 (3×6) | 0,75 | 0,75 | 0,75 |
| Sela | 0,66 (4) | 0,66 (4) | 0,62 (12) |

**Painel CV-V:**
- Nó no topo da lâmina, no nível da escora, 0,10 m abaixo do extradorso: H = 7,9 m, b = 5,37 m, β = 55,8°.
- Diagonal Ø36: 209 kN, η 0,88. δ = 16,6 mm, dentro do limite de 26,3 mm (H/300).
- `H_PAINEL_CVV` e `B_BAIA_CVV` em `main.py`.

**Bases L3a dos montantes:**
- Grelha girada 3×2 (920×520), com um pilarete Ø114,3×8 por lâmina (`TUBOS_CHS_LAMINA`; o Ø139,7 não cabe sob 160 mm).
- `verificar_base_pilar` ganhou `N_c_pe_kN`, `N_t_pe_kN`, `x_tubos_mm` e `tubos`.
- O pé passou a ser dimensionado também pelo cortante do choque, dividido entre as lâminas pelo espaçador do pé.
- As laterais montantes passam a usar a L3a. **Achado:** antes, P4, P6, P22 e P24 tinham base L3 sem o arrancamento do painel.

**Outras mudanças no cálculo:**
- Saíram a interface deslizante (`no_deslizante`) e as soldas "chapa do nó × chapa de topo". Entrou `no_escora_parafusos` (2 M24 em furo normal, η 0,48).
- As variantes de topo L3a saíram de `ligacao_topo_pilar`, porque a sela entre as lâminas as substitui.
- Soldas novas: aba da sela × chapa da sela.
- Catálogo: `pilar_lateral_montante` e `no_escora_parafusos`.
- Memorial: a equação do central montante virou a da lâmina.
- Quadro de espaçamentos: nó, sela e pé da lâmina (123 itens atendidos).

**Desenhos:**
- Plantas e elevações com as duas lâminas e o painel indo até o topo da lâmina.
- DES-07 refeita: base dos montantes, 1:30.
- **DES-15** nova: topo do pilar bipartido, com sela, nó, escora, olhal e folga de 25 mm. Total de 17 folhas.

**Tese:**
- cap08: nova `ssec:pilar-bipartido` (texto, Eq. λ_ef, `tab:pilar-bipartido`, figura); `ssec:no-topo` reescrita sem a interface deslizante; tabelas de bases, bloco e margens.
- cap07: pilares montantes e CV-V (0,88, 209 kN).
- cap05:
  - pilar de canto → montantes bipartidos;
  - Tab. 13;
  - `tab:distribuicao-paineis` refeita: 4/4 continua adotado, e o aço varia de 1.221 a 1.425 kg;
  - **varredura global refeita**: as mesmas 1.067 aprovadas e a mesma fronteira; o texto foi ajustado.
- cap09: objetivo (c) com o nó detalhado; o TODO saiu.
- Apêndice E com a DES-15.
- Tese: 167 páginas, 0 overfull, nenhuma referência pendente.

**Verificação:** pipeline APROVADO, η_max 0,90; 842 testes passam (`test_issue104_pilar_bipartido.py`, 7).

**Fica para a 99:**
- tabela de custo (volume dos pilares: 14 bipartidos ≈ 0,79 m³ cada, contra ≈ 0,58 antes);
- números de ancoragem dos montantes no cap. 8 (arrancamento de 357/342 kN, antes 327/313);
- contagens de verificações e de testes.

**Justificativa no texto (2026-11-11):**
- A `ssec:no-topo` passou a apresentar o problema geométrico e as quatro soluções examinadas, em alíneas e na `tab:solucoes-no-topo`: (a) nó no topo, sem equilíbrio; (b) nó na escora pela viga, com 26,5 mm > 23,3 e 374 kN > 239; (c) pórtico de aço, com 42 kN·m e montantes de 0,40×0,32; (d) bipartido.
- Novo esquema **ESQ-04** (`esquemas.esquema_no_topo` → `fig:esq-no-topo`).
- O parágrafo de decisão fecha o argumento: único caminho sem força ⊥ às fibras e sem momento; volume ≈ 0,79 contra 0,86 m³ por pilar; caso previsto no Anexo C da EN 1995-1-1; só 14 dos 29 pilares.
