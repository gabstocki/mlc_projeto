# 108 — Sela e pé das lâminas do pilar bipartido: tirante por lâmina?

- **Tema:** Ligações (continuação da issue 105)
- **Prioridade:** P2. É simplificação construtiva; o cálculo atual aprova.
- **Origem:** resto registrado na resolução da [issue 105](105-concepcao-ligacoes-padrao-grafico.md) e não rastreado. Achado ao conferir as issues fechadas, em 2026-11-14.

## Situação
A issue 105 aplicou a concepção "compressão por contato, tração por uma peça de aço" aos pilares correntes, com o tirante interno. A contagem de cavilhas Ø20 caiu de 1.448 para 928.

Ficaram fora a **sela** e o **pé das lâminas** dos 14 pilares bipartidos: cerca de 448 cavilhas, quase metade das 928 restantes. Lá, o arrancamento e o cortante ainda passam por cavilhas ∥ fibras.

## O que fazer
- [x] Estudar um tirante por lâmina, do nó/sela ao pilarete, como nos pilares correntes. Considerar o furo central na lâmina de 160 mm, a luva sob a sela e a porca dentro do pilarete Ø114,3.
- [x] Rever, com o tirante, o pé (só cortante do choque, dividido pelo espaçador) e a sela (só posicionamento e cortante).
- [x] Comparar a contagem de cavilhas e o aço; decidir.
- [x] ~~Se adotado~~ (não se aplica): DES-07 e DES-07B, `tab:pilar-bipartido`, `tab:cadeia-base` e o texto do cap. 8.

## Estudo (2026-11-14) — `issues/108-estudo-tirante-lamina.py`
O pé leva a tração da lâmina e o cortante do choque. A **sela é governada pela gravidade** (R_grav ≥ R_up): um tirante sozinho não reduz as cavilhas dela.

| Rota | Canto/lateral (8) | Central (6) | Bipartidos | Obra |
|---|---|---|---|---|
| Hoje | sela 4 + pé 6 por lâmina = 20 | 12 + 12 = 48 | 448 | 928 |
| A — tirante por lâmina (M20 / M24, η 0,39 / 0,52); pé só ao cortante: 4 | 16 | 32 | 320 | 800 |
| B — A + sela por contato num dente de 20 / 40 mm na face interna (σ∥ η 0,75; líquida 140 / 120 × 320, η 0,49 / 0,59); sela com 2 de posição | 12 | 12 | 168 | 648 |
| C — tirante único entre as lâminas (M20 / M30, η 0,71 / 0,62), sem furo nas lâminas | 16 | 32 | 320 | 800 |

Observações:
- **A e B** furam as lâminas de 160 mm pelas lamelas centrais, como nos pilares correntes. A barra recebe a força na borda inferior da aba da sela por uma luva soldada.
- **B** acrescenta um entalhe na face interna, na altura da sela, e tira as cavilhas da gravidade. Nos centrais, a sela passa de 12 para 2 cavilhas por lâmina.
- **C** deixa a barra no vão entre as lâminas, exposta ao incêndio de veículo (intumescente) e atravessando os espaçadores. Na base, ela chega ao centro da chapa, entre os pilaretes: exige ou a flexão da chapa de base ou uma ancoragem própria no bloco.

## Resolução ✅ (2026-11-14) — manter a solução atual (decisão do autor)
O cálculo atual aprova, e a sela e o pé das lâminas continuam com cavilhas ∥ fibras (448 no total). O estudo fica registrado para uma eventual revisão: a rota B reduziria a 168. Nada muda no código, nos desenhos nem na tese.
