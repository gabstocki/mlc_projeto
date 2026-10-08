# 66 — L1 nas baías contraventadas: força horizontal perpendicular ao pórtico não verificada

- **Tema:** Ligações — L1/L1c / caminho de carga longitudinal
- **Prioridade:** P1
- **Normas:** EN 1995-1-1 §8.2/§8.3 (pinos carregados ⊥ ao plano da chapa? → corte em outra direção), EN 1993-1-8
- **Arquivos:** `mlc_projeto/connections/connections.py` (L1 só com N e V no plano do pórtico); `checks/elu/contraventamento.py` (`R_ext_proj_kN` ≈ 104,7 kN por apoio da treliça); `checks/elu/contraventamento_vertical.py`
- **Origem:** achado ao resolver a [issue 42](42-caminho-reacao-apoio-L1-L1c.md); relaciona [41](41-ell-contraventamento-9-2-5.md), [64](64-caminho-longitudinal-linha-central.md)

## Problema
Nas duas baías rígidas, a treliça de contraventamento da cobertura entrega em cada apoio
(beiral e linha central) ≈ 104,7 kN **na direção longitudinal** (⊥ ao plano do pórtico). Essa
força passa da viga (banzo da treliça) ao topo do pilar — que é montante do painel de
contraventamento vertical — pela ligação L1/L1c, ou por escora/terça de beiral. Nenhuma
verificação cobre esse trecho: a L1 é dimensionada só com N e V no plano do pórtico, com a
chapa embutida trabalhando no seu próprio plano.

## O que fazer
- [ ] Definir o caminho: (a) pela L1 (chapa embutida carregada fora do plano → flexão da chapa
      e pinos ao corte na direção longitudinal), (b) pela terça de beiral/escora diretamente ao
      nó do painel vertical, (c) chapa de topo com batente.
- [ ] Verificar o elemento escolhido (madeira: embutimento/fendilhamento ⊥; aço: chapa/solda).
- [ ] Integrar com a escora de topo da linha central (pendência da issue 64) e com os desenhos (52).

## Resolução ✅ (2026-10-06) — opção (b): escora + nó metálico no topo do pilar

**Caminho:** treliça da cobertura → **escora** (terça sobre o apoio = montante de extremidade
da treliça = banzo superior do painel vertical) → **nó metálico** no topo do pilar (chapa
soldada à chapa de topo / sela, recebendo escora + diagonal da cobertura + diagonal vertical) →
painel vertical → fundação. A L1/L1c **não** recebe a força longitudinal.

**Código** — `checks/elu/no_contraventamento.py` (novo)
- `dimensionar_ligacao_axial_escora`: cavilhas em chapa embutida, θ = 0° (EC5 §8.2.3 modos f/g/h,
  corte duplo), n_ef §8.5.1.1, distâncias Tab. 8.5, ruptura de bloco (Anexo A); alvo frágil 0,75.
- `verificar_no_contraventamento`: N_beiral = máx(V_painel fachada; N_corda diafragma — direções
  de vento não concomitantes); N_central = 2 × V_painel central (painéis contíguos, envoltória);
  escoras pela verificação flexo-axial da corda de beiral (tributária s/2 no beiral, s no centro).
- `main.py` (`D_ESCORA_MM = 20`), catálogo e subseção no relatório.
- Testes: `tests/test_no_contraventamento.py` (3). Suíte 694 passed; 55 verificações; APROVADO.

**Resultados:**
| Escora | N (kN) | flexo-axial η | ligação | R_d (kN) | η lig. |
|---|---|---|---|---|---|
| Beiral | 106,6 | 0,225 | 6×Ø20 (1×6) | 150 | 0,710 |
| Linha central | 213,1 | 0,450 | 16×Ø20 (2×8) | 294 | 0,725 |

Fecha também a **pendência da escora central** da [issue 64](64-caminho-longitudinal-linha-central.md).

**Tese:** nova §8.5.1 “Nó de topo das baías contraventadas” (texto + tabela); §8.5 remete a ela;
contagens (55 verificações, 694 testes).

**Fica para o detalhamento (issues 43/52):** chapa-nó (espessura, soldas, furação), conexão das
diagonais ao nó (já dimensionadas por capacidade) e desenho.
