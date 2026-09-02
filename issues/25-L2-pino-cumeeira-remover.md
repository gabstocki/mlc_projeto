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
- [x] Decisão (confirmada pela usuária): peça **monolítica** → **remover L2/L2c**;
      cumeeira verificada só como **seção** (t90/ápice §6.4.3 — issue 10).
- [x] Remover L2/L2c das tabelas de fadiga, deslizamento e do relatório.
- [x] Limpar `D_CUM_MM` e o legado `analisar_3rotulas`.

## Critério de aceite
Cumeeira coerente com o modelo monolítico: sem ligação fictícia L2; relatório/fadiga
atualizados.

---

## ✅ Resolução (implementada)

**Decisão confirmada:** a viga de cada pórtico é peça única contínua no ápice (sem
junta). L2/L2c eram resquício do modelo triarticulado → **removidos**. A cumeeira
permanece verificada como **SEÇÃO** (t90/ápice §6.4.3, `cumeeira.py`, res "cumeeira").

### Remoções (coerência do modelo)
- `connections.py`: função `dimensionar_ligacao_cumeeira` **deletada**; L2/L2c
  saem de `dimensionar_ligacoes` e `dimensionar_ligacoes_central` (só L1/L3, L1c/L3c);
  `relatorio_ligacoes` sem o ramo L2; parâmetros `d_cum_mm` removidos.
- `fadiga_ligacoes.py`: bloco de fadiga/deslizamento de L2 **removido** (sem pino,
  sem junta → sem deslizamento de cumeeira).
- `main.py`: `D_CUM_MM` removido; L2/L2c fora dos prints, do critério η (issue 22),
  do pacote de relatório e da fadiga (`fadiga_L2`).
- `output/report.py`: L2/L2c e `fadiga_L2` fora do catálogo, das tabelas de ligações,
  da fadiga e do η_máx; nota do critério atualizada (cumeeira = seção, não ligação).
- `core/loads.py`: `analisar_3rotulas` (legado triarticulado, não usado) **deletado**.

### Verificação
- Ligações no pipeline agora: L1, L3, L1c, L3c (sem L2/L2c). Cumeeira coberta pela
  §6.4.3 (t90) e pela flexo-compressão da viga. Status global APROVADO, η_máx=1,00.
- Testes: `test_diametro_cavilha.py` (removido o caso via cumeeira; a guarda de Ø já
  é testada via L1) e `test_connections_nef.py` (sem `d_cum_mm`) atualizados.
  Suíte: 189 testes ✓. PDF/Excel regenerados sem L2, seção da cumeeira preservada.
