# 25 — L2 pino Ø30 na cumeeira: resquício do modelo triarticulado

- **Tema:** Modelo — coerência
- **Prioridade:** P1
- **Normas:** coerência do modelo (peça monolítica de MLC)
- **Arquivos:** `mlc_projeto/connections/connections.py:470-544`, `:934-935`; `mlc_projeto/main.py:143`; `mlc_projeto/connections/fadiga_ligacoes.py`

## Apontamento do orientador
> O memorial afirma tratar-se de peça única de dupla inclinação com continuidade
> física da MLC. Não existe, portanto, ligação na cumeeira. Ainda assim a seção 11
> apresenta L2 como pino passante Ø30 mm, verificado exclusivamente à compressão axial,
> com entradas próprias nas tabelas de fadiga e deslizamento. Eu acho que faltou
> eliminar do modelo triarticulado anterior.

## Estado atual no código
- O sistema é **monolítico/contínuo na cumeeira** (sem rótula) — [loads.py:4-27](../mlc_projeto/core/loads.py),
  [main.py:7](../mlc_projeto/main.py).
- Mesmo assim, `dimensionar_ligacao_cumeeira` cria **L2** com pino passante Ø30
  ([connections.py:470-544](../mlc_projeto/connections/connections.py)) e L2c
  ([:934-935](../mlc_projeto/connections/connections.py)), e o pipeline os inclui em
  fadiga/deslizamento ([main.py:639-643](../mlc_projeto/main.py),
  [fadiga_ligacoes.py](../mlc_projeto/connections/fadiga_ligacoes.py)) e no relatório.
- `D_CUM_MM = 30` ([main.py:143](../mlc_projeto/main.py)) ainda é passado.

## O que precisa ser feito
- [ ] Decidir: se a peça é monolítica, **remover L2/L2c** como ligação de cumeeira
      (não há junta); manter apenas a verificação da **seção** na cumeeira
      (t90/ápice — issue [10](10-apice-parametros.md)) se aplicável.
- [ ] Se por montagem existir uma emenda real na cumeeira, então **modelar a emenda**
      corretamente (transferência de M, V, N), não um "pino só à compressão".
- [ ] Remover L2/L2c das tabelas de fadiga, deslizamento e do relatório se eliminada.
- [ ] Limpar `D_CUM_MM` e o legado `analisar_3rotulas`
      ([loads.py:237-288](../mlc_projeto/core/loads.py)) se não usados.

## Critério de aceite
Cumeeira coerente com o modelo monolítico: sem ligação fictícia L2, ou emenda real
devidamente modelada; relatório/fadiga atualizados.
