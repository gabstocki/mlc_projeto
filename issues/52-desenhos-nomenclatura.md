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
- [ ] Definir esquema de nomenclatura (V, P, PC, T, CV-H, CV-V, TB…) e tabela de elementos.
- [ ] Gerar: planta de cobertura, planta de contraventamento, elevações longitudinal e
      transversal, detalhes L1, L1c, L3, L3c, ancoragem (cotas + escala gráfica).
- [ ] Ferramenta: CAD (exportar PDF) ou geração paramétrica (matplotlib/ezdxf) a partir da geometria do código.
- [ ] Substituir referências genéricas no memorial pelos nomes (“viga V3”, “pilar P5”…).
- [ ] Anexo de desenhos + figuras inseridas nos pontos de discussão.
