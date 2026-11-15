# 87 — Pilarete metálico em todas as bases (afastar a madeira da zona de respingo)

- **Tema:** Durabilidade + Base — novo elemento estrutural
- **Prioridade:** P0 (muda a cadeia da base, o impacto e os desenhos)
- **Normas:** EN 1993-1-1 (compressão, tração, flexão, flambagem), EN 1993-1-8 (soldas, chapa de topo), EN 1992-4 (ancoragem)
- **Arquivos:** `connections/base_pilar.py`, `checks/elu/` (pilares: altura livre H − h_pilarete → k_c), impacto de veículo, `output/desenhos.py` (DES-06, DES-07, DES-08), `tese/cap08.tex` §7.4 e §7.8 (substituir o “pedestal de concreto”)
- **Relaciona:** 74, 76, 80, 81, 91
- **Origem:** 4ª revisão, itens 4.7 e 6.6

## Problema
O pé do pilar apoia-se na chapa de base, no nível do bloco; a chapa, maior que a seção, forma uma
bandeja que retém água junto ao topo da madeira. O “pedestal de concreto” do §7.8 não aparece nos desenhos.

## O que fazer
- [ ] Conceber o pilarete: barra cilíndrica maciça ou tubo, chapa de topo ≤ seção do pilar (sem
      bandeja), altura justificada (~300 mm acima do piso acabado — citar prática/fonte).
- [ ] Verificar à compressão (até 293 kN), tração (até 284 kN), flexão pelo cortante na base
      (impacto: M = V·h ≈ 14 kN·m com 0,30 m) e flambagem; notar que com h ≥ 0,50 m ele recebe o
      choque diretamente.
- [ ] Manter a ligação das diagonais de contraventamento na chapa de base, abaixo do pilarete, para
      que o cortante dos painéis vá à chaveta sem fletir o pilarete.
- [ ] Revisar: altura livre do pilar H − h_pilarete (k_c), posição do impacto sobre a madeira, ligação pé do pilar ↔ chapa de topo do pilarete.
- [ ] Atualizar §7.8 e DES-06/07/08; cotar níveis: piso acabado, topo do pilarete, topo do bloco.

## Resolução ✅ (2026-11-07)
**Concepção:** pilarete de **tubo circular S355 Ø139,7 × 8** em todas as bases, h = **0,30 m** (topo da
chapa de topo acima do piso acabado = topo do bloco). Chapa de topo recuada 10 mm de cada face do pilar
(sem bandeja). Cadeia: cavilhas → chapa vertical → chapa de topo → tubo → chapa de base → chumbadores →
concreto. Diagonais CV continuam na chapa de base (cortante dos painéis → chaveta, sem fletir o pilarete).
Seção circular: choque de qualquer direção. Madeira: **H_m = 7,00 − 0,30 = 6,70 m** (k_c, vento, impacto,
fogo, pilar de frontão); painéis, estabilidade global e sucção seguem com 7,00 m.

**Código:** `connections/pilarete.py` (novo: `verificar_pilarete` — classe, N_c com χ (l_cr = 2h, curva a),
N_t, V, M_N,Rd = M_pl(1 − n^1,7), chapa de topo como faixa biengastada σ = 0,75·N_t/t², soldas tubo–chapas
§4.5.3.3; `tracao_equivalente_momento`); `base_pilar.py`: `tstub_base_tubo` (cada chumbador um T-stub,
padrões de canto Tab. 6.4), compressão em coroa sob o tubo, t_base ≥ max(12,5; a/0,7), folga arruela–tubo;
`ancoragem.verificar_base_corrente(M_persistente, M_acidental)` e L3f: binário M = V·h somado à tração.
`main.py`: `H_PILARETE_M`, `H_PILAR_MAD`, `H_IMP_PISO_M`; impacto a 0,20 m do pé da madeira.

**Resultados:** V do choque 46,4 → 48,5 kN; M = 14,6 kN·m. Tubo η ≤ 0,34 (barra); governam a chapa de topo
(19–31,5 mm) e a solda tubo–base (a = 6–10 mm) com η 0,74–0,90 (alvo dúctil 0,90). Chapas de base 12,5 (2×2)
e 16 mm (2×3). Ancoragem L3/L3c no choque: N_eq 72,8 kN → η 0,43. Pilar central montante 0,81 → 0,74
(H_m menor). **η_max 0,89 → 0,90** (chapa de topo do pilarete L3a). 66 verificações (o pilarete entra nas 5
bases). Testes: `tests/test_issue87_pilarete.py` (5) + 2 ajustados. 769 passed.

**Desenhos:** DES-06 e DES-07 com tubo, chapa de topo, níveis (±0,00 piso = topo do bloco; +0,30 topo do
pilarete) e nota das diagonais abaixo do pilarete. **Tese:** §7.4.x reescrita (cadeia, pilarete, tabela nova,
sem narrativa de correção), Eq. do cortante do choque com H_m, §7.8 sem “pedestal de concreto”, §3.1.

**Fica para:** soldas detalhadas e chaveta (78); plano da chapa vertical × direção do choque (76, já com
o tubo circular isotrópico); folga do furo da chapa de base (80); L3a canto sob choque não verificada à
parte (persistente 327 kN ≫ binário acidental ≈ 73 kN equivalente) — declarar no texto (76).
