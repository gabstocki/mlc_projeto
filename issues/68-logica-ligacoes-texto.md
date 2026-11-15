# 68 — Explicitar no texto a lógica das ligações (contato × pinos, Johansen, frágil × dúctil, cadeia da base)

- **Tema:** Ligações — fundamentação no texto (preparação para a banca)
- **Prioridade:** P2
- **Normas:** EN 14080 (f_t,90,k = 0,5; f_c,90,k = 2,5 MPa), EC5 §6.1.5, §8.1.4 (Eq. 8.4), §8.2.3, EN 1993-1-8 §6.2.4, EN 1992-4
- **Arquivos:** `tese/cap08.tex` §7.1 (critério de margem) e §7.2 (viga–pilar), §7.4 (base)
- **Origem:** 4ª revisão, item 1 (1.1–1.6)

## Contexto
O orientador confirmou que a concepção (gravidade por contato, arrancamento pelos pinos,
furos ovalizados verticais separando os caminhos) está correta, e explicou a lógica que a
banca deve encontrar no texto e que o autor deve dominar.

## O que fazer
- [ ] Conferir se o §7.2 apresenta, em ordem direta, os seis pontos: (1.1) caminho único por
      esforço — 99,6 kN para baixo por contato, 86,1 kN para cima pelos pinos, oblongos verticais;
      (1.2) f_t,90 ≪ f_c,90 → contato = compressão ⊥ dúctil, pinos = fendilhamento frágil
      (0,97 → 0,34); (1.3) h_e na Eq. 8.4 medido da borda **inferior** sob arrancamento,
      pinos no terço superior → h_e/h = 0,93; (1.4) Johansen com chapa espessa (t ≥ d) e
      f_h 24,0 → 14,1 MPa por k_90 a ~84°; (1.6) cadeia da base cavilhas → chapa vertical →
      T-stub → chumbadores → concreto, elo mais fraco.
- [ ] (1.5) Declarar explicitamente que η ≤ 0,75 para modos frágeis é **critério do autor**, não da
      norma, com a justificativa (ruptura sem aviso).
- [ ] Completar o que faltar sem repetir o que já está no texto.

## Resolução ✅ (2026-11-10) — só texto (`tese/cap08.tex`)

| Ponto | Onde estava | O que mudou |
|---|---|---|
| 1.1 caminho único | `ssec:concepcao-l1` | Reescrito em ordem direta: gravidade 106 kN ↓ por contato, arrancamento 100,5 kN ↑ pelos pinos, oblongos verticais; por que caminhos em paralelo seriam indeterminados (rigidez, folgas, umidade) |
| 1.2 f_t,90 ≪ f_c,90 | ausente | 0,5 × 2,5 MPa (remete a `tab:gl24h`): contato = compressão ⊥ dúctil; pinos = tração ⊥ → fendilhamento frágil |
| 1.3 h_e | `ssec:pinos-l1` | Explicado na concepção: a borda carregada é aquela para onde os pinos empurram a madeira. Gravidade nos pinos → borda superior, h_e = 182 → F_90,Rd ≈ 33 kN (⅓ da reação); arrancamento → borda inferior, h_e = 818 (h_e/h = 0,82; o 0,93 da issue era de geometria antiga) → η 0,67. Saiu o "era 0,97 … exigia reforço" (narrativa de revisão, issue 92) |
| 1.4 Johansen | `ssec:pinos-l1` | f_h pela Eq. 8.31 (§8.5.1.1, via §8.6); chapa central em corte duplo → Eq. 8.11 (modos f/g/h, conferido no PDF da EN 1995-1-1); chapa espessa §8.2.3(1): t 25 ≥ d 24 e folga 2 < 0,1d, condição para o pino ser engastado (modos com rótula) |
| 1.5 0,75 | `sec:criterio-ligacoes` | Explícito como "critério do autor, não exigência normativa": a EN 1995-1-1 usa o mesmo γ_M = 1,30, e η = 1,00 atenderia; justificativa: ruptura sem aviso e uso público |
| 1.6 cadeia da base | `ssec:chapa-base` | Nova `tab:cadeia-base`: 10 elos L3/L3c com η. Os frágeis ficam ≤ 0,67; governa o aço (solda tubo × chapa de base 0,86 em L3, chapa de topo do pilarete 0,74/0,75), de modo que cede primeiro um componente metálico |

Na `tab:modos-margem` foram corrigidas as linhas que contradiziam o novo texto: pinos L1/L1c 0,70 → 0,68, fendilhamento 0,34 → 0,67, T-stub de L3 0,84 → 0,31. A frase "os dois mais solicitados são os pinos, 0,70" virou "no limite de 0,75 ou abaixo". O restante da tabela e a `tab:ligacao-l1` (86,6 kN, 5 pinos, 0,70) continuam desatualizados e ficam para a issue 99.

Tese: 163 páginas, 0 overfull, nenhuma referência pendente.
