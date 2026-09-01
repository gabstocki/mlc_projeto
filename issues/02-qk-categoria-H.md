# 02 — Sobrecarga qk categoria H (0,25 → 0,4 kN/m²)

- **Tema:** Ações e combinações
- **Prioridade:** P1
- **Normas:** EN 1991-1-1 §6.3.4 / Tab. 6.10 (categoria H — coberturas não acessíveis)
- **Arquivos:** `mlc_projeto/main.py:110`, `mlc_projeto/core/loads.py:322`

## Apontamento do orientador
> Conferir o valor de qk = 0,25 kN/m. Acho que no EN 1990 [EN 1991-1-1] deveria ser,
> para categoria H, 0,4 kN/m².

## Estado atual no código
- `Q_AREA = 0.25` kN/m² em [main.py:110](../mlc_projeto/main.py) (default
  `Carregamentos.q_area = 0.25`, [loads.py:322](../mlc_projeto/core/loads.py)).

## O que precisa ser feito
- [x] Confirmado (EN 1991-1-1 Tab. 6.10, categoria H): **q_k = 0,40 kN/m²**
      (recomendado; faixa 0,0–1,0) e **Q_k = 1,0 kN** concentrado (faixa 0,9–1,5).
- [x] `Q_AREA` ajustado 0,25 → **0,40 kN/m²**, com fonte no código e no memorial (§4).
- [x] Interação com issue [3](03-psi0-categoria-H-vento.md) confirmada: q_k não combina
      com vento (não concomitante), então o aumento afeta só a combinação `ELU_Q` e a
      terça — o global segue governado pelo vento.

## Resolução (implementado)
- **`main.py`**: `Q_AREA = 0.40` (EN 1991-1-1 Tab. 6.10, cat. H); declarado também
  `QK_CONC_KN = 1.0` (concentrado — verificação local, issue 34).
- **`report.py`**: §4 com o valor e a fonte + nota do Q_k concentrado.
- **Testes**: [test_sobrecarga_catH.py](../tests/test_sobrecarga_catH.py).

## Efeito (dados)
Como o vento governa o global (issue 3), o M/V governantes **não mudam** (ELU_C2,
M=−265,5). O aumento de q_k afeta: `ELU_Q` (M −162,8 → −187,5, ainda < wind), a
**terça** (η 0,159 → 0,170) e `ELS_S1`. Tudo passa; status **APROVADO**.

## Follow-up
A carga **concentrada** `Q_k = 1,0 kN` (EN 1991-1-1 Tab. 6.10) exige verificação
**local** (terça/telha), fora do modelo global → issue
[34](34-qk-concentrado-terca-telha.md).

## Fonte
[EN 1991-1-1 Tab. 6.10](https://www.phd.eng.br/wp-content/uploads/2015/12/en.1991.1.1.2002.pdf)
(categoria H: q_k=0,4 kN/m², Q_k=1,0 kN).

## Critério de aceite
q_k = 0,40 kN/m² (EN 1991-1-1 Tab. 6.10, cat. H), com fonte citada **✓**.
