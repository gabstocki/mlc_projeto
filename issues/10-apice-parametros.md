# 10 — Zona do ápice: documentar kdis, kvol, Vap, σt,90, kr

- **Tema:** Viga — zona do ápice (cumeeira)
- **Prioridade:** P2
- **Normas:** EC5 §6.4.3, Eq. 6.50 a 6.54
- **Arquivos:** `mlc_projeto/checks/elu/cumeeira.py`

## Apontamento do orientador
> Zona do ápice detalhada: kdis, kvol, Vap, σt,90 e kr (EC5 §6.4.3, Eq. 6.50 a 6.54);
> tem material na apostila também.
> [Bloco de reprodutibilidade] Parâmetros da zona do ápice: kdis, kvol, Vap e kr.

## Estado atual no código
- [cumeeira.py](../mlc_projeto/checks/elu/cumeeira.py) já calcula a verificação de
  tração perpendicular na cumeeira (funções `calcular_k_p`, `calcular_k_vol`,
  `calcular_sigma_t90d`, `K_DIS` — usadas em
  [apoio.py:138-140](../mlc_projeto/checks/elu/apoio.py)).
- O **memorial** não expõe os parâmetros nem o volume de referência V_ap; publica só
  o resultado. Falta conferir `k_r` (raio/lamela) para viga de duplo-bisel.

## O que precisa ser feito
- [ ] Verificar se todos os parâmetros do §6.4.3 estão implementados: **k_dis, k_vol,
      V_ap** (volume da zona do ápice), **σ_t,90,d** e **k_r**.
- [ ] Confirmar a aplicabilidade a **viga de duplo-bisel** (double tapered) vs curva.
- [ ] Expor no memorial cada parâmetro, sua fórmula e valor (Eq. 6.50–6.54).

## Critério de aceite
Todos os parâmetros da zona do ápice calculados e publicados no memorial com as
equações do EC5 §6.4.3.
