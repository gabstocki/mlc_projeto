# 113 — Rigidez horizontal do apoio no sistema espacial (empuxo nulo)

- **Tema:** Modelo da viga — condição de apoio
- **Prioridade:** P1
- **Origem:** Revisão técnica (comentários tipo banca), 2026-11-14, item 5
- **Relaciona:** AUD-006 (memória: sway × afastamento são graus de liberdade distintos), issues 35/38, 110

## Diagnóstico — PARCIAL
- O empuxo nulo foi justificado pela rigidez do pilar isolado (52,8 kN/m). Mas os topos estão ligados ao diafragma e aos frontões, e a rigidez ao **afastamento relativo** dos dois apoios de uma viga depende do sistema.
- Nos pórticos intermediários, o afastamento A–B é resistido só pela própria viga, porque as terças são longitudinais. No pórtico de frontão, o CV-T prende P1, mas P2 é livre. É preciso demonstrar isso com o modelo espacial da issue 110.
- Os oblongos verticais não liberam o movimento horizontal.
- "Modelo conservador" é amplo demais: é o modelo que dá o maior momento positivo no cenário gravitacional.

## O que fazer
- [x] Com o modelo espacial (110), extrair a rigidez ao afastamento dos apoios em cada pórtico (incluindo os de frontão) e o empuxo que se desenvolve; incluir o atrito no contato.
- [x] Mostrar que H ≈ 0, ou incorporar H.
- [x] Trocar "conservador" pela formulação restrita (cap. 6).

## Resolução ✅ (2026-11-15)

**Achado:** com as cruzes CV-D (issue 110), o diafragma passou a restringir o afastamento dos apoios. A premissa da AUD-006 / `empuxo_no_frontao` ("o diafragma não restringe esse modo") deixou de valer, embora o efeito seja pequeno.

**Método** (`checks/elu/empuxo_sistema.py`)
- No modelo em planta (`diafragma_espacial`, agora com `sem_viga` e `cargas`), retira-se a viga A–B de cada pórtico e aplica-se ±10 kN nos dois apoios.
- k_ap = P/Δ. H_dev = H_rígido·k_ap/(k_ap + k_arco), com as duas molas em série.

**Resultados**
- k_ap: 1.032 kN/m (pórticos centrais) a 3.248 kN/m (pórticos 2 e 8, vizinhos das CV-H). Contra k_arco = 208.462 kN/m, fica duas ordens de grandeza abaixo.
- H_dev máx 4,0 kN (1,5 % do rígido, 263 kN) nos pórticos 2 e 8; 1,3 kN nos centrais; 3,9 / 3,0 kN nos frontões (substitui o `empuxo_no_frontao`, que usava geometria e diâmetro errados: vão de 20,25 m e D_BARRA_CV_MM).
- Efeitos: ΔM cumeeira −3,6 kN·m (favorável, desprezado); ΔN +4 kN (desprezável); força horizontal nos pinos da L1, η 0,03 (`empuxo_sistema` no catálogo).
- Sem as CV-D, os pórticos centrais voltam a k_ap = 0 (mecanismo).
- O atrito no contato viga–chapa não altera o resultado: a chapa acompanha o topo do pilar, e só o sistema restringe esse movimento.
- O modelo biapoiado (H = 0) continua adotado, agora justificado pelo sistema e não pelo pilar isolado.

**Tese**
- Cap. 6 (§ modelo do apoio): novo parágrafo com o diafragma, os furos ovalizados verticais (não liberam o movimento), k_ap, H_dev, efeitos e atrito; "nenhum esforço" → "nenhum esforço relevante".
- O "modelo conservador" já fora trocado na 114.
- Cap. 7: linha na tabela de contraventamentos.

**Testes:** `tests/test_issue113_empuxo_sistema.py` (2). Resultado: 871 passed.
