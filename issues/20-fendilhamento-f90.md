# 20 — Fendilhamento — F90,Rd (EC5 §8.1.4)

- **Tema:** Ligações
- **Prioridade:** P1
- **Normas:** EC5 §8.1.4 (Eq. 8.4 / 8.5 — splitting; capacity F90,Rd)
- **Arquivos:** `mlc_projeto/connections/connections.py` (verificação inexistente)

## Apontamento do orientador
> Verificações ausentes para ligações: fendilhamento — F90,Rd (EC5 §8.1.4).

## Estado atual no código
- Nenhuma verificação de fendilhamento (splitting) por componente de força
  **perpendicular às fibras** nas ligações.

## O que precisa ser feito
- [ ] Identificar as ligações com componente de força ⊥ às fibras (F_90,Ed) — a
      resultante inclinada em L1 tem componente vertical (⊥ eixo) relevante.
- [ ] Implementar a capacidade ao fendilhamento EC5 §8.1.4:
      `F_90,Rk = 14·b·w·√(h_e/(1 − h_e/h))`, com `w` e `h_e` conforme a norma.
- [ ] Verificar `F_90,Ed ≤ F_90,Rd` e integrar ao relatório.

## Critério de aceite
Verificação de fendilhamento (F90,Rd) implementada onde houver força perpendicular às
fibras, com η reportado.
