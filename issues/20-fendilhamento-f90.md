# 20 — Fendilhamento — F90,Rd (EC5 §8.1.4)

- **Tema:** Ligações
- **Prioridade:** P1
- **Normas:** EC5 §8.1.4 (Eq. 8.4 / 8.5 — splitting; capacity F90,Rd)
- **Arquivos:** `mlc_projeto/connections/connections.py` (verificação inexistente)

## Apontamento do orientador
> Verificações ausentes para ligações: fendilhamento — F90,Rd (EC5 §8.1.4).

## Estado atual no código
- Nenhuma verificação de fendilhamento (splitting) por componente de força
  **perpendicular às fibras** nas ligações.

## O que precisa ser feito
- [x] Identificar as ligações com componente de força ⊥ às fibras (F_90,Ed) — a
      resultante inclinada em L1/L1c tem componente vertical V_d (⊥ eixo) relevante.
- [x] Implementar a capacidade ao fendilhamento EC5 §8.1.4:
      `F_90,Rk = 14·b·w·√(h_e/(1 − h_e/h))`, com `w=1` (cavilhas) e `h_e` da norma.
- [x] Verificar `F_90,Ed ≤ F_90,Rd` e integrar ao relatório.

## Critério de aceite
Verificação de fendilhamento (F90,Rd) implementada onde houver força perpendicular às
fibras, com η reportado.

---

## ✅ Resolução (implementada)

**Funções novas** em [`connections/connections.py`](../mlc_projeto/connections/connections.py):
`verificar_fendilhamento(...)` (fórmula §8.1.4) + `fendilhamento_ligacao(...)`
(adaptador que lê o layout real da ligação) — espelham a estrutura da ruptura
de bloco (issue 19).

### Fórmula (EN 1995-1-1 §8.1.4)
    F_90,Rk = 14·b·w·√( h_e / (1 − h_e/h) )     (8.4)   [N, mm]
    w = 1 (cavilhas/pinos; só ≠1 em chapa puncionada, Eq. 8.5)
    F_90,Rd = k_mod·F_90,Rk/γ_M,  γ_M = 1,30 (ligação)
    η = F_90,Ed / F_90,Rd,   F_90,Ed = |V_d| (componente ⊥ fibras)

- **Ligações com componente ⊥ fibras:** L1 e L1c (resultante inclinada
  N_d//fibras + V_d⊥fibras). L2/L2c cumeeira: N_c90 é compressão distribuída
  (§6.1.5, já verificada como esmagamento), não força concentrada de grupo → §8.1.4
  não se aplica ali.
- **h_e** (borda carregada → fileira mais distante, grupo centrado em h0):
  `h_e = h0/2 + (n_linhas−1)·a2/2`.

### Resultado (D=24 mm, γ_M=1,30, k_mod=0,70)
- **L1:** F_90,Ed=|V_d|=44,2 kN | h_e=896 mm (h_e/h=0,90) | F_90,Rk=416 kN →
  F_90,Rd=224 kN | **η=0,197** ✓
- **L1c:** F_90,Ed=44,2 kN | h_e=716 mm (h_e/h=0,72) | F_90,Rk=225 kN →
  F_90,Rd=121 kN | **η=0,364** ✓ (menor capacidade: menos fileiras, h_e menor).

Falha FRÁGIL (sem redistribuição) — por isso a verificação é obrigatória sempre
que houver componente ⊥ às fibras, como apontado pelo orientador.

### Integração
- `main.py` Fase 4: `res_elu["fendilhamento_L1"]`/`["fendilhamento_L1c"]`,
  impresso e no resumo.
- `output/report.py`: duas linhas novas no catálogo de exportação (resumo/Excel/§12).
- **Testes:** [`tests/test_fendilhamento.py`](../tests/test_fendilhamento.py)
  (6 casos: fórmula 8.4 fechada, capacidade cresce com h_e, h_e inválido,
  efeito de w, F_90,Ed=|V_d|, L1 real passa com γ_M=1,30).
