# 18 — Cavilhas Ø36 mm > limite EC5 §8.6(2) — L1/L1c fora do escopo

- **Tema:** Ligações
- **Prioridade:** P0
- **Normas:** EC5 §8.6(2) (diâmetro de cavilhas < 30 mm)
- **Arquivos:** `mlc_projeto/main.py:142`; `mlc_projeto/connections/connections.py:292-465`, `:746-829`

## Apontamento do orientador
> Verificar se o diâmetro de 36 mm adotado para as cavilhas de L1 e L1c bate com o
> limite do EC5 §8.6(2), que, acho que não pois, restringe o diâmetro de cavilhas a
> valores inferiores a 30 mm. Confirmada a restrição, a ligação está fora do escopo
> normativo e precisa ser repensada — ou com maior número de planos de corte ou com
> parafusos autoperfurantes inclinados.

## Estado atual no código
- `D_BASE_MM = 36` em [main.py:142](../mlc_projeto/main.py).
- Aplicado a L1 ([connections.py:292-465](../mlc_projeto/connections/connections.py)) e
  L1c ([:746-829](../mlc_projeto/connections/connections.py)).
- **Não há** verificação do limite de diâmetro do EC5 §8.6(2) no código — o d é usado
  livremente nas fórmulas de Johansen e nas distâncias mínimas.

## O que precisa ser feito
- [x] Confirmar o limite do EC5 §8.6(2) para **cavilhas**: **6 mm ≤ d ≤ 30 mm** (as
      fórmulas de embutimento de §8.5/§8.6 são calibradas nessa faixa). Ø36 está fora.
- [x] Repensar a ligação: **reduzir d para 24 mm** (M24 padrão, inequivocamente dentro
      do escopo sob qualquer leitura), aumentando o número de pinos.
- [x] Adicionar **guarda** no código que rejeita d fora de [6, 30] mm.
- [~] Tolerâncias de furo (§10): coerentes com cavilha (mantém-se cavilha; sem mudança
      de tipo de conector). Detalhamento de furação → memorial/execução.

## Resolução (implementado)
- **Guarda EC5 §8.6(2)** em [connections.py](../mlc_projeto/connections/connections.py):
  constantes `D_CAVILHA_MIN_MM=6`, `D_CAVILHA_MAX_MM=30` e `_validar_diametro_cavilha`
  (lança `ValueError` fora da faixa). Chamada em `dimensionar_ligacao_base`,
  `dimensionar_ligacao_cumeeira` e `dimensionar_ligacao_base_central`. Resultado da L1
  ganhou `d_norma_ok` e norma "EC5 §8.6(2) 6–30 mm".
- **`main.py`**: `D_BASE_MM` 36 → **24** (L1/L1c). `D_CUM_MM=30` (L2, no limite — a
  cumeeira monolítica é a issue [25](25-L2-pino-cumeeira-remover.md)).
- **`report.py`**: §11 com nota do escopo EC5 §8.6(2) e do diâmetro adotado.
- **Testes**: [test_diametro_cavilha.py](../tests/test_diametro_cavilha.py); atualizado
  `test_connections_nef.py` (usava Ø36, agora Ø24).

## Resultado (redimensionamento, cargas da issue 1)
| d (mm) | n_pinos | layout | η | geometria |
|---|---|---|---|---|
| 36 (antigo, **fora de escopo**) | 48 | 6×8 | 0,71 | — |
| **24 (adotado)** | **96** | **8×12** | **0,697** | OK (L=1080 mm < 1800) |

L1c central Ø24: η=0,726. A guarda rejeita Ø36 e Ø4; aceita 6–30. Pipeline APROVADO.

## Nota (otimização futura, não bloqueante)
O nº de pinos sobe (48→96) por causa do limite de 30 mm + a força axial (F_res≈1226 kN,
que inclui o empuxo H). Reduções possíveis: **múltiplas chapas embutidas** (mais planos
de corte) ou **parafusos autoperfurantes inclinados** (regras próprias). Fica como opção
de detalhamento, fora do escopo mínimo desta issue.

## Critério de aceite
Conector dentro do escopo normativo (cavilha Ø24 ≤ 30 mm) **✓**; ligação L1/L1c
redimensionada **✓**; guarda de diâmetro no código **✓**.
