# 77 — Terça–viga: contenção à torção (apoio em garfo) e grandezas da Tabela 34

- **Tema:** Ligações — terça–viga
- **Prioridade:** P1
- **Normas:** EC5 §6.3.3 (apoio em garfo para l_ef da flambagem lateral), Tab. 8.6 (a1 = 7d = 56 mm; a2 = 5d = 40 mm)
- **Arquivos:** `connections/terca_viga.py`, `output/quadro_espacamentos.py` (linha “passo vertical (a2 terça, a1 viga)”), `tese/cap08.tex` §7.3, Tabela 34
- **Origem:** 4ª revisão, itens 2.11 e 3.4

## O que fazer
- [ ] Justificar (e se necessário detalhar) a contenção à torção da terça 200 × 580 mm sobre apenas
      160 mm de apoio (meia largura da viga) — hipótese de garfo da verificação de flambagem lateral
      da terça. Opções: momento de torção resistido pelos parafusos cruzados, cantoneira/bloqueio lateral.
- [ ] Corrigir a identificação das grandezas na Tabela 34 (a1/a2 trocados para parafusos axiais).

## Resolução ✅ (2026-11-07)
**Garfo** (`connections/terca_viga.verificar_garfo_terca`): terça 0,20 × 0,40 sobre meia largura da viga (160 mm).
Gravidade: banzo superior contido pela telha. Sucção: banzo inferior livre — l_ef = 0,9·L_T = 5,18 m (Tab. 6.1),
λ_rel,m = 0,41, **k_crit = 1** (flexão sob sucção η 0,31). Contenção exigida pelo EC5 §9.2.5.2: F_d = N_d/k_f,2,
N_d = (1 − k_crit)·M_d/h; limite superior k_crit = 0 → **M_tor = M_d/80 = 0,27 kN·m** (M_d sucção 21,7). Resistida
pelos parafusos da face oposta (tombamento sobre a aresta inferior, braço b_t, 45°): **ΔF = 0,48 kN/parafuso**,
incluído no laço de dimensionamento (interação Eq. 8.28). Para caber nos 4 parafusos/face que a altura de 400 mm
permite: **l_ef 120 → 160 mm** (parafuso ≈ 340 mm). Corrente: 8 × Ø8, η 0,49 (η_ax 0,70).

**Tab. 34 (quadro de espaçamentos):** a linha única “passo vertical (a2 terça, a1 viga)” com exigido 56 virou duas:
terça **a2 = 5d = 40** (adot. 56) e viga **a1 = 7d = 56** (adot. 56) — EC5 Tab. 8.6.

η_max 0,90 inalterado. Testes `tests/test_issue77_garfo.py` (3). 787 passed. Tese: §7.3 com o parágrafo do garfo e
números atuais (arrancamento 15,1; diafragma 4,1; montante 102,5 kN, 8 Ø20, η 0,70; corrente η 0,49).
