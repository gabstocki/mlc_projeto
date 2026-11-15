# 118 — Hierarquia de ruptura: retirar ductilidade presumida

- **Tema:** Filosofia de segurança das ligações
- **Prioridade:** P2 (texto; sem mudança de cálculo)
- **Origem:** Revisão técnica (comentários tipo banca), 2026-11-14, item 10

## Diagnóstico
- "A viga de MLC escoa progressivamente e redistribui": incorreto. A ruptura por tração das fibras é frágil.
- "A solda (0,86) cede antes do concreto (0,24)": uma hierarquia por capacidade exige resistências compatíveis, a sobrerresistência do elo dúctil e um mecanismo caracterizado. Taxas com γ distintos não a demonstram.

## O que fazer
- [x] Reescrever §7.1 (p. 73–74) e p. 89: manter a margem adicional (0,75) como reserva de resistência, sem afirmar mecanismo dúctil garantido.
- [x] Onde houver dimensionamento por capacidade de fato (diagonais com rosca recalcada → olhal), manter, explicitando a sobrerresistência.

## Resolução (2026-11-15) ✅ — só texto, cap. 8

- Johansen: os modos com plastificação do pino "desenvolvem, em geral, deformação apreciável antes da ruptura", mas a ductilidade depende da esbeltez do pino e da espessura da madeira e a norma não a quantifica nem garante (antes: "são dúcteis e permitem redistribuição"). Tabela dos modos: "Dúctil" → "Com plastificação".
- Retirado "uma viga que atinge a resistência à flexão escoa progressivamente e redistribui": a tração das fibras também é frágil; a distinção ligação × elemento passa a ser de critério (incerteza da repartição entre pinos e da tração ⊥, e a ruptura de uma ligação retira o apoio de uma peça inteira).
- Margem 0,75: "reserva de resistência sobre a exigência normativa … não transforma o modo frágil em dúctil nem garante mecanismo com aviso" (antes: "compensa a ruptura sem aviso"). Exceções (compressão no concreto/madeira, escoamento do aço) qualificadas como modo isolado, não mecanismo do conjunto. Contato ⊥: "modo com grande deformação antes da ruptura".
- Cadeia da base: retirado "quem cede primeiro é um componente metálico"; as taxas indicam a reserva de cada elo sob a mesma tração, com γ distintos, e não a ordem de ruptura; uma hierarquia exigiria resistências compatíveis, sobrerresistência e mecanismo caracterizado.
- Diagonais: declarado como o único dimensionamento por capacidade do projeto, entre resistências de cálculo e sem fator de sobrerresistência; margem disponível = taxas de 0,88–0,89 das ligações, que cobrem resistência real da barra até ~12 % acima da de cálculo.
