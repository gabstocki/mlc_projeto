# 16 — Terça: interação flexão + compressão combinada (Eq. 6.23/6.24)

- **Tema:** Terças
- **Prioridade:** P1
- **Normas:** EC5 §6.3.2, Eq. 6.23 / 6.24
- **Arquivos:** `mlc_projeto/checks/elu/tercas.py:155-160`; `mlc_projeto/checks/elu/contraventamento.py` (terça-biela); `mlc_projeto/main.py:525-547`

## Apontamento do orientador
> Na terça, corrigir a interação flexão e compressão, que deve ser verificada de
> forma combinada (fez separada: 0,299 e 0,075) — EC5 §6.3.2, Eq. 6.23/6.24.

## Estado atual no código
- A verificação de flexão da terça é **biaxial** (Eq. 6.12), sem termo de compressão:
  [tercas.py:155-160](../mlc_projeto/checks/elu/tercas.py).
- Quando a terça atua como **terça-biela** (elemento de contraventamento), ela recebe
  **compressão axial** de estabilização (§9.2.5) além da flexão da cobertura. Hoje a
  compressão (η≈0,075) e a flexão (η≈0,299) são reportadas **separadamente**
  (ver `res_elu["contraventamento"]["terca"]` e `res_elu["terca"]` em
  [main.py:529-547](../mlc_projeto/main.py)).

## O que precisa ser feito
- [ ] Combinar flexão + compressão axial na terça-biela conforme EC5 §6.3.2:
      `σ_c,0,d/(k_c·f_c,0,d) + σ_m,y,d/f_m,d + k_m·σ_m,z,d/f_m,d ≤ 1` (Eq. 6.23) e a
      permutação (Eq. 6.24).
- [ ] Usar a **mesma combinação de ações** para os dois efeitos (concomitância real).
- [ ] Reportar um único η combinado no relatório em vez de dois valores isolados.

## Critério de aceite
Terça-biela verificada com interação combinada (Eq. 6.23/6.24), η único reportado.
