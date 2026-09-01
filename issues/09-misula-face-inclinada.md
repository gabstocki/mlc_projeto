# 09 — Mísula: verificação da face inclinada σm,α,d ausente

- **Tema:** Viga — mísula (borda inclinada)
- **Prioridade:** P1
- **Normas:** EC5 §6.4.2, Eq. 6.38 a 6.40
- **Arquivos:** `mlc_projeto/checks/elu/` (verificação inexistente)

## Apontamento do orientador
> Verificações ausentes para mísula: σm,α,d ≤ km,α·fm,d na face inclinada
> (EC5 §6.4.2, Eq. 6.38 a 6.40). Tem material na apostila também.

## Estado atual no código
- Há verificação de flexão simples ([flexao.py](../mlc_projeto/checks/elu/flexao.py)),
  flambagem lateral, cisalhamento, apoio e zona da cumeeira/ápice
  ([cumeeira.py](../mlc_projeto/checks/elu/cumeeira.py)).
- **Não existe** verificação da **borda inclinada** (single tapered / double tapered
  beam) conforme EC5 §6.4.2: tensão de flexão na face inclinada com o fator k_m,α.

## O que precisa ser feito
- [x] Implementar a verificação da face inclinada (extradorso em bisel):
      `σ_m,α,d ≤ k_m,α · f_m,d` com `k_m,α` conforme se a face está em tração ou
      compressão paralela à borda (Eq. 6.39 / 6.40).
- [x] Aplicar na seção onde a borda inclinada é mais solicitada (não só no ápice).
- [x] Integrar no pipeline ELU e no relatório/`tabela_verificacoes`.
- [x] Documentar as equações e o valor de α usado.

## Critério de aceite
Nova verificação `σ_m,α,d ≤ k_m,α·f_m,d` no pipeline, com η reportado e memória de
cálculo no memorial.

## Resolução (2026-08-31)
- Novo módulo [misula.py](../mlc_projeto/checks/elu/misula.py) com `verifica_misula`
  (EC5 §6.4.2): `σ_m,α,d = 6·|M(x)|/(b·h(x)²) ≤ k_m,α·f_m,d`, com
  `k_m_alpha_compressao` (Eq. 6.40) e `k_m_alpha_tracao` (Eq. 6.39). α = ângulo do
  extradorso (`geo.alpha_deg`).
- **Varredura completa**: percorre TODAS as combinações ELU × TODAS as seções x;
  em cada seção usa k_m,α de tração (topo em hogging) ou de compressão (topo em
  sagging), com o material na **duração de cada combinação** (k_mod correto).
- Integrado no pipeline: [main.py](../mlc_projeto/main.py) (`res_elu["misula"]`,
  logo após a cumeeira) e no relatório — linha na tabela §7 e subseção de memória
  de cálculo com as três equações e o α ([report.py](../mlc_projeto/output/report.py)).
- **Resultado (GL24h, α=10°):** k_m,α(comp)=0,758 e k_m,α(**tração**)=0,414. O arco
  abatido biarticulado tem **momento de crown em hogging** (M_ap ≈ −366 kN·m), logo
  o **topo traciona no ápice** e o caso de tração (Eq. 6.39, f_t,90,d baixo) governa:
  σ_m,α,d = 0,86 MPa ≤ 5,57 MPa ⇒ **η = 0,155** (OK). É o incremento normativo que
  a flexão simples (`flexao.py`) não capturava (aquela usa σ_m sem k_m,α).
- **Relação com a issue 10 (§6.4.3):** o ápice também exige σ_t,90 (cumeeira, já
  existente) e o k_l de amplificação do momento no ápice (issue 10). A §6.4.2 aqui é
  a verificação (necessária) da tensão de flexão na face em bisel, complementar.
- **Testes:** [test_misula.py](../tests/test_misula.py) (k_m,α: degenera a 1 se α=0;
  tração < compressão < 1; valor fechado da Eq. 6.40; regime/seção/σ governantes).
  LaTeX do memorial compila (pdflatex). Suíte: 119 passam.

### Nota (fora de escopo, cosmético)
Descrições de combinação em `loads.py` contêm o caractere `⇒` (U+21D2), que o
`pdflatex`+`inputenc utf8` não mapeia — é aviso não-fatal (o PDF é gerado), mas o
caractere pode sair ausente no memorial. Não faz parte da issue 9.
