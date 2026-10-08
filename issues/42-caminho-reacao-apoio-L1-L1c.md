# 42 — Caminho da reação de apoio: contato direto em vez de pinos ⊥ às fibras; compressão no apoio; desenho da L1c

- **Tema:** Ligações — L1 / L1c / apoio
- **Prioridade:** P1 (fendilhamento η = 0,961 governa e força reforço; incoerência geométrica no apoio)
- **Normas:** EN 1995-1-1 §6.1.5 (compressão ⊥, k_c,90, l_ef), §8.1.4 (fendilhamento), §8.7 (parafusos autoperfurantes como reforço); EN 1993-1-8 (sapata metálica / placa de apoio)
- **Arquivos:** `mlc_projeto/connections/connections.py` (L1/L1c, fendilhamento); `mlc_projeto/checks/elu/apoio.py` (pressão de contato η = 0,266); `tese/cap07.tex:47` (Tabela — pressão de contato 0,2660); `tese/cap08.tex:50-140` (§8.2 L1, η = 0,961 em l. 104); `tese/cap09.tex:66`
- **Relaciona:** issues 20, 29, 43 (detalhamento), 52 (desenhos)

## Origem (3ª revisão do orientador (2026-10))
A reação vertical de 99,6 kN é transmitida por pinos com força praticamente ⊥ às fibras —
é isso que leva o fendilhamento a η = 0,961 e obriga ao reforço com parafusos
autoperfurantes. Avaliar transmitir a **reação vertical por contato direto** (viga apoiada
sobre o pilar, ou sapata metálica com placa de apoio), deixando os pinos só para
**arrancamento (sucção)** e **esforço horizontal**.
Esclarecer também a compressão no apoio (η = 0,266): o valor sugere **comprimento de apoio
≈ 0,5 m**, mas o pilar tem **0,27 m** no plano do pórtico; no **pilar central** esses 0,27 m
são **divididos entre duas vigas**, cada uma com sua ligação.

## O que fazer
- [ ] Estudar a alternativa de apoio por contato (viga sobre pilar / sapata metálica com
      placa); comparar com a solução atual (η fendilhamento, nº de pinos, reforço, custo).
- [ ] Rever a verificação de §6.1.5: qual l (comprimento de apoio) foi usado? Corrigir para a
      geometria real (0,27 m; no central, 0,27/2 por viga ou detalhe específico) e k_c,90.
- [ ] Redimensionar L1/L1c conforme a solução adotada; atualizar tese §7/§8 e §9.
- [ ] **Apresentar o desenho da ligação L1c** (pilar central, duas vigas) — ver issue 52.

## Resolução ✅ (2026-10-06) — apoio por contato + sela central (decisão do usuário)

**Concepção:** gravidade por **contato direto** (viga sobre chapa de topo do pilar lateral; no
central, **sela metálica**); pinos em furos **ovalizados verticais**, no **terço superior**, só
para **arrancamento** (86,1 kN, sucção) e axial.

**Esclarecimento da compressão no apoio:** o η = 0,266 vinha de `L_AP = 0,90 m` — placa fictícia
maior que o pilar (0,27 m). Corrigido para a geometria real.

**Código**
- `checks/elu/apoio.py`: `verifica_apoio_contato` (EC5 §6.1.5: l_ef = l + 30 mm do lado do vão,
  k_c,90 = 1,75 MLC apoio discreto l ≤ 400 mm; publica também η sem k_c,90),
  `verifica_sela_central` (placa em balanço, EN 1993-1-1 §6.2.5), `reacao_arrancamento_max`.
- `connections/connections.py`: `dimensionar_ligacao_base(..., V_pinos_kN)` e propagação a
  L1c/`dimensionar_ligacoes*`; `fendilhamento_ligacao` com grupo no terço superior
  (h_e = h − a4,c, borda carregada inferior sob arrancamento).
- `connections/fadiga_ligacoes.py`: com contato, slip só com o axial e alternância só com o
  arrancamento (sem compressão nos pinos).
- `output/figuras.py`: `plot_ligacao_L1c` (desenho cotado com escala gráfica) →
  `output/ligacao_L1c.png` e `tese/fig/ligacao_L1c.png`.
- `main.py`: `L_AP = H_PILAR`, `L_SELA_POR_VIGA = 0,25`, `FOLGA_SELA_M = 0,02`; catálogo.
- Testes: `tests/test_apoio_contato.py` (5). Suíte 691 passed; 54 verificações; APROVADO.

**Resultados**
| Verificação | antes | depois |
|---|---|---|
| Apoio L1 (l = 0,27 → l_ef 0,30 m) | 0,266 (l = 0,90 fictício) | **0,456** (0,798 sem k_c,90) |
| Apoio L1c, sela 0,25 m/viga | — | **0,489** (0,855 sem k_c,90) |
| Sela 520×320, balanço 125 mm, t_req 13,8 → 16 mm S275 | — | 0,740 |
| Pinos (arrancamento 86,1 kN) | 6 pinos, 0,663 | **5 pinos Ø24, 0,691** |
| Fendilhamento | 0,961 sem reforço → 0,722 c/ 8 parafusos | **0,339 sem reforço** (h_e = 928 mm) |
| Alternância / slip | 0,733 / 0,047 | 0,691 / 0,005 |

**Tese:** §8.2 reescrito (concepção, apoio por contato com Eq., Figura da L1c, pinos e
arrancamento com Eq. do fendilhamento), Tabela da viga (§7.2), Tabela dos modos frágeis, §9,
resumo e abstract (também atualizados para η_max 0,8352 do contraventamento vertical).

**Pendente:** força horizontal ⊥ ao pórtico na L1 das baías contraventadas (reação da treliça de
cobertura, ~105 kN) — ver [issue 66](66-l1-forca-fora-do-plano-bracing.md). Detalhe da sela
(nervuras, solda à chapa de topo do pilar) e do pilar lateral → issues 43/52.
