# 105 — Concepção das ligações e padrão gráfico dos desenhos

- **Tema:** Ligações e desenhos (pedido do autor após a 104)
- **Prioridade:** P1
- **Origem:** "os desenhos podem ser simplificados, muitas cavilhas; pense como projetista e cadista experiente"

## Resolução ✅ (2026-11-11)

### Concepção — compressão por contato, tração por uma peça de aço
1. **Tirante interno nos pilares correntes** (`connections/tirante_interno.py`, novo):
   - Barra 8.8 galvanizada num furo central (d + 16, ranhura nas lamelas centrais).
   - No topo, rosqueia numa luva soldada sob a chapa de topo ou a sela. No pé, porca e arruela-chapa Ø80 por dentro do pilarete, com janela de 60×110 no tubo.
   - L3: M20 (η 0,70); L3c: M27 (0,64); L3f: M20 (0,59). Alvo 0,75 (via única de tração). Solda da luva: 0,70–0,78.
   - Pilarete: chapa de topo como placa circular com carga central, mais a seção na janela (`verificar_pilarete(tirante=…)`).
   - Topo: 2 cavilhas de posicionamento. Pé: 4 cavilhas, pelo cortante do choque.
   - As fileiras contornam o furo, com os novos parâmetros `n_vert_min` e `a2_min_mm` em `dimensionar_ligacao_axial_escora`.
2. **Nó do pilar bipartido por contato:**
   - A chapa-capa no topo da lâmina leva D = 173 kN a 4,0 MPa (η 0,32).
   - A aba tem 2 cavilhas para o arrancamento das terças (30 kN, η 0,75). Antes eram 18 cavilhas.
3. **Chapas duplas** (`n_chapas=2`):
   - Quatro planos de corte por cavilha: Eq. 8.11 nas partes externas e 8.13 na central. Por cavilha, 33,1 kN contra 25,0.
   - Escoras: beiral 9 → 5, central 20 → 15.
   - Montante: 8 → 6 por lado, no rasgo superior de 171 mm.
4. **Família única:** Ø20 em todas as cavilhas e chapas de 20 mm.

**Contagem de cavilhas Ø20 na obra: 1.448 → 928 (−36 %).** Por ligação:

| Ligação | Antes | Depois |
|---|---|---|
| Topo e pé, L3 / L3c / L3f | 16 / 28 / 12 | 6 / 6 / 6 |
| Nó do bipartido | 18 | 2 |

Fora do alcance desta rodada, e restante: a sela e o pé das lâminas dos bipartidos (448). São candidatos a um tirante por lâmina numa próxima rodada, agora rastreada na [issue 108](108-tirante-por-lamina-bipartido.md).

A terça foi revista pela varredura e continua 0,20×0,40. Agora governa a escora central como peça (0,74), e não mais a sua ligação.

### Padrão gráfico
- **DES-00, notas gerais:** materiais, proteção, soldas, furos e folgas, convenções e lista de folhas. As notas repetidas saíram de todas as folhas (`REF_GERAIS`).
- **Marcas e listas:**
  - balões de marca (`_balao`);
  - listas de peças com marca, descrição, quantidade, aço e massa (`_lista_pecas`) nas DES-05, 05B, 07 e 07B;
  - quadro de variantes (`_tabela`) na DES-06.
- **Linhas e hachuras:** espessuras de linha `LW_CORTE`, `LW_VISTA` e `LW_FINA`; sem a hachura de pontos na madeira cortada.
- **Folhas: 17 → 16**, incluindo a DES-00:
  - topo dos pilares (ex-DES-11) incorporado às DES-05/05B;
  - pilarete (ex-DES-14) incorporado ao quadro da DES-06;
  - renumeradas: DES-07B (bipartido), DES-09B (juntas das terças), DES-11 (terminais).
- **Tese:**
  - cap08: `ssec:topo-pilar` virou "Tirante interno"; cadeia da base; tabelas de bases, bloco, margens, nó de topo e montante; o bipartido com o nó por contato; a proteção remete à DES-00;
  - cap04: tirantes 8.8;
  - cap05: terça;
  - cap09: 16 folhas;
  - Apêndice E reordenado.

**Verificação:** pipeline APROVADO, η_max 0,90; 846 testes passam (`test_concepcao_ligacoes.py`, novo); tese com 167 páginas, 0 overfull, nenhuma referência pendente.
