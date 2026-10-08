# 40 — Esforço normal: incluir a verificação analítica N(x) = V(x)·sen(α/2)

- **Tema:** Análise estrutural / Memorial
- **Prioridade:** P2 (valor correto; falta a demonstração)
- **Normas:** —
- **Arquivos:** `tese/cap06.tex:206-254` (§6.4 Esforços solicitantes); `mlc_projeto/core/loads.py` (`diagramas_MVN_ELU`); modelo FEM (OpenSeesPy) da issue 35
- **Relaciona:** issues 12, 27, 35

## Origem (3ª revisão do orientador (2026-10))
O valor de N está **correto**. Com empuxo nulo, N decorre só da inclinação do eixo
baricêntrico: intradorso horizontal e extradorso a α = 10° ⇒ eixo a **α/2 = 5°**:

    N(x) = V(x)·sen(α/2);  N_máx = 99,61 × sen 5° ≈ 8,7 kN no apoio, → 0 na cumeeira.

O FEM confirma: N/V = 0,088 = tg 5° em todos os elementos da viga.

## O que fazer
- [ ] Incluir a expressão no **§6.4** como verificação analítica (equação numerada), com a
      conferência pelo FEM (razão N/V = tg 5°).
- [ ] Comentar que usar N = 8,75 kN na **flexo-compressão da cumeeira é conservador**
      (ali N ≈ 0). Opcional: usar N(x) local na verificação da cumeeira.
- [ ] Opcional: teste unitário comparando N(x) do código com V(x)·sen(α/2).

## Resolução ✅ (2026-10-06)

- **Expressão:** com H = 0, `N(x) = S(x)·sen θ`, com **tg θ = tg α / 2** (eixo baricêntrico a meia
  altura; intradorso horizontal): θ = 5,04° (≈ α/2 = 5°). No apoio N = 99,61·sen 5,04° = **8,75 kN**
  (com sen 5° exato daria 8,68 kN, o valor do orientador); → 0 na cumeeira. É o que
  `Carregamentos.diagramas_MVN_ELU` já calcula (N = H·cosθ + S·senθ).
- **FEM:** `opensees_model.analisar_fem` passou a devolver `razao_N_V` (forças locais de cada
  elemento): **N/V = 0,08816 = tg θ nos 40 elementos** (≈ tg 5° = 0,0875 citado pelo orientador).
- **Cumeeira:** mantido N = 8,75 kN na flexo-compressão — conservador (N ≈ 0 ali), declarado.
- **Testes:** `tests/test_normal_analitico.py` (2: analítico ao longo do vão + FEM). Suíte 696 passed.
- **Tese:** §6.4 — parágrafo e Eq. `eq:normal-analitico` com a confirmação pelo FEM.
