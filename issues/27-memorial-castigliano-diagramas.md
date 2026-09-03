# 27 — Derivação de Castigliano + diagramas M/V/N (anexo de análise)

- **Tema:** Reprodutibilidade do memorial
- **Prioridade:** P1
- **Normas:** boa prática de memorial de cálculo
- **Arquivos:** `mlc_projeto/core/loads.py:84-234`; `mlc_projeto/output/report.py`

## Apontamento do orientador
> Omissões do memorial que tornam não reprodutíveis os resultados:
> 1 — Definição de yc(x) e I(x), sistema de eixos, convenção de sinais de momento e o
> desenvolvimento da integral de Castigliano com seus limites. Não pode apenas
> publicar o resultado.
> 2 — Diagramas de momento fletor, esforço cortante e esforço normal ao longo da viga.
> A análise tem que estar em um anexo.

## Estado atual no código
- A análise biarticulada está em [loads.py:118-234](../mlc_projeto/core/loads.py):
  `y_c(x) = x_sim·tan(α)/2`, `I(x) = b·h(x)³/12`,
  `H = ∫ M0·y_c/I dx / ∫ y_c²/I dx`, `M(x) = M0 − H·y_c`.
- Os arrays `M_x`, `M0_x`, `y_c`, `x` são calculados, mas o **memorial** publica apenas
  resultados-síntese; falta o **desenvolvimento** e faltam os **diagramas**.

## O que precisa ser feito
- [x] Anexo de análise no memorial: `y_c(x)`, `I(x)`, sistema de eixos, convenção de
      sinais (issue 12), integral de Castigliano com limites (0→L) e hipótese de apoio
      indeslocável (issue 24).
- [x] Diagramas M(x), V(x), N(x) gerados e incluídos (figura em `report.py`).
- [x] `V_ELU()` substituído: agora derivado do M(x) real (não mais aproximação).

## Critério de aceite
Anexo de análise reprodutível (definições, eixos, sinais, integral com limites) +
diagramas M/V/N publicados.

---

## ✅ Resolução (implementada)

### 1) Derivação rigorosa de V(x) e N(x) (loads.py)
Novo método `Carregamentos.diagramas_MVN_ELU()`:
    M(x) = M₀(x) − H·y_c(x)          (já existente)
    S(x) = dM₀/dx                     (cortante da viga simples)
    θ(x) = ±atan(tanα/2)              (inclinação local do eixo; ANALÍTICA)
    N(x) = H·cosθ + S·senθ            (normal no eixo, compressão +)
    V(x) = S·cosθ − H·senθ            (cortante ⊥ ao eixo)
Coincide nos apoios com N_apoio/V_apoio da análise. **`V_ELU()` reescrito** para
retornar esse V real (antes era `q·(L/2−x)`, aproximação de viga simples). O salto
de V e N no ápice (mudança de sinal de θ na quina do eixo) é capturado.

### 2) Figura M/V/N (output/figuras.py)
`plot_diagramas_MVN(load, geo, path)` — 3 painéis (M, V, N) da combinação governante,
salvos em PDF vetorial; gerado em `gerar_relatorio` e incluído via `\includegraphics`.

### 3) Anexo A no memorial (report.py)
"Anexo A — Análise estrutural (Castigliano) e diagramas":
- A.1 sistema de eixos + convenção de sinais (coerente com issue 12);
- A.2 geometria variável: x_sim, h(x), y_c(x), I(x) (com b, h₀, h_ap, α);
- A.3 grau de hiperestaticidade + integral de Castigliano **com limites 0→L**
  (E cancela; projeção horizontal dx) + hipótese de apoio indeslocável (issue 24);
- A.4 os diagramas M(x), V(x), N(x).

### Verificação
- Diagrama validado: M_max=−265,5 kN·m (=análise), N_apoio=1105,8 kN (=N_viga),
  V no ápice ≈ −96 kN (=−H·senθ). Pipeline gera figura + Anexo A no PDF, sem erros.
- **Testes:** [`tests/test_diagramas_mvn.py`](../tests/test_diagramas_mvn.py) (6 casos:
  M bate, N/V nos apoios, V≠aproximação, salto no ápice, arrays consistentes).
