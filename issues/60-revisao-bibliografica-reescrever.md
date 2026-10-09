# 60 — Reescrever a revisão bibliográfica (cap. 3)

- **Tema:** Texto — cap. 3
- **Prioridade:** P1 (reescrita estrutural do capítulo)
- **Arquivos:** `tese/cap03.tex` (§3.1 l. 13; §3.2 Propriedades l. 43; §3.3 Seção variável l. 98; §3.4 Estabilidade l. 122; §3.5 Contraventamento l. 145; §3.6 Ligações l. 164; §3.7 Ações l. 204); `tese/referencias.bib`
- **Relaciona:** issue 41 (o “efeito contraintuitivo” do §3.5 está errado)

## Origem (3ª revisão do orientador (2026-10), p. 17)
- §3.2 já é **metodologia**.
- Reescrever a revisão:
  - **3.1** pode ser mantida, mas incluir **casos de estudo com estruturas semelhantes**;
  - nova **3.2 — baixa adesão ao material no Brasil**;
  - nova **3.3 — abordagem do Eurocódigo e diferenças em relação à norma brasileira**;
  - atuais 3.2–3.4 ou são metodologia ou não agregam à revisão;
  - **mais trabalhos precisam ser citados**.

## O que fazer
- [x] Pesquisa bibliográfica: casos de coberturas/galpões em MLC com vigas duplo-bisel; estudos
      sobre mercado/adesão da madeira engenheirada no Brasil; comparações EC5 × NBR 7190:2022.
- [x] Nova estrutura 3.1 / 3.2 / 3.3; mover conteúdo de cálculo (propriedades, seção variável,
      estabilidade, ligações, ações) para a metodologia ou suprimir.
- [x] Ampliar `referencias.bib` (artigos, dissertações, normas); verificar com `tese/verificar_refs.py`.

## Resolução (2026-10-08) ✅
**Nova estrutura do cap. 3** (agora cap. 2 da tese, após a issue 59):
- 3.1 MLC como produto estrutural (mantida + requisitos de produção da NBR 7190-1 6.7.4) e
  3.1.1 «Coberturas de grande vão: estudos e lições» — Simón-Portela et al. (2023, otimização de
  vigas duplo-bisel GL32h, 15–30 m), Dietsch e Winter (2018, 230 falhas em grandes vãos, >2/3 MLC,
  46% fissuração ao longo das fibras, maioria erro de projeto), Frühwald et al. (2007, 127 casos,
  41% projeto deficiente); ligação explícita com as verificações de t90 e fendilhamento.
- 3.2 «A baixa adesão ao material no Brasil» — Pauli, Azambuja e Oliveira Neto (2021; Esmara 1934,
  estagnação nos anos 1980, ciclo custo × demanda, mão de obra), Leite, Santos e Valle (2017;
  adesivo importado), Zangiácomo (2003; espécies tropicais alternativas).
- 3.3 «A abordagem do Eurocódigo e a norma brasileira» — mudanças de 2022 (Jornada 2024: k_mod3
  eliminado, cisalhamento mais rigoroso), ligações (Baena 2015; Carneiro 2021); e três diferenças
  **conferidas no texto da NBR 7190-1:2022**: (i) 6.7.4 — vigas curvas, de dupla inclinação e
  bumerangue «devem ser analisadas individualmente» (sem regra de borda inclinada/cumeeira);
  (ii) 6.5.6/6.5.7 — LTB dispensável por L1/b; seção não retangular, estudo individual;
  (iii) 6.6 — contraventamento por rigidez mínima K_br e força F_1d × EC5 9.2.5.
- **Correção no §1.1**: a frase «não reproduz as regras de contraventamento» era falsa (a NBR tem
  6.6); substituída pela lacuna real (dupla inclinação → análise individual).

**Conteúdo de cálculo distribuído** (escolha do usuário): X_d, k_mod/k_def (`tab:kmod-kdef`,
`eq:valor-calculo`) → cap04 §Valores de cálculo; seção variável e LTB → início de cap07 §Viga
(label `sec:vigas-secao-variavel` mantido); flexo-compressão de pilares → cap07 §Pilares;
Johansen e modos de ruptura (`tab:modos-ruptura`) → cap08 §Critério das ligações; normas das ações
→ cap06 §Ações. Suprimidos por repetição: 9.2.5/k_ℓ (já no cap05) e α_cr (já no cap06).

**Referências** (9 novas, dados conferidos nas fontes via busca; PDFs de Leite 2017 e Simón-Portela
2023 não abriram, só metadados). Pendente com o autor: conferir as páginas/eventos e, se quiser,
ampliar com casos brasileiros de coberturas em MLC.
