# 123 — Redação: menos certeza do que a demonstração e ajustes pontuais

- **Tema:** Redação
- **Prioridade:** P2
- **Origem:** Revisão técnica (comentários tipo banca), 2026-11-14, item 15

## Expressões
- [x] "Testes automatizados impedem a propagação silenciosa de erros" → reduzem o risco de regressões nos comportamentos cobertos.
- [x] "Assegurando equivalência" → equivalência de execução e de resultados, não validação física.
- [x] "Veredito global de aprovação" → atendimento às verificações implementadas, sob as hipóteses adotadas.
- [x] "A margem compensa a ruptura sem aviso" → acrescenta reserva de resistência.
- [x] "Nenhuma verificação da viga governa" → restringir à geometria adotada; a fronteira paramétrica é governada pela viga.
- [x] "Sem momento" / "sem efeito da umidade" → delimitar ao modelo idealizado.
- [x] "Cerca de metade de 1,50 kN/m²" → retirar ou reduzir: a referência é arbitrada (issue 96).
- [x] "Espaço de soluções viáveis" → soluções aprovadas pelo conjunto de critérios implementados.
- [x] Resumo: "cobertura… composta por nove pórticos" (concordância).
- [x] Uniformizar "água", "meia-água", "tramo" e "vão" ("terças a oito painéis por água").

## Ajustes
- [x] Tab. 13 × §4.3: os critérios de inclinação e altura não coincidem com a justificativa.
- [x] Símbolos de cortante vertical, cortante local e reação (com a 115).
- [x] 75 itens cadastrados × 73 executados: a conclusão não pode dizer "75 atendidas".
- [x] 228 mm/h: identificar a fonte pluviométrica e o local.
- [x] "Ficha técnica" → produto identificado, ou premissa declarada.
- [x] Escala das pranchas: figuras reduzidas na monografia não preservam a escala indicada (nota ou escala gráfica).
- [x] Fig. 4 (p. 40): texto inferior cortado.
- [x] Reduzir a repetição dos mesmos resultados no resumo, §4.2.3, §6.8 e cap. 8.

## Resolução (2026-11-15) ✅

Expressões:
- "impedem a propagação silenciosa de erros" (cap. 1) → "reduzem o risco de regressões nos comportamentos que cobrem"; "espaço de geometrias viáveis" → "grade de geometrias candidatas".
- "Assegurando equivalência": resumo/abstract (122), cap. 9 e Apêndice A → "equivalência de execução e de resultados", com a ressalva de que não é validação física.
- "Veredito global de aprovação" (cap. 7) → "todas as verificações executadas atendem aos critérios adotados, sob as hipóteses de modelo declaradas".
- "A margem compensa a ruptura sem aviso" → feito na 118 ("reserva de resistência").
- "Nenhuma verificação da viga governa" → feito na 122 (restrito à geometria adotada).
- "Sem momento e sem efeito da umidade" (Tab. das soluções do nó) → "no modelo idealizado, sem momento no topo e sem o inchamento da viga entre os níveis".
- "Cerca de metade de 1,50 kN/m²" retirado do cap. 6 e do cap. 9 (o 4.º resultado passa a falar das distribuições: viga pela altura, terças como linhas de carga).
- "Espaço de soluções" → "grade" (cap. 5) e "entre as geometrias aprovadas na grade examinada" (122).
- Resumo: "composto" → "composta".
- Terminologia: "meia-água" → "água" (cap. 6, 8, apêndice C e geradores `apendice_analise.py`, `report.py`, `validacao.py`); "tramo" mantido só como termo da NBR 6123, agora definido no cap. 4.

Ajustes:
- Tab. 13 (`criterios-predim`) alinhada à § geometria adotada: inclinação = mínimo de 8° da calha + margem + transporte; h₀ = L1 com rasgo, margem na viga e beiral; largura = margem nos modos frágeis da L1 + alinhamento; diagonal da cobertura Ø28 → Ø36; terças = varredura + escora de beiral. Texto introdutório reescrito.
- Símbolos: V_Ed definido como cortante perpendicular ao eixo, no apoio, junto ao vão (R_Ed e S(x) já distintos; tabela do cap. 6 separou R_Ed 107 e V_Ed 95,0 na 115/117).
- Contagem: cap. 9 diz "N implementadas, das quais N executadas e N não aplicáveis, é atendido" (macros geradas).
- 228 mm/h: declarado no texto como tabela 5 da NBR 10844 para Curitiba, premissa até a definição do local.
- "Ficha técnica" da telha → "Premissa, ordem de grandeza de catálogo".
- Escala: nota no cap. 8 — figuras reduzidas; a escala do carimbo vale nas folhas do Apêndice E (tamanho natural) e a escala gráfica permite medir em qualquer reprodução.
