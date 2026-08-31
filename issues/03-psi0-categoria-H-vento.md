# 03 — ψ₀ categoria H = 0: sobrecarga de cobertura não combina com vento

- **Tema:** Ações e combinações
- **Prioridade:** P1
- **Normas:** EN 1990 Tab. A1.1; EN 1991-1-1 §3.3.2(1)
- **Arquivos:** `mlc_projeto/core/loads.py:55`, `:472-473`, `:490-495`

## Apontamento do orientador
> Outro fator na combinação que precisa ser verificado: 1,05Q combinado com vento.
> O EN 1990 (Tab. A1.1; EN 1991-1-1 §3.3.2(1)) prevê que, para cobertura não
> acessível (categoria H), ψ₀ = 0, e a sobrecarga de cobertura não se combina com
> vento.

## Estado atual no código
- `PSI_0_Q = 0.70` em [loads.py:55](../mlc_projeto/core/loads.py).
- Combinação com **vento dominante** aplica `ψ₀·1,5·Q = 1,05Q` como acompanhante:
  [loads.py:472-473](../mlc_projeto/core/loads.py)
  (`1,35G + 1,5W + 1,05Q`).
- Combinação com **Q dominante** aplica `ψ₀,W·1,5·W = 0,9W`:
  [loads.py:490-495](../mlc_projeto/core/loads.py).

## O que precisa ser feito
- [x] Para categoria H, adotar **ψ₀,Q = 0**: removida a parcela `1,05Q` das
      combinações com vento dominante (ELU_W_*/ELU_S_*).
- [x] Q e vento **não concomitantes**: removido o vento das combinações de Q
      dominante (EN 1991-1-1 §3.3.2(1)).
- [x] Duas famílias separadas: (a) `ELU_Q = 1,35G+1,5Q` (sem vento); (b) vento
      dominante `1,35G+1,5W` e `0,9G+1,5W` (sem Q). Governante reavaliado.
- [x] ELS característico coerente: `ELS_S1 = G+Q` (sem vento).

## Resolução (implementado)
- **`loads.py`**: `PSI_0_Q = 0.00` (cat. H, era 0,70); no laço de padrões geram-se
  só `ELU_W` (1,35G+1,5W) e `ELU_S` (0,9G+1,5W), **sem Q**; a sobrecarga entra numa
  **única** combinação `ELU_Q = 1,35G+1,5Q` (duração «média», EC5 Tab. 2.1), sem
  vento. `ELU_C1` e `ELS_S1` idem (sem vento). Governante por |M| agora considera
  todas as combinações gravíticas (vento-pressão + Q).
- **`report.py`**: §4 com nota de concomitância (EN 1990 Tab. A1.1 + EN 1991-1-1
  §3.3.2(1); vento pela **NBR 6123:2023**).
- **Testes**: [test_combinacoes_catH.py](../tests/test_combinacoes_catH.py); atualizado
  `test_vento_cpe.py` (contagem 24 → 17).

## Efeitos (com o modelo corrigido)
- **Combinações ELU: 24 → 17** (8×2 vento + 1 Q) — reflete a não-concomitância.
- **M governante** (ELU_C2) cai de −294 → **−265,5 kN·m** (sem o 1,05Q); H de
  1216 → **1098 kN**.
- **Bônus (resolve a ambiguidade da issue 13):** o pilar central deixa de ser
  governado pela antiga combinação Q-dominante rotulada «longa» (η=0,868) e passa a
  ser governado por `ELU_W` (curta) com **η=0,31** — agora consistente com o
  EC5 §3.1.3 (o combo de Q puro é «média», não «longa»).

## Nota de escopo
- ψ₁ (combinação frequente ELS_S2) permanece 0,5 → **issue [5](05-psi1-combinacao-frequente.md)**
  (categoria H: ψ₁=0).
- Coeficiente de G favorável (0,9) na sucção → **issue [4](04-coef-G-favoravel-C3.md)**.
- Vento-dominante em ELS (uplift) e wfin → **issue [6](06-wfin-vento-psi2.md)**.

## Critério de aceite
Combinações revisadas sem concomitância Q+W para categoria H **✓**; ψ₀,Q = 0
documentado (§4) **✓**.
