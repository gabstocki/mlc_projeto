# 64 — Caminho longitudinal: a treliça da cobertura apoia-se na linha central, que não tem contraventamento vertical

- **Tema:** Estabilidade / Contraventamento — caminho de carga
- **Prioridade:** P1 (pode dobrar a força na diagonal da cobertura: η 0,79 → ≈1,6)
- **Normas:** EN 1995-1-1 §9.2.5.3; EN 1990 §6.4.3 (caminho de carga)
- **Arquivos:** `mlc_projeto/checks/elu/contraventamento.py` (treliça com apoios no beiral E na linha central); `mlc_projeto/checks/elu/contraventamento_vertical.py`; `mlc_projeto/main.py:288-300` (“o alinhamento CENTRAL … não é usado”); `tese/cap05.tex` §5.5, `tese/cap08.tex` §8.5
- **Origem:** achado ao resolver a [issue 41](41-ell-contraventamento-9-2-5.md)

## Problema
Na baía rígida, a treliça de cada água vence ℓ = 20,25 m entre o **beiral** e a **linha
central**, e entrega metade da força longitudinal (vento θ=0° + estabilização) em cada apoio.
Os 8 painéis de contraventamento vertical estão **só nas duas fachadas**: a linha central
(pilares biarticulados, interior do estacionamento) **não tem caminho longitudinal** até a
fundação. A reação central (2 × 104,7 kN por baía) fica sem destino. O código antigo já
tinha a mesma premissa (painéis em x≈0 e x≈L).

## Opções
- **A — Contraventamento vertical na linha central** (cruzes ou pórtico/mão-francesa nas
  baías extremas do alinhamento central). Mantém ℓ = 20,25 m e η_diag = 0,79; custa baías
  livres no estacionamento (2 baías) e mais download/ancoragem nos pilares centrais.
- **B — Treliça única beiral–beiral** (ℓ = 40,5 m; k_ℓ = 0,61; n por sistema igual):
  cortante no beiral ≈ 2×; diagonal Ø28 → η ≈ 1,6 ⇒ Ø36–Ø40 nos painéis extremos;
  flecha ℓ/500 = 81 mm; os pilares de fachada recebem toda a força (já é o caso no
  contraventamento vertical, que soma 837 kN).
- **C — Pilar central engastado na direção longitudinal** (verificar rigidez/2ª ordem).

## O que fazer
- [x] Decidir A/B/C (decisão de projeto — arquitetura do estacionamento).
- [x] Implementar no `contraventamento.py` (apoios da treliça) e no `contraventamento_vertical.py`.
- [x] Atualizar tese §5.5/§8.5, desenhos (issue 52) e custo.

## Resolução ✅ (2026-10-06) — Opção A, 4 painéis nas fachadas + 4 na linha central

**Repartição:** as treliças da cobertura entregam 1/4 da força longitudinal a cada beiral e
1/2 à linha central (a nocional na mesma proporção — o pilar central tem o dobro da carga
vertical). Varredura no pipeline (diagonal auto, η ≤ 0,90):

| fachadas / central | η pilar central montante | η canto | status |
|---|---|---|---|
| 8 / 2 | 1,01 (Ø48 central) | 0,34 | reprova |
| 4 / 2 | 1,01 | 0,43 | reprova |
| 8 / 4 | 0,74 | 0,34 | aprova, 12 baías |
| **4 / 4** | **0,74** | **0,43** | **adotado, 8 baías** (decisão da usuária) |

4 + 4 mantém a força por painel do projeto anterior (105,9 kN, Ø36, η=0,788), logo canto,
massa de aço (1.158 kg) e custo não mudam.

**Código**
- `contraventamento_vertical.py`: `reparticao_alinhamentos()`; `verificar_contraventamento_vertical(..., fracao_demanda, alinhamento)` (escala V_lat e a carga vertical do α_cr).
- `main.py`: `N_PAINEIS_CV_VERT=4`, `N_PAINEIS_CV_CENTRAL=4`, `N_CHU_CENTRAL_CV=6`; 2ª chamada
  (`contraventamento_vertical_central`), ligação de extremidade da diagonal central,
  `pilar_central_contraventado` (2·R_v + download 129 kN → η=0,744), ancoragem da base central
  montante (6×M24 + chaveta: η_aço 0,20, cone 0,53, chaveta 0,40), estabilidade global com
  K_lat das duas linhas.
- `succao_uplift.py`: base central montante (N=151,8+129,0=280,8 kN, V=105,9 kN; η=0,585).
- `cargas_fundacao.py`: linha “Central montante” (6 bases = 2 grupos × 3 pilares; no pilar comum
  a dois painéis os efeitos se anulam); H longitudinal total = 847,4 kN.
- `report.py`: catálogo (5 novas linhas) e §8b.1 em duas colunas (fachadas | linha central).
- Testes: `tests/test_contraventamento_linha_central.py` (6) + `test_f13_configuracao_adotada.py`
  revisto (4+4; 2 centrais reprovam). Suíte 663 passed; pipeline APROVADO, η_max 0,79.

**Tese:** §5.5.2 (repartição + Tabela de distribuição), síntese do cap. 5, §6.1, §7.3 (pilar
central montante), §7.5 (tabela e texto), §8.4 (arrancamento, ancoragem central), §8.5, §8.6
(quadro de fundação), §9.2.

**Pendência resolvida na issue 66:** escora longitudinal no topo do alinhamento central entre os
pilares das baías contraventadas (≈106 kN, tração/compressão) — definir o elemento (terça da
calha ou peça dedicada) e verificá-lo; entra nos desenhos da issue 52.
