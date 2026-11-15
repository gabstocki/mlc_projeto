# 112 — Deslocamento total sob sucção: folgas, pinos, tirante, chapas e viga

- **Tema:** Serviço e compatibilidade
- **Prioridade:** P1
- **Origem:** Revisão técnica (comentários tipo banca), 2026-11-14, itens 4 e 7 (p. 81)

## Diagnóstico — CONFIRMADO
- O texto chama de "pequeno, diante das flechas" um levantamento de 8–12 mm. Mas as flechas são 6,20 mm (instantânea) e 3,28 mm (ascendente líquida): a comparação está invertida.
- Tirante interno M20: ΔL = N·L/(E·A_s) = 98,3·7.000/(200.000·245) ≈ 14 mm na força de cálculo. Em serviço é menor, mas é da mesma ordem.

## O que fazer
- [x] Somar, ao longo do caminho de carga sob sucção (combinação característica): folgas dos oblongos, deslizamento dos pinos (K_ser), alongamento do tirante, deformação das chapas e da ancoragem, e flecha ascendente da viga.
- [x] Verificar a compatibilidade com escoras, nó, telha, calha, rufos e terça–viga. Definir um limite e citar a sua origem.
- [x] Corrigir a frase da p. 81.

**Nota (issue 111, 2026-11-15):** com o grupo 3×2 no topo, o levantamento antes do engajamento passa a 11 mm (fileira inferior) e 12 mm (superior). `verificar_engajamento` já devolve o levantamento sob P_d (`levantamento_P_d_mm`) do modelo do grupo — ponto de partida para a soma desta issue.

## Resolução (2026-11-15) ✅

Nova verificação `deslocamento_succao` (`checks/els/deslocamento_succao.py`; catálogo ELS), combinação característica G + W (EN 1990 §6.5.3(2)a): R_up,k = 48,7 kN por apoio (`reacao_arrancamento_caracteristica`, em `checks/elu/apoio.py`).

| Parcela (mm) | L3 14 % | L3 19 % | L3c 14 % | L3c 19 % | Montante 14 % | Montante 19 % |
|---|---|---|---|---|---|---|
| Folga acima dos pinos | 11,3 | 2,0 | 11,3 | 2,0 | 11,3 | 2,0 |
| Deslizamento (K_ser 35,9 kN/mm/pino, engajamento sequencial) | 0,5 | 0,2 | 0,5 | 0,2 | 0,5 | 0,2 |
| Tirante interno (M20 / M27, 6,7 m) | 6,7 | 6,7 | 7,1 | 7,1 | — | — |
| Lâminas + pé (folga d0 − d = 2 mm + K_ser) | — | — | — | — | 2,9 | 2,9 |
| Chapas e chumbadores | 0,2 | 0,2 | 0,3 | 0,3 | 0,1 | 0,1 |
| **Total** | **18,6** | 9,1 | **19,2** | 9,7 | **14,8** | 5,2 |

O tirante, estimado na revisão em ~14 mm com a força de cálculo, dá 6,7 mm na característica. Flecha ascendente líquida da viga: 3,0 mm no meio do vão → até 22,2 mm no meio do vão.

**Limite (EN 1990 A1.4.2: critérios de funcionalidade fixados no projeto):** o curso de cada detalhe deslizante.
- Escora dos montantes: subida nos pinos + inchamento da altura toda desde a montagem mais seca = 17,2 mm (u = 19 %) de 25 mm → η 0,69. A folga de 25 mm (constante do desenho) passa a ser verificada.
- Topo dos PF (L1f, curso 20 mm): apoio bipartido 14,8 + flecha ascendente 2,4 + inchamento até o pino mais alto da L1f = 18,0 mm → η 0,90 (governa).
- Condutor da calha (sobe com o apoio central, 19,2 mm): junta deslizante de 30 mm, especificada no DES-10.
- Terças/telhas: diferencial de 15,6 mm entre escora do montante e viga corrente vizinha → rotação 1/370, acomodada pela ligação rotulada.

**Frase da p. 81 corrigida:** o levantamento (≈ 6× a flecha ascendente) deixou de ser chamado "pequeno"; remete à nova §`ssec:deslocamento-succao` (cap. 8, com tabela).

Arquivos: `checks/els/deslocamento_succao.py` (novo), `checks/elu/apoio.py`, `main.py`, `output/report.py`, `output/desenhos.py` (DES-10; `flecha_no_ponto` passa a vir do módulo novo). Testes: `tests/test_issue112_deslocamento_succao.py` (4).

**Complemento (2026-11-15, durante a 115):** a varredura com a verificação nova reprovou 310 geometrias de viga alta (h₀ ≥ 1,10 m): o curso do L1f era fixo pela flecha descendente (20 mm) e a subida cresce com a altura do pino da L1. O curso passa a ser dimensionado também pela subida (`topo["curso_min_mm"]`, múltiplos de 5 mm, taxa ≤ 0,90, laço no main; `detalhe_topo_pf` lê o mínimo, e desenho e quadro de espaçamentos acompanham). Na geometria adotada continua 20 mm. Varredura refeita.
