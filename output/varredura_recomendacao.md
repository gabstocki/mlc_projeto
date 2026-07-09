# Varredura factível — pórtico de 3 rótulas (EC5)

**Data:** 2026-07-08  
**Concepção mantida:** pórtico isostático de 3 rótulas · MLC GL24h · CS2 · vão L = 20,25 m · espaçamento L_t = 5,75 m · pórtico intermédio (área tributária = L_t) · terças s = 2,53 m  

**Modelo estrutural (RM):** intradorso horizontal · rótulas no centroide ·  
`f_c = (h_ap − h0)/2 = (L/4)·tan(α)` · `H = (q·L²/8)/f_c`

**Normas:** EN 1995-1-1 (com A1: `k_cr`), EN 1990, EN 14080:2013, NBR 6123 (vento)

---

## Por que α = 4,5° original é inviável

Com `α = 4,5°`, `f_c ≈ 0,40 m` e cargas de intermédio:

| Grandeza | Ordem de grandeza |
|----------|-------------------|
| H | ~2500 kN |
| N na viga | ~2500 kN |
| F_res na L1 | ~2500 kN |

A ligação de base (pinos EC5 §8) **não fecha** geometria de distâncias mínimas Tab. 8.2 na secção do apoio. Não é falha de “calibragem”: é estática do arco abatido de 3 rótulas.

---

## Resultados da varredura

- Grelha: `α ∈ [6; 18]°`, `h0 ∈ [0,60; 1,10] m`, `b ∈ [0,22; 0,34] m`
- **57 combinações** com todas as η ≤ 1 (viga, ELS, apoio, pilar, L1/L2/L3 factíveis)
- CSV: `output/varredura_factivel.csv`

### Candidatas validadas (pipeline completo)

| ID | α | h0 | b | Pilar | l_ap | L1 | H | η_gov | Notas |
|----|---|----|----|-------|------|-----|---|-------|-------|
| **A** | 9,5° | 0,90 | 0,32 | 0,22×0,22 | 0,70 | 36×d30 | 1243 kN | 0,97 | α **mínima** que passa |
| **B** | 10° | 0,65 | 0,30 | 0,22×0,22 | 0,70 | 36×d30 | 1189 kN | 0,99 | **menor volume** madeira |
| **C** | 10° | 0,70 | 0,30 | 0,22×0,22 | 0,70 | 36×d30 | 1189 kN | 0,99 | **recomendada** (margem cis.) |
| **D** | 12° | 0,70 | 0,28 | 0,22×0,22 | 0,60 | 30×d30 | 1017 kN | 0,98 | menos pinos, H menor |
| **E** | 12° | 0,75 | 0,28 | 0,22×0,22 | 0,60 | 30×d30 | 1017 kN | 0,98 | margem extra em cis. |

### Recomendação adotada no `main.py`: **C**

```
L = 20,25 m
α = 10,0°
h0 = 0,70 m
b  = 0,30 m
h_ap ≈ 2,485 m
f_c ≈ 0,893 m
l_ap = 0,70 m
pilar lateral = 0,22 × 0,22 m
pilar central = 0,26 × 0,26 m (inalterado em conceito)
pinos L1 = d30, malha ~6×6 (n=36)
pinos L2 = d30
chumbadores L3 = M20 @ 80 kN → n ≈ 15 (H≈1189 kN)
```

**Critério de escolha:** menor α próximo da concepção original entre soluções robustas; `h0` com margem face a η_cis ≈ 0,95 de B; secções comerciais; todas as verificações EC5 implementadas com η ≤ 1.

---

## Verificações exigidas (todas η ≤ 1 em C)

| Verificação | Norma |
|-------------|--------|
| Cumeeira t90 | EC5 §6.4.3 (M≈0 → η=0) |
| Flambagem lateral | EC5 §6.3.3 Eq. 6.32–6.33 |
| Flexo-compressão + LTB | EC5 §6.3.2 Eq. 6.23–6.24 + §6.3.3 Eq. 6.35 |
| Cisalhamento | EC5 §6.1.7 (`b_ef = k_cr·b`) |
| Apoio c90 + Hankinson | EC5 §6.1.5 + §6.2.2 |
| Pilar compressão | EC5 §6.3.2 |
| ELS flecha | EC5 §2.3.2.2 + Tab. 7.2 |
| Terças | EC5 §6.1.6–6.1.7 + Tab. 7.2 |
| Contraventamento | EC5 §9.2 + EN 1993-1-1 |
| Ligações pinos | EC5 §8.2–8.6, γ_M=1,30 |
| Sapata/chumbadores | EN 1993-1-8 / EN 1992-4 (simplificado) |
| Deslizamento / alternadas | EC5 §7.1 + §8.1.5 |

---

## Observações de engenharia (sem abandonar a norma)

1. **Empuxo H** continua da ordem de **1 MN** mesmo com α=10°. A fundação e os chumbadores são dimensionantes (L3).
2. **h_ap ≈ 2,5 m** resulta do bisel com α=10° e vão 20 m — fabricável em MLC, mas exige logística de transporte/montagem.
3. Alternativa **D (α=12°)** reduz H e o número de pinos (30) se a arquitetura aceitar cobertura mais inclinada.
4. **Não se adotou** tirante nem mudança para pórtico rígido: isso alteraria a concepção. Se no futuro H for inaceitável em fundação, o caminho normativo é **outro sistema** (autorização explícita), não “ajustar” H no modelo de 3 rótulas.
