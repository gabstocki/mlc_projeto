# 106 — Efeitos do pilar bipartido e do tirante interno ainda não propagados

- **Tema:** Coerência cálculo × tese após as issues 104 e 105
- **Prioridade:** P1 (os itens 2 e 3 podem mudar o dimensionamento das lâminas)
- **Origem:** revisão pedida pelo autor em 2026-11-11 ("a tese tem itens que sofreram alteração depois dessa opção")

## O que fazer
- [x] 1. Cap. 6, figura 11 e Tabela 18: o texto cita 504 kN·m (FEM) e 504 kN·m (analítico); hoje são 481 (FEM) e 478 kN·m (pipeline); V 99,6 → 106 kN. As quatro imagens do modelo 3D já foram regeneradas (beirais, bipartidos, PF).
- [x] 2. Incêndio de veículo (EN 1991-1-2 An. C) e R30 informativo: verificar as lâminas de 0,16 × 0,32 m dos montantes, mais finas que os pilares maciços.
- [x] 3. Choque de veículo (EN 1991-1-7) na lâmina: flexão e cortante da lâmina atingida, com o espaçador do pé.
- [x] 4. Cargas para a fundação: conferir se as bases dos montantes recebem a força do pilar inteiro, e não a de uma lâmina.
- [x] 5. Varredura global: refazer depois do tirante interno e das chapas duplas (issue 105).
- [x] 6. Apêndice B: conferir as equações do pé/topo e da base mais solicitada com a nova concepção.

- [x] 7. Números antigos na tese: a comparação do console do último commit com o atual mostra valores de antes das issues 82 (beiral), 104 e 105 ainda citados em cap06, cap07, cap09 e apêndice C. Exemplos: g_k 0,823 → 0,764 kN/m², atrito 777 → 862 kN, α_cr 124,75 → 117,18, pilar central 199 → 212 kN, CV-V Ø33 → Ø36. Script: `issues/106-numeros-antigos.py`.

Custo, contagens de verificações e de testes ficam para a issue 99.

## Resolução (2026-11-12)

1. **Cap. 6:** a figura 11 agora cita 481 kN·m (MEF) contra 478 kN·m (analítico), diferença de 0,6%. Na Tabela 18: M 478, V 106, N 8,37 kN e sucção −7,91 kN/m. A tabela de rigidez do apoio foi refeita com a auditoria atual (282 → 481 kN·m, +70,4%) e explica o alívio de 3 kN·m do beiral. N = 95,3·sen 5,04° (cortante do lado do vão) e Q+0,6W 500/478. Atualizados também cargas permanentes (0,764/0,330), atrito 862 kN (2,29×), α_cr 103,83/19,63 e k_II 1,05. Resumo e cap. 9 passam a 70,4%.
2. **Incêndio:** `pilar_bipartido.verificar_lamina_fogo` aplica a seção residual nas 4 faces e refaz o pilar composto (Anexo C) com b_fi. `tempo_colapso_lamina` alimenta o incêndio de veículo.
   - R30: 104×264 mm, η 0,18.
   - Incêndio de veículo: colapso em 61 min contra 54 min de exposição, η 0,89. Passa a governar a robustez.
   - Pilarete Ø114,3×8 da lâmina: 1,05 sem proteção e 0,36 com intumescente (já especificada para todos os pilaretes).
3. **Choque:** `verificar_lamina_impacto` parte da força a 0,20 m acima do pé, dentro do espaçador do pé (80–530 mm). Cada lâmina recebe metade, por contato (fachada) ou pelos 2 M16 (pórtico), a mesma hipótese da base L3a (V/2). Resultado η 0,48, governado pelos parafusos. Com a lâmina sozinha, 0,84 (informativo).
4. **Fundação:** o quadro usa as reações do carregamento mais o download dos CV, não a força por lâmina. Nada a corrigir.
6. **Apêndice B:** é gerado por `memorial_equacoes` e já está com a concepção atual (L1 com 6 pinos, pé da L3a, ancoragem 357/527).
7. **Cap. 7, 8 e 9:** a varredura de números antigos (`issues/106-numeros-antigos.py`) corrigiu:
   - Viga, pilares, terças (seção 0,20×0,40), balanços, estabilidade global, ELS (14,34 mm, 0,18), síntese (0,90).
   - Ancoragens: canto 357/188 kN, η 0,36/0,68/0,71; central montante 342/118 kN.
   - Pinos de L1 (6 pinos, 100,5 kN, 0,68), L1f (69,8 kN, 4 cavilhas, 0,63) e L3f (0,27).
   - CV-V Ø36/M39 e CV-T Ø27/M30.

   Ficam para a issue 99, como já previsto, a seção de custo (volumes, massas de aço, 1.863 → 2.067 m² e 0,189 → 0,130) e as contagens.

5. **Varredura global** refeita (`-j 7`): 1.115 de 3.213 aprovadas (antes 1.067).
   - Agora b = 0,30 m aprova; as larguras ≤ 0,28 m reprovam pela ligação terça–viga.
   - O cap. 5 foi atualizado: alíneas, contagens, fronteira (0,30 m até a margem de 0,60), faixa do bipartido 0,66–0,75 e justificativa da largura.
   - A decisão de manter 0,32 m virou a issue 107.

Testes: `tests/test_issue106_laminas_acidentais.py`.
