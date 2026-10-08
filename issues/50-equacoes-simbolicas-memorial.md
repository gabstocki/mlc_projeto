# 50 — Memorial: verificações por equações simbólicas (expressão → substituição → resultado)

- **Tema:** Memorial / Apresentação
- **Prioridade:** P1 (pedido explícito; hoje só 3 equações numeradas)
- **Arquivos:** `tese/cap06.tex`, `tese/cap07.tex`, `tese/cap08.tex`; `mlc_projeto/output/report.py`
- **Relaciona:** issues 53 (precisão), 56 (símbolos)

## Origem (3ª revisão do orientador (2026-10))
O memorial precisa explicar as verificações por equações: **expressão normativa,
substituição dos valores e resultado**, ao menos para as **verificações governantes de cada
elemento**. Hoje há apenas três equações numeradas; as verificações aparecem só como taxas.

## O que fazer
- [ ] Listar a verificação governante de cada elemento (viga: flexão/mísula/ápice/cisalhamento/
      LTB/flecha; pilares; terças; diagonais; L1/L1c/L3/ancoragem; telha).
- [ ] Para cada uma, bloco `equation` numerado: forma normativa (com cláusula) → valores
      substituídos (com unidades) → resultado e η.
- [ ] Idealmente gerar os valores substituídos automaticamente do `report.py` / um `.tex`
      de macros exportado pelo pipeline, para evitar divergência texto × código.

## Resolução ✅ (2026-10-07)

**Abordagem:** o apêndice é **gerado pelo pipeline** a partir dos mesmos resultados do memorial,
para que texto e cálculo não divirjam.

- `mlc_projeto/output/memorial_equacoes.py` (novo): `gerar_apendice_memoria(res, path)` →
  `tese/apendiceB.tex` — **Apêndice B — Memória de cálculo das verificações governantes**:
  12 equações numeradas (expressão normativa → substituição → resultado), vírgula decimal:
  - Viga: cisalhamento (6.13, k_cr), t90 na cumeeira (6.54/6.55), borda inclinada (6.38–6.40,
    k_m,α), flexo-compressão (6.23), flecha final líquida;
  - Pilar central montante (6.23 com download e k_c);
  - Terça-biela (6.24) e fixação da telha (NBR 6123 §7.2.6);
  - Diagonal da cobertura (k_ℓ, q_d, soma com vento, N_t,Rd) e vertical (V_painel, N, min(N_pl; N_u));
  - Pinos da L1 (Johansen modo de 1 rótula, n_ef) e ancoragem do canto (cone, EN 1992-4).
- Gerado só em execução real (junto do `gerar_relatorio`); os testes, que rodam cenários alterados,
  não reescrevem o apêndice.
- `pilares.verifica_pilar_contraventado` passou a publicar σ_c, f_c0,d, f_m,d, k_mod, λ_rel.
- `tese/main.tex` inclui `apendiceB`; cap. 7 e 8 remetem ao apêndice.
- Testes: `tests/test_memorial_equacoes.py` (2). Suíte 698 passed.

Com as equações acrescentadas nas issues 39–66 no corpo do texto (apoio por contato, fendilhamento,
LTB sob sucção, φ do EC5, N(x), rosca recalcada, corte de impacto, combinação Q+W, k_ℓ…), a tese
passa de 3 para **21 equações numeradas**.
