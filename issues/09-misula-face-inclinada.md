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
- [ ] Implementar a verificação da face inclinada (extradorso em bisel):
      `σ_m,α,d ≤ k_m,α · f_m,d` com `k_m,α` conforme se a face está em tração ou
      compressão paralela à borda (Eq. 6.39 / 6.40).
- [ ] Aplicar na seção onde a borda inclinada é mais solicitada (não só no ápice).
- [ ] Integrar no pipeline ELU e no relatório/`tabela_verificacoes`.
- [ ] Documentar as equações e o valor de α usado.

## Critério de aceite
Nova verificação `σ_m,α,d ≤ k_m,α·f_m,d` no pipeline, com η reportado e memória de
cálculo no memorial.
