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
- [x] Publicar a memória completa de L1: `f_h,0,k`, `M_y,Rk`, modos de Johansen +
      governante, `t₁`/`t₂`, `a₁..a₄`, `n_ef` e `K_ser`.
- [x] Coerência com issues 18 (diâmetro), 19 (bloco), 20 (fendilhamento), 21 (aço).

## Critério de aceite
Memória de L1 completa e reprodutível no memorial (todos os parâmetros listados).

---

## ✅ Resolução (implementada)

### 1) Exposição no resultado de L1 (connections.py)
`dimensionar_ligacao_base` agora publica no dict a memória completa (antes só o
modo governante era exposto):
- `f_h0k_MPa` = 24,0 (Eq. 8.32), `M_y_Rk_Nmm` = 465,3 kN·mm (Eq. 8.30);
- **modos de Johansen** por plano: I=92,1 · **IIIb=26,6 (governa)** · IV=37,6 kN;
  `F_v_Rk_plano_kN` = min = 26,6; `modo_gov`;
- `t1_madeira_mm` = 160 (= b/2); `a1/a2/a3t/a4t` = 120/72/168/72 mm;
- `n_ef_row`=4,54, `n_ef`=54,5; **`K_ser_Nmm`=8982** (ρ_m^1,5·d/23, §7.1 Tab. 7.1,
  computado no próprio L1).

### 2) Subseção "Memória da ligação L1" no memorial (report.py)
Tabela completa (§11): d, t₁, f_h,0,k, M_y,Rk, os 3 modos de Johansen + governante,
F_v,Rd (2 planos, k_mod/γ_M), a₁/a₂/a3t/a4t, n_ef,row/n_ef, K_ser, R≥F_res; mais as
fórmulas (8.32, 8.30, K_ser) e as remissões aos modos frágeis complementares
(bloco §11.3, fendilhamento §8.1.4, aço EN 1993-1-8) e ao escopo §8.6(2) (issue 18).

### Verificação
- Fórmulas conferidas: M_y,Rk=0,3·f_u,k·d^2,6; f_h,0,k=0,082(1−0,01d)ρ_k;
  K_ser=ρ_m^1,5·d/23; F_v,Rk=min dos modos.
- **Testes:** [`tests/test_memoria_L1.py`](../tests/test_memoria_L1.py) (7 casos:
  campos presentes, governante=min, M_y, f_h0k, K_ser, t₁=b/2, n_ef<n).
