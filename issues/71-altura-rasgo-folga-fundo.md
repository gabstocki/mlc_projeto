# 71 — Altura do rasgo: madeira remanescente sobre a chapa e folga no fundo do rasgo

- **Tema:** Viga — integridade da extremidade / caminho da gravidade
- **Prioridade:** P1
- **Normas:** EC5 §6.1.7 (cisalhamento), §6.5 (entalhes, por analogia), §8.1.4
- **Arquivos:** `mlc_projeto/main.py` (altura do esquadro L1/L1c = h0·1000 − 3d + folga + 1,5d = 974 mm), `connections/connections.py`, `output/desenhos.py` (DES-05), `tese/cap08.tex` §7.2 e §7.7
- **Relaciona:** 70, 72, 79, 90
- **Origem:** 4ª revisão, itens 2.3, 6.3 e 10.8

## Problema
Com a chapa de 974 mm numa viga de h0 = 1000 mm, restam ~14 mm de madeira entre o topo do rasgo
e o extradorso na posição dos pinos: a extremidade da viga fica, na prática, dividida em duas
lâminas. Se a chapa tocar o fundo do rasgo, a gravidade passa pela ponta da chapa, e não pelo
contato com a chapa de topo.

## O que fazer
- [ ] Cotar a folga no fundo do rasgo e garantir que a chapa nunca encoste nele (incluir retração/fluência).
- [ ] Avaliar o efeito das duas lâminas sobre o cisalhamento e a integridade da extremidade;
      considerar reduzir a altura da chapa (subir pinos menos / menos pinos / pinos mais próximos)
      mantendo h_e/h alto para o fendilhamento e e4 ≥ 1,5 d0 (issue 79).
- [ ] **Conferir com o orientador:** ele afirma (6.3 e 10.8) que 974 mm é “anterior à correção do
      §7.7”; no código 974 mm **já é** o valor corrigido (e4 26 → 36 mm). Responder com a
      geometria final; se a altura mudar aqui, regenerar DES-05 e o Apêndice D na mesma execução.

## Resolução ✅ (2026-11-07)
**Achado:** com o grupo de pinos a 3d do topo, chapa (987) + folga no fundo do rasgo (15) = 1.002 mm >
h0 = 1.000 — o rasgo atravessaria a viga. O fundo do rasgo precisa de folga sobre o topo da chapa igual
ao curso inferior (retração + fluência à altura do topo da chapa); senão a gravidade passa pela ponta da chapa.

**Solução** (`connections/oblongo_L1.geometria_rasgo`): o grupo sobe o mais possível sujeito a
fundo do rasgo = y_topo + c_cima + 1,5·d0 + folga_fundo ≤ h0 − 100 mm (madeira inteira, 2,5 lamelas) e
a4,c ≥ 3d. Resultado: pino mais alto a **818 mm** do apoio (182 mm do extradorso); chapa **877 mm**; folga no
fundo **15 mm**; fundo do rasgo **892 mm**; **108 mm** de madeira inteira acima. O fendilhamento lê a posição
(`a4c_topo_mm`): h_e 928 → 818, F_90,Rd 254 → 150 kN, **η 0,40 → 0,67** (< 0,75). Curso do oblongo
recalculado (15 abaixo / 20 acima, η 0,72 com adoção ≤ 0,90); levantamento 8–12 mm.

**Integridade:** rasgo 29 × 270 × 892 mm separa duas lâminas de 146 mm; com o beiral (82) o rasgo não está
na extremidade — lâminas ligadas pela seção inteira acima e pela viga contínua dos dois lados.
Cisalhamento com b − t_rasgo → **issue 70** (próxima).

**Resposta ao orientador (6.3/10.8):** 974 mm era o valor pós-§7.7; com d0 (79), curso (72) e rasgo (71) a
chapa passou a 877 mm — DES-05 e Apêndice D regenerados pelo pipeline.

Desenho DES-05: fundo do rasgo pontilhado + cotas (folga, madeira acima). Tese: nova §7.2.x «Altura do
rasgo»; Eq. do fendilhamento com h_e = 818; curso e §7.7 atualizados. Testes: 1 novo + 2 ajustados. 773 passed.
