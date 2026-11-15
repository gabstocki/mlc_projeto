# 90 — Desenhos da L1/L1c: corte A–A, linha oculta e chapa em verdadeira grandeza

- **Tema:** Desenhos
- **Prioridade:** P1
- **Arquivos:** `mlc_projeto/output/desenhos.py` (DES-05 e folha da L1c), `tese/apendiceE.tex`
- **Relaciona:** 70, 71, 72, 73, 79 (geometria final antes de desenhar)
- **Origem:** 4ª revisão, itens 6.1, 6.2 e 6.3

## O que fazer
- [x] Corte transversal A–A da L1 e da L1c: rasgo, chapa, as duas faixas de madeira em contato com
      a chapa de topo e a folga no fundo do rasgo (demonstra o apoio por contato).
- [x] Furos da chapa embutida em **linha oculta** (hoje traço contínuo, como se fosse ligação lateral).
- [x] Vista da chapa em verdadeira grandeza com os oblongos cotados: comprimento, d0, posição do pino na montagem.
- [x] DES-05 com a altura de chapa final (ver nota da issue 71 sobre o valor 974 mm).

## Resolução ✅

- **DES-05 (L1):** elevação + **corte A–A** pela fileira de pinos.
  - O corte mostra o rasgo de 29 mm, a chapa embutida de 25 mm hachurada, os furos ovalizados abertos em volta dos pinos, os pinos cortados com tampões nas faces e a folga de 15 mm no fundo do rasgo.
  - Cotas: as duas faixas de 145,5 mm em contato com a chapa de topo e 138 mm de madeira inteira acima do rasgo.
  - Por baixo: o topo do pilar com a chapa vertical e as cavilhas.
- **DES-05B (L1c):** elevação + **corte B–B**, fora do pilar, sobre o consolo da sela, com os 3 enrijecedores cortados na altura correspondente.
- **DES-05C:** chapas embutidas L1 (270×877) e L1c (250×877) em verdadeira grandeza, escala 1:10.
  - Alturas dos furos cotadas a partir da borda soldada.
  - Detalhe do furo ampliado 4×: d0 = 26, comprimento 61, folgas 21/16 com o pino na posição de projeto.
  - Tabela de montagem: folga acima de cada pino para u = 13, 15 e 17 %, vinda de `curso_oblongo`.
- **Linha oculta:** os furos ovalizados (dentro da viga) agora são tracejados (`_pino(oculto=True)`); a ponta do pino na face continua cheia.
- **Altura final da chapa:** 877 mm, lida do esquadro (o 974 já tinha caído na issue 71).
- **Legibilidade:**
  - As cotas ganharam fundo branco.
  - As cotas da L1/L1c foram redistribuídas: ℓef virou nota; "chapa e pilar 270" foi para cima da viga.
- **Desenho antigo** `des05_ligacoes_L1_L1c.pdf` removido. cap08 com três figuras (`fig:des-l1`, `fig:des-l1c`, `fig:des-chapa-l1`); apêndice E atualizado.
- **Testes:** `test_issue90_desenhos_L1.py`; contagem de folhas 10 → 12. 825 passed. Tese 154 p., 0 overfull.
