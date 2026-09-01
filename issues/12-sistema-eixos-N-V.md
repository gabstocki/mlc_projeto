# 12 — Sistema de eixos: N no eixo da peça vs V vertical

- **Tema:** Sistema de eixos e esforços
- **Prioridade:** P1
- **Normas:** EC5 §6.1.5, §6.2.2 (apoio); coerência de convenção
- **Arquivos:** `mlc_projeto/core/loads.py:209-212`, `mlc_projeto/checks/elu/apoio.py:76`

## Apontamento do orientador
> Me parece que o sistema de eixos está confuso. Veja se está certo o seguinte: o
> esforço normal de apoio, N = 1642,60 kN, reproduz exatamente H·cos θ + Rv·sen θ com
> θ = 5,04°, ou seja, está referido ao eixo da peça. O cortante, contudo, adota
> V = 209,59 kN = Rv vertical. O cortante perpendicular ao eixo vale
> Rv·cos θ − H·sen θ ≈ 65,5 kN. O procedimento é conservador — o coeficiente cairia
> de 0,748 para cerca de 0,23.

## Estado atual no código
- Em [loads.py:209-212](../mlc_projeto/core/loads.py) a análise já calcula ambos:
  - `N_apoio = H·cos θ + R_A·sin θ` (eixo da peça) → armazenado em `N_viga_kN`.
  - `V_apoio = R_A·cos θ − H·sin θ` (perpendicular ao eixo) → armazenado em `V_viga_kN`.
- Mas a verificação de **apoio** usa a **reação vertical** `R_d = V_max_ELU()`
  (= `R_v_gov`, vertical), não o cortante perpendicular ao eixo:
  [apoio.py:76](../mlc_projeto/checks/elu/apoio.py) e Hankinson em
  [apoio.py:83-85](../mlc_projeto/checks/elu/apoio.py).
- Resultado: N referido ao eixo, mas V/reação referida à vertical → **inconsistência
  de referencial** (conservadora no apoio, η≈0,748).

## O que precisa ser feito
- [x] Definir **um** referencial explícito (eixo da peça) e aplicá-lo de forma
      consistente em N, V e nas verificações de apoio/Hankinson.
- [x] Decidir: usar o cortante perpendicular ao eixo (`V_viga_kN`, ~65,5 kN) — mais
      correto — ou manter a reação vertical declarando explicitamente que é
      conservador. Documentar a escolha.
- [x] Revisar todos os consumidores de `V_max_ELU()` vs `V_viga_ELU()` para coerência.

## Critério de aceite
Referencial único e explícito; verificações de apoio coerentes com ele; memorial
mostra a convenção de eixos e sinais (ver issue [27](27-memorial-castigliano-diagramas.md)).

## Resolução (2026-08-31)
**Decisão:** referencial do **eixo da peça** (θ = atan(tan α / 2) ≈ 5,04°). Não é
só conservadorismo — usar a reação vertical como cortante da seção transversal era
um **erro de referencial**, então adotou-se o cortante ⊥ ao eixo (correto).

**Diagnóstico dos consumidores** (todos revisados):
- `cisalhamento.py` (§6.1.7) usava `V_max_ELU()` = **reação vertical R_v** — ERRADO
  (a seção transversal é ⊥ ao eixo). **Corrigido** para o cortante transversal
  `V = R_v·cosθ − H·senθ`.
- `apoio.py` (§6.1.5/§6.2.2) usa R_v (vertical) — **correto e mantido**: a compressão
  atua na face HORIZONTAL do intradorso (plano distinto da seção). Documentado.
- Pilares, contraventamentos, estabilidade, impacto, base das ligações: usam R_v
  como **reação vertical / axial do pilar** — correto, mantidos.
- `connections.py` e `fadiga_ligacoes.py` já usavam `V_viga` (⊥ eixo) — coerentes.

**Cortante transversal governante:** descobri que a combinação que maximiza o
cortante ⊥ ao eixo **não é** a de |M| (vento assimétrico governa). Adicionei
`combinacao_ELU_Vtransversal()` e `V_viga_max_ELU()` em `loads.py`; a §6.1.7 agora
usa o **máximo entre todas as combinações ELU** (evita subestimar V).

**Resultado (projeto, GL24h):** R_v = 175,7 kN, H grande ⇒ **V_transversal = 67,7 kN**
(comb. ELU_W_C1_asim); θ = 5,04°; N_eixo ≈ 1233 kN. η do cisalhamento cai de
**0,69 → 0,24** (o arco leva quase toda a reação para o eixo, N; sobra pouco cortante).
O apoio §6.1.5 permanece com R_v (correto para a face horizontal).

**Memorial:** nova subseção "Convenção de eixos e esforços no apoio" com θ, a
decomposição N/V, e por que o cisalhamento usa V (⊥ eixo) e o apoio usa R_v
(vertical) — planos distintos, não incoerência. Campos de referencial expostos em
`cisalhamento` e `apoio`. (Ver issue 27 para os diagramas M/V/N.)

**Testes:** [test_eixos_cortante.py](../tests/test_eixos_cortante.py) (identidade
N/V no eixo; §6.1.7 usa V transversal; V é o máximo entre combinações; apoio usa R_v;
η menos conservador). LaTeX compila. Suíte: 133 passam.
