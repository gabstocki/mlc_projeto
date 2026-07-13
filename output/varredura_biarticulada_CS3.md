# Varredura — biarticulada + **CS3 global**

**Data:** 2026-07-12  
**Modelo:** viga MLC monolítica biarticulada (Castigliano, \(y_c\) centroide, ∫dx)  
**Material:** GL24h, **classe de serviço 3**  
**CSV:** `output/varredura_biarticulada_CS3.csv` — **386** combinações aprovadas  

---

## 1. O que muda com CS3 (EC5 Tab. 3.1 / 3.2)

| Parâmetro | CS2 | **CS3** | Efeito |
|-----------|-----|---------|--------|
| \(k_{mod}\) curta (ELU vento) | 0,90 | **0,70** | \(f_d\) **−22%** |
| \(k_{mod}\) longa | 0,70 | **0,55** | −21% |
| \(k_{mod}\) permanente | 0,60 | **0,50** | −17% |
| \(k_{def}\) | 0,80 | **2,00** | fluência **×2,5** |
| \(\gamma_M\) peças | 1,25 | 1,25 | igual |
| \(\gamma_M\) ligações | 1,30 | 1,30 | igual; \(F_{Rd}\) também cai com \(k_{mod}\) |

**Esforços** \(H\), \(M\), \(V\), \(N\) **não mudam** com a CS (só a resistência e a fluência).

### Impacto na geometria antiga C (α=11°, h0=0,70, b=0,30)

| Verificação | η CS2 | η **CS3** | Estado CS3 |
|-------------|-------|-----------|------------|
| Cisalhamento | 0,90 | **1,16** | ✗ |
| Pilar 0,22×0,22 | 0,73 | **1,20** | ✗ |
| Cumeeira t90 | 0,19 | 0,25 | ✓ |
| Flexão / LTB | ~0,08 | ~0,11 | ✓ |
| ELS | 0,03 | 0,05 | ✓ (ainda folgado) |
| L1 (η) | 0,98 | 0,77* | ✗ geometria (n=60) |
| L3 | 0,96 | 0,96 | ✓ (H igual) |
| H / M_cum | 1544 / −442 | **iguais** | — |

\* Com \(k_{mod}=0{,}70\) a ligação pede **mais pinos**; a malha deixa de caber em \(h_0\).

**Conclusão:** a solução CS2 **C não é reutilizável** em CS3.

---

## 2. Resultados da varredura CS3

| Métrica | Valor |
|---------|--------|
| Combinações testadas (úteis) | ~1000 |
| **Aprovadas** | **386** |
| Falha dominante (após viga) | **L1** (ligação base) |
| α mínimo factível | **9,5°** (CS2 era ~8,5°) |
| H nas soluções | **1,11 – 1,70 MN** |
| \(h_0\) típico mínimo | **≥ ~1,0 m** (cisalhamento + pinos) |
| \(b\) típico mínimo | **≥ 0,30 m** |

Governantes frequentes: **L1**, **L3**, por vezes **cisalhamento**.

---

## 3. Candidatas validadas (pipeline completo, CS3)

| ID | α | h0 | b | Pilar | L1 | H | η_gov | Notas |
|----|---|----|----|-------|-----|---|-------|-------|
| **R1** | 9,5° | 1,00 | 0,30 | 0,22×0,26 | 48×d36 | 1700 kN | 0,993 L1 | α mínima; L1 no limite |
| **R2** | 10° | 1,00 | 0,30 | 0,22×0,26 | 48×d36 | 1631 kN | 0,971 L3 | **recomendada** |
| **R3** | 12° | 0,80 | 0,32 | 0,22×0,26 | 42×d36 | 1429 kN | 0,993 L3 | menos h0, mais α |
| **R4** | 16,5° | 0,80 | 0,40 | 0,24×0,24 | 35×d36 | 1120 kN | 0,934 L3 | menor H; secção muito alta |
| C antiga | 11° | 0,70 | 0,30 | 0,22×0,22 | — | 1544 kN | — | **REPROVADA** CS3 |

### Recomendação de trabalho: **R2** (adoptada em `main.py`)

```
CS3 global | biarticulada | GL24h
α = 10,0°
h0 = 1,00 m
b  = 0,30 m
h_ap ≈ 2,79 m
l_ap = 0,90 m
Pilar lateral = 0,22 × 0,26 m
Pilar central = 0,28 × 0,28 m   # N≈2·R_v; 0,26×0,26 falha em CS3
L1: d = 36 mm, n ≈ 48 (layout ~6×8)
L3: n_chu ≈ 21 @ 80 kN  (H ≈ 1631 kN)
k_mod,curta = 0,70 | k_def = 2,00
```

**Critério:** α ainda baixo; L1 com margem face a R1; volume próximo do mínimo CS3.  
**Nota:** a varredura dimensionava o pilar **lateral**; o central (carga duplicada) exige secção própria — adoptado 0,28×0,28 (η≈0,73).

---

## 4. Comparação CS2 (varredura anterior) vs CS3

| | CS2 (C) | **CS3 (R2)** |
|--|---------|--------------|
| α | 11° | **10°** |
| h0 | 0,70 m | **1,00 m** |
| b | 0,30 m | 0,30 m |
| Pilar | 0,22×0,22 | **0,22×0,26** |
| n pinos L1 | ~35 | **~48** |
| H | ~1544 kN | ~1631 kN (α/h ligeiramente diferentes) |
| Volume madeira (métrica varredura) | ~21 m³ | **~24 m³** (+~15%) |
| k_mod ELU vento | 0,90 | **0,70** |
| k_def | 0,80 | **2,00** |

---

## 5. Impactos de projecto (críticos)

1. **Mais madeira na viga** (h0 sobe ~30 cm face a C) e **ligação L1 ainda mais pesada** (n≈48).  
2. **Fundação:** H continua ~1,6 MN — CS3 **não reduz** empuxo.  
3. **ELS:** com \(k_{def}=2\) a fluência sobe, mas no modelo actual a flecha **ainda não governa** (η_ELS ~0,03).  
4. **Pilar:** secção mínima sobe (0,22×0,26 vs 0,22×0,22).  
5. **Fabrico:** \(h_{ap}\approx 2{,}8\,\mathrm{m}\) e grupo grande de pinos — crítico em montagem e chapa (EN 1993-1-8).  
6. O modelo de **arco no centroide** mantém M de **fecho** na cumeeira e H grande; CS3 só agrava resistências, não a estática.

---

## 6. Avisos

- Soluções no **fio da navalha** em L1 (η > 0,95) exigem pormenor cuidadoso e preferência por candidatas com margem (R2/R3).  
- Se no futuro se adoptar eixo **reto** (H≈0), a varredura CS3 **tem de ser refeita** — números actuais não se aplicam.  
- OpenSees de validação de H/M continua pendente.
