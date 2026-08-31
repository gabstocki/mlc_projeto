# 19 — Ruptura de bloco na ligação de 64 pinos

- **Tema:** Ligações
- **Prioridade:** P0
- **Normas:** EC5 §8.1.4 e Anexo A (block/plug shear); EN 1995-1-1 Anexo A
- **Arquivos:** `mlc_projeto/connections/connections.py:292-465` (verificação inexistente)

## Apontamento do orientador
> Verificações ausentes para ligações: ruptura de bloco na ligação de 64 pinos com
> chapa embutida.

## Estado atual no código
- L1 dimensiona a malha de pinos por Johansen + n_ef (grupo)
  ([connections.py:355-432](../mlc_projeto/connections/connections.py)), com layout que
  pode chegar a dezenas de pinos.
- **Não há** verificação de **ruptura de bloco/plug** (falha frágil do bloco de
  madeira delimitado pelo grupo de conectores) — EC5 Anexo A.

## O que precisa ser feito
- [x] Implementar a verificação de ruptura de bloco (EC5 Anexo A, Eq. A.1–A.3):
      `F_bs,Rk = max(1,5·A_net,t·f_t,0,k ; 0,7·A_net,v·f_v,k)`.
- [x] Calcular as áreas líquidas a partir do layout real (n_par, n_perp, a1, a2, a3t).
- [x] Integrar no pipeline e no relatório, com η próprio.
- [x] Aplicar à L1 e à L1c (grupos de cavilhas).

## Formulação (EN 1995-1-1 Anexo A, texto normativo confirmado)
    F_bs,Rk = max{ 1,5·A_net,t·f_t,0,k ; 0,7·A_net,v·f_v,k }     (A.1)
    A_net,t = L_net,t·t_1  (A.2) ;  A_net,v = L_net,v·t_1  (A.3, block shear Fig. A.1)
    L_net,t = (n_⊥−1)·a2 ;  L_net,v = 2·[(n_∥−1)·a1 + a3,t] ;  t_1 = b

## Resolução (implementado)
- **`ruptura_de_bloco`** (função pura) e **`ruptura_de_bloco_ligacao`** (lê o layout
  real da ligação) em [connections.py](../mlc_projeto/connections/connections.py).
  γ_M = 1,25 (glulam, material — a ruptura de bloco é falha do material da peça).
- **`main.py`**: calcula para L1 e L1c (Fase 4), imprime os dois termos e η.
- **`report.py`**: §11.3 (memória + nota crítica) + linhas no resumo §12.
- **Testes**: [test_ruptura_bloco.py](../tests/test_ruptura_bloco.py).

## Resultados (layout Ø24 — issues 1/18)
| Ligação | grupo | tração (A.1) | cisalh. (A.1) | F_bs,Rd | F_//,Ed | η (Anexo A) | η só-cisalh. |
|---|---|---|---|---|---|---|---|
| **L1** | 8×12 | 7299 kN | 1580 kN | 4088 kN | 1226 kN | **0,300** | **1,385** |
| **L1c** | — | 4645 kN | 2333 kN | 2601 kN | 1226 kN | **0,471** | 0,938 |

## ⚠ Nota crítica de transparência
A Eq. (A.1) usa `max{}` e é **governada pela tração** (bloco largo → grande A_net,t),
dando η<1. Porém o **mecanismo de cisalhamento isolado** da L1 dá **η≈1,39** — a
formulação `max{}` do Anexo A é reconhecidamente **pouco conservadora** para grupos
grandes. Pela norma, a ligação passa; mas recomenda-se, no detalhamento, **distribuir
o grupo / usar múltiplas chapas** (mais planos de corte, menos pinos por plano) para
trazer o mecanismo de cisalhamento a η≤1 — mesma direção da otimização da issue
[18](18-cavilhas-diametro-36mm.md). Registrado no relatório (§11.3).

## Critério de aceite
Ruptura de bloco implementada (Anexo A) para L1 e L1c, com η reportado, memória de
cálculo (§11.3) e a ressalva do `max{}`/cisalhamento **✓**.
