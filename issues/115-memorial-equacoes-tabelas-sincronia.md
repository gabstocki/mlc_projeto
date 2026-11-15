# 115 — Memorial: equações que não reproduzem o resultado e tabelas dessincronizadas

- **Tema:** Coerência do memorial
- **Prioridade:** P1 — erros objetivos
- **Origem:** Revisão técnica (comentários tipo banca), 2026-11-14, item 7

## Itens (conferidos)
- [x] **B.1:** imprime b = 0,32 m e τ = 0,73 MPa. Com 0,32 dá 0,664; 0,73 exige b − t_rasgo = 0,291 m. Corrigir o gerador (`memorial_equacoes.py`) para mostrar a largura líquida.
- [x] **B.6:** 106 + 173 = 279, mas mostra 285. Falta a parcela do vento (ΔN = M_vento/a₁ ≈ 5,4 kN) e, no canto, a do frontão. Mostrar todos os termos.
- [x] **P. 62 × Tab. 58:** −394 × −408 kN·m. Identificar combinação e grandeza (M na seção crítica da LTB × extremo).
- [x] **Tab. 18 × Tab. 58:** 106 × 94,9 kN. Distinguir reação, cortante vertical no vão e cortante no eixo local (símbolos: issue 97).
- [x] **Tab. 18 × Tab. 58:** −7,91 × (−9,71; −6,11) kN/m. Definir −7,91 (média das meias-águas?) ou trocar.
- [x] **P. 62 × Apêndice B:** borda inclinada a 3,48 m × 16,8 m. Explicar a simetria e a origem de x.
- [x] **Tab. 48 × Tab. 38 × Apêndice D:** escora de beiral com 3 × 5 fileiras. Uniformizar com a solução da 105 (chapas duplas).
- [x] Teste automático: cada equação do Apêndice B recalculada a partir dos números impressos deve reproduzir o resultado impresso (tolerância de arredondamento).

## Resolução (2026-11-15) ✅

**Conferidor automático** (`mlc_projeto/output/conferir_memorial.py`; `python -m mlc_projeto.output.conferir_memorial`): converte cada trecho numérico das equações do Apêndice B para Python e confere "expressão = resultado impresso" com tolerância de 1 unidade da última casa (as taxas são arredondadas para cima) + 0,6 % (entradas arredondadas). Trechos com símbolos são ignorados. Teste `tests/test_issue115_memorial.py` gera o apêndice de uma execução nova e exige 0 erros em ≥ 25 igualdades (hoje 31/31); outro teste confirma que uma conta errada (104 + 258 = 368) é acusada.

O conferidor achou dois erros:
- **B.1 (cisalhamento):** imprimia b = 0,32; a conta usa b − t_rasgo = 0,291. Gerador corrigido: k_cr·(b − t_rasgo)·h.
- **Cone da ancoragem de canto (não listado na revisão):** imprimia h_ef = 400 fixo no gerador; o cálculo usa 500 (ancoragem dos montantes, issue 109) → 8,9·√25·400^1,5 = 356 ≠ 498. O cone passa a devolver `h_ef_mm` e o gerador o imprime.

Demais itens:
- **B.6:** N = R + D + M_w/a₁ = 104 + 258 + 2,69/0,50 = 368 (antes a parcela do vento não aparecia); f_c,0,d impresso numericamente (12,5 MPa) para a linha de η ser conferível. `pilar_bipartido` devolve `dN_vento_kN` e `f_c0d_MPa`.
- **M −394 (cap. 7) × apêndice C:** −394 era antigo; o maior momento de sucção é −390 (comb. 17). Texto corrigido, com remissão ao apêndice C; "15 combinações" → 27 (contagem do código); seção da LTB: "15,90 m do apoio esquerdo, ou 4,35 m do direito".
- **106/104 × 94,9 kN:** a Tab. de esforços governantes chamava de "cortante" a reação vertical. Agora duas linhas: R_Ed = 104 kN (reação) e V_Ed = 94,9 kN (cortante no eixo, no apoio). Símbolos já distintos na lista.
- **−7,91 kN/m:** é a média das duas águas (−9,71 e −6,11, comb. 15). Rotulado nas duas tabelas do cap. 6.
- **Borda inclinada 3,48 × 16,8 m:** mesma seção, medida de apoios opostos (o padrão governante é o espelhado). Gerador e cap. 7 dão as duas distâncias.
- **Escora de beiral 3 × 5 fileiras:** a tabela de retração (cap. 8) estava desatualizada em três linhas (escora de beiral, montante terça–viga, pés e topos). Passa a ser **gerada** (`output/tab_retracao.py` → `tese/tab_retracao.tex`) a partir de `retracao_chapas`, agrupando linhas iguais.

De passagem: durante a 115 a varredura revelou que o curso do L1f precisava acompanhar a subida (ver complemento na issue 112).
