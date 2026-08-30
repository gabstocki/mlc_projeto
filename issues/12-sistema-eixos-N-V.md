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
- [ ] Definir **um** referencial explícito (eixo da peça) e aplicá-lo de forma
      consistente em N, V e nas verificações de apoio/Hankinson.
- [ ] Decidir: usar o cortante perpendicular ao eixo (`V_viga_kN`, ~65,5 kN) — mais
      correto — ou manter a reação vertical declarando explicitamente que é
      conservador. Documentar a escolha.
- [ ] Revisar todos os consumidores de `V_max_ELU()` vs `V_viga_ELU()` para coerência.

## Critério de aceite
Referencial único e explícito; verificações de apoio coerentes com ele; memorial
mostra a convenção de eixos e sinais (ver issue [27](27-memorial-castigliano-diagramas.md)).
