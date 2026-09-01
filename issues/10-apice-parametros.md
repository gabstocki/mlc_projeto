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
- [x] Verificar se todos os parâmetros do §6.4.3 estão implementados: **k_dis, k_vol,
      V_ap** (volume da zona do ápice), **σ_t,90,d** e **k_r**.
- [x] Confirmar a aplicabilidade a **viga de duplo-bisel** (double tapered) vs curva.
- [x] Expor no memorial cada parâmetro, sua fórmula e valor (Eq. 6.50–6.54).

## Critério de aceite
Todos os parâmetros da zona do ápice calculados e publicados no memorial com as
equações do EC5 §6.4.3.

## Resolução (2026-08-31)
Fontes conferidas no **texto integral da EN 1995-1-1:2004+A1:2008 §6.4.3** (Eq.
6.41–6.56, lidas do PDF da norma) e no manual de teoria da SCIA (fórmula fechada
dos volumes para duplo-bisel, Ref. Blaß).

**Correções/adições em [cumeeira.py](../mlc_projeto/checks/elu/cumeeira.py):**
- **V_ap corrigido** (era `0,15·b·h_ap²`, ad hoc e **não-conservador**):
  `V_b = b·L·[h_ap − 0,25·L·tan(α_ap)]` e `V = b·h_ap²·[1 − 0,25·tan(α_ap)] ≤ 2·V_b/3`
  (`calcular_volumes_apice`). Para a viga do projeto V passa de ~0,37 → **1,77 m³**,
  logo `k_vol` cai de ~0,49 → **0,355** e a η de tração ⊥ sobe de ~0,16 → **0,32**
  (a antiga superestimava a resistência).
- **k_r = 1,0** (duplo-bisel, §6.4.3(5)) e **k_l = 1 + 1,4·tanα_ap + 5,4·tan²α_ap**
  (`calcular_k_l`; r→∞ ⇒ termos em h_ap/r somem, Eq. 6.43/6.44).
- **Verificação de flexão no ápice** (Eq. 6.41/6.42): `σ_m = k_l·6M_ap/(b·h_ap²) ≤
  k_r·f_m,d` (`calcular_sigma_m_ap`) — antes ausente.
- `verifica_cumeeira` agora expõe **k_p, k_l, k_r, k_dis, k_vol, V_ap, V_b, V,
  σ_t,90,d, σ_m,ap, η_t90, η_flexão_ap** e reporta η = max(...) com o governante.
- Atualizados todos os chamadores de `calcular_k_vol` (nova assinatura com L e α):
  apoio, cisalhamento, flambagem_lateral (varreduras) e creep.

**Resultado (GL24h, α_ap=10°, M_ap≈−395 kN·m ELU gov.):** k_p=0,035, k_dis=1,4,
k_vol=0,355, k_l=1,415, k_r=1,0 → η_t90 = **0,32** (governa), η_flexão_ap = 0,13
⇒ **η = 0,32 (OK)**.

**Memorial:** nova subseção "Zona do ápice / cumeeira (§6.4.3)" com as duas
verificações, os volumes (Fig. 6.9) e todos os parâmetros/fórmulas; linha na tabela
§7 renomeada para "Zona do ápice ($t_{90}$ e $\sigma_m$)". LaTeX compila (pdflatex).

**Testes:** [test_cumeeira_apice.py](../tests/test_cumeeira_apice.py) (constantes
duplo-bisel; fórmulas k_p/k_l; volumes; k_vol correto < aproximação antiga; exposição
de todos os parâmetros). Suíte: 124 passam.

**Relação com issue 9 (§6.4.2):** a §6.4.2 (face inclinada, `misula.py`) trata as
partes em bisel simples; a §6.4.3 (aqui) trata a zona do ápice. Complementares
(EN 1995-1-1 §6.4.3(2)).
