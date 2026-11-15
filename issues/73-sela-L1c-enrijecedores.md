# 73 — Sela da L1c: enrijecedores sob os balanços de 125 mm

- **Tema:** Ligações — L1c
- **Prioridade:** P1
- **Normas:** EN 1993-1-8 / EN 1993-1-5 (flexão da chapa em balanço), EC5 §6.1.5 (pressão uniforme admitida)
- **Arquivos:** verificação da sela (t = 16 mm) em `connections/`, `output/desenhos.py`, `tese/cap08.tex` §7.2.2
- **Relaciona:** 78 (soldas), 91 (desenho)
- **Origem:** 4ª revisão, itens 2.5 e 6.6

## O que fazer
- [ ] Incluir enrijecedores sob os balanços de 125 mm da sela, para garantir a pressão de
      contato uniforme admitida na verificação de compressão ⊥.
- [ ] Verificar a chapa da sela + enrijecedores à flexão e as soldas dos enrijecedores.
- [ ] Desenhar os enrijecedores.

## Resolução ✅ (2026-11-07)
**Por quê:** sem enrijecedor, a ponta do balanço de 125 mm (chapa 16 mm) desce 0,55 mm sob a pressão de contato
— da ordem do encurtamento da madeira sob o apoio → pressão não uniforme (contrária à hipótese da Eq. 7.1).

**Solução** (`checks/elu/apoio.verifica_enrijecedores_sela`): 3 enrijecedores triangulares **125 × 125 × 12,5 mm**
S275 sob cada balanço (bordas + eixo da sela), filete duplo a = 4 mm; **chapas laterais de 250 mm** em cada face
do pilar, soldadas à sela e aos enrijecedores.
- chapa entre enrijecedores (vão 146 mm): t_req 8,7 mm → η 0,29;
- consolo F = 23,6 kN, M = 1,48 kN·m: flexão η 0,17; **borda livre c/t = 10 ≤ 14ε = 12,9 → η 0,78 (governa)**
  (10 mm daria 0,97); solda η 0,10;
- binário da raiz: tração pela sela (equilibra o balanço oposto) + compressão C = 26,6 kN contra a face do pilar
  pela chapa lateral, p_max = 0,73 MPa ≤ f_c,90,d (η 0,58);
- flecha da ponta 0,55 → 0,013 mm.
Sela no catálogo: η 0,87 → **0,78** (conjunto enrijecido). η_max 0,90 inalterado. Testes
`tests/test_issue73_sela.py` (4). 777 passed.

**Desenho:** DES-05 com enrijecedores e chapas laterais; cota ℓef da L1 = 330 (beiral). **Tese:** §7.2.2 com o
parágrafo dos enrijecedores.

**Fica para:** soldas sela–chapa embutida e sela–pilar (78); ligação da sela ao pilar — as chapas laterais podem
servir à ligação da issue 69.
