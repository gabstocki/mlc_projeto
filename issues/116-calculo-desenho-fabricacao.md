# 116 — Equivalência cálculo × cota de desenho × lista de fabricação

- **Tema:** Desenhos e detalhamento
- **Prioridade:** P1
- **Origem:** Revisão técnica (comentários tipo banca), 2026-11-14, item 8

## Exemplos apontados (a conferir)
- Chapa de topo da L1: o cálculo usa apoio de 270 mm e largura 320 mm, e o texto diz "cobre toda a seção do pilar". A lista de peças da Fig. 13 traz 250 × 300 × 16 mm.
- Rasgo: 270 mm (p. 82) × prolongamento de 30 mm além de cada face (p. 108) → ≥ 330 mm.

## O que fazer
- [x] Conferência sistemática: cada dimensão de cálculo (apoio, chapas, rasgos, furos, distâncias) deve vir da mesma variável que gera a cota e a lista de peças. Teste que compara `res_elu`/conexões com as listas de `desenhos.py`.
- [x] Corrigir as divergências encontradas, no cálculo ou no desenho.

## Resolução (2026-11-15) ✅

**Teste de equivalência** `tests/test_issue116_calculo_desenho.py`: monta o arranjo dos desenhos de uma execução nova (com `main.arranjo_kwargs(res)`, agora fonte única dos argumentos do desenho) e confere, contra as variáveis de cálculo:
- chapa de topo L1 (CH-01 da lista) = comprimento de apoio da verificação de contato × largura do pilar × t;
- sela por viga = l de apoio da verificação central;
- chapa embutida, pinos (n, d, posições x e y), fundo, largura e comprimento do rasgo, cursos do oblongo;
- tirante da lista (TR-01) = diâmetro e comprimento de corte do cálculo; comprimento elástico do deslocamento sob sucção = livre do tirante;
- folga da escora, curso do L1f e junta do condutor = os verificados em `deslocamento_succao`;
- chapas de base desenhadas = calculadas.

**Divergências corrigidas:**
- **Chapa de topo da L1:** desenho/lista com 250 × 300 (pilar − 20 mm), cálculo e texto com a seção inteira 270 × 320. Desenho passa a usar `chapa_topo_L1(arr)` = h × b do pilar.
- **Rasgo:** texto dizia 270 mm (o comprimento da chapa); o rasgo passa 30 mm além da chapa (ventilação, issue 83): 330 mm na L1 e 389 mm na L1c. Valor único `esquadro[...]["L_rasgo_mm"]`, usado no desenho (DES-05 desenha; DES-05B cota na nota) e no texto.
- **Tirante interno:** lista com M20 × 7.000 (altura nó a nó). Nova `comprimento_tirante` (`connections/tirante_interno.py`): livre = madeira + chapa do pilarete (6.719 mm), corte = livre + rosca na luva + arruela + porca + sobra → 6.790 mm (M20). O deslocamento sob sucção usa o livre.
- **Lâmina do montante:** o desenho a leva até a escora (madeira + h₀ + folga de 25 mm), o cálculo de flambagem usava L_y = madeira + h₀. Constante `FOLGA_ESCORA_VIGA_MM` movida para `checks/elu/pilar_bipartido.py` (fonte única) e somada a L_y (η 0,91 inalterada a duas casas).

Varredura refeita após estas mudanças.
