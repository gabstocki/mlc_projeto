# 29 — Memória da ligação L1 (Johansen, fh,0,k, My,Rk, t1/t2, a1–a4, Kser)

- **Tema:** Reprodutibilidade do memorial
- **Prioridade:** P1
- **Normas:** EC5 §8.2 (Johansen), §8.5.1.1 (n_ef), §8.3 (distâncias), §7.1 (Kser)
- **Arquivos:** `mlc_projeto/connections/connections.py:53-465`; `mlc_projeto/connections/fadiga_ligacoes.py`

## Apontamento do orientador
> [Bloco de reprodutibilidade] Ligação L1: modos de ruptura de Johansen, fh,0,k,
> My,Rk, espessuras t₁ e t₂, espaçamentos a₁ a a₄ e módulo de deslizamento Kser.

## Estado atual no código
- Tudo isto é **calculado**, mas não integralmente publicado:
  - Modos de Johansen e governante:
    [connections.py:92-156](../mlc_projeto/connections/connections.py).
  - `f_h,k` ([:55-71](../mlc_projeto/connections/connections.py)) e
    `M_y,Rk` ([:74-87](../mlc_projeto/connections/connections.py)).
  - Espessuras `t = b/2` ([:338](../mlc_projeto/connections/connections.py)); confirmar
    a nomenclatura `t₁/t₂` (madeira × chapa).
  - Distâncias `a1..a4` ([:189-219](../mlc_projeto/connections/connections.py)).
  - `K_ser`: usado na fadiga/deslizamento
    ([fadiga_ligacoes.py](../mlc_projeto/connections/fadiga_ligacoes.py)) — confirmar a
    fórmula EC5 §7.1 (Tab. 7.1) e publicar.

## O que precisa ser feito
- [ ] Publicar no memorial a memória completa de L1: `f_h,0,k`, `M_y,Rk`, os **modos de
      Johansen** com o governante, `t₁`/`t₂`, `a₁..a₄`, `n_ef` e `K_ser`.
- [ ] Coerência com issues [18](18-cavilhas-diametro-36mm.md) (diâmetro),
      [19](19-ruptura-de-bloco.md), [20](20-fendilhamento-f90.md),
      [21](21-chapas-aco-en1993.md).

## Critério de aceite
Memória de L1 completa e reprodutível no memorial (todos os parâmetros listados).
