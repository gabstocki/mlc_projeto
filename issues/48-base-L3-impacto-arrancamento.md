# 48 — Base L3: cortante de impacto de veículo e arrancamento de 83,9 kN; η = 0,0000 incoerente

- **Tema:** Ligações — base L3 / ancoragem
- **Prioridade:** P1 (verificação aparente nula, incoerente entre tabelas)
- **Normas:** EN 1991-1-7 §4.3 (impacto, situação acidental); EN 1990 Eq. 6.11; EN 1993-1-8; EN 1992-4
- **Arquivos:** `mlc_projeto/connections/connections.py` (L3: `H=0.0 kN`, η = 0,0000); `mlc_projeto/connections/ancoragem.py`; `mlc_projeto/checks/elu/impacto_veiculo.py`; `output/pipeline_console.txt:181-183,317`; `tese/cap08.tex:141-247,337` (Tabela 23 × Tabela 25)
- **Relaciona:** issues 33, 37, 43

## Origem (3ª revisão do orientador (2026-10))
Verificar L3 para o **cortante na base devido ao impacto de veículo** (≈ 50 × 6,5/7 ≈ 46 kN,
situação acidental) e para o **arrancamento de 83,9 kN**. A Tabela 23 mostra η = 0,0000 para
os chumbadores de L3, incoerente com a Tabela 25.

## O que fazer
- [ ] Explicar a origem do η = 0 (L3 hoje só verifica H = 0 do empuxo?) e corrigir: L3 deve
      receber V_Ed (impacto acidental, e vento/contraventamento) e N_t (arrancamento 83,9 kN).
- [ ] Verificar chumbadores à tração, corte e interação (EN 1993-1-8 Tab. 3.4 / EN 1992-4),
      chapa de base e solda, com γ da situação acidental para o impacto.
- [ ] Unificar L3 com a “ancoragem de canto” (Fase 4d) ou explicar a diferença.
- [ ] Coerência entre Tabelas 23 e 25 da tese.

## Resolução ✅ (2026-10-06)

**Origem do η = 0,0000:** `dimensionar_sapata` (sem tirante) reportava η = η_H, e H_d = H_arco = 0
na Opção B. O arrancamento e o impacto nunca chegavam à L3.

**Código**
- `connections/ancoragem.py`: `verificar_base_corrente()` — duas situações não concomitantes
  (EN 1990 §6.4.3), via `verificar_grupo_ancoragem` (aço EN 1993-1-8; concreto EN 1992-4):
  persistente (sucção: N_t + ½ arrasto do vento no pilar) e acidental (choque: V = R_base =
  50·6,5/7 = 46,4 kN). Sem chaveta (corte nos chumbadores), sem atrito creditado, γ da
  persistente mantidos na acidental (conservador).
- `connections/connections.py`: `dimensionar_sapata` sem tirante passa a η = max(η_H, η_N).
- `main.py` (Fase 4c): aplica a L3 (N_t 83,9) **e L3c** (N_t 151,8; pilares centrais também
  expostos a choque); a ligação reporta max(η_N, η_ancoragem) e o critério frágil (0,75) é
  reaplicado. Quadro de fundação: H das bases correntes = 46,4 kN (acidental).
- `output/report.py` (catálogo), `output/cargas_fundacao.py` (`V_base_corrente_kN`).
- Testes: `tests/test_ancoragem_bases_correntes.py` (5). Suíte 679 passed; pipeline APROVADO
  (52 verificações).

**Resultados (4×M24 8.8, c = 600, h_ef = 400):**

| Base | Situação | N (kN) | V (kN) | η aço | η concreto |
|---|---|---|---|---|---|
| L3 | sucção | 83,9 | 1,7 | 0,124 | 0,199 (cone) |
| L3 | impacto | 0 | 46,4 | 0,086 | **0,332** (borda, V_Rd,c = 139,8 kN) |
| L3c | sucção | 151,8 | 1,7 | 0,224 | **0,360** (cone) |
| L3c | impacto | 0 | 46,4 | 0,086 | 0,332 |

L3 η 0,0000 → **0,332**; L3c 0,133 → **0,360** (frágeis, ≤ 0,75). Canto e central montante já
têm chaveta + 6 chumbadores dimensionados para cortes maiores.

**Tese:** §8.3 reescrito (Eq. do corte de impacto + Tabela das bases correntes), Tabela dos modos
frágeis (L3 0,3322; L3c 0,3599), quadro de fundação (H = 46,4 kN + nota acidental), contagens
(52 verificações, 679 testes).
