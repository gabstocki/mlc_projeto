# 93 — Refazer a varredura global com o critério atual (EC5 §5.4.4 e demais correções)

- **Tema:** Pré-dimensionamento
- **Prioridade:** P1
- **Arquivos:** varredura global do pipeline, `tese/cap05.tex` §4.5.2 (tabela/figura), figuras de varredura
- **Relaciona:** 92, 46, 49 (pendência registrada: regenerar ~1 h)
- **Origem:** 4ª revisão, item 7.1 (§4.5.2)

## O que fazer
- [x] Reexecutar a varredura com o código atual (imperfeições §5.4.4 e todas as verificações vigentes,
      incluindo as que entrarem nas issues 69–87) — rodar **depois** das issues que mudam resultados.
- [x] Atualizar tabela, figura e texto do §4.5.2; retirar a justificativa da defasagem.
- [x] Confirmar que a geometria adotada continua a ótima (ou explicar).

- [x] (issue 82) `predim/varredura_global.py` cria `GeometriaViga` sem `a_bal`: incluir o beiral.

## Resolução ✅

- **`predim/varredura_global.py`:**
  - Grade completa da tese: α 6–16° (0,5), h₀ 0,40–1,20 (0,05), b 0,20–0,36 (0,02) = 3.213 pontos.
  - Paralela (`-j`).
  - Volume com os 18 balanços do beiral.
  - Listas de verificações atualizadas (balanco_viga, apoio_central, flexo_comp; sem ruptura_bloco_L1).
  - Coluna `reprova` com as verificações que falham.
  - Figura com eixos automáticos.
  - **Tabela gerada** `tese/tab_fronteira_volume.tex` (antes digitada à mão).
- **Resultado:** 1.067 de 3.213 aprovadas (antes 1.104 de 1.391). As reprovações vêm de restrições externas à viga:
  - **b ≤ 0,28 (todas reprovadas):** ligação terça–viga, bases L3/L3f/L3c/L3a e pilar central contraventado (1,19 com b = 0,24; 0,74 com b = 0,32).
  - **α < 8° (todas reprovadas):** calha da issue 83, com o último pano < 5 %.
  - **b = 0,30:** pés dos pilares (frágil > 0,75) em parte da grade.
  - **h₀ = 0,40:** cisalhamento e borda inclinada.
- **Fronteira:** mínimo 131,7 m³ (α 8, h₀ 0,40, b 0,32). Adotada: 226,6 m³ com beiral (220,8 sem).
  - Na adotada, a viga é governada pelo apoio central (0,58).
  - O conjunto é governado pelas bases ancoradas, soldas e retração (0,90) e pelos contraventamentos (0,89 e 0,82).
- **Geometria adotada confirmada (cap05 reescrito):**
  - b 0,32 é a menor largura que aprova em todas as h₀.
  - h₀ 1,00 acomoda a L1, o rasgo e o beiral.
  - Margem de 0,58 na viga.
  - α 10° = mínimo de 8° + 2°: último pano a 9,2 %. α 8° pouparia 9 %.
- **Atualizados:**
  - Contagens 1.391 → 3.213 no resumo, no abstract e no cap09.
  - "metade do volume" → "cerca de 60 %" (cap08 custo, cap09).
- **Pendente (99):**
  - Volume de vigas na tabela de custo (220,8 → 226,6).
  - Contagens de verificações e testes no resumo e no cap09.
  - CSVs antigos `varredura_global_extendida.csv` e `varredura_global_pipeline.csv`, agora obsoletos.
- **Testes:** 822 passed. Tese 151 p., 0 overfull.
