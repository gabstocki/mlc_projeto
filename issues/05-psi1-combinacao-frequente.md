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
- [x] Confirmado na EN 1990 Tab. A1.1: categoria H → **ψ₀ = ψ₁ = ψ₂ = 0**.
- [x] `PSI_1_Q = 0,00` (era 0,50) → combinação frequente `ELS_S2 = G` (sem Q).
- [x] Rotulagem ajustada (loads.py e docstring de deflection_els.py).
- [x] Coerência com issues [03](03-psi0-categoria-H-vento.md) (ψ₀) e
      [06](06-wfin-vento-psi2.md) (ψ₂/wfin).

## Resolução (implementado)
- **`loads.py`**: `PSI_1_Q = 0.00` (cat. H). `ELS_S2 = G + ψ₁·Q = G`.
- **`deflection_els.py`**: docstring das combinações ELS atualizado (S1=G+Q; S2=G; S3=G).
- **Testes**: `test_combinacoes_catH.py` (ψ₁=ψ₂=0; S2=S3=G).

## Fato relevante
Para categoria H (ψ₁=ψ₂=0), a combinação **frequente** (`ELS_S2`) e a
**quase-permanente** (`ELS_S3`) **reduzem-se ambas a G** — numericamente idênticas
(g_k ≈ 4,73 kN/m). A sobrecarga só aparece no **característico** (`ELS_S1 = G+Q`) e a
distinção entre S2 e S3 deixa de ter efeito. Efeito só no valor **informativo** da
flecha frequente (w_S2 diminui); nenhuma η muda.

## Critério de aceite
ψ₁ para categoria H confirmado (EN 1990 Tab. A1.1) e aplicado na combinação frequente
(ELS_S2 = G), com fonte citada **✓**.
