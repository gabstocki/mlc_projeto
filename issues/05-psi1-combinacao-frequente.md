# 05 — Combinação frequente ψ₁ categoria H = 0

- **Tema:** Ações e combinações (ELS)
- **Prioridade:** P2
- **Normas:** EN 1990 Tab. A1.1 (valores ψ para categoria H)
- **Arquivos:** `mlc_projeto/core/loads.py:57`, `:586-591`

## Apontamento do orientador
> A combinação frequente adota G + 0,5Q; verificar se, para categoria H, ψ₁ = 0.

## Estado atual no código
- `PSI_1_Q = 0.50` em [loads.py:57](../mlc_projeto/core/loads.py).
- Combinação frequente `ELS_S2 = G + 0,5Q`, [loads.py:586-591](../mlc_projeto/core/loads.py).

## O que precisa ser feito
- [ ] Confirmar na EN 1990 Tab. A1.1 (e Anexo Nacional) os valores de ψ₁ e ψ₂ para
      **categoria H**. Tipicamente ψ₀ = ψ₁ = ψ₂ = 0 para coberturas não acessíveis.
- [ ] Se ψ₁ = 0, a combinação frequente passa a `G` (Q não aparece) — ajustar
      `ELS_S2` e a rotulagem.
- [ ] Coerência com issue [06](06-wfin-vento-psi2.md) (ψ₂ na flecha final).

## Critério de aceite
ψ₁ para categoria H confirmado e aplicado na combinação frequente; fonte citada.
