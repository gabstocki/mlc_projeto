# 72 — Furos ovalizados da L1/L1c: posição do pino na montagem e curso para retração/fluência

- **Tema:** Ligações — L1/L1c
- **Prioridade:** P1
- **Normas:** EC5 §2.3.2.2 / k_def (fluência ⊥), EN 1995-1-1 §3.4 (umidade, CS3); retração ⊥ às fibras da MLC (coeficiente ~0,25 %/% de umidade — citar fonte)
- **Arquivos:** `main.py` (`FOLGA_OBLONGO_L1_MM = 10`), `connections/connections.py`, `output/desenhos.py`, `tese/cap08.tex` §7.2
- **Relaciona:** 71, 79, 90
- **Origem:** 4ª revisão, item 2.4

## Problema
Não está definida a posição do pino dentro do oblongo na montagem. A folga deve ficar **abaixo**
do pino para absorver a retração e a fluência por compressão ⊥ no apoio. Se a folga se esgotar,
a gravidade volta aos pinos e o fendilhamento volta a 0,97 sem reforço.

## O que fazer
- [ ] Estimar a variação de umidade esperada em CS3 (faixa de equilíbrio) e a retração ⊥ da altura
      da viga entre o apoio e o pino mais alto; somar o recalque por fluência da compressão ⊥ (k_def).
- [ ] Dimensionar o curso do oblongo com margem e definir a posição do pino na montagem (topo do furo).
- [ ] Reverificar e4 com o novo curso (issue 79) e cotar no desenho (issue 90).

## Resolução ✅ (2026-11-07) — curso duplo + umidade de montagem (decisão do autor)
**Achado:** para MLC (sai seca da fábrica, EN 14080 ≤ 15 %), o movimento dominante em CS3 é o
**inchamento** (pino sobe em relação à chapa fixa), não a retração suposta no item 2.4. Folga só abaixo
impediria o inchamento (compressão ⊥ ≫ f_c,90 e pinos carregados). Resposta ao orientador: curso nos dois
sentidos.

**Modelo** (`connections/oblongo_L1.py`): Δ = α⊥·Δu·y, α⊥ = 0,25 %/% (Thelandersson & Larsen); montagem
**15 ± 2 %** (especificada, com aclimatação); serviço **14–19 %** (UR 70–85 % sob a cobertura); compressão ⊥
com dispersão 45°: δ = R/(2·b·E90)·ln((l+2y)/l), ×(1+k_def) na permanente; tolerância 2 mm em cada sentido.
Pino mais alto y = 928 mm: baixo = retração 7,0 + fluência 1,6 + elástica 0,3 + 2 = 10,9 → **15 mm**;
cima = inchamento 13,9 + 2 = 15,9 → **20 mm** (múltiplos de 5). η = 0,80 (exigido/adotado), nova verificação
no catálogo. **Levantamento** sob arrancamento antes de os pinos pegarem: 9 mm (1.º pino) a 14 mm (mais
alto), na umidade mínima — declarado. **Regra de montagem:** folga acima do pino i = α⊥(19 − u_medido)·y_i
+ 2 mm (16 / 11 / 6,6 mm no pino alto a 13 / 15 / 17 %).

**Efeitos:** chapa embutida L1/L1c 977 → **987 mm** (e4 = 39 mm acima do centro do raio superior); restam
13 mm de madeira sobre a chapa → **issue 71**. FOLGA_OBLONGO_L1_MM removido; quadro e DES-05 com curso
assimétrico. 67 verificações; η_max 0,90 inalterado. Testes `tests/test_issue72_oblongo.py` (3) + 3
ajustados. 772 passed.

**Tese:** nova §7.2.x «Curso dos furos ovalizados» (parcelas, tabela, regra de montagem, levantamento);
§7.7 com 987 mm.

**Fica para:** a escora/nó de topo deve acomodar o movimento vertical da viga (issues 69/81/91); altura do
rasgo (71); vista da chapa em VG com os oblongos cotados (90).
