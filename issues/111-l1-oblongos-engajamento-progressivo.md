# 111 — L1: furos ovalizados e engajamento progressivo dos pinos

- **Tema:** Ligação viga–pilar (L1/L1c) sob arrancamento
- **Prioridade:** P1 — a taxa de 0,68 não está demonstrada para o detalhe
- **Origem:** Revisão técnica (comentários tipo banca), 2026-11-14, item 3

## Diagnóstico
- A gravidade passa por contato e o arrancamento pelos pinos em furos ovalizados verticais. O texto diz que os pinos só engajam após ~8 mm e ~12 mm: as folgas diferem de pino para pino com a retração e o inchamento.
- O cálculo soma 6·F_v,Rd, como se todos os pinos estivessem ativos. Numa ligação classificada como frágil, a redistribuição não pode ser presumida.
- O uso de Johansen para chapa espessa (folga < 0,1d) compara só a largura do furo (26 mm) com d (24 mm). O alongamento do furo na direção da força não é discutido.

## O que fazer
- [x] Modelo força–deslocamento do grupo: folga individual, K_ser/K_u por pino, embutimento, plastificação e fendilhamento durante o engajamento sequencial. Verificar o primeiro pino a encostar.
- [x] Ou reformular o detalhe para engajamento controlado: furos ovalizados com folga igual em todos os pinos, chapa ajustada em obra (furação in loco), ou um dispositivo único de arrancamento (ex.: tirante interno, como no pilar corrente).
- [x] Justificar ou trocar o modo de Johansen aplicável com furo alongado.
- [x] Texto §7.2 e Apêndice B.

## Resolução (2026-11-15) — decisão do autor: grupo 3×2 no topo ✅

**Diagnóstico confirmado** (`issues/111-estudo-engajamento.py`, modelo elástico-perfeitamente plástico por pino, K_u = 2/3·K_ser aço–madeira, patamar em F_v,Rd):
- Coluna 1×6 (458–818 mm), umidade mínima (14 %): folgas de 7,7 a 12,2 mm, Δg = 4,5 mm. Sob P_d = 100,5 kN o pino mais alto não encostou, 3 pinos no patamar (F_el,máx = 2,2·F_Rd), e o fendilhamento com h_e ativo = 746 mm dá η = 0,83 > 0,75. Reprovado.

**Johansen com furo alongado:** a fórmula (8.11) do EC5 §8.2.3(3) vale para chapa central "de qualquer espessura": por simetria o pino não gira junto à chapa; a distinção fina/espessa do §8.2.3(1) (folga < 0,1d) não se aplica. O texto antigo justificava pela chapa espessa — corrigido.

**Novo critério** (`oblongo_L1.verificar_engajamento`, catálogo `engajamento_L1`): Δg = α⊥·Δu·(y_max − y_min) + 1,0 mm (fabricação, ±0,5 mm) ≤ d0 − d = 2 mm, a folga normal para a qual a regra de grupo n_ef·F_v,Rd é usada; e a fileira superior em carga sob P_d. Limita o grupo a 2 fileiras (`n_fileiras_max`, aplicado no otimizador quando há apoio por contato).

**n_ef** por interpolação EC5 §8.5.1.1(4) (n ⊥ fibras; `n_ef_angulo`): fileira de 3 a 85,2° → 2,94; grupo 5,88.

**Resultado:**
- L1 e L1c: 6 × Ø24, 3 por fileira × 2 fileiras (818 e 746 mm), a1 = 76, a2 = 72. R_d = 147 kN, η = 0,69 (antes 0,68 com n_ef = 6).
- Engajamento: Δg = 0,9 + 1,0 = 1,9 mm → η = 0,95 (**novo η_max do projeto**; a maior de resistência segue 0,91, lâmina do central montante).
- Fendilhamento inalterado (h_e = 818, η 0,67).
- Chapa L1 270 mm (grupo centrado sobre o pilar, 59/76/76/59); chapa L1c 359 mm (a3,t = 168 da extremidade), avança 109 mm além da sela por dentro do rasgo.
- Levantamento antes do engajamento: 11 mm (fileira inferior) e 12 mm (superior) — ver issue 112.
- Desempate do otimizador: menor nº de pinos → grupo mais compacto → menor η (antes a L1c escolhia fileira única de 6, chapa 587 mm).

**Arquivos:** `connections/connections.py` (n_ef_angulo, limite de fileiras, desempate), `connections/oblongo_L1.py` (critério e verificação; `geometria_rasgo(n_fileiras=)`), `main.py` (verificação, chapas e posições dos pinos; rótulos do critério frágil corrigidos — havia 2 nomes "bloco" sobrando que deslocavam os rótulos), `output/report.py`, `output/desenhos.py` (DES-05, 05B, 05C com colunas × fileiras), `output/memorial_equacoes.py` (n_ef interpolado no Apêndice B). Testes: `tests/test_issue111_engajamento.py` (7).

**Tese:** cap. 8 (§ pinos: arranjo, n_ef, Johansen; nova §`ssec:engajamento-pinos`; curso 11/12 mm; rasgo 270/359 mm; tabelas de modos e da cadeia L3 0,69); cap. 7 e resumo/abstract (η_max 0,95 atribuído ao engajamento). De passagem, números antigos de contraventamento corrigidos: cap. 5, 7, 8 e 9 (transversal 0,82 → 0,55; cobertura 0,89 → 0,80) e a tabela das ligações de extremidade das diagonais (Ø45/Ø33/Ø36/Ø12, η de capacidade 0,88/0,88/0,89/0,85; sobre-resistência da vertical 1,20).
