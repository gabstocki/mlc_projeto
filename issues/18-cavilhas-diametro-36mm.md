# 18 — Cavilhas Ø36 mm > limite EC5 §8.6(2) — L1/L1c fora do escopo

- **Tema:** Ligações
- **Prioridade:** P0
- **Normas:** EC5 §8.6(2) (diâmetro de cavilhas < 30 mm)
- **Arquivos:** `mlc_projeto/main.py:142`; `mlc_projeto/connections/connections.py:292-465`, `:746-829`

## Apontamento do orientador
> Verificar se o diâmetro de 36 mm adotado para as cavilhas de L1 e L1c bate com o
> limite do EC5 §8.6(2), que, acho que não pois, restringe o diâmetro de cavilhas a
> valores inferiores a 30 mm. Confirmada a restrição, a ligação está fora do escopo
> normativo e precisa ser repensada — ou com maior número de planos de corte ou com
> parafusos autoperfurantes inclinados.

## Estado atual no código
- `D_BASE_MM = 36` em [main.py:142](../mlc_projeto/main.py).
- Aplicado a L1 ([connections.py:292-465](../mlc_projeto/connections/connections.py)) e
  L1c ([:746-829](../mlc_projeto/connections/connections.py)).
- **Não há** verificação do limite de diâmetro do EC5 §8.6(2) no código — o d é usado
  livremente nas fórmulas de Johansen e nas distâncias mínimas.

## O que precisa ser feito
- [ ] Confirmar o limite do EC5 §8.6(2) para **cavilhas** (dowels): d ≤ 30 mm (e d ≥ 6 mm).
- [ ] Como Ø36 mm excede o limite, **repensar a ligação**, por exemplo:
      - reduzir d (≤ 30 mm) aumentando o **número de pinos/planos de corte**; ou
      - usar **parafusos passantes** (bolts, cujo limite difere) devidamente verificados; ou
      - **parafusos autoperfurantes inclinados** (fully threaded screws) conforme regras próprias.
- [ ] Adicionar uma **verificação/guardas** no código que rejeite d fora do escopo do
      conector escolhido.
- [ ] Rever tolerâncias de furo (§10) coerentes com o tipo de conector.

## Critério de aceite
Conector dentro do escopo normativo (cavilha ≤ 30 mm ou outro tipo justificado);
ligação L1/L1c redimensionada; guarda de diâmetro no código.
