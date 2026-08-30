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
- [ ] Implementar a verificação de ruptura de bloco (EC5 Anexo A):
      `F_bs,Rk = max(1,5·A_net,t·f_t,0,k ; 0,7·A_net,v·f_v,k)` (conforme a norma).
- [ ] Calcular as áreas líquidas de tração e cisalhamento a partir do layout real
      (espaçamentos a1..a4, nº de fileiras/colunas, espessura).
- [ ] Integrar no pipeline de ligações e no relatório, com η próprio.
- [ ] Aplicar também à L1c (pilar central) e onde houver grupos de pinos.

## Critério de aceite
Verificação de ruptura de bloco implementada para as ligações com grupos de pinos,
com η reportado e memória de cálculo.
