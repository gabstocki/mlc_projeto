# Varredura — modelo biarticulado (MLC monolítica)

**Data:** 2026-07-10  
**Modelo estrutural (código actual):**
- Viga de duplo-bisel **monolítica** (sem rótula na cumeeira)
- Rótulas **só** nos apoios
- Eixo centroidal com flecha \(f_c=(h_{ap}-h_0)/2\), \(y_c=x_{\mathrm{sim}}\tan\alpha/2\)
- Empuxo \(H\) por Castigliano: \(H=\int M_0 y_c/I\,\mathrm{d}x\big/\int y_c^2/I\,\mathrm{d}x\) (projecção \(\mathrm{d}x\))
- Área tributária \(L_t=5{,}75\,\mathrm{m}\) (pórtico intermédio)
- Material GL24h, CS2; vento NBR 6123

**CSV:** `output/varredura_biarticulada.csv` — **196** combinações com η ≤ 1 em todas as verificações EC5 + ligações factíveis.

---

## Leitura crítica do modelo (RM + norma)

1. **H não é ~0.** Com \(y_c\neq 0\), o modelo é de **arco abatido de secção variável**. Em toda a grelha aprovada:
   - \(H \approx 1{,}26\) a \(1{,}86\,\mathrm{MN}\)
   - sempre **maior** que o H do triarticulado legado (\(H/H_3\approx 1{,}35\)–\(1{,}45\)), por \(I\) maior na cumeeira.
2. **Momento na cumeeira é de fecho** (\(M_{ap}<0\)):  
   \(M(L/2)=qL^2/8 - H f_c < 0\).  
   As verificações usam \(|M|\) (taxa de utilização). §6.4.3 aplica-se a \(|M_{ap}|\).
3. **Govemam tipicamente:** L1 (pinos, \(F_{res}\approx\sqrt{N^2+V^2}\sim H\)) e L3 (chumbadores a \(H\)).  
   Cisalhamento e cumeeira t90 ficam em geral η < 1 quando a ligação fecha.
4. **α ≤ 8°** praticamente **não fecha L1** (H demasiado alto + geometria de pinos EC5 Tab. 8.2).  
   **α = 4,5°** não aparece entre soluções factíveis neste modelo.
5. **h_ap ≈ 2,5–3,2 m** e **n_pinos ≈ 30–40 × d30–36** são pesados em fabrico/montagem — factíveis na varredura, mas **críticos em obra**.
6. Isto **não** é o modelo “viga reta H≈0, \(M=qL^2/8\)”. Esse seria outro eixo (\(y_c\equiv 0\)).

---

## Critérios de varredura

| Item | Intervalo / regra |
|------|-------------------|
| α | 6° … 22° (passo 0,5°) |
| h0 | 0,60 … 1,20 m (0,05) |
| b | 0,22 … 0,36 m (0,02) |
| h_ap/b | ≤ 9 (filtro de esbeltez de secção) |
| l_ap | 0,40 … 0,80 m |
| Pilar | secções comerciais 0,20–0,32 |
| Pinos L1 | d ∈ {20,24,30,36}, n ≤ 40, L_lig ≤ 1,5 m, distâncias EC5 |
| Chumbadores | F_chu = 80 kN (100 kN se necessário) |
| ELU/ELS | EC5 §6.x, §2.3.2.2, Tab. 7.2; k_cr = 0,67; γ_M lig. = 1,30 |

---

## Candidatas validadas (pipeline completo)

| ID | α | h0 | b | Pilar | L1 | H | \|M_cum\| | η_gov | Notas |
|----|---|----|----|-------|-----|---|----------|-------|-------|
| **A** | 8,5° | 1,00 | 0,28 | 0,20×0,24 | 40×d36 | 1862 kN | 372 | 0,996 L1 | **α mínima**; L1 no limite |
| **B** | 11° | 0,65 | 0,30 | 0,22×0,22 | 35×d36 | 1551 kN | 449 | 0,983 L1 | **menor volume**; cis. 0,97 |
| **C** | 11° | 0,70 | 0,30 | 0,22×0,22 | 35×d36 | 1544 kN | 442 | 0,979 L1 | **recomendada** (margem cis.) |
| **D** | 14,5° | 0,60 | 0,36 | 0,22×0,22 | 40×d30 | 1258 kN | 512 | 0,983 L3 | **menor \|H\|**; h_ap alto |
| **E** | 12° | 0,75 | 0,32 | 0,22×0,22 | 35×d36 | 1435 kN | 450 | 0,997 L3 | compromisso |

Todas: cumeeira §6.4.3, flexão/LTB, ELS, terças, contraventamento e fadiga **OK**.

---

## Recomendação de projecto: **C**

```
Sistema:   viga MLC biarticulada (continuidade na cumeeira)
L        = 20,25 m
α        = 11,0°
h0       = 0,70 m
b        = 0,30 m
h_ap     ≈ 2,67 m
f_c      ≈ 0,98 m
l_ap     = 0,80 m
Pilar    = 0,22 × 0,22 m  (lateral)
L1       = pinos d=36 mm, n≈35 (layout ~7×5), γ_M=1,30
L2       = continuidade + pino d=30 (assimetria vento)
L3       ≈ 20 chumbadores @ 80 kN (H≈1544 kN)
```

**Critério:** α não no mínimo absoluto (A está no fio da navalha em L1 e pilar); h0 com margem em cisalhamento face a B; volume próximo do mínimo.

---

## Avisos de engenharia (não suavizar)

1. **Fundação:** H ≈ 1,5 MN por pórtico intermédio — sapata e chumbadores são **dimensionantes**.
2. **L1:** grupo grande de pinos; detalhe de chapa (EN 1993-1-8), fenda, e montagem exigem estudo de pormenor além do Johansen.
3. **Momento de fecho na cumeeira:** confirmar com o produtor MLC a combinação flexão + compressão + t90 na zona de cumeeira (laminação e secção).
4. Se o objectivo de projecto for **H≈0 e M≈qL²/8**, este modelo de eixo **não** é o adequado — haveria de se adoptar eixo reto (\(y_c=0\)), decisão de modelo à parte.
5. OpenSees de validação do H/M ainda **não** foi corrido (combinado: analítico primeiro).

---

## Comparação com a varredura “3 rótulas” (inválida fisicamente)

| | 3 rótulas (legado) | Biarticulada (actual) |
|--|--------------------|------------------------|
| M cumeeira | 0 (fictício) | ≠0 (fecho) |
| H (ordem) | ~1,2 MN (α=10°) | ~1,5–1,9 MN |
| α mínimo factível | ~9,5° | ~8,5° (com ligações pesadas) |
| η cumeeira | 0 artificial | 0,14–0,20 real |
