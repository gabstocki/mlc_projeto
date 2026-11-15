# 69 — Ligação da chapa de topo (L1, L1f) e da sela (L1c) ao pilar de madeira

- **Tema:** Ligações — caminho de cargas (arrancamento até a fundação)
- **Prioridade:** P0 — hoje o arrancamento não tem caminho definido entre a chapa e o pilar
- **Normas:** EC5 §8.2.3 (Johansen), §8.5.1.1 (n_ef), Tab. 8.5, Anexo A (bloco), §6.1.2 (seção líquida); EN 1993-1-8 (furos, soldas §4)
- **Arquivos:** `mlc_projeto/connections/connections.py` (L1/L1c), `checks/elu/pilar_frontao.py` (L1f), `checks/elu/no_contraventamento.py` (nó de topo), `connections/base_pilar.py` (modelo do pé — reutilizar), `output/desenhos.py`, `output/quadro_espacamentos.py`, `tese/cap08.tex` §7.2
- **Relaciona:** 66 (nó de topo), 75 (bloco), 78 (soldas), 79 (d0), 81 (retração), 91 (desenho)
- **Origem:** 4ª revisão, item 2.1 (+ 4.1 último parágrafo)

## Problema
Não está definido, nem no texto nem nos desenhos, como a chapa de topo (L1, L1f) e a sela (L1c)
se prendem ao pilar. Essa ligação precisa levar:
- arrancamento: 86,1 kN (L1), ~150 kN (L1c), ~67 kN (L1f);
- nas baías contraventadas, as forças do nó de topo: 107 kN (beiral) e 214 kN (linha central).

## O que fazer
- [ ] Conceber o detalhe (provável: chapa vertical soldada sob a chapa de topo/sela, embutida em
      rasgo no topo do pilar, com cavilhas — espelho do pé do pilar).
- [ ] Já na concepção, adotar o critério da issue 81 (furos ovalizados ⊥ às fibras ou chapa
      dividida, para não impedir a retração do pilar).
- [ ] Verificar com o rigor do pé do pilar: Johansen, n_ef, espaçamentos (Tab. 8.5), ruptura de
      bloco (Anexo A), seção líquida do pilar (§6.1.2), chapa (seção líquida, esmagamento) e soldas.
- [ ] Combinar arrancamento + força do nó de topo nas baías contraventadas (concomitância por combinação).
- [ ] Entrar no catálogo de verificações, no quadro de espaçamentos, no Apêndice B e no desenho (issue 91).

## Insumos das issues 72/73/81 (2026-11-07)
- Critério de retração: D⊥ ≤ 133 mm (Ø20 a 60 mm) ou furos ovalizados ⊥ — `connections/retracao.py`.
- As chapas laterais de 250 mm da sela (issue 73) podem ser parte da ligação sela–pilar.
- Movimento vertical relativo viga × topo do pilar: levantamento ≤ 12 mm (72) + umidade ≈ 15 mm no extradorso:
  o nó de topo (escora sobre a viga ↔ pilar) deve acomodá-lo (ex.: furos ovalizados verticais no nó).

## Resolução ✅ (2026-11-07)
**Concepção** (`connections/ligacao_topo_pilar.py`): espelho do pé do pilar — chapa vertical soldada sob a chapa de
topo / sela, embutida em rasgo no topo do pilar, cavilhas Ø20 corte duplo // fibras; **no mesmo plano da chapa
embutida da viga** (arrancamento atravessa a chapa de topo na espessura → aço classe Z, EN 1993-1-10). Tração de
projeto = a da base correspondente (L1↔L3, L1c↔L3c, L1f↔L3f, canto/central montante↔L3a). Malha ≤ 3 fileiras ⊥
(issue 81). Verificações: cavilhas (Johansen, n_ef, bloco), cortante do pilar ⊥ (1,6 kN), solda dupla a = 5 mm,
compressão // fibras sob a chapa descontado o rasgo.

| Variante | N_t (kN) | Cavilhas | η |
|---|---|---|---|
| L1 lateral | 98,3 | 8 (2×4) | 0,65 |
| L1c sela | 169 | 12 (3×4) | 0,74 |
| L1f | 82,8 | 6 (3×2) | 0,68 |
| L1 canto | 327 | 27 (3×9), 940 mm | 0,69 |
| L1c central montante | 313 | 24 (3×8) | 0,74 |

**Nó de topo:** forças horizontais seguem em aço (chapa de topo/nó → diagonais); o pilar recebe só a componente
vertical (já na tração da base). **Interface deslizante** escora ↔ nó (movimento vertical viga × pilar: +29/−11 mm =
levantamento 12 + umidade α·Δu·h0 + tolerância): **2 × M24 8.8 corte duplo em furos ovalizados verticais 26 × 71**,
F_b × 0,6 (EN 1993-1-8 Tab. 3.4): η 0,24 (beiral 118 kN) / 0,48 (central 236 kN).

Novas verificações no catálogo: “Chapa de topo/sela → pilar” (0,74) e “Nó de topo deslizante” (0,48) — 70 no total;
η_max 0,90. Quadro de espaçamentos com as ligações de topo; retração inclui o topo. DES-05 mostra a chapa vertical
e as cavilhas no topo dos pilares (tracejado). Testes `tests/test_issue69_topo_pilar.py` (3). 784 passed.
Tese: nova §7.2.x «Ligação da chapa de topo e da sela ao pilar» (tabela), §7.6.1 nó de topo com a interface
deslizante e números atualizados (escoras 118/236 kN; tabela das ligações das escoras). Ref. EN 1993-1-10.

**Fica para:** folha própria da ligação topo–pilar e do nó (issue 91); soldas detalhadas (78).
