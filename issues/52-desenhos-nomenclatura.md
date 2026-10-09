# 52 — Desenhos cotados e em escala + nomenclatura dos elementos (V1, P1, …)

- **Tema:** Desenhos / Memorial
- **Prioridade:** P1 (pedido explícito; hoje faltam desenhos)
- **Arquivos:** `tese/fig/`; `mlc_projeto/visualization/` (viz_3d, VTK); `tese/cap04.tex`, `cap07.tex`, `cap08.tex`; anexos
- **Relaciona:** issues 42 (L1c), 43 (espaçamentos), 48 (L3)

## Origem (3ª revisão do orientador (2026-10))
Faltam: **planta de cobertura e de contraventamento; elevações; detalhes das ligações L1, L1c,
L3 e da ancoragem**. Podem ser isométricos, mas **todos com cotas e escalas**. Os elementos
(vigas, pilares, contraventamentos, terças…) precisam ter **nomes nos desenhos** (V1, V2…,
P1, P2…) e os **mesmos nomes no memorial**. Os desenhos devem constar **em anexo** e também
**como figuras no texto**, onde são discutidos.

## O que fazer
- [x] Definir esquema de nomenclatura (V, P, PC, T, CV-H, CV-V, TB…) e tabela de elementos.
- [x] Gerar: planta de cobertura, planta de contraventamento, elevações longitudinal e
      transversal, detalhes L1, L1c, L3, L3c, ancoragem (cotas + escala gráfica).
- [x] Ferramenta: CAD (exportar PDF) ou geração paramétrica (matplotlib/ezdxf) a partir da geometria do código.
- [x] Substituir referências genéricas no memorial pelos nomes (“viga V3”, “pilar P5”…).
- [x] Anexo de desenhos + figuras inseridas nos pontos de discussão.

## Resolução (2026-10-08) ✅
**Nomenclatura** (cap. 4, `tab:nomenclatura`): eixos 1–9 × A, B, C; V1–V18 (V(2i−1) vão A–B,
V(2i) B–C); P1–P27 (P(3i−2) A, P(3i−1) B, P(3i) C; cantos P1/P3/P25/P27; B montantes
P2/P5/P8/P20/P23/P26); PF1/PF2; T1–T17 (T1/T9/T17 sobre apoios); CV-H1/2, CV-V1–8, CV-T1/2;
L1, L1c, L1f, L3, L3c, L3f, L3a.

**Desenhos** — `mlc_projeto/output/desenhos.py` (matplotlib), gerados pelo pipeline em
`tese/fig/des0*.pdf`, largura = `\textwidth` (455 pt) → escala verdadeira no papel, escala
gráfica em todas: DES-01 planta de cobertura 1:400; DES-02 planta de contraventamento 1:400;
DES-03 elevações A e B 1:400; DES-04 pórtico do frontão 1:300; DES-05 L1/L1c 1:20; DES-06
bases L3/L3c/L3f 1:15; DES-07 base L3a + bloco 1:25; DES-08 topo do PF (L1f) 1:10.
Apêndice E com as 8 folhas + figuras nos caps. 4, 5 e 8.

**O desenho expôs três falhas de projeto, corrigidas (escolhas do usuário):**
1. *Painel do frontão sem montante* — CV-T dimensionado com baía de 5,75 m, mas no frontão os
   pilares estão a 20,25 m. → **Pilar de frontão PF1/PF2** (`checks/elu/pilar_frontao.py`),
   0,32×0,27, a 5,75 m do canto (P1–PF1 no eixo 1, PF2–P27 no eixo 9). Não apoia a viga:
   topo L1f com 3×Ø20 em furos oblongos (curso ±20 > flecha 12,1 mm no ponto; a2 = 90 na chapa).
   Montante η 0,212; L1f 0,683; L3f 0,483. Arrasto dos 2 PF incluído (`n_pilares_extra`):
   **η_max 0,8352 → 0,8452, agora CV-T** (CV-V 0,8396); diâmetros inalterados.
2. *Chapa de base 400×400 com chumbadores a 400* (cone EN 1992-4) — chumbadores na face do
   pilar. → `connections/base_pilar.py`: chapa = grelha + 2·60 (520×520; L3a 520×920).
3. *Sem verificação da chapa sob tração nem do pé do pilar* → T-stub EN 1993-1-8 §6.2.4
   (alvo 0,90) + compressão por área efetiva §6.2.5 + cavilhas Ø20 no pé (EC5 §8, alvo 0,75).
   L3 η 0,840 (t=8); L3c 0,663 (12,5); L3f 0,721; L3a canto 0,749 / central 0,745 (12,5).
Também: esquadro L1/L1c com a geometria desenhada (270×964); constantes declaradas
T_CHAPA_TOPO_MM=16, FOLGA_OBLONGO_L1_MM=10. Tese: ~40 números atualizados, custo +1,2 m³
(R$ 2.790.943), 63 verificações, 714 testes. Pendente fora do escopo: força de coletor nas
L1/L1c do frontão (sessão sugerida).
