# 75 — Ruptura de bloco (EC5 Anexo A) no pé dos pilares e no montante terça–viga; bloco da L1/L1c

- **Tema:** Ligações — modos frágeis
- **Prioridade:** P0 — estimativa preliminar do orientador indica η > 0,75 na L3a
- **Normas:** EN 1995-1-1 Anexo A, §8.5.1.1 (n_ef, Eq. 8.34)
- **Arquivos:** `connections/base_pilar.py` (pé do pilar: L3, L3c, L3f, L3a canto/central), `connections/terca_viga.py` (montante 5×Ø20, η = 0,75), `checks/elu/no_contraventamento.py` (`dimensionar_ligacao_axial_escora` — já tem bloco?), `connections/connections.py` (L1/L1c), `output/memorial_equacoes.py`, `tese/cap08.tex` §7.4.1, Tabelas 25 e 29
- **Origem:** 4ª revisão, itens 2.7, 2.8 e 2.9

## Problema
- O §7.4.1 cita o Anexo A, mas nenhuma taxa de ruptura de bloco é apresentada para o pé dos pilares
  — o caso típico do anexo (tração // às fibras junto à extremidade).
- O montante terça–viga (5 cavilhas // às fibras) está com η = 0,75, exatamente no limite, sem bloco.
- Na L1/L1c (força a ~84° das fibras) o modo pertinente é o fendilhamento; o bloco aparece na Tab. 25 sem dizer para qual componente.

## O que fazer
- [ ] Calcular a ruptura de bloco no pé de L3, L3c, L3f e L3a (canto e central); redimensionar o que passar de 0,75.
- [ ] Idem no montante terça–viga e nas escoras do nó de topo (conferir se já está no código).
- [ ] Apresentar a taxa na Tabela 29 e a demonstração no Apêndice B, junto com n_ef (Eq. 8.34).
- [ ] L1/L1c: retirar o bloco da Tabela 25 ou justificar para qual componente foi calculado.

## Resolução ✅ (2026-11-09)
**Achado (confirma o orientador):** a implementação usava comprimentos BRUTOS (a2, a1, a3,t) e t_1 = b inteira —
não conservadora. Com o Anexo A completo, o bloco reprovava: L3a canto 1,14, L3a central 1,09, L3c 0,98.

**Anexo A completo** (`connections.ruptura_de_bloco(d_m, n_lados, t_ef_m)`, `no_contraventamento.t_ef_bloco_mm`):
- comprimentos líquidos (Fig. A.1): L_net,t = (n⊥ − 1)(a2 − d); L_net,v = 2[(n// − 1)(a1 − d) + a3,t − d/2];
- madeira de CADA lado da chapa central, t_1 = (b − t)/2, bloco nos 2 lados;
- A_net,v (Eq. A.3): L_net,v·t_1 (embutimento) ou L_net,v/2·(L_net,t + 2t_ef) (modos com rótula), adotando o
  menor; modo governante na madeira lateral de 150 mm = duas rótulas → t_ef = 1,4√(M_y/(f_h·d)) = 33,5 mm
  (menor forma do anexo, a favor da segurança — a EN 1995-1-1 não está no projeto para conferir o mapeamento
  modo → t_ef; declarado no texto).
**Correção da malha:** `dimensionar_ligacao_axial_escora` passa a escolher também **a2** (60…180 mm), exigindo
pinos E bloco ≤ 0,75, com D⊥ ≤ 133 mm (retração, 81) e bordas ≥ a4,t (76). Mesmas cavilhas, fileiras afastadas:
L3c a2 = 80 (0,66), L3a canto 120 (0,74), L3a central 110 (0,75); L3 0,57; L3f 0,48. Topo = pé.
Escoras 0,53, montante terça–viga 0,31.
**L1/L1c (2.9):** força a ~84° das fibras → modo pertinente é o fendilhamento; o bloco (componente axial ~9 kN)
saiu do catálogo e da tabela de modos, mantido só como informativo. Catálogo: 68 verificações.

**Apresentação:** nova §7.4.x «Ruptura de bloco no pé e no topo dos pilares» com tabela (a2, L_net,t, L_net,v,
F_bs,Rd, η); tabela das escoras com η bloco 0,53; tabela dos modos frágeis com o bloco dos pilares. **Apêndice B**:
nova equação `eq:mem-pe-bloco` com n_ef (Eq. 8.34), R_d, t_ef, A_net,t, A_net,v, F_bs,Rk (A.1) e η para a base mais
solicitada (L3a central). Testes `tests/test_issue75_bloco.py` (3) + 1 ajustado. 796 passed. η_max 0,90.

**Conferência com a EN 1995-1-1:2004+A1:2008 (adicionada ao projeto, 2026-11-09):** Eq. A.3 — 1.ª forma nos modos
(c, f, j/l, k, m), 2.ª nos demais; Eq. A.7 (chapa grossa) — t_ef = 2√(M_y/(f_h d)) nos modos (e)(h) e
t_1[√(2+4M_y/(f_h d t_1²)) − 1] nos (d)(g). Substituído o 1,4√ (chapa fina, Eq. A.6, conservador) por **2√ →
t_ef = 47,9 mm**, e a 2.ª forma aplicada pelo modo (sem o mínimo). Resultado: L3a canto e central com **a2 = 90**
(η 0,74 / 0,71); demais inalterados. Com fileiras a 60 mm o canto daria 0,84. PDF no .gitignore.
