# 97 — Lista de símbolos: ausentes, um significado por símbolo, notação única

- **Tema:** Pré-textuais / notação
- **Prioridade:** P1 (trabalhoso: renomear no texto, no Apêndice B gerado e eventualmente no console)
- **Arquivos:** `tese/00-simbolos.tex`, todos os `capNN.tex`, `output/memorial_equacoes.py` (Apêndice B), `output/apendice_analise.py`
- **Origem:** 4ª revisão, itens 9.1, 9.2 e 9.3

## 9.1 Ausentes da lista
- [x] X_d, X_k (eq. 3.1); S(x) (eq. 5.2); F (eq. 7.3); w (eq. 7.2)
- [x] a1, a4,t, a1,CG, a2,CG; d0, e1 a e4, p1, p2; c e s das ancoragens; a e c dos olhais
- [x] n^0,9; w_G, w_Q; λ_y, λ_z; volume da zona de cumeeira (V, k_vol); f_h,0,k

## 9.2 Símbolos com mais de um significado (escolher e renomear)
- [x] q: carga distribuída × pressão dinâmica (F_t = 0,5 q a b, §6.4) → ex.: q_p ou q_vento
- [x] a, b em F_t: dimensões em planta × b (largura da viga) × a, c (olhais)
- [x] h: altura da seção × altura livre da NBR 6123 (7,00 m) que coincide com H
- [x] θ: inclinação do eixo da viga (§5.4) × inclinação das águas (§3.5.2, tg θ = tg 10°)
- [x] α: inclinação do extradorso × ângulo força–fibras × incidência do vento (Tab. 10 NBR 6123)
- [x] V_Ed: cortante × carga vertical total em H_imp = φ V_Ed (§5.5)
- [x] k_h: rigidez da mola × fator de altura do EC5 §3.2
- [x] s: espaçamento entre terças × entre chumbadores (Tabela 36)

## 9.3 Redundâncias e grafia
- [x] Uma notação: M_Ed/M_d, N_Ed/N_d, V_Ed/V_d; M_ap,d/M_cum; R_v/R_A, R_B.
- [x] “w_net,f in” → w_net,fin (\mathrm{fin} no subscrito).

## Resolução (2026-11-12)
**9.1 — incluídos na lista:**
- X_k e X_d; S(x); F (choque); w (fendilhamento, fórmula 8.4); w_G e w_Q.
- a₁; a₁,CG e a₂,CG; a₄,t; d₀; e₁ e e₂; p.
- c e s das ancoragens; n^{0,9}; λ_y e λ_z; V (com k_vol); f_h,0,k.
- Também F_Ed, M_tor, P_Ed, R_Ed, a_p e b_p, q_v, s_t, α_F e α_v.

**9.2 — um significado por símbolo:**
- q: pressão dinâmica → **q_v**; q fica como carga distribuída.
- a, b do atrito → **a_p, b_p**; b é a largura da viga.
- Os a, c dos olhais só aparecem no console (Apêndice D), não no texto.
- h da NBR 6123 e da fórmula de φ do EC5 (5.1) → **H**, a altura dos pilares, que coincide com ela.
- θ das águas (cap. 4 e cap. 6, padrões de vento) → **α**, o mesmo ângulo do extradorso. θ fica só para o eixo da viga. A diagonal da cobertura no Apêndice B passou de θ para **β**, como as demais diagonais.
- α: o ângulo força–fibras passou a **α_F** (f_h,α_F,k), e a incidência do vento a **α_v** (cap. 6 e Apêndice C gerado).
- V_Ed em H_imp = φ·V_Ed → **P_Ed** (carga vertical total de cálculo).
- k_h → **k_ap**, no texto e no esquema ESQ-03 regenerado.
- s: espaçamento entre terças → **s_t**; s fica para os chumbadores.

**9.3 — notação única:**
- Subscrito de cálculo sempre "Ed": M_d, N_d, V_d, q_d e F_d foram trocados no cap. 7, no cap. 8 (§ do garfo) e no Apêndice B gerado (`memorial_equacoes.py`).
- M_cum → **M_ap,d** no Apêndice C gerado (`apendice_analise.py`).
- R_v → **R_Ed** = max(R_A; R_B); R_A e R_B ficam definidos como reações por combinação.
- **w_{\mathrm{net,fin}}** e w_{\mathrm{inst}} na lista e no Apêndice B.
- Os símbolos do console (Apêndice D, saída literal do programa) não foram renomeados.
