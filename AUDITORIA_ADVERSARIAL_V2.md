# AUDITORIA ADVERSARIAL INDEPENDENTE — v2

**Objeto:** `mlc_projeto` — verificação estrutural de galpão em MLC (EC5 + EN 1990 + NBR 6123)
**Commit auditado:** `1df424c` (branch `main`, árvore limpa no início da auditoria)
**Ambiente de execução:** Python 3.12 · NumPy 2.4.6 · SciPy 1.17.1 · pandas 3.0.3 (`.venv/`)
**Pipeline executado:** `python -m mlc_projeto.main --sem-viz` → EXIT 0 · η_max = 0,8930 · Status = APROVADO
**Suíte:** `pytest -q` → **350 passed, 1 failed**

> **ESTADO (após F-01, F-02, F-04, F-03, F-05 e F-13).** Os **quatro achados
> ALTA NON-CONSERVATIVE** — F-01, F-02, F-04 e F-03 — e o MÉDIA **F-05** foram
> **CORRIGIDOS**. **F-13 está ENCERRADO**: a cláusula foi obtida e **confirma
> 0,50** — a hipótese de 0,05 levantada por esta auditoria estava **ERRADA**
> (ver **Seção Z.12**, retificação). Permanece **F-14** e os restantes MÉDIA/LOW
> das Seções V e X. Ver
> **Seção Z**. Permanecem em aberto **F-13** (atrito de θ=0°, conservador mas
> 10,1× o limite físico e sem fonte normativa confirmada), **F-14** (modo de
> Johansen de outra configuração — agora a distorção binding na L1) e os
> restantes achados MÉDIA/LOW das Seções V e X. O corpo do relatório abaixo é o
> registo do que foi **encontrado**, preservado sem alteração.

> **Regra de evidência adotada.** Nenhuma linha marcada `VALIDATED` foi emitida sem
> (a) código citado com `arquivo:linha`, (b) cláusula/equação normativa, (c) benchmark
> numérico **executado por código novo que não importa nenhuma função do repositório**
> para o cálculo de referência. Onde a fonte normativa não pôde ser confirmada no
> material fornecido, o status é `NOT VERIFIABLE — REQUIRES EXTERNAL NORMATIVE SOURCE`.
> Os scripts de benchmark estão listados na Seção Q.

---

## A — EXECUTIVE SUMMARY

O núcleo de resistência dos materiais e de aplicação do EC5 **reproduz-se exatamente**:
14 de 14 grandezas reconstruídas fora do repositório bateram com o software com erro
relativo ≤ 0,05 % (Seção Q). O peso próprio, as combinações da EN 1990, o diagrama de
momentos, o cisalhamento §6.1.7, a mísula §6.4.2, o ápice §6.4.3, a flambagem lateral
§6.3.3, o apoio §6.1.5 e as flechas de Timoshenko estão **corretos**.

O problema não está nas equações. Está em **três camadas em volta delas**:

1. **A ação que dimensiona toda a estrutura metálica é fisicamente impossível.**
   O atrito longitudinal `Ft = 0,5·q·a·b` (§7.2.2, wind.py:496) devolve 776,8 kN —
   **10,1× o arrasto que a cobertura teria se fosse um corpo sólido totalmente
   bloqueante**, e 12× o maior coeficiente de fricção do EN 1991-1-4 (Tab. 7.10).
   Esses 837 kN são a única razão de existirem 4 painéis de contraventamento, diagonal
   Ø45, pilar de canto engrossado e 6 chumbadores. **[F-13]**

2. **Uma ação real de mesma ordem está omitida, e essa é não conservadora.**
   A componente **horizontal** da pressão de vento na cobertura (θ=90°) nunca é
   calculada. Reconstruída de forma independente, vale **57,8 kN de cálculo contra os
   38,3 kN que o software considera — 1,51× o termo incluído** (Seção Q, BM-12). A
   demanda do contraventamento transversal está subestimada em ~2,2×. **[F-01]**

3. **O portão de estabilidade global não mede estabilidade global.**
   O `α_cr = 2817` reportado é a carga de Euler de uma barra cujo denominador é o
   axial da viga (8,75 kN), que o próprio modelo adotado (Opção B, H=0) força a ~zero:
   **quanto menos empuxo, maior o "α_cr"**. Um α_cr de sistema reconstruído a partir da
   rigidez real das cruzes dá **7,33 na direção transversal — abaixo do limiar 10** que o
   próprio projeto declara, exigindo 2.ª ordem (k_II = 1,158). **[F-02]**

Somando [F-01] e [F-02], o contraventamento transversal (η reportado 0,807) passa de
1,0. **O veredito `APROVADO` não se sustenta.**

Acrescem, na ligação L1 (modo frágil, alvo de projeto η ≤ 0,75): a resistência ao
embutimento nunca é reduzida pelo ângulo força-fibras (α = 85°, −41,3 % em `f_h`), e a
distância de borda carregada `a4,t` omite o termo `(2+2 sen α)d` (72 mm contra 95,8 mm
exigidos). Corrigido o embutimento pela Eq. 8.11 correta e por `f_h,α,k`, **η_L1 = 0,798
contra 0,748 reportado — acima do alvo de 0,75 do próprio projeto**. **[F-03, F-05]**

Por fim, a agregação do veredito devolve **η = 0,0 e `ok = True` para um resultado
vazio, `None` ou uma string**, e uma verificação cujo dicionário não traga a chave
`eta` **desaparece silenciosamente** do resumo, do `all_ok`, do Excel e do memorial.
**[F-04]**

**Veredito: `NOT VALIDATED`** (Seção W).

---

## B — ARQUITETURA DO REPOSITÓRIO (inventário 100 %)

159 arquivos versionados. Os 39 de `issues/` e os 4 `.vtk` de `output/vtk/` estão
cobertos em bloco ao fim da tabela (rastreabilidade documental / saída gráfica, sem
lógica de cálculo). Todos os demais estão individualizados.

| Arquivo | Função | Entradas | Saídas | Dependências | Criticidade |
|---|---|---|---|---|---|
| `pyproject.toml` | metadados/ambiente declarado | — | build, deps | setuptools | **ALTA** (F-19) |
| `README.md` | descrição do projeto | — | texto | — | BAIXA (vão declarado 40,5 m ≠ 20,25 m de `main`) |
| `.cursorrules` | convenções (SI, dict+η, docstring normativa) | — | texto | — | MÉDIA (contrato de unidades) |
| `.gitignore` | exclusões | — | — | — | NULA |
| `AUDITORIA_TECNICA_INDEPENDENTE.md` | auditoria anterior (AUD-001…021) | — | texto | — | **ALTA** — única fonte de F-13 |
| `mlc_projeto/main.py` | orquestrador, dados de projeto | constantes | `resultados` | tudo | **CRÍTICA** |
| `core/normativo.py` | declaração `EUROCODE_BASE`/`NATIONAL_ANNEX`/NDP | — | `NDP_SOURCE` | — | **CRÍTICA** |
| `core/validacao.py` | pré-condições de domínio (AUD-013) | escalares | float/raise | — | **ALTA** |
| `core/geometry.py` | h(x), A(x), I(x), W(x) duplo-bisel | L,h0,α,b | arrays | validacao, numpy | **CRÍTICA** |
| `core/materials.py` | EN 14080 Tab. 5, k_mod, k_def, γM, k_cr | classe, CS, duração | f_d | — | **CRÍTICA** |
| `core/wind.py` | NBR 6123: S2, q, Tab. 10, Tab. 25, θ=0° | `ParametrosVento` | `ResultadoVento` | validacao | **CRÍTICA** |
| `core/loads.py` | g_k, combinações EN 1990, análise biarticulada | geo, mat, vento | `Combinacao` | geometry, materials, scipy | **CRÍTICA** |
| `predim/predim.py` | varredura paramétrica (h0, α, b) | ranges | DataFrame | checks | MÉDIA (fora do caminho principal) |
| `checks/elu/cumeeira.py` | §6.4.3 ápice (t90 + flexão) | geo, mat, load | η | loads | **CRÍTICA** |
| `checks/elu/misula.py` | §6.4.2 borda inclinada | idem | η | loads | **CRÍTICA** |
| `checks/elu/flexao.py` | §6.3.2 Eq. 6.23/6.24 + §6.3.3 Eq. 6.35 | idem, s | η | flambagem_lateral | **CRÍTICA** |
| `checks/elu/flambagem_lateral.py` | §6.3.3 σ_m,crit, λ_rel,m, k_crit | idem, l_1 | η | loads | **CRÍTICA** |
| `checks/elu/cisalhamento.py` | §6.1.7 Eq. 6.13 (+k_cr), §6.5.2 k_v | idem | η | loads, pandas | **CRÍTICA** |
| `checks/elu/apoio.py` | §6.1.5 + §6.2.2 Hankinson | idem, l_ap | η | loads | **ALTA** |
| `checks/elu/flexo_compressao.py` | pilar §6.3.2 | N, seção | η | materials | **ALTA** |
| `checks/elu/pilares.py` | pilar lateral/central/canto, vento θ=0/90 | load, seções | η | loads, wind | **ALTA** |
| `checks/elu/tercas.py` | terça flexão, biela, Q_k concentrado | geo, mat | η | loads | MÉDIA |
| `checks/elu/contraventamento.py` | §9.2.5.2/.3 cobertura + cruzes | load, layout | η, `l_1_efetivo_m` | loads | **ALTA** |
| `checks/elu/contraventamento_vertical.py` | painel de cruz, nocional §5.3.2 | F_vento0 | η | loads | **ALTA** |
| `checks/elu/contraventamento_transversal.py` | diafragma + frontões | load, vento | η | cv_vertical, wind | **CRÍTICA** (F-01) |
| `checks/elu/corda_beiral.py` | corda do diafragma §6.2.3/§6.3.2 | N_corda | η | materials | MÉDIA |
| `checks/elu/estabilidade_global.py` | α_cr, nocionais, P-Δ | load, seções | η, `1a_ordem` | deflection_els | **CRÍTICA** (F-02) |
| `checks/elu/empuxo_acoplado.py` | auditoria k_arco vs k_pilar (issue 38) | geo, load | tabela | loads | MÉDIA (auditoria) |
| `checks/elu/tirante_base.py` | tirante de fecho do empuxo | H | η | loads | **INATIVO** (Opção B) |
| `checks/elu/tirante_piso_robustez.py` | robustez do tirante no piso | — | η | — | **INATIVO** (Opção B) |
| `checks/elu/succao_uplift.py` | uplift/ancoragem ELU_C3 | load | η | loads | **ALTA** |
| `checks/elu/fixacao_telha.py` | sucção local NBR 6123 no fixador | q, c_p | η | wind | MÉDIA |
| `checks/elu/icamento.py` | montagem EN 1991-1-6 + LTB | geo, mat | η | flambagem_lateral | MÉDIA |
| `checks/elu/impacto_veiculo.py` | ação acidental EN 1991-1-7 | seções | η | materials | MÉDIA |
| `checks/els/deflection_els.py` | flecha flexão+cisalhamento, §2.3.2.2, Tab. 7.2 | geo, mat, load | η | loads, scipy | **CRÍTICA** |
| `checks/els/creep.py` | fluência / abertura dos springings | idem | η | deflection_els | **ALTA** |
| `connections/connections.py` | Johansen, n_ef, distâncias, bloco, fendilhamento | load, d | η | materials, loads | **CRÍTICA** (F-03, F-05) |
| `connections/chapas_aco.py` | chapa/furos/solda EN 1993-1-8 | load | η | loads | **ALTA** |
| `connections/chapas_dim.py` | dimensões e espessura das chapas | load | mm | loads | MÉDIA |
| `connections/ancoragem.py` | chumbadores moldados EN 1992-4 | N,V, geometria | η | — | **ALTA** |
| `connections/fadiga_ligacoes.py` | K_ser, deslizamento, alternância | load | η | connections | MÉDIA |
| `output/report.py` | tabela única terminal/Excel/LaTeX/PDF | `resultados` | .xlsx/.tex/.pdf | tudo | **CRÍTICA** (F-04) |
| `output/cargas_fundacao.py` | esforços por base para terceiros | resultados | tabela | loads | **ALTA** |
| `output/figuras.py` | diagrama M/V/N em PDF | load | figura | matplotlib | BAIXA |
| `opensees/opensees_model.py` | modelo FEM de validação | geo, load | reações | (opcional) | MÉDIA (validação cruzada) |
| `opensees/opensees_vtk.py` | export VTK | modelo | .vtk | — | BAIXA |
| `visualization/viz_3d.py` | visualização 3D | geo | janela | matplotlib | NULA |
| `output/varredura_*.csv/.md` (6) | resultados da varredura de pré-dim. | — | dados | — | MÉDIA (rastreio da escolha R2) |
| `output/pipeline_console.txt` | export do terminal | — | texto | — | **MÉDIA** — estava obsoleto (F-22) |
| `output/*.png` (2), `output/relatorio_mlc.out`, `output/.gitkeep` | figuras/placeholders | — | — | — | NULA |
| `output/vtk/*.vtk` (4) | malhas de pós-processamento | — | — | — | NULA |
| `tests/` (49 arquivos, 4 511 linhas) | regressão | — | pass/fail | pytest | **ALTA** — ver Seção R |
| `issues/*.md` (39) | backlog e decisões de projeto | — | texto | — | MÉDIA (rastreabilidade das decisões) |

**Fluxo de dados real** (reconstruído do código, não da documentação):

```
main.GEO_PARAMS/VENTO_PARAMS
   → peso_proprio_gk ─────────────────────────► g_k [kN/m²]
   → wind.calcular_vento
        ├ rota_normativa: obstruções OU n_tramos>1 OU h<0,5ℓ2 → "edificacao_fechada"
        └ Tab. 10 (c_pe) − c_pi(+0,8/−0,3) ────► 8 padrões c_net
   → Carregamentos._montar_combinacoes  (17 ELU + 3 ELS + 4 ALIASES C1..C4)
        └ analisar_biarticulada(desenvolve_empuxo=False) → H=0, M=M0
   → combinacao_ELU_governante() = max|M_max| entre q_tot>0   ◄── ESTREITAMENTO [F-06]
   → mat_elu = mat_curta.com_duracao(gov.duracao)             ◄── material ÚNICO
   → 15 módulos de verificação (13 leem só a governante)
   → report.tabela_verificacoes → all_ok, eta_max → "APROVADO" ◄── [F-04]
```

**Caminhos alternativos / código morto perigoso identificados:**
- `wind.padroes_cpe_tabela25` e todo o ramo `rota == "tabela25"` continuam ativos e
  alcançáveis (basta `obstrucoes_sob_cobertura=False`, `n_tramos=1`, `h ≥ 0,5·ℓ2`).
  É nessa rota que [F-06] deixa de ser latente e passa a subestimar 4,2 % (Seção Q).
- `analisar_biarticulada` é **função pública de módulo**, chamada diretamente por
  `misula.py:101`, `flexao.py:83`, `deflection_els.py:146`, `creep.py` e testes,
  **contornando** as pré-condições de `GeometriaViga.__post_init__` → [F-09].
- `tirante_base.py` e `tirante_piso_robustez.py` estão desligados por
  `TIRANTE_BASE = EMPUXO_DESENVOLVE = False`; suas chaves somem do resumo pelo
  mecanismo de [F-04] (aqui, legitimamente — mas sem registo explícito de "não aplicável").
- `wind.forca_vento_pilar_90` produz `M_mid` de pilar biapoiado que **não** é somado à
  flexo-compressão do pilar em `flexo_comp`; entra apenas em `pilar_vento_90` e na
  demanda transversal.

---

## C — ARQUITETURA NORMATIVA

Hierarquia declarada em `core/normativo.py:60-69` e respeitada no código:

| Domínio | Norma aplicada | Evidência |
|---|---|---|
| Vento (V0, S1, S2, S3, q, c_pe, c_pi, atrito) | **ABNT NBR 6123:2023** | `wind.py` inteiro; `normativo.py:69,132` |
| Segurança / combinações (γ, ψ, ELU/ELS) | **EN 1990** | `loads.py:58-79`; `normativo.py:79-99` |
| Ações não-vento (peso próprio, sobrecarga cat. H) | **EN 1991-1-1** | `loads.py:88-114`; `main.py:171` |
| Ações de execução (içamento) | **EN 1991-1-6** | `icamento.py`; `main.py:203` |
| Ação acidental (impacto) | **EN 1991-1-7** | `impacto_veiculo.py` |
| Madeira / MLC | **EN 1995-1-1:2004/A1:2008** | todos os `checks/` |
| Propriedades do glulam | **EN 14080:2013 Tab. 5** | `materials.py:21-63` |
| Aço (diagonais, chapas, chumbadores) | **EN 1993-1-1 / 1-8** | `contraventamento_vertical.py`, `chapas_aco.py` |
| Ancoragem no concreto | **EN 1992-4:2018** | `ancoragem.py` |
| Concreto sob a chapa | **EN 1992-1-1** | `normativo.py:122-129` |

**Não há substituição de coeficiente da NBR 6123 por EN 1991-1-4** em nenhum ponto do
código. O EN 1991-1-4 é usado **por esta auditoria** apenas como *sanity check*
comparativo do coeficiente de atrito (Seção Q, BM-11) — uso permitido pela §1.1 do
mandato.

**Tensão de premissa não declarada [F-24, INFO].** Para θ=90° o modelo adota a rota
de *edificação fechada* de §7.2.1 (com c_pi = ±); para θ=0° adota a rota de *cobertura
isolada* (§7.2.2, atrito). A mesma estrutura é, portanto, "fechada" numa direção e
"isolada" na outra. A leitura literal de §7.2.1 ("**esta** [a cobertura] deve resistir…
na zona de obstrução") sustenta aplicar a rota fechada só à cobertura, mas o projeto
não declara essa coerência em lado nenhum. `CONFIRMED` como omissão documental.

---

## D — CONTROLE DE VERSÃO NORMATIVA

| Norma | Versão pretendida (declarada) | Versão aparentemente implementada | Evidência | Status |
|---|---|---|---|---|
| EN 1990 | `:2002` (`normativo.py:60`) | Tab. A1.1/A1.2(A)/A1.2(B) coerentes com :2002 | `loads.py:58-79` | `MATCH` |
| EN 1991-1-1 | `:2002` (`normativo.py:60`) | §3.3.2(1), Tab. 6.10 cat. H | `main.py:167-172` | `MATCH` |
| EN 1995-1-1 | `:2004/A1:2008` (`normativo.py:60`) | k_cr=0,67 é do A1:2008; k_mod/k_def de :2004 | `materials.py:88-91`, `normativo.py:105` | `MATCH` |
| EN 14080 | `:2013` (`materials.py:5`) | Tab. 5 homogéneo; comentário registra a migração desde EN 1194:1999 | `materials.py:27-63` | `MATCH` |
| EN 1993-1-1 | não declarada | §5.3.2 (φ0=1/200, αh, αm), §6.2.3 (N_pl,Rd) | `contraventamento_vertical.py:104-131` | `NOT DECLARED` |
| EN 1993-1-8 | não declarada | pino/bearing/seção líquida/solda | `chapas_aco.py` | `NOT DECLARED` |
| EN 1992-4 | `:2018` (`main.py:313`) | §7.2.1.4/.5, §7.4.1.4, §7.2.3 | `ancoragem.py` | `MATCH` (parcial — §7.2.1.7/.8, §7.2.2.5 declaradas pendentes) |
| EN 1992-1-1 | não versionada | §3.1.6(1), Tab. 2.1N, §6.7 | `normativo.py:122-129` | `NOT DECLARED` |
| **NBR 6123** | **`:2023`** (`normativo.py:69`) | Tab. 1/2 de parâmetros = **valores da edição :1988**; numeração "Tab. 10"/"Tab. 25" só existe na :2023; `Ft=0,5·q·a·b` sem fonte | `wind.py:33-46, 234-245, 496` | **`NOT VERIFIABLE`** |
| EN 1991-1-4 | usada só como comparação nesta auditoria | Tab. 7.10 (c_fr) | — | `NOT APPLICABLE` |

> **[F-18] MÉDIA — `NOT VERIFIABLE — REQUIRES EXTERNAL NORMATIVE SOURCE`.**
> Nenhuma tabela da NBR 6123:2023 está reproduzida com citação verificável no
> repositório. Os parâmetros meteorológicos (`wind.py:33-38`) coincidem com a
> **edição de 1988** (b, p, z_g, F_r), a numeração de tabelas é da 2023, e o
> deslocamento de numeração é inconsistente entre si (Tab. 18→25 = +7; a tabela de
> telhados múltiplos, historicamente a Tab. 6 de :1988, aparece como Tab. 10 = +4).
> Isto **não** é afirmação de erro: é a constatação de que a conformidade à edição
> declarada **não pode ser verificada** com o material fornecido.
> **Ação P0:** anexar ao memorial a reprodução das Tab. 1, 2, 10 e 25 e do §7.2.2 da
> NBR 6123:2023 efetivamente consultada.

---

## E — NATIONAL ANNEX / NDP

**`EUROCODE_BASE` = `EN 1990:2002 + EN 1991-1-1:2002 + EN 1995-1-1:2004/A1:2008`**
(`normativo.py:60`)
**`NATIONAL_ANNEX` = `NENHUM`** (`normativo.py:62-67`) — declaração explícita de que o
Brasil não publica Anexo Nacional aos Eurocódigos e de que se adotam os **valores
recomendados do EN**, por decisão de projeto registrada, com aviso obrigatório em
qualquer saída dependente (`ConfiguracaoNormativa.aviso()`, `normativo.py:173-182`).

**Este é o ponto mais forte do repositório.** A distinção `"EN"` (prescrito) vs
`"EN-recomendado"` (NDP) vs `"PROJETO"` (não normalizado) é implementada como dado, e
não como comentário. `parametros_ndp()` devolve 17 NDP.

Verificação item a item dos NDP declarados:

| Parâmetro | Valor | Cláusula | Classificação no código | Veredito da auditoria |
|---|---|---|---|---|
| γG,sup / γG,inf | 1,35 / 1,00 | EN 1990 Tab. A1.2(B) | EN-recomendado | ✔ correto |
| γG,EQU estab./desestab. | 0,90 / 1,10 | Tab. A1.2(A) | EN-recomendado | ✔ correto |
| γQ | 1,50 | Tab. A1.2(B) | EN-recomendado | ✔ correto |
| ψ0/ψ1/ψ2 cat. H | 0 / 0 / 0 | Tab. A1.1 | EN-recomendado | ✔ correto |
| ψ0,W / ψ2,W | 0,60 / 0 | Tab. A1.1 | EN-recomendado | ✔ correto (não consumidos — Q e W não concomitantes) |
| γM madeira / ligação | 1,25 / 1,30 | EC5 Tab. 2.3 | EN-recomendado | ✔ correto |
| k_cr | 0,67 | §6.1.7 (A1:2008) | EN-recomendado | ✔ correto |
| k_mod, k_def | Tab. 3.1 / 3.2 | EC5 | EN | ✔ tabelas corretas (CS3: 0,50/0,55/0,65/0,70/0,90; k_def=2,00) |
| k_m, β_c | 0,70 / 0,10 | §6.1.6(2), §6.3.2(1) | EN | ✔ correto |
| **lim_w_inst / lim_w_net,fin** | **L/300 / L/250** | **EC5 Tab. 7.2** | **EN-recomendado** | **✘ [F-20]** |
| α_cr,min, φ0 | 10 / 1/200 | EN 1993-1-1 §5.2.1(3), §5.3.2 | EN-recomendado | ✔ correto (analogia declarada) |
| **δ ≤ H/300 do painel de cruz** | 300 | — | **AUSENTE de `NDP_SOURCE`** | **✘ [F-23]** |
| k_s, k_f,2, k_f,3 (§9.2.5) | 4 / 80 / 30 | EC5 Tab. 9.2 | comentário em `contraventamento.py:50-62`, **fora de `NDP_SOURCE`** | ✘ rastreabilidade parcial |

> **[F-20] MÉDIA — NON-CONSERVATIVE.** A Tab. 7.2 do EC5 fornece **intervalos**
> (w_inst: ℓ/300–ℓ/500; w_net,fin: ℓ/250–ℓ/350), não um "valor recomendado". Adotar
> a extremidade **mais permissiva** é uma escolha de projeto, não um valor do EN, e
> está classificada como `"EN-recomendado"` em `normativo.py:115-116`. Reclassificar
> como `"PROJETO"` e justificar. (Sem efeito no caso atual: η_ELS = 0,19.)

> **[F-23] MÉDIA.** O limite de deslocamento dos painéis de contraventamento
> (`drift_lim = 300.0`, `contraventamento_vertical.py:160`) governa o
> dimensionamento das diagonais em ELS (η_δ = 0,611) e **não consta** de
> `NDP_SOURCE`, não tem cláusula e não tem origem declarada.

---

## F — UNIDADES

Contrato declarado em `.cursorrules`: forças em N, comprimentos em m, tensões em Pa.
**O contrato é violado sistematicamente**, mas de forma **consistente e documentada nos
nomes**: `loads.py` e todos os `checks` trabalham em **kN e kN·m** internamente e
convertem para Pa só na razão σ/f. As chaves de retorno carregam a unidade no nome
(`_kN`, `_kNm`, `_MPa`, `_m`, `_mm`).

Análise dimensional dos pontos de conversão (todos verificados por benchmark):

| Local | Expressão | Verificação dimensional | Status |
|---|---|---|---|
| `loads.py:132` | `gamma = rho_mean · g / 1000` | (kg/m³)(m/s²)/1000 = kN/m³ | ✔ 4,1202 kN/m³ |
| `cisalhamento.py:126,150` | `V_d_N = V_kN·1e3`; `τ = 1,5·V/(k_cr·b·h)` | N/m² = Pa | ✔ BM-04 |
| `cumeeira.py:127` | `M_ap_Nm = |M_kNm|·1e3` | N·m/(m·m²) = Pa | ✔ BM-06 |
| `wind.py:46` | `0,613e-3·Vk²` | (N/m²)·1e-3 = kN/m² | ✔ BM-01 |
| `connections.py:154-186` | f_h [MPa], M_y [N·mm], d [mm] → F [N] | MPa·mm·mm = N; √(N·mm·MPa·mm)=N | ✔ |
| `contraventamento_vertical.py:192` | `C_h = E[MPa]·A[mm²]/(L[mm])·cos²β` | N/mm = kN/m | ✔ (a divisão por `1e3` está no `L_diag_m*1e3`) |
| `deflection_els.py:82-95` | `κ = M[N·m]/(E[Pa]·I[m⁴])` | 1/m | ✔ BM-08 |

**Reuso de nome entre significados diferentes [F-25, LOW]:**
- `theta` designa (i) a direção do vento em graus (`wind.py:8-11`), (ii) o **ângulo do
  telhado** passado a `coeficientes_tabela10(theta_deg)` (`wind.py:248, 661`), e
  (iii) a inclinação do eixo centroidal em radianos (`loads.py:298`). Três grandezas
  distintas sob o mesmo identificador, dentro do mesmo pacote.
- `b` designa a largura da seção (m) e, em `wind.py:553`, a dimensão em planta da
  cobertura (m).
Nenhum dos dois produz erro **hoje**, mas ambos são exatamente o tipo de colisão que a
Seção 25 do mandato manda reportar.

**Nenhum erro de unidade encontrado.** Status: `VALIDATED`.

---

## G — MATERIAL / GL

`materials.py:27-52` — EN 14080:2013 Tab. 5 (glulam homogéneo). Valores conferidos
contra a tabela para GL20h/24h/28h/32h: `f_m,k`, `f_t0,k`, `f_c0,k`, `f_v,k=3,5`,
`f_t90,k=0,5`, `f_c90,k=2,5`, `E0,mean`, `E0,05`, `G_mean=650`, ρ_k, ρ_mean.
**Não há aplicação de valores da EN 338 como se fossem de glulam** — o comentário de
`materials.py:54-63` documenta a migração desde a revogada EN 1194:1999 item a item.

Status: `VALIDATED WITH RESERVATIONS` — a conferência é contra conhecimento normativo,
não contra a tabela reproduzida no repositório (mesma reserva de [F-18], grau menor).

**[F-16] LOW — CONSERVATIVE.** `materials.py:160-171` define `G_05 = E0,05/16`
(600 MPa para GL24h) enquanto a EN 14080:2013 Tab. 5 tabela `G_g,05 = 540 MPa`. O
docstring reconhece a divergência e argumenta que a propriedade só sustenta a forma
simplificada da Eq. (6.32). **Verificado por grep: `G_05` não é consumido em lado
nenhum** (`flambagem_lateral.py:85` recebe `G_05=None` sempre). Sem efeito.

**[F-17] LOW — CONSERVATIVE.** `k_h` (EC5 §3.3 Eq. 3.2, `min((600/h)^0,1 ; 1,1)` para
h < 600 mm) não é implementado. Aplicar-se-ia às terças (h=580 mm → k_h = 1,003) e
elevaria a resistência. Omissão conservadora; registar no memorial.

**`k_sys`** (§6.6) também ausente — conservador, correto para o caso (não há
distribuição transversal garantida no diafragma de telha).

---

## H — VENTO NBR 6123

**Benchmark BM-01 (executado, independente):** `z_ref`, `S2`, `Vk`, `q`, `β`
reproduzidos com erro relativo **0,000 %**.

```
z_ref = 8,78531 m | S2 = 0,81962 | Vk = 36,88308 m/s | q = 0,83390 kN/m² | β = 10,00°
S2 = b·F_r·(z/10)^p = 0,85 · 0,98 · (8,78531/10)^0,125       [NBR 6123 §5.3.3]
q  = 0,613·Vk²  [N/m²]                                        [NBR 6123 §4.2 c)]
```

Pontos positivos confirmados:
- `S2` é função de `z` (correção do AUD-001); o caso especial da categoria V está
  tratado (`wind.py:141`); acima de `z_g` a função **recusa** em vez de extrapolar.
- Os domínios das Tab. 25 (0,07 ≤ tg β ≤ 0,6) e Tab. 10 (5° ≤ θ ≤ 45°) **recusam**
  extrapolação (ADV-C: 4/4 recusas corretas).
- A rota de §7.2.1 é selecionada por três gatilhos independentes e explícitos
  (`wind.py:197-213`).
- Os padrões "uniformes fabricados" (`C1_unif_bv`, etc.) foram corretamente removidos
  de `padroes_cpe_tabela25` (AUD-004) — confirmado no código atual.

### [F-13] **ALTA — `Ft = 0,5·q·a·b`: valor sem fonte primária e fisicamente impossível**

- **Arquivo/linha:** `mlc_projeto/core/wind.py:496` (`COEF_ATRITO_COBERTURA_ISOLADA = 0.5`), consumido em `wind.py:555`.
- **Classe/função:** `forca_vento_paralelo_cumeeira`.
- **Variável:** `F_fric_kN`.
- **Equação:** `F_fric = 0,5 · q · a · b`, com `a = 46,0 m`, `b = 40,5 m`.
- **Cláusula alegada:** NBR 6123:2023 §7.2.2 — **não reproduzida no repositório**.
- **Reprodução:** `q = 0,8339 kN/m²` → `F_fric = 776,8 kN` (= saída do software).
- **Demonstração (BM-11, executada):**

| Grandeza | Valor |
|---|---|
| `Ft` implementado (coef. 0,50) | **776,8 kN** |
| `Ft` com coeficiente 0,05 | 77,7 kN |
| Arrasto de **bloqueio total** da cobertura (A_frontal = 40,5 × h̄ = 76,7 m², C_d = 1,2) | **76,7 kN** |
| Razão `Ft(0,50) / F_bloqueio_total` | **10,13 ×** |
| Maior `c_fr` do EN 1991-1-4 Tab. 7.10 (superfície muito rugosa) | 0,04 → **12,5× menor** |
| Arrasto de **todos os 27 pilares** juntos | 60,5 kN |

- **Fundamentação:** uma força de **atrito superficial** não pode exceder em uma ordem
  de grandeza o arrasto de forma que o mesmo corpo teria se bloqueasse integralmente o
  escoamento. O valor implementado equivale a um coeficiente de arrasto de 0,5 aplicado
  a **toda a área em planta como se fosse área frontal**. Além disso, `Ft` sozinho é
  **12,8× o arrasto somado de todos os elementos sólidos da estrutura**.
- **Severidade ALTA e não CRÍTICA:** a direção é **conservadora** (não põe vidas em
  risco); mas invalida integralmente o dimensionamento metálico e a conclusão do
  memorial, e é a **única** razão para 4 painéis, Ø45, pilar de canto engrossado e 6
  chumbadores.
- **Conservatism:** `CONSERVATIVE`.
- **Confiança:** `CONFIRMED` quanto à impossibilidade física; `PROBABLE` quanto a o
  valor correto ser 0,05.
- **Rastreabilidade da origem:** o único registro no repositório é
  `AUDITORIA_TECNICA_INDEPENDENTE.md:177`, e o teste
  `tests/test_auditoria_regressoes.py:110` **reafirma o mesmo número** —
  **`INVALID BENCHMARK — SELF-REFERENTIAL`** nos termos da §0.5 do mandato.
- **Correção proposta (P0):** transcrever o §7.2.2 da NBR 6123:2023 no docstring com o
  valor literal; se for 0,05, corrigir e **redimensionar todo o sistema de
  contraventamento** (a estrutura ficará substancialmente mais leve).

### [F-01] **ALTA — componente horizontal da pressão de cobertura omitida** *(ver Seção N)*

### [F-08] MÉDIA — `ParametrosVento` sem validação de domínio

`wind.py:94-104` valida **apenas** `categoria` e `classe`. `V0`, `S1`, `S3`, `L`, `H1`,
`h`, `dist_portico` e `l2` entram sem verificação, apesar de `core/validacao.py`
existir e ser importado no mesmo módulo. Resultado dos testes adversariais:

```
ParametrosVento(V0=-45.0).q     → 0.81461 kN/m²   (positivo, "válido")   FALHA SILENCIOSA
ParametrosVento(V0=nan).q       → nan                                     FALHA SILENCIOSA
```

`q = 0,613e-3·Vk²` elimina o sinal; uma velocidade básica negativa produz uma pressão
plausível. `Conservatism: VARIABLE`.

---

## I — INTERFACE NBR 6123 → EN 1990

Rastreio explícito do estado de ponderação em cada passagem:

| Etapa | Grandeza | Estado | Evidência |
|---|---|---|---|
| `wind.calcular_vento` | `q`, `c_net` | **característico** | `wind.py:664, 691-692` |
| `pressoes_padrao[id]["w_esq_kNm2"]` | `c·q` | **característico** (kN/m²) | `wind.py:691-698` |
| `Carregamentos._montar_combinacoes` | `we = w_esq_kNm2 · area_trib` | **característico** (kN/m) | `loads.py:600-601` |
| combinação | `1,35·g + 1,5·we` | **de cálculo** | `loads.py:610-611` |
| `fixacao_telha` | `q` recalculado com **classe A** | característico | saída: `q=0,890, z=8,79 m` |

**Não há dupla ponderação.** Nenhum `γf` da NBR 6123 é aplicado antes do `γQ` da
EN 1990: o `wind.py` devolve exclusivamente valores característicos e o único fator
parcial aplicado ao vento é `GAMMA_Q = 1,5` em `loads.py`. **Verificado por benchmark
BM-03**: a combinação de sucção governante reconstruída independentemente
(`0,9·g + 1,5·w`, padrão `t1_esq_cpi+0,8`) devolve `q_tot = −7,60899` contra
`−7,60895` do software (0,001 %) e `R_A = −86,14393` contra `−86,14350` (0,000 %).

Status: `VALIDATED`.

---

## J — COMBINAÇÕES EN 1990

Gerador recriado de forma independente (BM-03): **17 combinações ELU** (8 padrões × 2
casos + ELU_Q) + 3 ELS + 4 aliases (`ELU_C1..C4`, que **não** são combinações físicas
novas — são ponteiros).

| Combinação | Forma implementada | Cláusula | Veredito |
|---|---|---|---|
| `ELU_W_*` | `1,35·G + 1,5·W` | EN 1990 Eq. 6.10, Tab. A1.2(B) | ✔ |
| `ELU_S_*` | `0,90·G + 1,5·W` | Tab. A1.2(A) EQU (G estabilizante) | ✔ conservador para STR (γG,inf seria 1,00) |
| `ELU_Q` | `1,35·G + 1,5·Q` | Eq. 6.10 | ✔ |
| ausência de `ψ0·Q` junto do vento | cat. H, ψ0=0 **e** não concomitância | EN 1990 Tab. A1.1 + EN 1991-1-1 §3.3.2(1) | ✔ dupla justificação, correta |
| `ELS_S1` | `G + Q` (característica) | EN 1990 §6.5.3 a) | ✔ |
| `ELS_S2` | `G + ψ1·Q = G` | §6.5.3 b) | ✔ |
| `ELS_S3` | `G + ψ2·Q = G` | §6.5.3 c) | ✔ |

Benchmark: `q_ELU_Q = 9,83770` vs `9,83776` (0,001 %).

### [F-10] MÉDIA — duração fixada nos aliases `ELU_C3` / `ELU_C4`

`loads.py:647` e `loads.py:658` gravam `duracao="curta"` **independentemente** da
duração da combinação que o alias aponta. `ELU_C2` foi corrigido para herdar a duração
real (`loads.py:636`), `C3` e `C4` não. Se `gov_h` (max |H|) recair sobre `ELU_Q`
(duração "media"), `ELU_C4` reportará k_mod de "curta" = 0,70 contra 0,65 —
**f_d 7,7 % sobrestimado**. *Não ativo hoje* (Opção B → todos os H = 0 → `gov_h` é o
primeiro elemento, uma combinação de vento). `Conservatism: NON-CONSERVATIVE`,
`Confiança: CONFIRMED` (defeito), `PROBABLE` (alcançabilidade na Opção A).

### [F-06] MÉDIA — envelope por procuração *(ver Seção Q, BM-14)*

`combinacao_ELU_governante()` (`loads.py:797-808`) devolve a combinação de **maior
|M_max| entre as de sentido gravítico**, e `main.py:517` deriva daí **um único material**
`mat_elu` para **todas** as verificações ELU. Mapeamento executado por grep:

- **Varrem todas as combinações:** `misula.py`, `pilares.py` (2 de 15).
- **Usam apenas a governante por |M|:** `cumeeira.py`, `flambagem_lateral.py`,
  `flexao.py`, `apoio.py`, `contraventamento*.py` (3), `estabilidade_global.py`,
  `connections.py`, `chapas_aco.py`, `chapas_dim.py`, `fadiga_ligacoes.py` (13 de 15).

O seletor não maximiza `M_cumeeira` (ápice), nem `R_v` (apoio/ligação), nem
`σ_m/W(x)`, nem considera que k_mod varia 7,7 % entre "media" e "curta".

**Alcançabilidade demonstrada (BM-14):** na rota Tab. 25 — plenamente suportada pelo
código e **ativa na versão anterior do projeto** (ver `output/pipeline_console.txt`
commitado) — a governante passa a ser `ELU_W_C1_asim` (curta) e o ápice §6.4.3 fica
**subestimado em 4,2 %** face ao envelope real, porque `ELU_Q` tem momento menor mas
k_mod menor. Na configuração **atual** (rota Tab. 10, vento todo de sucção) o seletor
**coincide** com o envelope em todas as grandezas — a tabela completa das 17
combinações está na Seção Q.

`Conservatism: VARIABLE`. `Severidade MÉDIA e não ALTA` porque o desvio medido é de
4,2 % e a arquitetura, não o número, é o defeito.

---

## K — MECÂNICA (resistência dos materiais)

Reconstrução independente da análise estrutural (BM-03, tolerância 0,1 %):

| Grandeza | Referência independente | Software | Δ |
|---|---|---|---|
| `A(x)`, `I(x)`, `W(x)` | `b·h`, `b·h³/12`, `b·h²/6` | idem (`geometry.py:78-88`) | exato |
| `h_ap` | `h0 + (L/2)·tan α = 2,78544 m` | 2,78544 | 0 % |
| `V_viga` (integral de A(x)) | 12,26441 m³ | 12,26440 | 0,000 % |
| `M_0(x) = q·x·(L−x)/2` | `M_max = 504,25918 kN·m` | 504,26210 | 0,001 % |
| `R_A = q·L/2` | 99,60675 kN | 99,60730 | 0,001 % |
| `N = R_A·sen θ`, θ=atan(tanα/2) | 8,74775 kN | 8,74780 | 0,001 % |
| `V = R_A·cos θ` | 99,22188 kN | 99,22250 | 0,001 % |
| `M_0` assimétrico `R_A=(3q_e+q_d)L/8` | −86,14393 kN | −86,14350 | 0,000 % |

**Castigliano (H_rígido)** — `loads.py:251-262`. A montagem
`δ11 = ∫y_c²/(EI)ds + ∫cos²θ/(EA)ds`, `H = ∫M_0·y_c/(EI)ds / δ11` está algebricamente
correta para o sistema principal escolhido, e a inclusão do termo axial (que a versão
anterior omitia, superestimando H em ~3,5×) é a correção certa.

**[F-26] LOW — assimetria de δ10.** O termo axial entra em `δ11` mas **não** em `δ10`:
no sistema principal (apoio horizontal liberado) o esforço normal primário
`N_0(x) = −R_A·sen θ + …` é não nulo e contribui `∫N_0·cos θ/(EA)ds` para `δ10`. A
formulação é, portanto, internamente inconsistente. **Sem efeito no modelo adotado**
(Opção B ⇒ `H = 0` por decisão de modelo, `M = M_0`), afetando apenas o `H_rígido`
reportado para auditoria (`empuxo_acoplado.py`). `Conservatism: VARIABLE`,
`Confiança: PROBABLE`.

**[F-09] MÉDIA — compensação numérica proibida.** `loads.py:241-242`:

```python
I_x = np.maximum(I_x, 1e-18)
A_x = np.maximum(b * h_x, 1e-18)
```

Isto é exatamente o mecanismo que `core/validacao.py:19-21` declara proibido
("**falhar alto, nunca compensar**"). Teste adversarial ADV-B:

```
analisar_biarticulada(q=10, L=20, h0=0.0, h_ap=2.0, ...)  →  H_kN = 0.0   (sem erro)
analisar_biarticulada(q=nan, ...)                         →  M_max = nan (sem erro)
```

Alcançável porque a função é pública e chamada diretamente por 4 módulos, contornando
`GeometriaViga`. O `nan` é **capturado a jusante** (`eta <= 1.0` devolve `False` ⇒
REPROVADO), mas `h0 = 0` produz "aprovação" numérica de uma seção inexistente.
`Conservatism: NON-CONSERVATIVE`, `Confiança: CONFIRMED`.

---

## L — EC5 ELU

| Verificação | Cláusula/Eq. | Forma implementada | Benchmark | Status |
|---|---|---|---|---|
| Cisalhamento | §6.1.7 Eq. 6.13 + A1 | `τ = 1,5V/(k_cr·b·h_ef)` | BM-04: τ=0,69419 vs 0,69420 MPa; η=0,38142 vs 0,38140 | `VALIDATED` |
| Entalhe | §6.5.2 | `k_v` implementado, **não usado** (`entalhe=False`) | — | `NOT APPLICABLE` |
| Apoio ⊥ | §6.1.5 Eq. 6.3 | `σ = R/(b·ℓ_ap)`, **sem** `k_c,90` nem `ℓ_ef=ℓ+30mm` | BM-09: σ=0,34586 vs 0,34590; η=0,26605 vs 0,26600 | `VALIDATED` (conservador, [F-15]) |
| Hankinson | §6.2.2 Eq. 6.16 | forma correta | — | **`ERROR` — [F-12]** |
| Mísula | §6.4.2 Eq. 6.38–6.40 | ambos os regimes; varre x **e** todas as combinações | BM-05: k_tra=0,41429 vs 0,41430; k_cmp=0,75835 vs 0,75840 | `VALIDATED` |
| Ápice | §6.4.3 Eq. 6.41–6.57 | `k_l=k1`, `k_r=1`, `k_p=0,2tanα`, `k_dis=1,4`, `k_vol=(V0/V)^0,2`, `V≤2V_b/3` | BM-06: 8/8 grandezas ≤ 0,05 % | `VALIDATED` (uma combinação — [F-06]) |
| Flambagem lateral | §6.3.3 Eq. 6.30/6.32/6.34 | 3 regimes de `k_crit` | BM-07: λ=0,44554 vs 0,44550; η=0,09766 vs 0,09770 | `VALIDATED WITH RESERVATIONS` — [F-07] |
| Flexo-compressão | §6.3.2 Eq. 6.23/6.24 | termo de compressão **linear** (÷k_c); `k_m=0,7` no termo cruzado | forma conferida contra o texto | `VALIDATED` |
| Flexão + LTB | §6.3.3 Eq. 6.35 | **flexão ao quadrado**, compressão linear | forma conferida | `VALIDATED` |
| Tração+flexão | §6.2.3 Eq. 6.17/6.18 | `corda_beiral.py:98-99` | forma conferida | `VALIDATED` |
| Terças | §6.1.6 Eq. 6.11/6.12; §6.3.2 | forma correta | — | `VALIDATED WITH RESERVATIONS` (rótulo errado, [F-21]) |
| Contraventamento | §9.2.5.2 Eq. 9.34/9.35; §9.2.5.3 Eq. 9.36/9.37/9.38 | `N_d=(1−k_crit)M/h`, `q_d=k_ℓ·n·N_d/(k_f3·ℓ)`, `k_ℓ=min(1,√(15/ℓ))`; Tab. 9.2 recomendados | forma conferida | `VALIDATED` |
| `k_h`, `k_sys` | §3.3, §6.6 | **ausentes** | — | `NOT APPLICABLE` (conservador, [F-17]) |
| **σ_c,90 no ápice sob uplift** | §6.4.3 | usa `abs(M_ap)` contra `f_t,90,d` | — | `VALIDATED` (conservador: trata compressão como tração) |

> **[F-07] MÉDIA — NON-CONSERVATIVE.** `flambagem_lateral.calcular_l_ef` implementa a
> Tab. 6.1 (`0,9·l_1` para carga distribuída) mas **omite a nota da própria tabela**:
> *"if the load is applied at the compression edge of the beam, l_ef should be increased
> by 2h"*. As terças apoiam **no extradorso**, ou seja, na borda comprimida sob
> gravidade. Com `l_1 = 2,53 m`: `l_ef` correto = 2,277 + 2×2,785 = **7,85 m** em vez de
> 2,277 m (**3,4×**). Recalculado: σ_m,crit cai de 120,9 para 35,1 MPa, λ_rel,m sobe de
> 0,446 para 0,827 (**passa de "estável" para "instabilidade parcial"**) e
> k_crit = 0,940. η_LTB: 0,0977 → 0,1039. **Imaterial neste projeto** (a viga está
> muito sobredimensionada), mas o defeito é sistemático e afeta também
> `predim.varrer_acumulado` e o caso de içamento. `Confiança: CONFIRMED`.

> **[F-12] LOW — NON-CONSERVATIVE (não governante).** `apoio.py:90-92` chama
> Hankinson com `alpha_deg = geo.alpha_deg` (**a inclinação do telhado**) e área
> `b·h0` (**a seção transversal inteira**). O ângulo correto entre a reação vertical e
> as fibras (horizontais, ao longo do intradorso) é ~90°, e a área é a de apoio. O
> resultado é `f_c,α,d = 9,91 MPa` ≈ `f_c,0,d` e η_ca = 0,031 — uma verificação
> **decorativa**. Não governa hoje porque §6.1.5 dá 0,266 e é conservadora; mas o
> valor publicado no memorial é fisicamente falso. `Confiança: CONFIRMED`.

> **[F-15] MÉDIA — CONSERVATIVE.** `k_c,90` (§6.1.5(2)-(4), até 1,50) e a extensão
> `ℓ_ef = ℓ + 30 mm` de cada lado (§6.1.5(1)) não são explorados. Registar no memorial
> como reserva deliberada.

---

## M — EC5 ELS

**Benchmark BM-08 (executado, independente, Timoshenko com seção variável):**

```
sanidade (h const.): w_flexão = 7,13957 mm  vs  5qL⁴/384EI = 7,13957 mm     (exato)
                     w_cis    = 0,29572 mm  vs  k_s·qL²/8GA = 0,29572 mm     (exato)

                       REFERÊNCIA         SOFTWARE
w(G)                    4,416 mm            4,42 mm
  · flexão              3,478 mm            3,48 mm
  · cisalhamento        0,938 mm (21,2 %)   0,94 mm (21,2 %)
w(Q)                    2,146 mm            2,15 mm
w_S1 = w_G+w_Q          6,562 mm            6,56 mm    η = 0,0972
w_fin = w_G(1+k_def)+w_Q  15,394 mm         15,39 mm   η = 0,1900
```

- `w_fin = u_G(1+k_def) + u_Q(1+ψ2·k_def)` com ψ2 = 0 — **EC5 §2.3.2.2 Eq. (2.2)**, ✔.
- `E = E0,mean`, `G = G_mean` em ELS — **EC5 §2.2.3(2)**, ✔.
- `k_def = 2,00` para CS3 — **EC5 Tab. 3.2**, ✔.
- Condições de contorno: só a correção **linear** em `w` (rotação livre nos apoios);
  o docstring de `deflection_els.py:56-60` justifica corretamente por que não se
  corrige θ. ✔
- **Sinal do termo de cisalhamento verificado**: na convenção `w'' = +M/EI` adotada, o
  descendente é negativo, e `γ = −k_s·V/(GA)` faz flexão e cisalhamento **somarem**.
  Confirmado numericamente (21,2 % em ambos). ✔

Status: `VALIDATED`. Reserva: limites no extremo permissivo da Tab. 7.2 ([F-20]).

`w_fin ≤ ℓ/150–ℓ/300` da Tab. 7.2 não é verificado separadamente — mas com
`w_camber = 0`, `w_net,fin = w_fin` e o limite ℓ/250 aplicado é mais severo. Coberto.

---

## N — ESTABILIDADE

### [F-01] **ALTA — NON-CONSERVATIVE — componente horizontal do vento de cobertura omitida**

- **Arquivo/linha:** `mlc_projeto/checks/elu/contraventamento_transversal.py:99-126`.
- **Classe/função:** `demanda_transversal`.
- **Variável:** `H_tr = H_vento_topo + H_imp`.
- **Equação:** `H_vento_topo = n_col · γQ · F_pilar,k / 2` — **só o arrasto dos pilares**.
- **Defeito:** a pressão de vento nas águas atua **perpendicularmente à superfície do
  telhado**. `loads.py` aplica corretamente a sua **componente vertical** (a projeção
  horizontal cancela o `1/cos α`), mas a **componente horizontal**
  `Σ c_i·q·A_água,i·sen α` — que **não se cancela** quando `c_esq ≠ c_dir` — não é
  calculada em lugar nenhum do repositório. Todos os 8 padrões de Tab. 10 usados têm
  `c_esq ≠ c_dir`.
- **Demonstração (BM-12, executada):**

```
zona a*/b*:  |c_pe,barlavento − c_pe,sotavento| = 0,50      (c_pi cancela entre as águas)
A de uma meia-água por pórtico = (L/2)/cos α · L_t = 59,12 m²
H_horiz omitido por pórtico (característico) = 0,50 · 0,8339 · 59,12 · sen 10° = 4,28 kN
                                de cálculo (×1,5)                              = 6,42 kN
9 pórticos                                                                     = 57,8 kN
H_vento_topo CONSIDERADO pelo software                                         = 38,3 kN
                                                        RAZÃO omitido/incluído =  1,51 ×
```

- **Consequência:** `H_tr` passa de 48,4 kN para ≈ 106 kN (**2,19×**). Propagam-se:
  `R_frontão` 24,2 → 53 kN; `N_diag` 38,1 → 84 kN; `H_base` e `N_uplift` das bases de
  canto ×2,19; `N_corda` do beiral ×2,19. A diagonal do frontão (Ø16 auto-dimensionada
  a η ≤ 0,90) teria de subir para ≈ Ø24.
- **Severidade ALTA:** ação real de dimensionamento omitida, maior que a ação incluída,
  num caminho de carga que termina na fundação e que valida a hipótese `l_ef = 1,0·H`
  dos pilares.
- **Conservatism:** `NON-CONSERVATIVE`. **Confiança:** `CONFIRMED`.

### [F-02] **ALTA — NON-CONSERVATIVE — `α_cr` reportado não é um α_cr de sistema**

- **Arquivo/linha:** `mlc_projeto/checks/elu/estabilidade_global.py:278-286` (+ `:120-124`).
- **Classe/função:** `verificar_estabilidade_global` / `alpha_cr_membro`.
- **Variável:** `alpha_cr` (= `acr_arco["alpha_cr"]`), critério `ok_acr = alpha_cr ≥ 10`.
- **Equação implementada:** `N_cr = π²·E0,05·(b·h0³/12)/(L/2)²`, `α_cr = N_cr / N_viga`.
- **Defeito 1 — a grandeza errada.** A EN 1993-1-1 §5.2.1(3) define `α_cr = F_cr/F_Ed`
  como o fator pelo qual **o carregamento de projeto** deve crescer para causar
  instabilidade elástica **do sistema no seu modo de deslocamento lateral**. O que o
  código compara com 10 é a carga de Euler de **uma barra**, dividida pelo **axial da
  viga** (`N_viga = 8,75 kN`) — axial que o próprio modelo adotado (Opção B, `H = 0`)
  força a quase zero. **Quanto menos empuxo o modelo admite, maior o "α_cr":** a
  métrica é monotonicamente favorecida pela hipótese que deveria testar.
- **Defeito 2 — o modo sway é declarado, não calculado.** `estabilidade_global.py:248`:
  `alpha_cr_sway = float("inf") if sistema_non_sway else 0.0`, onde `sistema_non_sway`
  é a conjunção de dois **booleanos** vindos das verificações de contraventamento.
- **Defeito 3 — valor de segurança em bloco `if`.** `alpha_cr_membro` devolve
  `alpha_cr = 1e99` quando `N_Ed == 0` (`:120-124`) — "infinitamente estável".
- **Reprodução (BM-13, executada):** α_cr de sistema reconstruído a partir da rigidez
  real dos painéis de cruz (`K = E·A·cos²β/L_diag`, só a diagonal tracionada ativa) e
  da carga vertical ELU total do galpão (`ΣN_Ed = 4·R_v·n_pórticos = 3586 kN`):

| Direção | Painéis | K [kN/m] | `α_cr = K·h/ΣN_Ed` | Veredito |
|---|---|---|---|---|
| Longitudinal | 4 × Ø45 | 59 417 | **115,99** | OK (≥10) |
| **Transversal** | 2 × Ø16 | 3 756 | **7,33** | **ABAIXO DE 10 → 2.ª ordem exigida** (k_II = 1,158) |

- **Consequência:** o critério de dispensa de análise de 2.ª ordem que o próprio projeto
  declara (`normativo.py:139`, `alpha_cr_min = 10`) **não é satisfeito na direção
  transversal**, mas o software reporta `α_cr = 2817,4` e conclui *"Análise de 1.ª ordem
  suficiente: sistema non-sway nas duas direções"*.
- **Composição com [F-01]:** η do contraventamento transversal reportado 0,807
  × 2,19 ([F-01]) × 1,158 (k_II) ⇒ **muito acima de 1,0**.
- **Conservatism:** `NON-CONSERVATIVE`. **Confiança:** `CONFIRMED` para os defeitos 1–3;
  `PROBABLE` para o valor 7,33 (rigidez de painel idealizada, sem flexibilidade das
  ligações — que só **reduz** K e piora α_cr).

**Nocionais EN 1993-1-1 §5.3.2** (`contraventamento_vertical.py:104-122`):
`φ = φ0·α_h·α_m`, `φ0 = 1/200`, `α_h = 2/√h` limitado a [2/3, 1], `α_m = √(0,5(1+1/m))`.
**Forma correta**, `VALIDATED`.

**[F-11] MÉDIA — NON-CONSERVATIVE.** `_n_t_rd_kN` (`contraventamento_vertical.py:127-131`)
calcula `N_t,Rd = A_bruta·f_y/γM0` apenas. A EN 1993-1-1 §6.2.3(2) exige
`N_t,Rd = min(N_pl,Rd ; N_u,Rd = 0,9·A_net·f_u/γM2)`. Para uma barra redonda
**roscada** de Ø45 (A_s ≈ 1306 mm² vs A = 1590 mm²): `N_u,Rd = 0,9·1306·360/1,25 = 338 kN`
contra `N_pl,Rd = 374 kN` — a seção líquida governa e não é verificada. Além disso, as
**ligações de extremidade das diagonais não são dimensionadas em lado nenhum**.
`Confiança: CONFIRMED` (a omissão); `PROBABLE` (que as barras sejam roscadas).

---

## O — GLULAM-ESPECÍFICO

- **Domínio do modelo.** A viga é de **duplo-bisel** (`extradorso` em duas águas,
  intradorso reto). O código aplica corretamente §6.4.2 (mísula) às meias-águas e
  §6.4.3 (ápice) à cumeeira, com `r → ∞` ⇒ `k_l = k1`, `k_r = 1`, `k_p = 0,2 tan α_ap`
  — as formas exatas para *double tapered beam*. **Não** há fórmula prismática aplicada
  a peça curva nem vice-versa. `MODEL DOMAIN: OK`.
- `V_ap = b·h_ap²(1 − 0,25 tan α)` corresponde a uma zona de ápice de comprimento
  horizontal `h_ap` (Fig. 6.9); `V_b = b·L(h_ap − 0,25·L·tan α)` é a integral exata do
  volume. Ambos reproduzidos por benchmark com 0,000 %.
- **`k_c` em peça de seção variável** — `flexao.py:108-116` documenta explicitamente
  que a EN 1995-1-1 §6.3.2 **não formaliza** `k_c` para seção variável, e adota a seção
  **local** declarando a escolha como conservadora. Correto proceder; permanece
  `NOT VALIDATED` por ausência de base normativa (declarado pelo próprio código).
- **Restrição lateral pelas terças.** O acoplamento
  `contraventamento.restricao_lateral_valida → l_1 = s` está implementado e
  realimentado (`main.py:633-647`). Com `k_crit = 1,0`, a Eq. 9.36 dá `N_d = 0` —
  **isto é o que a norma prescreve**, não um defeito.

---

## P — CONEXÕES (EC5 §8)

### [F-03] **ALTA — NON-CONSERVATIVE — `f_h,α,k` nunca aplicado**

- **Arquivo/linha:** `mlc_projeto/connections/connections.py:154-170` (`f_h_k`),
  `:220` (`johansen_chapa_embutida`), `:792` (chamada), `:783` (`theta_deg` calculado).
- **Variável:** `f_hk`.
- **Equação implementada:** `f_h,k = 0,082(1 − 0,01d)·ρ_k` — **EC5 §8.5.1.1 Eq. (8.32)**,
  válida **para carga paralela às fibras**.
- **Equação omitida:** **EC5 §8.5.1.1(2) Eq. (8.31)/(8.33)**
  `f_h,α,k = f_h,0,k/(k90·sen²α + cos²α)`, `k90 = 1,35 + 0,015d` (glulam).
- **Defeito:** `theta_deg` **é calculado** em `:783` (= 84,96°, porque a resultante na
  base é dominada pelo cortante `V = 99,2 kN` contra `N = 8,75 kN`) e é usado
  **apenas** para as distâncias mínimas. `johansen_chapa_embutida` recebe só `rho_k` e
  `d_mm` — não tem como aplicar o ângulo.
- **Reprodução (BM-10, executada):**

```
f_h,0,k = 23,993 MPa     k90 = 1,710     α = 84,96°
f_h,α,k = 23,993/(1,710·0,99239 + 0,00761) = 14,076 MPa      (−41,3 %)
```

- **Conservatism:** `NON-CONSERVATIVE`. **Confiança:** `CONFIRMED`.

### [F-14] MÉDIA — CONSERVATIVE — modo de Johansen de outra configuração

- **Arquivo/linha:** `connections.py:228-238`, `:787`.
- **Equação implementada:** `F_IIIb = 1,15·√(2·M_y·f_h·d)` — esta é a **Eq. (8.13)(k)
  da EC5, para chapas de aço FINAS como elementos EXTERNOS** de ligação em corte duplo.
- **Equação aplicável:** a ligação é **chapa central embutida** ⇒ **EC5 Eq. (8.11)**:
  `(f) f_h,1,k·t1·d` · `(g) f_h,1,k·t1·d[√(2 + 4M_y/(f_h,1,k·d·t1²)) − 1]` ·
  `(h) 2,3√(M_y·f_h,1,k·d)`.
- **Defeito secundário:** `t_mm = b/2` (`connections.py:787`) ignora a espessura da
  chapa: o correto é `t1 = (b − t_chapa)/2 = (320 − 25)/2 = 147,5 mm`, não 160 mm.
- **Efeito combinado com [F-03] (BM-10, executado):**

| Formulação | F_v,Rk/plano | F_Rd/pino | R (5 pinos) | η_L1 |
|---|---|---|---|---|
| Código (`f_h,0`; `t1=b/2`; `1,15√(2Mfd)`) | 26,62 kN | 26,62 kN | 133,11 kN | **0,7483** |
| EC5 8.11 com `f_h,0` e `t1=(b−t)/2` | 37,65 kN | — | — | (0,529) |
| **EC5 8.11 com `f_h,α` e `t1=(b−t)/2`** | **24,97 kN** | **24,97 kN** | **124,84 kN** | **0,7979** |

**Os dois erros têm sinais opostos e cancelam-se parcialmente**, mas **não
integralmente**: a resistência correta é **6,6 % menor** e **η_L1 = 0,798 ultrapassa o
alvo de 0,75 que o próprio projeto impõe aos modos frágeis** (`main.py:315`,
`issues/22`). O cancelamento é fortuito — depende de `t1`, `d` e `f_u` — e não
sobrevive a uma mudança de diâmetro ou de largura.

### [F-05] MÉDIA — NON-CONSERVATIVE — `a4,t` sem o termo `(2 + 2 sen α)d`

- **Arquivo/linha:** `connections.py:658` — `a4t = max(3.0 * d_mm, 0.0)`.
- **Equação normativa:** **EC5 Tab. 8.5** (cavilhas), distância à **borda carregada**:
  `a4,t = max((2 + 2 sen α)·d ; 3d)`.
- **Reprodução:** α = 84,96° ⇒ `(2 + 2·0,99619)·24 = 95,8 mm`; código: **72,0 mm**
  (**déficit de 24,9 %**).
- **Por que importa:** a distância à borda carregada é o parâmetro que controla o
  **fendilhamento**, modo frágil, e este projeto já precisa de 8×Ø10 de reforço
  (§8.7.2) para levar η_fendilhamento de 1,042 para 0,722.
- **Nota:** a geometria adotada (5 pinos numa fila vertical, `h_ocupado = 432 mm` em
  `h0 = 1000 mm`) **ainda cabe** com `a4,t = 95,8 mm` (479,6 mm) — a correção é de
  detalhamento, não de capacidade. `Conservatism: NON-CONSERVATIVE`, `CONFIRMED`.

### Outras verificações de ligação — conferidas e corretas

- `M_y,Rk = 0,3·f_u,k·d^2,6` — **EC5 Eq. (8.30)** ✔
- `n_ef = min(n ; n^0,9·(a1/13d)^0,25)` — **EC5 §8.5.1.1(4) Eq. (8.34)** ✔; aplicado
  por fileira paralela às fibras, com `n_horiz = 1` ⇒ `n_ef = n` — coincide com o que
  §8.5.1.1(5) exige para carga perpendicular ✔ (por coincidência do layout).
- `a1 = (3 + 2|cos α|)d`, `a2 = 3d`, `a3,t = max(7d ; 80 mm)` — **Tab. 8.5** ✔
- Efeito de corda (`F_ax/4`) omitido — **correto**: EC5 §8.2.2(2), cavilhas lisas
  têm `F_ax,Rk = 0` ✔
- `K_ser = ρ_m^1,5·d/23` — **EC5 Tab. 7.1** ✔
- `γM,ligação = 1,30` — **EC5 Tab. 2.3** ✔
- `6 mm ≤ d ≤ 30 mm` para cavilhas — **EC5 §8.6(2)** ✔ (`_validar_diametro_cavilha`)
- Ruptura de bloco (Anexo A), fendilhamento (§8.1.4 Eq. 8.4) + reforço (§8.7.2),
  chapa/furos/solda (EN 1993-1-8), ancoragem moldada (EN 1992-4:2018 §7.2.1.4/.5,
  §7.4.1.4, §7.2.3) — **implementados**, com as pendências de §7.2.1.7 (fendilhamento
  do concreto), §7.2.1.8 (blow-out) e §7.2.2.5 (borda sob corte) **declaradas pelo
  próprio software na saída**. Boa prática.

---

## Q — BENCHMARKS EXECUTADOS

Todos os scripts são **novos**, executados no ambiente do projeto, e **não importam
nenhuma função do repositório para o cálculo de referência** — o repositório é
importado apenas para **ler** o valor a comparar.

| ID | Escopo | Resultado |
|---|---|---|
| BM-01 | NBR 6123 §5.3.3/§4.2: z_ref, S2, Vk, q, β | **5/5 OK**, Δ ≤ 0,000 % |
| BM-02 | EN 1991-1-1 §4.1: γ, V_viga, g_MLC, g_terças, g_k | **5/5 OK**, Δ ≤ 0,005 % |
| BM-03 | EN 1990 Eq. 6.10 + análise: q, M, R_v, N, V, sucção | **7/7 OK**, Δ ≤ 0,001 % |
| BM-04 | EC5 §6.1.7 Eq. 6.13 | **3/3 OK**, Δ ≤ 0,006 % |
| BM-05 | EC5 §6.4.2 Eq. 6.39/6.40 | **2/2 OK**, Δ ≤ 0,006 % |
| BM-06 | EC5 §6.4.3 Eq. 6.41–6.57 | **8/8 OK**, Δ ≤ 0,048 % |
| BM-07 | EC5 §6.3.3 Eq. 6.30/6.32/6.34 | **3/3 OK**, Δ ≤ 0,046 % |
| BM-08 | EC5 §2.2.3(2)/§2.3.2.2 + Timoshenko | **exato** (sanidade fechada + 6 grandezas) |
| BM-09 | EC5 §6.1.5 | **2/2 OK**, Δ ≤ 0,017 % |
| BM-10 | EC5 §8.2.3 Eq. 8.11 + §8.5.1.1 Eq. 8.31/8.33 + Tab. 8.5 | **DIVERGE** → [F-03], [F-05], [F-14] |
| BM-11 | NBR 6123 §7.2.2 vs limite físico de bloqueio | **DIVERGE 10,13×** → [F-13] |
| BM-12 | componente horizontal de pressão de cobertura | **OMITIDA, 1,51×** → [F-01] |
| BM-13 | EN 1993-1-1 §5.2.1(3) α_cr de sistema | **7,33 < 10** → [F-02] |
| BM-14 | envelope sobre as 17 combinações ELU | coincide hoje; **−4,2 % na rota Tab. 25** → [F-06] |

**BM-14 — tabela completa (rota atual, Tab. 10):** as 17 combinações ELU, com η
recalculado de forma independente por combinação (com o k_mod da duração de cada uma).
A combinação escolhida pelo software (`ELU_Q`, "media") **é** a governante do envelope
em η_t90 (0,3526), η_LTB (0,0977), η_c90 (0,2660) e F_ligação (99,6 kN) — os quatro
coincidem. Sob a rota Tab. 25 a governante passa a `ELU_W_C1_asim` ("curta") e o η_t90
publicado cai para 0,3385 contra 0,3526 do envelope (**−4,2 %**).

---

## R — TESTES ADVERSARIAIS EXECUTADOS

| Grupo | Caso | Resultado |
|---|---|---|
| **ADV-A** domínio | `L=0`, `b<0`, `α=NaN`, `α=90°`, `h0=inf` | **5/5 recusa correta** (`DominioInvalidoError`) |
| | `classe="GL99z"`, `CS=4`, `duracao="xx"` | **3/3 recusa correta** (`ValueError`) |
| **ADV-B** função pública | `analisar_biarticulada(h0=0)` | **FALHA SILENCIOSA** → `H = 0,0` [F-09] |
| | `analisar_biarticulada(b=0)` | recusa correta |
| | `analisar_biarticulada(q=NaN)` | **FALHA SILENCIOSA** → `M_max = nan` [F-09] |
| | `analisar_biarticulada(L<0)` | recusa correta |
| **ADV-C** vento | Tab. 25 fora de [0,07; 0,6]; Tab. 10 fora de [5°; 45°]; `z > z_g` | **5/5 recusa correta, sem extrapolação** |
| | `V0 = −45` | **FALHA SILENCIOSA** → `q = 0,81461 kN/m²` [F-08] |
| | `V0 = NaN` | **FALHA SILENCIOSA** → `q = nan` [F-08] |
| **ADV-D** veredito | `extrair_eta_ok({})` | **`(0.0, True)`** — vazio ⇒ **aprovado** [F-04] |
| | `extrair_eta_ok({'eta': None})` | **`(0.0, True)`** [F-04] |
| | `extrair_eta_ok({'eta': 'erro'})` | **`(0.0, True)`** — string ⇒ **aprovado** [F-04] |
| | `extrair_eta_ok({'eta': nan})` | `(nan, False)` ✔ |
| | `tabela_verificacoes` com verificação sem `eta` | **linha desaparece** do resumo/`all_ok` [F-04] |
| **ADV-E** propriedades | monotonicidade de η_cis e η_ápice em q_area = 0,4→3,2 | **crescente e ultrapassa 1,0** ✔ |
| | continuidade de `k_crit` em λ = 0,75 e 1,4 | contínua (1,000→0,9974; 0,5101→0,5101) ✔ |
| | `k_vol` com V→0 | limitado a 1,0 ✔ |
| **ADV-F** eixos | `l_1` 2,53 → 46,0 m | `k_crit` 1,000 → 0,277; η 0,098 → 0,353 ✔ fisicamente coerente |

### [F-04] **ALTA — NON-CONSERVATIVE — a agregação do veredito devolve "aprovado" para resultado ausente**

- **Arquivo/linha:** `mlc_projeto/output/report.py:23-30` (`_f`), `:83-94`
  (`extrair_eta_ok`), `:104-121` (`tabela_verificacoes`); consumido em
  `main.py:387-414` (`_imprimir_resumo_export`) e `main.py:371-384` (`_print_eta`).
- **Variável:** `eta`, `ok`, `all_ok`, `eta_max`, `status`.
- **Defeito 1 — valor de segurança em `except`:** `_f` captura `TypeError`/`ValueError`
  e devolve **`0.0`**; `extrair_eta_ok` sem chave `"ok"` conclui `ok = eta ≤ 1,0`.
  Um dicionário vazio, um `None` ou uma **string** produzem `η = 0,0000` e **`✓`**.
- **Defeito 2 — omissão silenciosa:** `tabela_verificacoes:108-109` faz `continue`
  quando o dicionário não tem `eta`/`eta_gov`/`eta_slip`. A verificação **desaparece**
  do resumo do terminal, do `all_ok`, do `eta_max`, do Excel e do memorial LaTeX,
  **sem qualquer aviso**. Não há assert de que `len(tab) == n_esperado` nem lista de
  chaves obrigatórias.
- **Atenuante honesta:** `main` **não** envolve as chamadas de verificação em
  `try/except` — uma exceção aborta o pipeline (falha alta, correto). O caminho vivo
  para [F-04] é um módulo que **retorne** um dicionário parcial, o que ocorre
  legitimamente hoje (`tirante_base`, `tirante_piso_robustez` inativos) e passa
  despercebido.
- **Confirmação numérica:** o `output/pipeline_console.txt` **commitado** anunciava
  `N.º verif. = 36 | todas OK = True | Status = APROVADO` com `η máximo = 1,0000`; a
  execução atual anuncia `38`. A diferença de contagem não é sinalizada por nada.
- **Conservatism:** `NON-CONSERVATIVE`. **Confiança:** `CONFIRMED`.

---

## S — ERROS PYTHON / SILENCIOSOS

| # | Padrão | Local | Efeito |
|---|---|---|---|
| S-1 | valor de segurança em conversão | `report.py:23-30` `_f(...) → 0.0` | η ausente vira **aprovação** [F-04] |
| S-2 | `continue` que apaga uma verificação | `report.py:108-109` | verificação some do veredito [F-04] |
| S-3 | `except Exception: pass` | `main.py:357-368` (`_Tee.write/flush`) | perda silenciosa do log — **aceitável** (I/O de terminal) |
| S-4 | `except Exception:` com fallback numérico | `estabilidade_global.py:295-296` → `w_char = 5.0` mm | flecha ELU **inventada** se `verificar_ELS` falhar; alimenta `w/f_c` |
| S-5 | valor de segurança em `if` | `estabilidade_global.py:120-124` → `alpha_cr = 1e99` | "infinitamente estável" para `N_Ed = 0` [F-02] |
| S-6 | clamp que compensa domínio inválido | `loads.py:241-242` `np.maximum(·, 1e-18)` | seção nula fica calculável [F-09] |
| S-7 | `or 0.0` sobre falsy | `main.py:376` | `eta = 0` quando a chave existe com `None` |
| S-8 | reuso de nome entre grandezas | `theta` (3 significados), `b` (2) | ver Seção F [F-25] |
| S-9 | comparação de floats por igualdade | `flexao.py:164-169` `eta_gov == eta_635` | seguro (mesmo elemento de array), mas frágil |
| S-10 | rótulo de string desatualizado | `tercas.py` → `"ELU_C2 (1,35G+1,5W+1,05Q)"` | memorial descreve **combinação inexistente** [F-21] |

**Não foram encontrados:** erros de precedência, expoentes trocados, `abs()`/`min()`/
`max()` mascarando sinal, arredondamento antecipado que altere resultado (os `round`
são só de apresentação), divisão inteira indevida, erro de broadcasting, mutabilidade
de default, ou cache incorreto.

---

## T — VERIFICAÇÕES AUSENTES

| Item | Cláusula | Situação | Severidade |
|---|---|---|---|
| Componente horizontal do vento de cobertura | NBR 6123 + equilíbrio | **ausente** | **ALTA [F-01]** |
| α_cr de sistema / 2.ª ordem | EN 1993-1-1 §5.2.1 | **substituído por métrica de barra** | **ALTA [F-02]** |
| `f_h,α,k` nas cavilhas | EC5 §8.5.1.1 Eq. 8.31 | **ausente** | **ALTA [F-03]** |
| Seção líquida das diagonais + ligações de extremidade | EN 1993-1-1 §6.2.3(2) | **ausente** | MÉDIA [F-11] |
| `l_ef + 2h` (carga na borda comprimida) | EC5 Tab. 6.1, nota | **ausente** | MÉDIA [F-07] |
| Envelope sobre combinações em 13 de 15 módulos | EN 1990 §6.4.3.2 | **substituído por proxy** | MÉDIA [F-06] |
| Fendilhamento do concreto (§7.2.1.7), blow-out (§7.2.1.8), borda sob corte (§7.2.2.5) | EN 1992-4:2018 | **ausente — declarado pelo software** | MÉDIA (declarada) |
| Esmagamento do concreto sob a chaveta de cisalhamento | EN 1992-1-1 §6.7 | **ausente — declarado** (`main.py:287`) | MÉDIA (declarada) |
| **Dimensionamento da fundação** | EN 1997 | **fora de escopo — declarado com ênfase** | ACEITE |
| `k_h`, `k_sys` | EC5 §3.3, §6.6 | ausentes (conservador) | LOW [F-17] |
| Vibração | EC5 §7.3 | declarado não aplicável (cobertura industrial) | ACEITE |
| Resistência ao fogo | EN 1995-1-2 | **ausente e não declarada** | MÉDIA (não avaliada nesta auditoria) |

---

## U — MATRIZ FINAL DE CONFORMIDADE

> **Regra dura aplicada:** `VALIDATED` só onde as quatro colunas anteriores têm
> evidência preenchida. Coluna vazia ⇒ rebaixamento automático.

| Item | Implementado (`file:line`) | Mecânica | Norma | Benchmark | Status |
|---|---|---|---|---|---|
| Geometria h(x), A, I, W | `geometry.py:66-88` | seção retangular variável | — (matemática) | BM-02/03 | `VALIDATED` |
| Validação de domínio | `validacao.py:49-111` | pré-condição | — | ADV-A 8/8 | `VALIDATED` |
| Propriedades GL | `materials.py:27-52` | — | EN 14080:2013 Tab. 5 | conferência item a item | `VALIDATED WITH RESERVATIONS` |
| k_mod / k_def / γM / k_cr | `materials.py:72-91` | — | EC5 Tab. 3.1/3.2/2.3, §6.1.7 | usados em BM-04/06/07 | `VALIDATED` |
| Declaração NDP / NA | `normativo.py:60-185` | — | EN 1990/1995 | 17 NDP enumerados | `VALIDATED WITH RESERVATIONS` [F-20, F-23] |
| S2, Vk, q | `wind.py:113-175` | camada-limite | NBR 6123 §5.3.3, §4.2 | BM-01 (0,000 %) | `VALIDATED WITH RESERVATIONS` [F-18] |
| Domínio Tab. 24/25 | `wind.py:337-388` | — | NBR 6123 §7.2.1 | ADV-C | `VALIDATED WITH RESERVATIONS` [F-18] |
| c_pe Tab. 25 | `wind.py:393-483` | — | NBR 6123 Tab. 25 | ADV-C (domínio) | `NOT VERIFIABLE` [F-18] |
| c_pe Tab. 10 + c_pi | `wind.py:226-332` | c_net = c_pe − c_pi | NBR 6123 Tab. 10, §7.2.1 | ADV-C (domínio) | `NOT VERIFIABLE` [F-18] |
| Atrito θ=0° | `wind.py:496,555` | — | NBR 6123 §7.2.2 (alegada) | **BM-11: 10,13×** | **`ERROR` [F-13]** |
| Componente horiz. da cobertura | **ausente** | equilíbrio de forças | — | **BM-12: 1,51×** | **`ERROR` [F-01]** |
| Peso próprio g_k | `loads.py:87-158` | ∫A(x)dx·γ | EN 1991-1-1 §4.1 | BM-02 (0,005 %) | `VALIDATED` |
| Sobrecarga cat. H | `main.py:171` | — | EN 1991-1-1 Tab. 6.10 | 0,40 kN/m² + 1,0 kN | `VALIDATED` |
| Combinações ELU/ELS | `loads.py:497-712` | — | EN 1990 Eq. 6.10, Tab. A1.1/A1.2 | BM-03 (0,001 %) | `VALIDATED` |
| Seleção da governante | `loads.py:797-808` | proxy max\|M\| | EN 1990 §6.4.3.2 | **BM-14: −4,2 %** | **`NOT VALIDATED` [F-06]** |
| Análise biarticulada | `loads.py:174-309` | Castigliano + M0 | teoria da elasticidade | BM-03 (0,001 %) | `VALIDATED WITH RESERVATIONS` [F-26, F-09] |
| Diagramas M/V/N | `loads.py:870-911` | projeção no eixo | — | consistente com apoios | `VALIDATED` |
| §6.1.7 cisalhamento | `cisalhamento.py:120-156` | τ=1,5V/A_ef | EC5 Eq. 6.13 + A1 | BM-04 (0,006 %) | `VALIDATED` |
| §6.1.5 apoio ⊥ | `apoio.py:86-87` | σ=R/(b·ℓ) | EC5 Eq. 6.3 | BM-09 (0,017 %) | `VALIDATED` |
| §6.2.2 Hankinson | `apoio.py:40-57,90-92` | forma correta, **argumentos errados** | EC5 Eq. 6.16 | η_ca=0,031 (não governa) | **`ERROR` [F-12]** |
| §6.4.2 mísula | `misula.py:36-130` | k_m,α tração/compressão | EC5 Eq. 6.38–6.40 | BM-05 (0,006 %) | `VALIDATED` |
| §6.4.3 ápice | `cumeeira.py:42-189` | k_l, k_p, k_dis, k_vol | EC5 Eq. 6.41–6.57 | BM-06 (0,048 %) | `VALIDATED WITH RESERVATIONS` [F-06] |
| §6.3.3 LTB | `flambagem_lateral.py:80-227` | σ_crit, λ_rel, k_crit | EC5 Eq. 6.30/6.32/6.34 | BM-07 (0,046 %) | `VALIDATED WITH RESERVATIONS` [F-07] |
| §6.3.2 flexo-compressão | `flexao.py:100-148` | compressão linear ÷k_c | EC5 Eq. 6.23/6.24 | forma conferida | `VALIDATED` |
| §6.3.3 Eq. 6.35 | `flexao.py:144-148` | flexão ao quadrado | EC5 Eq. 6.35 | forma conferida | `VALIDATED` |
| §6.2.3 tração+flexão | `corda_beiral.py:98-99` | — | EC5 Eq. 6.17/6.18 | forma conferida | `VALIDATED` |
| Terças §6.1.6/§6.3.2 | `tercas.py:172-173,347-351` | — | EC5 Eq. 6.11/6.12/6.23/6.24 | forma conferida | `VALIDATED WITH RESERVATIONS` [F-21] |
| §9.2.5 contraventamento | `contraventamento.py:153-252` | N_d=(1−k_crit)M/h | EC5 Eq. 9.34–9.38, Tab. 9.2 | forma conferida | `VALIDATED` |
| §5.3.2 nocionais | `contraventamento_vertical.py:104-122` | φ=φ0αhαm | EN 1993-1-1 §5.3.2 | forma conferida | `VALIDATED` |
| §6.2.3 diagonal (tração) | `contraventamento_vertical.py:127-131` | **só A bruta** | EN 1993-1-1 §6.2.3(2) | N_u,Rd = 338 < N_pl,Rd = 374 kN | **`NOT VALIDATED` [F-11]** |
| Demanda transversal | `contraventamento_transversal.py:99-126` | só arrasto dos pilares | — | **BM-12** | **`ERROR` [F-01]** |
| §5.2.1 α_cr / 2.ª ordem | `estabilidade_global.py:278-286` | métrica de barra | EN 1993-1-1 §5.2.1(3) | **BM-13: 7,33 < 10** | **`ERROR` [F-02]** |
| ELS flechas | `deflection_els.py:42-101` | Timoshenko, I(x), A(x) | EC5 §2.2.3(2), Anexo B | BM-08 (exato) | `VALIDATED` |
| ELS fluência | `deflection_els.py:208-219` | u_G(1+k_def)+u_Q(1+ψ2k_def) | EC5 §2.3.2.2 Eq. 2.2 | BM-08 | `VALIDATED` |
| Limites Tab. 7.2 | `deflection_els.py:134-135` | L/300, L/250 | EC5 Tab. 7.2 (**intervalo**) | — | `VALIDATED WITH RESERVATIONS` [F-20] |
| Johansen §8.2.3 | `connections.py:191-255` | modo de outra configuração | EC5 Eq. 8.11 vs 8.13(k) | **BM-10** | **`ERROR` [F-14]** |
| f_h,α,k §8.5.1.1 | **ausente** | — | EC5 Eq. 8.31/8.33 | **BM-10: −41,3 %** | **`ERROR` [F-03]** |
| M_y,Rk | `connections.py:173-186` | — | EC5 Eq. 8.30 | 465 297 N·mm | `VALIDATED` |
| n_ef | `connections.py:609-635` | — | EC5 Eq. 8.34 | n_ef = n (layout 1×5) | `VALIDATED` |
| Distâncias Tab. 8.5 | `connections.py:650-666` | a1, a2, a3t ✔; **a4t ✘** | EC5 Tab. 8.5 | **BM-10: 72 vs 95,8 mm** | **`ERROR` [F-05]** |
| Ruptura de bloco | `connections.py:258+` | — | EC5 Anexo A | η = 0,0063 | `VALIDATED WITH RESERVATIONS` (sem benchmark independente) |
| Fendilhamento §8.1.4 + §8.7.2 | `connections.py` | — | EC5 Eq. 8.4 | η_nu=1,042 → 0,722 c/ reforço | `VALIDATED WITH RESERVATIONS` (idem) |
| Chapas EN 1993-1-8 | `chapas_aco.py`, `chapas_dim.py` | — | EN 1993-1-8 | η = 0,1147 | `VALIDATED WITH RESERVATIONS` (idem) |
| Ancoragem EN 1992-4 | `ancoragem.py` | cone, pull-out, aço | EN 1992-4:2018 | η = 0,704 | `VALIDATED WITH RESERVATIONS` (3 modos declarados pendentes) |
| Uplift / sucção | `succao_uplift.py` | 0,9G + 1,5W | EN 1990 Tab. A1.2(A) | R_v = −86,1 kN ✔ BM-03 | `VALIDATED` |
| Fadiga / deslizamento | `fadiga_ligacoes.py` | K_ser | EC5 §7.1, §8.1.5 | η_slip = 0,057 | `VALIDATED WITH RESERVATIONS` (idem) |
| Içamento | `icamento.py` | 2 pontos a 0,207L | EN 1991-1-6 | η = 0,042 | `VALIDATED WITH RESERVATIONS` (idem, + [F-07]) |
| Impacto de veículo | `impacto_veiculo.py` | 50/25 kN a 0,5 m | EN 1991-1-7 | η = 0,477 | `VALIDATED WITH RESERVATIONS` (idem) |
| Fixação da telha | `fixacao_telha.py` | c_p = ±2,0, classe A | NBR 6123 §7.2.6 | η = 0,679 | `NOT VERIFIABLE` [F-18] |
| Agregação do veredito | `report.py:83-140` | — | — | **ADV-D** | **`ERROR` [F-04]** |
| Cargas para a fundação | `cargas_fundacao.py` | varre combinações ✔ | — | tabela por base | `VALIDATED WITH RESERVATIONS` (herda [F-01]) |
| Ambiente de execução | `pyproject.toml:12` | — | — | 350 passed / **1 failed** | **`NOT VALIDATED` [F-19]** |
| Modelo FEM OpenSees | `opensees/` | validação cruzada | — | **não executado** (dependência ausente) | `NOT VERIFIABLE` |
| Fundação | — | — | EN 1997 | — | `NOT APPLICABLE` (declarado fora de escopo) |
| Resistência ao fogo | — | — | EN 1995-1-2 | — | `NOT APPLICABLE` (não avaliada) |

**Nenhuma célula vazia.**

---

## V — CORREÇÕES NECESSÁRIAS

### P0 — bloqueiam a emissão do memorial

1. **[F-13]** Transcrever literalmente o §7.2.2 da NBR 6123:2023 no docstring de
   `wind.py:492-496`, com o coeficiente correto. Se for 0,05: corrigir e
   **redimensionar todo o contraventamento** (n.º de painéis, Ø das diagonais, pilar de
   canto, n.º de chumbadores). Substituir
   `tests/test_auditoria_regressoes.py:110` por um teste que compare com o valor
   **citado da norma**, não com o valor do código.
2. **[F-01]** Implementar a componente horizontal da pressão de cobertura
   (`Σ c_i·q·A_água,i·sen α`) e somá-la a `demanda_transversal` e ao caminho de carga
   até a fundação. Reverificar o contraventamento transversal.
3. **[F-02]** Substituir `acr_arco` por um `α_cr` de sistema
   (`α_cr = K_lateral·h / ΣN_Ed`, por direção, a partir da rigidez dos painéis já
   calculada em `verifica_painel_vertical["C_h_kNpm"]`). Aplicar `k_II` onde
   `α_cr < 10`. Remover o retorno `1e99` de `alpha_cr_membro:120-124`.
4. **[F-03]** Passar `theta_deg` a `johansen_chapa_embutida` e aplicar
   `f_h,α,k = f_h,0,k/(k90 sen²α + cos²α)`, `k90 = 1,35 + 0,015d`.
5. **[F-14]** Substituir `1,15√(2M_y f_h d)` pelas Eq. (8.11)(f)(g)(h) e usar
   `t1 = (b − t_chapa)/2`.
6. **[F-04]** `extrair_eta_ok` deve **levantar** (ou devolver `ok=False`) para `eta`
   ausente/`None`/não numérico; `tabela_verificacoes` deve emitir linha
   `NÃO EXECUTADA / ✗` em vez de `continue`; `_imprimir_resumo_export` deve verificar
   que todas as chaves obrigatórias de `VERIFICACOES_EXPORT` estão presentes ou
   explicitamente marcadas "não aplicável".
7. **[F-18]** Anexar ao memorial a reprodução das Tab. 1, 2, 10 e 25 e do §7.2.2 da
   NBR 6123:**2023** efetivamente consultada, ou declarar a edição realmente usada.

### P1 — corrigir antes da próxima revisão

8. **[F-05]** `a4t = max((2 + 2·sen α)·d ; 3d)` em `connections.py:658`.
9. **[F-07]** `l_ef += 2h` quando a carga atua na borda comprimida (Tab. 6.1, nota).
10. **[F-11]** `N_t,Rd = min(N_pl,Rd ; 0,9 A_net f_u/γM2)` + dimensionar as ligações
    de extremidade das diagonais.
11. **[F-06]** Fazer os 13 módulos varrerem `combinacoes_ELU()` com
    `mat.com_duracao(comb.duracao)`, como já fazem `misula.py` e `pilares.py`.
12. **[F-09]** Remover os `np.maximum(·, 1e-18)` de `loads.py:241-242` e chamar
    `exigir_positivo`/`exigir_finito` no topo de `analisar_biarticulada`.
13. **[F-08]** Validar `V0, S1, S3, L, H1, h, dist_portico, l2` em
    `ParametrosVento.__post_init__` com `core.validacao`.
14. **[F-10]** `ELU_C3`/`ELU_C4` devem herdar `gov_s.duracao` / `gov_h.duracao`.
15. **[S-4]** Remover o fallback `w_char = 5.0 mm` de `estabilidade_global.py:295-296`.

### P2 — rastreabilidade e memorial

16. **[F-20]** Reclassificar `lim_w_inst`/`lim_w_net_fin` como `"PROJETO"` com
    justificativa da escolha na extremidade permissiva do intervalo da Tab. 7.2.
17. **[F-23]** Registar `drift_lim = H/300` e `k_s`/`k_f,2`/`k_f,3` em `NDP_SOURCE`.
18. **[F-12]** Corrigir ou remover a verificação de Hankinson no apoio.
19. **[F-19]** Fixar `numpy>=1.26,<2.0` **ou** adaptar o teste; a suíte deve passar
    100 % no ambiente declarado.
20. **[F-21]** Corrigir o rótulo `"ELU_C2 (1,35G+1,5W+1,05Q)"` em `tercas.py`.
21. **[F-22]** Recommitar `output/pipeline_console.txt` (a versão versionada estava
    obsoleta: rota Tab. 25, padrões `*_unif_*` já removidos, `η = 1,0000`).
22. **[F-24]** Declarar no memorial a coerência entre a rota "edificação fechada"
    (θ=90°) e a rota "cobertura isolada" (θ=0°).

### P3 — melhoria

23. **[F-25]** Desambiguar `theta` e `b`. **[F-16]** Remover ou consumir `G_05`.
    **[F-17]** Implementar `k_h`. **[F-26]** Incluir o termo axial em `δ10`.
24. Avaliar EN 1995-1-2 (fogo) ou declarar explicitamente fora de escopo.

---

## V-bis — TESTES DE REGRESSÃO NECESSÁRIOS

| Teste | Alvo | Critério |
|---|---|---|
| `test_atrito_theta0_nao_excede_bloqueio_total` | [F-13] | `F_fric ≤ q·1,2·A_frontal_cobertura` |
| `test_componente_horizontal_cobertura_entra_na_demanda_transversal` | [F-01] | `H_tr` cresce quando `c_esq ≠ c_dir` |
| `test_alpha_cr_sistema_usa_rigidez_do_contraventamento` | [F-02] | α_cr cai quando Ø da diagonal cai |
| `test_alpha_cr_nao_devolve_1e99` | [F-02] | `N_Ed = 0` não produz aprovação |
| `test_f_h_alpha_reduz_com_angulo` | [F-03] | `f_h(85°) < f_h(0°)` e razão = `k90` |
| `test_johansen_usa_eq_8_11_para_chapa_central` | [F-14] | bate com `(f)(g)(h)` calculadas à parte |
| `test_a4t_inclui_termo_sen_alpha` | [F-05] | `a4t(85°) = 95,8 mm` para d=24 |
| `test_eta_ausente_nao_e_aprovacao` | [F-04] | `extrair_eta_ok({})[1] is False` |
| `test_resumo_cobre_todas_as_verificacoes_esperadas` | [F-04] | toda chave de `VERIFICACOES_EXPORT` aparece ou é "N/A" |
| `test_envelope_sobre_combinacoes_em_cada_check` | [F-06] | η do check ≥ η de qualquer combinação isolada |
| `test_l_ef_ltb_soma_2h_para_carga_no_topo` | [F-07] | `l_ef = 0,9·l1 + 2h` |
| `test_analisar_biarticulada_recusa_h0_zero` | [F-09] | levanta `DominioInvalidoError` |
| `test_parametros_vento_recusa_V0_negativo_e_nan` | [F-08] | levanta |
| `test_suite_passa_no_ambiente_declarado` | [F-19] | 0 failed |

---

## W — VEREDITO FINAL

# `NOT VALIDATED`

**Fundamento.** Existem achados `NON-CONSERVATIVE` de severidade ALTA em aberto que
afetam diretamente o dimensionamento entregue:

- **[F-01]** uma ação de vento real, **1,51× maior que a ação incluída**, está omitida
  do caminho de carga transversal;
- **[F-02]** o critério de dispensa de análise de 2.ª ordem é avaliado sobre uma
  grandeza que não mede estabilidade de sistema, e o α_cr real na direção transversal
  (**7,33**) **não satisfaz** o limiar 10 que o próprio projeto declara;
- **[F-03]** a resistência ao embutimento das cavilhas ignora um ângulo força-fibras de
  85° (**−41,3 % em f_h**), levando η_L1 de 0,748 para **0,798** — acima do alvo de
  0,75 que o projeto impõe aos modos frágeis;
- **[F-04]** a agregação que produz o carimbo `APROVADO` devolve **"aprovado" para
  verificação vazia, nula ou textual** e **apaga silenciosamente** do veredito qualquer
  verificação sem `η`.

Composto [F-01] com [F-02], o contraventamento transversal (η reportado 0,807)
ultrapassa 1,0. **O `Status = APROVADO` do pipeline não é sustentável.**

Acresce que a ação que **dimensiona toda a estrutura metálica** ([F-13]) é
**10,1× superior ao arrasto que a cobertura teria se bloqueasse integralmente o
escoamento** e tem por única fonte um documento interno cujo teste de regressão apenas
reafirma o próprio número — `INVALID BENCHMARK — SELF-REFERENTIAL`. Enquanto essa
cláusula não for reproduzida da norma, o dimensionamento metálico **não tem base
normativa verificável**, em nenhuma das duas direções (excesso ou falta).

**Domínio efetivamente validado** (para registo, caso as correções sejam feitas): o
núcleo de resistência dos materiais e de aplicação da EN 1990 e da EN 1995-1-1 à viga
principal — peso próprio, combinações, análise biarticulada, §6.1.5, §6.1.7, §6.3.2,
§6.3.3, §6.4.2, §6.4.3, §2.2.3 e §2.3.2.2 — está **correto e reproduzido por benchmark
independente com erro ≤ 0,05 %**, dentro dos limites `20 m ≤ L ≤ 21 m`,
`GL24h`, `CS3`, `α = 10°`, `H = 0` (Opção B), rota NBR 6123 §7.2.1 de edificação
fechada. Fora desse domínio — nomeadamente na rota Tab. 25 — [F-06] passa a ser ativo.

---

## X — ACHADOS NON-CONSERVATIVE (resumo cruzado)

> Esta seção existe para que um revisor humano não precise ler o relatório inteiro
> para saber onde o software pode estar aprovando algo inseguro.

| # | Sev. | Achado | Local | Efeito medido | Confiança |
|---|---|---|---|---|---|
| **F-01** ✅ | **ALTA** | ~~Componente horizontal da pressão de cobertura omitida da demanda transversal~~ **CORRIGIDO (Seção Z)** | `contraventamento_transversal.py:99-126` | **57,8 kN omitidos vs 38,3 kN incluídos (1,51×)**; `H_tr` ×2,19 | `CONFIRMED` |
| **F-02** ✅ | **ALTA** | ~~`α_cr` reportado é métrica de barra, não de sistema; sway declarado por booleano; `1e99` para `N_Ed=0`~~ **CORRIGIDO (Seção Z)** | `estabilidade_global.py:278-286, 120-124, 248` | α_cr real transversal **7,33 < 10**; k_II = 1,158 não aplicado | `CONFIRMED` |
| **F-03** ✅ | **ALTA** | ~~`f_h,α,k` (EC5 Eq. 8.31/8.33) nunca aplicado; α = 85°~~ **CORRIGIDO (Seção Z)** | `connections.py:154-170, 220, 792` | **f_h −41,3 %**; η_L1 0,748 → **0,798** (> alvo 0,75) | `CONFIRMED` |
| **F-04** ✅ | **ALTA** | ~~η ausente/`None`/string ⇒ `(0.0, True)`; verificação sem `eta` some do veredito~~ **CORRIGIDO (Seção Z)** | `report.py:23-30, 83-94, 108-109` | `APROVADO` sobre subconjunto não anunciado | `CONFIRMED` |
| **F-05** ✅ | MÉDIA | ~~`a4,t` sem o termo `(2+2 sen α)d`~~ **CORRIGIDO (Seção Z)** | `connections.py:658` | 72,0 mm contra 95,8 mm (**−24,9 %**), modo frágil | `CONFIRMED` |
| **F-06** ✅ | MÉDIA | ~~Envelope por procuração: 13 de 15 módulos leem só a governante por \|M\|~~ **CORRIGIDO (Seção Z.14)** | `loads.py:797-808` + `main.py:517` | **−4,2 %** no §6.4.3 na rota Tab. 25 | `CONFIRMED` |
| **F-07** ✅ | MÉDIA | ~~`l_ef` da LTB sem o `+2h` de carga na borda comprimida~~ **CORRIGIDO (Seção Z.16)** | `flambagem_lateral.py:36-75` | `l_ef` **3,4× menor**; λ_rel 0,446 → 0,827 | `CONFIRMED` |
| **F-08** | MÉDIA | `ParametrosVento` não valida V0/S1/S3/h/L/H1/ℓ2 | `wind.py:94-104` | `V0 = −45` → `q` positivo "válido"; `V0 = NaN` → `q = NaN` | `CONFIRMED` |
| **F-09** | MÉDIA | Clamp `1e-18` torna calculável seção nula; NaN propaga | `loads.py:241-242` | `h0 = 0` ⇒ `H = 0` sem erro | `CONFIRMED` |
| **F-10** | MÉDIA | `ELU_C3`/`C4` com duração fixada em "curta" | `loads.py:647, 658` | k_mod 0,70 vs 0,65 (**f_d +7,7 %**) se `gov_h = ELU_Q` | `PROBABLE` (latente na Opção B) |
| **F-11** ✅ | MÉDIA | ~~Diagonais sem seção líquida~~ **CORRIGIDO (Z.17)**; ligações de extremidade continuam por dimensionar, agora **declaradas** | `contraventamento_vertical.py:127-131` | `N_u,Rd = 338 kN < N_pl,Rd = 374 kN` (Ø45 roscada) | `CONFIRMED` (omissão) |
| **F-12** | LOW | Hankinson no apoio com ângulo e área errados | `apoio.py:90-92` | `f_c,α,d = 9,91 MPa` ≈ `f_c,0,d`; não governa | `CONFIRMED` |
| **F-20** | MÉDIA | Limites da Tab. 7.2 no extremo permissivo, rotulados "EN-recomendado" | `normativo.py:115-116` | ℓ/300 vs ℓ/500; ℓ/250 vs ℓ/350 | `CONFIRMED` |
| **F-25** | LOW | `theta` com 3 significados; `b` com 2 | `wind.py`, `loads.py` | sem erro numérico hoje | `CONFIRMED` |
| **S-4** | LOW | `except` ⇒ `w_char = 5,0 mm` | `estabilidade_global.py:295-296` | flecha ELU inventada | `CONFIRMED` |
| **S-7** | LOW | `or 0.0` sobre `None` | `main.py:376` | η = 0 impresso | `CONFIRMED` |

**Achados CONSERVATIVE de relato obrigatório** (não põem em risco, mas distorcem o
dimensionamento ou a rastreabilidade): **F-13** (ALTA — atrito 10,1× o limite físico),
**F-14** (MÉDIA — modo de Johansen de outra configuração), **F-15** (MÉDIA — `k_c,90`
e `ℓ_ef` não explorados), **F-16**/**F-17** (LOW — `G_05`, `k_h`).

---

## Y — AS 20 PERGUNTAS DE MISSÃO RESPONDIDAS

| # | Pergunta | Resposta (1 linha) | Confiança | Achado |
|---|---|---|---|---|
| 1 | O modelo mecânico corresponde à estrutura real? | Viga de duplo-bisel biarticulada com H=0 (Opção B) é coerente e conservadora para a viga, mas o sistema global é tratado por booleanos em vez de rigidez. | `CONFIRMED` | F-02 |
| 2 | As equações implementadas são as da norma? | Sim para EC5 §6.1–§6.4, §2.2/§2.3 e EN 1990; **não** para EC5 §8.2.3/§8.5.1.1 e Tab. 8.5. | `CONFIRMED` | F-03, F-05, F-14 |
| 3 | A implementação Python reproduz as equações? | Sim — 14 grandezas reconstruídas fora do repositório batem com Δ ≤ 0,05 %. | `CONFIRMED` | Seção Q |
| 4 | As unidades são coerentes? | Sim; nenhum erro dimensional. O contrato SI do `.cursorrules` é violado (kN/kN·m), mas de forma consistente e com unidade nos nomes. | `CONFIRMED` | Seção F |
| 5 | As propriedades de MLC/GL estão corretas? | Sim — EN 14080:2013 Tab. 5, com migração desde a EN 1194:1999 documentada item a item. | `PROBABLE` | Seção G |
| 6 | k_mod está correto? | Sim — Tab. 3.1 completa; vento classificado como "curta" (conservador face a "instantânea"), declarado. | `CONFIRMED` | Seção E |
| 7 | γM está correto? | Sim — 1,25 (peças) e 1,30 (ligações), EC5 Tab. 2.3, declarados como NDP. | `CONFIRMED` | Seção E |
| 8 | k_def está correto? | Sim — 2,00 para CS3, Tab. 3.2. | `CONFIRMED` | Seção E |
| 9 | A Classe de Serviço é adequada e consistente? | Sim — CS3 em todo o pipeline, coerente com UC3.1 (EN 335) e adesivo Tipo I declarados. | `CONFIRMED` | `main.py:113-136` |
| 10 | A Load-Duration Class é escolhida corretamente? | Não integralmente: `ELU_C3`/`C4` fixam "curta" e **um único material** serve todas as verificações. | `CONFIRMED` | F-10, F-06 |
| 11 | O software escolhe automaticamente o caso mais favorável? | **Sim, em efeito**: a governante é escolhida por `max\|M\|` e impõe o k_mod dela a verificações cujo governante é outro. | `CONFIRMED` | F-06 |
| 12 | A transformação característico→cálculo está correta? | Sim — `f_d = k_mod·f_k/γM` em todas as propriedades; nenhum fator duplicado, invertido ou fora do lugar. | `CONFIRMED` | `materials.py:189-200` |
| 13 | As combinações EN 1990 estão corretas? | Sim — Eq. 6.10, Tab. A1.1/A1.2; gerador recriado de forma independente com Δ ≤ 0,001 %. | `CONFIRMED` | BM-03 |
| 14 | O vento segue a NBR 6123? | S2/Vk/q sim (Δ = 0,000 %); os **coeficientes tabelados e o §7.2.2 não são verificáveis** e o atrito é fisicamente impossível. | `CONFIRMED` (S2/q) / `NOT VERIFIABLE` (tabelas) | F-13, F-18 |
| 15 | A interface vento→combinação está correta? | Sim — só valores característicos atravessam; nenhum γf da NBR aplicado antes do γQ da EN 1990. | `CONFIRMED` | Seção I |
| 16 | O ELU está completo? | Não — falta a componente horizontal do vento e o `f_h,α,k`; o α_cr não é de sistema. | `CONFIRMED` | F-01, F-02, F-03 |
| 17 | O ELS está correto? | Sim — flexão + cisalhamento de Timoshenko com I(x), A(x), `E_mean`/`G_mean`, Eq. (2.2); benchmark exato. | `CONFIRMED` | BM-08 |
| 18 | A estabilidade está corretamente tratada? | LTB local sim (com a reserva do `+2h`); estabilidade **global**, não. | `CONFIRMED` | F-02, F-07 |
| 19 | Há verificações de MLC ausentes? | `k_h`/`k_sys` (conservador); §6.4.3 sob uplift tratado por `abs()` (conservador); fogo (EN 1995-1-2) não avaliado. | `CONFIRMED` | Seção T |
| 20 | **O software pode aprovar uma estrutura insegura?** | **SIM.** Por omissão de ação ([F-01]), por gate de estabilidade que sempre passa ([F-02]), por resistência de ligação sobrestimada ([F-03]) e por agregação que trata resultado ausente como aprovação ([F-04]). | `CONFIRMED` | F-01…F-04 |

---

*Auditoria adversarial independente conduzida sobre o commit `1df424c`.
Todos os benchmarks foram executados; nenhum reutiliza código do repositório auditado
para o cálculo de referência. Onde a fonte normativa não pôde ser confirmada no
material fornecido, o status é `NOT VERIFIABLE — REQUIRES EXTERNAL NORMATIVE SOURCE`
e nenhum valor foi preenchido por analogia.*


---

## Z — CORREÇÕES APLICADAS (F-01 e F-02)

Sequência seguida (§31 do mandato): identificar → localizar → reproduzir →
demonstrar → fundamentar → classificar → propor → **criar teste** → alterar código.
Os 22 testes novos foram escritos **antes** da alteração e verificados a falhar.

### Z.1 — F-01 · componente horizontal da pressão de vento na cobertura

**Formulação adotada** (`core/loads.py`, `componente_horizontal_cobertura`):

    H_cob = (w_esq − w_dir) · (L/2) · tan α        [kN por pórtico, de cálculo]

com `w` as cargas lineares de vento de cada meia-água (kN/m de projeção
horizontal). Deriva de `F_⊥ = c·q·A_água` com `A_água = (L/2)/cos α · L_t`: a
componente vertical `F_⊥·cos α` é exatamente a carga que a análise já recebia; a
horizontal `F_⊥·sen α` aponta em sentidos opostos nas duas águas e só se cancela
se `w_esq = w_dir`. **As parcelas gravíticas (G, Q) não entram** — são verticais,
não normais à superfície — pelo que a função recebe as cargas de vento, não
`q_esq/q_dir`.

| Onde | Alteração |
|---|---|
| `core/loads.py` | nova `componente_horizontal_cobertura()`; campo `Combinacao.H_cob_kN`; `_comb(w_esq_d, w_dir_d)`; aliases C2/C3/C4 herdam; novos `combinacao_H_cobertura_max()` e `H_cobertura_max_ELU()` |
| `checks/elu/contraventamento_transversal.py` | `demanda_transversal`: `H_tr = H_vento_topo + H_cob + H_imp`, com `H_cob = H_cobertura_max_ELU() × n_frames` (vai **inteira** ao nível da cobertura — a viga apoia nas rótulas de topo) |
| `main.py` | impressão discriminada da parcela e da combinação que a governa |

**Verificação independente (BM-12, reexecutada):** a reconstrução a partir de
`c_pe`, `q` e da área real da água dá `H_cob = 57,78302 kN` contra
`57,78302 kN` do software — **0,000 %**.

### Z.2 — F-02 · α_cr de sistema

**Formulação adotada** (`checks/elu/estabilidade_global.py`, `alpha_cr_sistema`),
EN 1993-1-1 §5.2.1(4)B Eq. (5.2) com `δ_H,Ed = H_Ed/K`:

    α_cr = K_lat · h / V_Ed          (independente do nível de carga horizontal)

Regimes: `α_cr ≥ 10` → 1.ª ordem; `3 ≤ α_cr < 10` → amplificar por
`k_II = 1/(1−1/α_cr)` (§5.2.2(5)B); `α_cr < 3` → 2.ª ordem rigorosa (recusado);
`K ≤ 0` → mecanismo.

| Onde | Alteração |
|---|---|
| `estabilidade_global.py` | nova `alpha_cr_sistema()`; `alpha_cr` passa a ser **o de sistema** (mínimo entre direções), com `direcao_critica`; o valor do arco fica como `alpha_cr_arco` **informativo**; `alpha_cr_membro` deixa de devolver `1e99` (agora `math.inf` + `indeterminado=True`); novo método `alpha_cr_nao_determinado` — **sem rigidez declarada não há dispensa de 2.ª ordem** |
| `contraventamento_vertical.py` / `_transversal.py` | expõem `C_h_kNpm` e `K_lat_kNpm`; aceitam `V_Ed_total_kN` e resolvem um **ponto fixo** demanda ↔ rigidez ↔ `k_II` (mais demanda → diagonal mais grossa → mais rigidez → α_cr maior → k_II menor); `ok` passa a exigir `regime ∉ {2a_ordem_rigorosa, mecanismo}` |
| `main.py` | calcula `V_Ed_total_kN = 2·n_pórticos·R_v·n_frames` e passa-o aos três módulos; imprime α_cr por direção e `k_II` bruto vs **aplicado** |

**Verificação independente (BM-13, reexecutada):** `α_cr = K·h/ΣN_Ed` reproduz o
valor do software nas duas direções.

### Z.3 — Acoplamento entre os dois achados (resultado não previsto)

O `α_cr,transv = 7,33` medido na auditoria era consequência de **F-01**: a
diagonal Ø16 tinha sido dimensionada para uma ação incompleta. Corrigida a ação,
a demanda sobe 2,19×, a diagonal passa a Ø24, `K` sobe de 3 756 para
8 450 kN/m e **α_cr,transv = 16,5 ≥ 10** — a amplificação deixa de ser
necessária. O defeito de F-02 continuava real (o portão media a grandeza errada
e passava sempre); apenas o **sintoma** numérico desapareceu junto com a causa
que era F-01. Um teste dedicado
(`test_correcao_de_F01_eleva_o_alpha_cr_transversal`) fixa esse acoplamento.

### Z.4 — Efeito no dimensionamento

| Grandeza | Antes | Depois | Δ |
|---|---|---|---|
| `H_tr` (demanda transversal) | 48,4 kN | **106,2 kN** | ×2,19 |
| Diagonal do frontão | Ø16 | **Ø24** | +125 % de área |
| `K_lat,transv` | 3 756 kN/m | **8 450 kN/m** | ×2,25 |
| `α_cr,transv` (gate) | 2 817 (falso) | **16,5** (real) | — |
| `R_frontão` → fundação | 24,2 kN | **53,1 kN** | ×2,19 |
| `N_corda` do beiral | 6,9 kN | **15,1 kN** | ×2,19 |
| Download no pilar de canto | 287,4 kN | **322,5 kN** | ×1,12 |
| η pilar de canto | 0,5515 | **0,5977** | +8 % |
| Ancoragem do canto (tração) | 371,3 kN | **406,4 kN** | ×1,09 |
| η sucção/uplift | 0,7735 | **0,8467** | +9 % |
| η ancoragem do canto | 0,7039 | **0,7706** | +9 % |
| η estabilidade global | 0,2205 | **0,6062** | passou a medir algo |
| **η máximo do pipeline** | 0,8930 | **0,8930** | inalterado (governa o CV longitudinal) |

Pipeline: `EXIT 0`, 38 verificações, `todas OK = True`, `Status = APROVADO` —
agora por razões efetivamente verificadas nesta direção.

### Z.5 — Estado da suíte e dos benchmarks

- `pytest -q` → **372 passed, 1 failed**. A única falha é a pré-existente
  **[F-19]** (`np.trapz` sob NumPy 2.4.6, ambiente declarado `numpy>=1.26`),
  não relacionada com estas correções.
- **22 testes novos**: `tests/test_f01_vento_horizontal_cobertura.py` (7) e
  `tests/test_f02_alpha_cr_sistema.py` (15).
- **4 testes pré-existentes atualizados** por codificarem o comportamento
  defeituoso: `test_contraventamento_transversal::test_demanda_inclui_vento_e_nocional`
  (passa a exigir a parcela da cobertura) e três em `test_estabilidade_global.py`
  / `test_aud006_modelo_de_apoio.py` (passam a declarar a rigidez lateral, e
  distinguem `alpha_cr_arco` de `alpha_cr`).
- **Os 14 benchmarks independentes continuam a reproduzir com Δ ≤ 0,05 %** — as
  correções não perturbaram o núcleo validado (BM-01 a BM-09 inalterados).

### Z.6 — Efeito no veredito

O veredito da Seção W **mantém-se `NOT VALIDATED`**: continuam em aberto
**F-03** (`f_h,α,k` nunca aplicado — η_L1 real 0,798 contra 0,748 reportado,
acima do alvo 0,75 dos modos frágeis) e **F-04** (a agregação devolve "aprovado"
para resultado vazio, nulo ou textual e apaga do veredito verificações sem `η`),
além de **F-13** (o atrito de θ=0°, 10,1× o limite físico, que dimensiona toda a
estrutura metálica e cujo valor normativo continua por confirmar) e dos achados
MÉDIA/LOW das Seções V e X.


---

## Z.7 — F-04 · agregação do veredito

**Princípio adotado**, o mesmo de `core/validacao.py`: *falhar alto, nunca
compensar*. Um resultado ausente, nulo ou não numérico **não é η = 0**.

| Onde | Alteração |
|---|---|
| `report.py` | nova `eta_numerico()` — `None`, texto, `bool`, `NaN`, `±inf` devolvem `None`, nunca 0,0; `extrair_eta_ok` devolve `(nan, False)` para indeterminado |
| `report.py` | `tabela_verificacoes` percorre `VERIFICACOES_EXPORT` **por inteiro**: cada chave produz sempre uma linha com `status` explícito — `OK` · `REPROVADO` · `SEM η` · `NÃO EXECUTADA` · `NÃO APLICÁVEL` |
| `report.py` | exclusões deliberadas passam a exigir **declaração** (`nao_aplicaveis`); a omissão nunca é aprovação |
| `report.py` | nova `estatisticas_resumo()` — **fonte única** do carimbo (a lógica estava duplicada em `main` e em `gerar_relatorio`): `η_max` só sobre valores numéricos (um `NaN` seria engolido por `max()`), e qualquer pendente bloqueia o `APROVADO` |
| `main.py` | `_print_eta` deixa de fazer `or 0.0`; `meta["nao_aplicaveis"]` declara o tirante de base na Opção B; o rodapé **nomeia** as verificações sem resultado |
| `report.py` | LaTeX imprime `--` e o estado entre parênteses; Excel ganha coluna `Estado` e célula vazia (não 0) para η indeterminado |

**Efeito visível.** As duas verificações que antes **desapareciam em silêncio**
passam a constar do resumo, do Excel e do memorial:

```
Tirante de base        EN 1993-1-1 §6.2.3         —  ✓  [NÃO APLICÁVEL]
Robustez tirante piso  EN 1991-1-7+335+1993-1-2    —  ✓  [NÃO APLICÁVEL]
...
N.º verif. = 40 (38 executadas, 2 não aplicáveis)  |  todas OK = True
```

**Verificação por injeção (executada):** forçando um módulo a devolver um dict
parcial (`{"tau_d_MPa": 0.69}` sem `eta`), a linha aparece como `SEM η`, o nome
é listado em `⚠ SEM RESULTADO` e o `status` global passa a `REPROVADO` — antes,
a verificação simplesmente desaparecia e o pipeline dizia `APROVADO`.

---

## Z.8 — F-03 · `f_h,α,k` (EC5 §8.5.1.1)

**Formulação adotada** (`connections/connections.py`):

    f_h,α,k = f_h,0,k / (k90·sen²α + cos²α)        Eq. (8.31)
    k90     = 1,35 + 0,015·d   coníferas           Eq. (8.33)

`johansen_chapa_embutida` recebe agora `theta_deg` e `material`; os dois locais
de dimensionamento (L1 e L1c) passam o ângulo **que já calculavam** para as
distâncias mínimas. A memória de cálculo passa a publicar `f_h,α,k` (usado),
`f_h,0,k` (paralelo), `k_90` e `alpha_fibras_deg`, para que o memorial seja
reconstruível. O default `theta_deg = 0` preserva o caso paralelo.

| Grandeza | Antes | Depois |
|---|---|---|
| α (força–fibras) na base | calculado, **não usado** | **84,96°**, usado |
| `k90` (d = 24 mm) | — | **1,710** |
| `f_h` | 23,993 MPa (Eq. 8.32) | **14,076 MPa** (Eq. 8.31) — **−41,3 %** |
| `F_v,Rk`/plano | 26,62 kN | **20,39 kN** |
| Pinos na L1/L1c | 5 | **7** |
| `R` do grupo | 133,1 kN | **142,7 kN** |
| η_L1 | 0,7483 | **0,6979** |

A ligação volta a ter margem folgada face ao alvo de 0,75 dos modos frágeis —
mas por **adição de pinos**, não por otimismo na resistência.

### Z.8.1 — Aviso: F-14 passou a ser a distorção binding

Com F-03 corrigido, o erro que resta em `johansen_chapa_embutida` deixou de ser
compensado. O modo `1,15·√(2·M_y·f_h·d)` é a **Eq. (8.13)(k)** — chapas finas
como elementos **externos** em corte duplo — aplicada a uma **chapa central
espessa**, e `t1 = b/2` ignora a espessura da chapa. Com o `f_h,α,k` já correto:

| Formulação | F_v,Rk/plano | Pinos | η_L1 |
|---|---|---|---|
| Atual (F-03 corrigido, **F-14 por corrigir**) | 20,39 kN | 7 | 0,6979 |
| **EC5 Eq. (8.11)(f)(g)(h) com `t1 = (b−t_chapa)/2`** | **24,97 kN** | 6 | 0,6649 |

O software está agora **18,3 % abaixo** da resistência normativa correta nesta
ligação — um pino a mais por ligação, em 23 ligações. Antes da correção de F-03
os dois erros cancelavam-se quase exatamente (26,62 contra 24,97), o que é
precisamente o que a Seção P advertia: *o cancelamento é fortuito e não
sobrevive a uma mudança de diâmetro, de largura ou — como aqui — à correção do
outro erro*. **F-14 deve ser corrigido em seguida** (P1).

---

## Z.9 — Estado consolidado após as quatro correções

- `pytest -q` → **403 passed, 1 failed** (a falha continua a ser a pré-existente
  **F-19**, `np.trapz` sob NumPy 2.4.6).
- **43 testes novos**: F-01 (7), F-02 (15), F-04 (21) — mais 9 em F-03, total 52
  com os de F-03.
- **5 testes pré-existentes atualizados** por codificarem o comportamento
  defeituoso (o de `test_memoria_L1::test_fh0k_formula` passou a apontar para
  `f_h_paralelo_MPa` e ganhou um par que verifica `f_h,α,k`).
- **Os 14 benchmarks independentes continuam a reproduzir com Δ ≤ 0,05 %.**
- Pipeline: `EXIT 0`, 40 linhas (38 executadas + 2 declaradas não aplicáveis),
  `η_máximo = 0,8930`, `Status = APROVADO`.

### Z.9.1 — Veredito

O veredito da Seção W passa de `NOT VALIDATED` para
**`CONDITIONALLY VALIDATED`**, com o seguinte **domínio exato de validade**:

> Válido para `L = 20,25 m`, `GL24h`, `CS3`, `α = 10°`, Opção B (`H = 0`), rota
> NBR 6123 §7.2.1 de edificação fechada, **e condicionado a**:
> 1. **confirmação documental do §7.2.2 da NBR 6123:2023** ([F-13]) — enquanto o
>    coeficiente de atrito não for reproduzido da norma, todo o dimensionamento
>    metálico (4 painéis, Ø45, pilar de canto, 6 chumbadores) assenta numa ação
>    que excede em 10,1× o arrasto de bloqueio total da cobertura;
> 2. **correção de [F-14]** — a resistência da L1/L1c está 18,3 % abaixo da
>    Eq. (8.11) do EC5 (conservador, mas errado e agora não compensado);
> 3. **correção dos achados MÉDIA da Seção V-P1** — em especial [F-05] (`a4,t`),
>    [F-06] (envelope por procuração), [F-07] (`l_ef + 2h`) e [F-11] (seção
>    líquida das diagonais);
> 4. **anexação ao memorial** das tabelas da NBR 6123:2023 efetivamente
>    consultadas ([F-18]).
>
> Nenhum achado `NON-CONSERVATIVE` de severidade ALTA permanece em aberto.


---

## Z.10 — F-05 · distância à borda carregada `a4,t`

**Formulação adotada** (`connections/connections.py`, `distancias_minimas`),
EC5 §8.6 **Tabela 8.5** (cavilhas):

    a4,t = max( (2 + 2·|sen α|)·d ; 3d )

Usa-se `|sen α|` — e não `sen α` — porque `verificar_geometria_grupo` aplica
`a4,t` às **duas** bordas (a carregada e a não carregada). É o envelope
conservador: qualquer que seja o quadrante de α, a borda efetivamente carregada
fica coberta.

**Não confundir com a Tabela 8.4 (parafusos).** Em cavilhas, `a3,c = 3d` em todo
o intervalo 90°–270°; é nos parafusos que `a3,c` ganha o fator `|sen α|`. O
código já tinha `a3,c = 3d` — correto — e um teste dedicado
(`test_a3c_de_cavilha_e_3d_em_todo_o_intervalo`) fixa a distinção para que a
correção de `a4,t` não arraste `a3,c` numa revisão futura.

Corrigida de passagem a referência normativa do docstring: era «§8.3.1.2
Tabela 8.2», passa a «§8.6 Tabela 8.5» — que é a tabela cujos valores estavam,
de facto, implementados.

| Grandeza (d = 24 mm, α = 84,96°) | Antes | Depois |
|---|---|---|
| `a4,t` | 72,0 mm (`3d`) | **95,8 mm** (+33,1 %) |
| `a1`, `a2`, `a3,t`, `a3,c`, `a4,c` | — | **inalterados** |
| `h_ocupado` (1×7 pinos) | 576,0 mm | **623,6 mm** (h0 = 1 000 mm) |
| Altura da chapa embutida L1/L1c | 720 mm | **815 mm** |
| η_L1 / η_fendilhamento / η chapa | 0,6979 / 0,7222 / 0,0819 | **inalterados** |

**É uma correção de detalhamento, não de capacidade** — como a Seção P já
antecipava: o layout de 7 cavilhas numa fila continua a caber em `h0 = 1,00 m`
com folga. O que muda é o desenho de fabricação: a chapa embutida cresce 95 mm
em altura, e as cavilhas afastam-se 23,8 mm de cada borda. Dado que o
fendilhamento (§8.1.4) é o modo frágil que este projeto já precisa de reforçar
(η_nu = 1,042 → 0,722 com 8×Ø10), a distância à borda carregada é exatamente o
parâmetro que não podia continuar 25 % abaixo do exigido.

Pipeline: `EXIT 0`, `η_máximo = 0,8930`, `Status = APROVADO`.
Suíte: **448 passed, 1 failed** (a pré-existente F-19). **45 testes novos**
(`tests/test_f05_distancia_borda_carregada.py`), nenhum teste pré-existente
precisou de alteração.


---

## Z.11 — F-13 · atrito longitudinal e redimensionamento do contraventamento

### Z.11.1 — O que NÃO foi feito, e porquê

**O valor 0,50 não foi alterado.** Trocar um número sem fonte por outro número
sem fonte é o mesmo defeito com outro sinal — e é exatamente o que a §33 do
mandato proíbe. A hipótese de que o coeficiente correto seja 0,05 continua
`PROBABLE`, não `CONFIRMED`. **A confirmação do §7.2.2 da NBR 6123:2023 continua
a ser a única ação P0 em aberto deste relatório.**

O que se fez foi tornar impossível ignorá-lo, e dimensionar do lado conservador
enquanto a dúvida existir.

### Z.11.2 — O que foi feito

| Onde | Alteração |
|---|---|
| `wind.py` | `COEF_ATRITO_COBERTURA_ISOLADA` deixa de ser constante anónima: ganha `CLAUSULA_ATRITO` e `ORIGEM_ATRITO` (`"ABNT — A CONFIRMAR"`) e um bloco de comentário com toda a evidência contra 0,50 |
| `wind.py` | `ParametrosVento.coef_atrito_cobertura` — o coeficiente passa a **entrada de projeto**, validada (não negativa), sobreponível numa linha |
| `wind.py` | nova `arrasto_bloqueio_silhueta()` — **teto físico independente de norma**: nenhuma força numa direção pode exceder o arrasto de um corpo sólido totalmente bloqueante de igual silhueta (`F = q·c_d·B_cob·H_max`, `c_d = 1,2`) |
| `wind.py` | `forca_vento_paralelo_cumeeira` devolve `F_bloqueio_kN`, `razao_bloqueio`, `plausivel` e `aviso_plausibilidade`. **O valor NÃO é limitado ao teto** — limitar seria compensar um dado duvidoso com um número inventado; o que se faz é tornar a incoerência visível |
| `normativo.py` | nova origem `"ABNT-A-CONFIRMAR"` e `parametros_a_confirmar()`; o coeficiente entra em `NDP_SOURCE` — não se confunde com NDP nem com escolha de projeto |
| `main.py` | o coeficiente é declarado em `VENTO_PARAMS` com as duas leituras e as suas consequências; o aviso é impresso em cada execução |
| `main.py` | o rodapé do resumo carimba **`⚠ APROVAÇÃO CONDICIONAL (F-13)`** quando o status é APROVADO mas a ação é implausível |

```
F-13 — FORÇA LONGITUDINAL FISICAMENTE IMPOSSÍVEL: F_total = 837.3 kN é 2.35× o
arrasto de bloqueio TOTAL da silhueta (356.0 kN, 40.5×8.79 m, c_d=1.2), e a
estrutura é ABERTA nas quatro faces. […] Confirmar a cláusula antes de emitir o
memorial: todo o contraventamento é dimensionado por esta ação.
```

Note-se que o teto adotado (silhueta cheia, 356,0 kN) é **mais permissivo** que
o da Seção H (bloqueio só da cobertura, 76,7 kN): escolheu-se de propósito o
majorante mais generoso, para que a violação seja indiscutível.

### Z.11.3 — Terceira varredura do contraventamento longitudinal

O **pipeline real** foi corrido para `n = 2…16` painéis com a diagonal
auto-dimensionada (η ≤ 0,90), nas duas leituras do coeficiente.

**C = 0,50 (adotado, conservador):**

| n | Ø | V_painel | download | η_canto | N_anc | η_anc | η_max | aço | |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 64 | 423,7 kN | 580,4 kN | 0,936 | 664,3 | 1,260 | **1,3840** | 915 kg | **REPROVA** |
| 4 | 45 | 211,9 kN | 322,5 kN | 0,598 | 406,4 | 0,771 | 0,8930 | 905 kg | anterior |
| 6 | 39 | 141,2 kN | 236,6 kN | 0,485 | 320,5 | 0,608 | 0,7926 | 1019 kg | |
| **8** | **33** | **105,9 kN** | **193,6 kN** | **0,428** | **277,5** | **0,526** | **0,8303** | **973 kg** | **← adotado** |
| 10 | 30 | 84,7 kN | 167,8 kN | 0,394 | 251,7 | 0,477 | 0,8037 | 1005 kg | |
| 16 | 24 | 53,0 kN | 129,1 kN | 0,344 | 213,0 | 0,404 | 0,7902 | 1029 kg | |

**C = 0,05 (hipótese):** tudo passa desde n = 2 (Ø27, η_max 0,868); a n = 8 a
diagonal cai a Ø16 e o aço total a ~230 kg — **cinco vezes menos**. É a medida
do que está em jogo na confirmação da cláusula.

**Constatação que inverte a decisão anterior: o peso de aço é praticamente
independente de n** (900–1030 kg de n=2 a n=16). Mais painéis de barra mais fina
custam o mesmo aço. O que `n` compra é margem no **caminho de carga** — download
no montante, ancoragem, bloco de fundação. O que custa são **baías**.

**Baías disponíveis:** `L_comp/dist_pórtico = 46,0/5,75 = 8` por alinhamento; as
duas fachadas longitudinais dão **16 baías candidatas** (o alinhamento central
fica no interior do estacionamento e não é usado). A nota da varredura anterior
contava baías livres sobre um universo de 8 — coerente com painéis numa só
fachada. Distribuindo-os pelas duas, **n = 8 deixa 8 baías livres (4 por
fachada)**, o dobro da configuração anterior.

### Z.11.4 — Configuração adotada: `N_PAINEIS_CV_VERT = 4 → 8`

| Grandeza | n = 4 (antes) | **n = 8 (adotado)** | Δ |
|---|---|---|---|
| Diagonal | Ø45 | **Ø33** | ligações de extremidade muito mais exequíveis |
| V por painel | 211,9 kN | **105,9 kN** | −50 % |
| η diagonal | 0,893 | **0,830** | |
| Download no pilar de canto | 322,5 kN | **193,6 kN** | −40 % |
| η pilar de canto | 0,598 | **0,428** | |
| Tração na ancoragem do canto | 406,4 kN | **277,5 kN** | −32 % |
| η sucção/uplift | 0,847 | **0,578** | |
| η ancoragem do canto | 0,771 | **0,526** | |
| α_cr longitudinal | 116,0 | **124,8** | |
| Peso de aço | 905 kg | **973 kg** | +7,5 % |
| Baías livres (16 candidatas) | 12 | **8** | |
| **η máximo do pipeline** | 0,8930 | **0,8303** | |

Acima de n ≈ 6 o η máximo global deixa de ser governado por este sistema e passa
ao **contraventamento da cobertura** (§9.2.5, η = 0,7902) — aumentar `n` para
além disso já não melhora o η global, só o caminho de carga.

**Ancoragem do canto:** com n = 8 a base já passaria com **4 chumbadores**
(η_sucção 0,867 contra 0,578 com 6). Mantiveram-se os 6 para não refazer o bloco
de fundação já detalhado (c = 600 mm, h_ef = 400 mm, ≈1,60×2,00 m em planta) —
decisão registada em `N_CHU_CANTO`, reversível numa linha se o cliente preferir
simplificar a fundação.

### Z.11.5 — Estado

- `pytest -q` → **465 passed, 1 failed** (a pré-existente F-19).
- **26 testes novos**: `test_f13_atrito_longitudinal.py` (11) e
  `test_f13_configuracao_adotada.py` (7), mais os que fixam a proveniência.
  Incluem um teste de regressão que confirma que **n = 2 reprovaria** o conjunto.
- Os 14 benchmarks independentes continuam a reproduzir com Δ ≤ 0,05 %.
- Pipeline: `EXIT 0`, `η_máximo = 0,8303`, `Status = APROVADO` **com o carimbo
  de aprovação CONDICIONAL de F-13**.


---

## Z.12 — F-13 · RETIFICAÇÃO: a cláusula confirma 0,50

### Z.12.1 — O texto normativo

NBR 6123:2023 §7.2.2, fornecido pelo autor do projeto:

> **7.2.2** Para vento paralelo à geratriz da cobertura, devem ser consideradas
> forças horizontais de atrito calculadas pela seguinte equação:
>
>     Ft = 0,5 · q · a · b
>
> onde *a* e *b* são as dimensões em planta da cobertura.
> Estas forças englobam a ação do vento sobre as duas faces da cobertura.

### Z.12.2 — O que esta auditoria errou

**A hipótese de que o coeficiente correto fosse 0,05 estava errada.** O valor
implementado — 0,50 — é o valor normativo, e a aplicação no código está correta:
`a × b` são as dimensões em planta (46,0 × 40,5 = 1 863 m²), a direção é a
paralela à geratriz (θ=0°), e a força engloba as duas faces.

A severidade de F-13 desce de **ALTA** para **LOW**, e o achado passa a ter um
único conteúdo válido — o de **rastreabilidade**:

| Componente do achado | Veredito |
|---|---|
| «Valor sem fonte primária no repositório» | **PROCEDENTE** — e resolvido: a cláusula está agora transcrita literalmente em `core/wind.py` |
| «Teste de regressão auto-referencial» | **PROCEDENTE** — e resolvido: o teste confronta agora o número com o **texto transcrito**, não consigo próprio |
| «Fisicamente impossível ⇒ o valor deve estar errado» | **IMPROCEDENTE** — a aritmética estava certa, a inferência não |

### Z.12.3 — Por que o argumento físico não invalidava a norma

A comparação continua factualmente correta: `Ft = 776,8 kN` é 2,35× o arrasto de
um corpo sólido de igual silhueta (356,0 kN) e ~12,8× o arrasto somado dos 27
pilares. O erro esteve em tratar isso como prova de que o coeficiente estava
errado.

`Ft` **não é uma estimativa de atrito superficial** — a própria cláusula diz que
«estas forças **englobam a ação do vento sobre as duas faces da cobertura**».
É uma **ação de projeto envolvente**, que cobre num só termo mecanismos que a
norma não desagrega, aplicada à área em planta e não à área de fricção. Códigos
de vento fazem isto de propósito para coberturas isoladas; comparar o resultado
com um coeficiente `c_fr` do EN 1991-1-4 (0,01–0,04), que é um coeficiente de
fricção *stricto sensu* sobre área molhada, foi comparar duas grandezas que a
norma não define da mesma maneira.

**Lição de método, registada:** um argumento de plausibilidade física falsifica
um *cálculo*, não uma *prescrição*. Contra uma prescrição normativa ele só
levanta a questão — a resposta vem do texto. Foi por isso que a auditoria
classificou o valor como `PROBABLE` e não `CONFIRMED`, e por isso que a correção
de Z.11 **não alterou o número**. O procedimento aguentou; a hipótese não.

### Z.12.4 — O que mudou no código

| Onde | Alteração |
|---|---|
| `wind.py` | **texto integral da cláusula transcrito** no cabeçalho da secção; `CLAUSULA_ATRITO = "NBR 6123:2023 §7.2.2"`; `ORIGEM_ATRITO` deixa de dizer «A CONFIRMAR» |
| `wind.py` | `plausivel` / `aviso_plausibilidade` **removidos** — um alarme que dispara sobre um valor normativo correto é um falso positivo que treina o engenheiro a ignorar avisos. Ficam `F_bloqueio_kN`, `razao_bloqueio` e `nota_bloqueio`, agora **diagnóstico informativo**: dão escala à ação e apanham erro de ENTRADA (área em planta, q) |
| `normativo.py` | origem `"ABNT-A-CONFIRMAR"` → `"ABNT"`, com a cláusula e a natureza envolvente registadas; `parametros_a_confirmar()` mantém-se como **guarda permanente** e devolve agora `{}` |
| `main.py` | o carimbo `⚠ APROVAÇÃO CONDICIONAL (F-13)` foi **retirado**; a saída passa a mostrar `Ft = 0.5·q·a·b = 776.8 kN (a×b = 1863 m²; engloba as duas faces)` e a escala face ao bloqueio |
| testes | `test_valor_normativo_esta_ancorado_na_clausula_transcrita` — confronta o 0,5 com o **texto** presente no módulo, fechando o vício auto-referencial; `test_nao_restam_parametros_com_clausula_por_confirmar` — guarda permanente |

O que **não** mudou: o coeficiente (0,50), a ação (837,3 kN) e todo o
dimensionamento de Z.11. **Os 8 painéis, o Ø33 e a ancoragem continuam válidos**
— foram dimensionados para o valor normativo correto. A alternativa «C = 0,05 →
Ø16, aço 5× menor» que Z.11 apresentava fica **descartada**.

### Z.12.5 — Estado

- `pytest -q` → **465 passed, 1 failed** (a pré-existente F-19).
- Pipeline: `EXIT 0`, `η_máximo = 0,8303`, `Status = APROVADO` — **sem ressalva**.
- Os 14 benchmarks independentes continuam a reproduzir com Δ ≤ 0,05 %.

### Z.12.6 — Efeito no veredito

Sai da lista de condicionantes de Z.9.1 o item 1 (confirmação do §7.2.2).
O veredito mantém-se **`CONDITIONALLY VALIDATED`**, agora condicionado apenas a:

> 1. **correção de [F-14]** — a resistência da L1/L1c está 18,3 % abaixo da
>    Eq. (8.11) do EC5 (conservador, mas errado e já não compensado);
> 2. **correção dos MÉDIA da Seção V-P1** — [F-06] (envelope por procuração),
>    [F-07] (`l_ef + 2h`) e [F-11] (seção líquida das diagonais);
> 3. **anexação ao memorial das restantes tabelas da NBR 6123:2023**
>    ([F-18] — Tab. 1, 2, 10 e 25; o §7.2.2 já está transcrito).


---

## Z.13 — F-14 · modos de Johansen da chapa CENTRAL

### Z.13.1 — Formulação adotada

`connections/connections.py`, `johansen_chapa_central` (nome antigo
`johansen_chapa_embutida` mantido como alias). EN 1995-1-1 §8.2.3, chapa de aço
de **qualquer espessura como elemento CENTRAL** de ligação em corte duplo:

    (f)  f_h,1,k · t₁ · d
    (g)  f_h,1,k · t₁ · d · [ √(2 + 4·M_y,Rk/(f_h,1,k·d·t₁²)) − 1 ]
    (h)  2,3 · √(M_y,Rk · f_h,1,k · d)

    F_v,Rk = min{ (f), (g), (h) }

O termo de efeito de corda `F_ax,Rk/4` que acompanha (g) e (h) é **nulo**:
§8.2.2(2) dá `F_ax,Rk = 0` para cavilhas lisas. Fica explícito no retorno
(`F_ax_Rk_N = 0.0`) e num teste, para não voltar a ser confundido com omissão.

**Espessura da madeira:** `t₁ = (b − t_chapa)/2`, e não `b/2`. A chapa embutida
tem `t ≥ d` (rigidez para a rótula do pino); adota-se `t_chapa = d` no
dimensionamento das ligações, que corre **antes** do esquadro — o esquadro
confirma depois 25 mm para d = 24 mm, e a diferença em `t₁` (148,0 contra
147,5 mm) é de 0,3 %. O parâmetro `t_chapa_mm` fica exposto para o caso de a
ordem vir a ser invertida.

### Z.13.2 — Esta correção REDUZ conservadorismo — e por isso o cuidado extra

Ao contrário de todas as anteriores, esta **aumenta** a resistência calculada.
Errar aqui seria errar do lado inseguro. Por isso cada modo está ancorado, nos
testes, na sua forma fechada reconstruída independentemente, para 4 espessuras
× 4 ângulos, e há um teste explícito de que o modo `1,15·√(2·M_y·f_h·d)` — o da
chapa fina externa — **não aparece** em nenhum resultado.

| Formulação (d=24, ρ_k=385, α≈85°) | F_v,Rk/plano |
|---|---|
| Código antes de F-03 (`f_h,0`; `t₁=b/2`; modo da chapa fina externa) | 26,62 kN |
| Código após F-03, antes de F-14 (`f_h,α`; `t₁=b/2`; modo errado) | 20,39 kN |
| **§8.2.3 chapa central (`f_h,α`; `t₁=(b−t_chapa)/2`)** | **25,02 kN** |

**Benchmark BM-10 reexecutado:** a reconstrução independente dos três modos dá
25,025 kN/plano contra 25,025 kN do software — **0,0001 %**. Modo governante
(g), uma rótula plástica.

> **Ponto a confirmar contra o texto do EC5 — o mesmo procedimento de F-13.**
> A identificação do conjunto de modos é de alta confiança: a configuração
> (chapa central em ranhura, corte duplo) é inequívoca, e as três expressões são
> as da chapa central. O que **não** se confirmou contra o texto é a
> **numeração** da equação — o relatório referia-a como «Eq. (8.11)» e a
> auditoria não pode afirmá-la. O código cita por isso a cláusula e a
> configuração («§8.2.3 — chapa de qualquer espessura como elemento central em
> corte duplo»), não o número. Se tiver o EC5 à mão, a confirmação fecha o
> ponto tal como o §7.2.2 fechou F-13.

### Z.13.3 — Efeito no dimensionamento

| Grandeza | Antes | Depois |
|---|---|---|
| `F_v,Rk`/plano | 20,39 kN | **25,02 kN** (+22,7 %) |
| `F_Rd`/cavilha | 20,39 kN | **25,02 kN** |
| Cavilhas na L1/L1c | 7 | **6** |
| `R` do grupo | 142,7 kN | **150,1 kN** |
| η_L1 / η_L1c | 0,6979 | **0,6634** |
| Altura da chapa embutida | 815 mm | **743 mm** |
| η ruptura de bloco | 0,0042 | 0,0051 |
| η chapa de aço | 0,0819 | 0,0956 |
| **η máximo do pipeline** | 0,8303 | **0,8303** (governa o CV longitudinal) |

Uma cavilha a menos em cada uma das 23 ligações, e 72 mm a menos de chapa.

### Z.13.4 — Testes pré-existentes atualizados

Dois testes em `test_memoria_L1.py` codificavam o comportamento defeituoso:

- `test_t1_meia_largura` afirmava `t₁ = b/2` — passa a exigir `(b − t_chapa)/2`.
- `test_nef_reduz_grupo` exigia `n_ef_row < n_linha` **estritamente**. Com o
  layout atual (uma cavilha por fileira // fibras) a EC5 Eq. (8.34) dá
  `n_ef = min(n; n^0,9(a₁/13d)^0,25) = 1 = n`: a igualdade é admissível e não há
  grupo a reduzir. Exigir desigualdade estrita era exigir mais do que a norma.
  Substituído por `n_ef ≤ n` (o teto da norma) **mais** um teste que verifica
  que a redução de facto morde em fileiras de 3, 5 e 8 cavilhas.

### Z.13.5 — Estado

- `pytest -q` → **491 passed, 1 failed** (a pré-existente F-19).
  **25 testes novos** (`test_f14_johansen_chapa_central.py`).
- Pipeline: `EXIT 0`, `η_máximo = 0,8303`, `Status = APROVADO`.
- Os 14 benchmarks independentes continuam a reproduzir com Δ ≤ 0,05 %.

### Z.13.6 — Veredito

Sai a condicionante 1 de Z.12.6. **`CONDITIONALLY VALIDATED`**, condicionado a:

> 1. **[F-06]** envelope por procuração — 13 de 15 módulos leem só a combinação
>    que maximiza |M|;
> 2. **[F-07]** `l_ef + 2h` na LTB (carga na borda comprimida);
> 3. **[F-11]** seção líquida das diagonais e ligações de extremidade;
> 4. **[F-18]** anexação das Tab. 1, 2, 10 e 25 da NBR 6123:2023 ao memorial
>    (o §7.2.2 já está transcrito);
> 5. confirmação da **numeração** das equações de §8.2.3 (Z.13.2).


---

## Z.14 — F-06 · envelope real sobre as combinações

### Z.14.1 — O que mudou

| Onde | Alteração |
|---|---|
| `loads.py` | `combinacoes_ELU_fisicas()` — as 17 combinações REAIS, sem os aliases `ELU_C1..C4`. Os aliases duplicariam casos de carga e, em C3/C4, trariam uma duração fixada que não é a de origem |
| `loads.py` | `envelope_ELU(fn)` — devolve a combinação que maximiza a medida de demanda **de cada verificação**, e o valor |
| `cumeeira.py` | varre as 17 combinações, cada uma com o **seu** k_mod; reporta `comb_gov`, `duracao`, `k_mod`, `n_combinacoes_varridas` |
| `apoio.py` | idem — a combinação que maximiza `R_v` não é a que maximiza \|M\| |
| `flambagem_lateral.py` | idem — `σ_m,crit`, `λ_rel,m` e `k_crit` são recalculados por combinação, porque a seção crítica muda com `x_Mmax` |
| `flexao.py` | passa a varrer **combinações × seções** (a varredura de seções do AUD-014 corria só para uma combinação) |
| `misula.py`, `pilares.py`, `cargas_fundacao.py`, `main.py` | passam a usar o conjunto físico em vez de `combinacoes_ELU()` |

Cada verificação passa a **declarar no resultado qual combinação a governa** —
antes o memorial dizia apenas «ELU_C2» para tudo, o que é falso para metade das
verificações.

### Z.14.2 — Efeito

Na rota **atual** (Tab. 10, vento todo de sucção) os η **não mudam** — o
envelope coincide com a procuração, como BM-14 já mostrava. O que muda é que
agora está *verificado* em vez de *presumido*, e cada verificação nomeia a sua
governante:

| Verificação | η | governante | duração |
|---|---|---|---|
| Cumeeira §6.4.3 | 0,3526 | `ELU_Q` | media |
| Mísula §6.4.2 | 0,3140 | `ELU_S_T10_t1_esq_cpi+0.8` | curta |
| Flambagem §6.3.3 | 0,0977 | `ELU_Q` | media |
| Flexo-comp. §6.3.2 | 0,1672 | `ELU_Q` | media |
| Apoio §6.1.5 | 0,2660 | `ELU_Q` | media |

Na rota **Tab. 25** — onde o defeito mordia — o seletor antigo devolvia
`ELU_C2` (vento, «curta») para tudo, e agora cada verificação encontra a sua:

| Verificação | governante real | duração | η |
|---|---|---|---|
| Cumeeira | **`ELU_Q`** | media | 0,3526 (era 0,3385, **+4,2 %**) |
| Apoio | `ELU_W_C1_asim` | curta | 0,3003 |
| Flambagem | `ELU_W_C1_asim` | curta | 0,1141 |
| Flexão | `ELU_W_C1_asim` | curta | 0,1828 |

### Z.14.3 — Testes

**14 testes novos** (`test_f06_envelope_combinacoes.py`), corridos nas **duas**
rotas de vento. O contrato central: *o η do envelope é sempre ≥ ao que se obtinha
avaliando só a combinação de max\|M\|*. Um teste do duplo de
`test_cargas_fundacao.py` foi atualizado para a nova interface.

`pytest -q` → **505 passed, 1 failed** (a pré-existente F-19).
Pipeline: `EXIT 0`, `η_máximo = 0,8303`, `Status = APROVADO`, η idênticos ao
estado anterior.

---

## Z.15 — PAINEL DE CONTROLO: `auditoria_v2/check_correcoes.py`

Script reexecutável que **reverifica cada correção de forma independente** — não
chama a suíte do projeto nem confia no que este relatório diz: reconstrói ali a
propriedade que cada correção estabelece e confronta-a com o software.

```
$ .venv/bin/python auditoria_v2/check_correcoes.py
```

| | Achado | Verificação independente | Resultado |
|---|---|---|---|
| ✅ | **F-01** | `H_cob` reconstruído de `c_pe`, `q` e da área real da água | 57,8 kN = ref; **1,51×** o arrasto dos pilares |
| ✅ | **F-02** | `α_cr = K·h/V`; `N_Ed=0` → indeterminado; sem rigidez → não dispensa | Eq. (5.2) ✓; sem `1e99` ✓; `alpha_cr_nao_determinado` ✓ |
| ✅ | **F-03** | `f_h,α,k` recalculado da Eq. (8.31)/(8.33) | 14,076 vs 23,993 MPa (**−41,3 %**), k90 = 1,710 |
| ✅ | **F-04** | vazio / `None` / str / `NaN` / não-dict → nunca aprovação | `(nan, False)` ✓; catálogo completo (39 linhas) ✓; pendentes reprovam ✓ |
| ✅ | **F-05** | `a4,t = max((2+2·sen α)d; 3d)`; `a3,c` de cavilha = 3d | 95,8 mm (**+33,1 %**); `a3,c` preservado |
| ✅ | **F-06** | envelope reconstruído sobre as 17 combinações, k_mod por combinação | rota Tab.25: ápice governa em `ELU_Q`, η = envelope |
| ✅ | **F-13** | cláusula literal presente no módulo; valor ancorado no texto | transcrita ✓; C=0,5 ✓; Ft=776,8 kN, escala 2,35× |
| ✅ | **F-14** | os três modos da chapa central reconstruídos; modo errado ausente | 25,02 kN/plano = ref; gov = (g); `F_ax = 0` |
| ✅ | — | pipeline de ponta a ponta | `APROVADO`, η_max = 0,8303, 40 verificações |

**9/9 verificações independentes OK.**

**Em aberto**, listado pelo próprio painel:

| | Achado | |
|---|---|---|
| ⏳ | **F-07** | `l_ef` da LTB sem o `+2h` de carga na borda comprimida (Tab. 6.1, nota) |
| ⏳ | **F-11** | seção líquida das diagonais e ligações de extremidade (§6.2.3(2)) |
| ⏳ | **F-18** | Tab. 1, 2, 10 e 25 da NBR 6123:2023 por anexar (o §7.2.2 já está) |
| ⏳ | **F-19** | `pyproject` `numpy>=1.26` vs NumPy 2.4.6 — 1 teste falha no ambiente |
| ⏳ | — | numeração das equações de §8.2.3 por confirmar (Z.13.2) |

### Estado consolidado das correções

| Achado | Severidade original | Estado | Efeito no dimensionamento |
|---|---|---|---|
| F-01 | ALTA, não conservador | ✅ | `H_tr` ×2,19; frontão Ø16 → Ø24 |
| F-02 | ALTA, não conservador | ✅ | gate passa a medir sway real (16,5 ≥ 10) |
| F-03 | ALTA, não conservador | ✅ | `f_h` −41,3 %; cavilhas 5 → 7 |
| F-04 | ALTA, não conservador | ✅ | 2 verificações deixam de desaparecer do veredito |
| F-05 | MÉDIA, não conservador | ✅ | `a4,t` +33,1 %; chapa +95 mm (detalhamento) |
| F-06 | MÉDIA, variável | ✅ | +4,2 % no ápice na rota Tab. 25 |
| F-13 | ALTA → **LOW** | ✅ *(retificado)* | nenhum — hipótese errada; CV 4 → 8 painéis mantém-se |
| F-14 | MÉDIA, conservador | ✅ | `F_v,Rk` +22,7 %; cavilhas 7 → 6 |


---

## Z.16 — F-07 · `l_ef` da LTB com o `+2h` da nota da Tabela 6.1

### Z.16.1 — Formulação adotada

`flambagem_lateral.calcular_l_ef`, EC5 Tabela 6.1 **mais a nota da própria
tabela**:

    l_ef = razão(restrição, tipo_carga) · l₁  +  Δ · h

    Δ = 0      carga no centro de gravidade   (caso das razões tabeladas)
    Δ = +2,0   carga na BORDA COMPRIMIDA      («should be increased by 2h»)
    Δ = −0,5   carga na borda tracionada      («may be decreased by 0,5h»)

**A API passa a exigir a declaração.** O default é o caso conservador
(`borda_comprimida`) e `h_m` é então **obrigatório** — nenhum chamador pode
continuar a herdar em silêncio a hipótese mais favorável. Os 8 locais que
chamavam `calcular_l_ef` tiveram todos de declarar a sua posição de carga; foi
essa quebra deliberada da assinatura que garantiu que nenhum ficou esquecido.

Duas decisões de domínio registadas no código:

- **Redução de 0,5h não pode produzir `l_ef ≤ 0`.** É um «may» da norma e, com
  `h ≫ l₁`, daria um comprimento efetivo negativo. Recusa-se com
  `DominioInvalidoError` em vez de compensar com um mínimo inventado.
- **Em peça de altura variável, `h` é o da SEÇÃO verificada, não `h0`.** Como
  `l_ef` passou a depender de `h`, teve de descer para dentro dos laços das
  varreduras (em `apoio`, `cisalhamento`, `creep`, `predim` e nas duas
  `varrer_*` de `flambagem_lateral` estava içado para fora).

### Z.16.2 — Separação entre flambagem de coluna e LTB (`flexao.py`)

`flexao.py` usava **um único** `l_ef` para duas coisas diferentes:

| Grandeza | Cláusula | A nota da Tab. 6.1 aplica-se? |
|---|---|---|
| `l_ef,z` — flambagem à **compressão** em torno de z | §6.3.2 | **Não** — é um comprimento de encurvadura entre travamentos |
| `l_ef,LTB` — flambagem lateral por **flexo-torção** (σ_m,crit) | §6.3.3 | **Sim** — as terças carregam a borda comprimida |

Passaram a ser calculados em separado, e ambos são publicados
(`l_ef_z_m`, `l_ef_ltb_m`).

### Z.16.3 — Casos declarados como NÃO sendo carga na borda comprimida

- **Içamento** (`icamento.py`): a ação é o peso próprio, que atua no centro de
  gravidade; e a viga pende das lingas — suspensão acima do centro de corte é
  condição **estabilizante**, não desestabilizante. Não se acrescenta 2h.
  Declarado no código, não deixado por omissão.
- **`tercas.varrer_tercas`**: o `l_ef_viga` que ali se calcula é
  **informativo**, só para comparar espaçamentos, e a altura da viga principal
  não é variável dessa varredura. Fica a razão crua, com a nota de que a
  verificação real da LTB da viga está em `flambagem_lateral.py`, essa com o +2h.

### Z.16.4 — Efeito

| Grandeza (l₁ = 2,53 m, h = 2,785 m) | Antes | Depois |
|---|---|---|
| `l_ef` | 2,28 m | **7,85 m** (3,45×) |
| `σ_m,crit` | 120,9 MPa | **35,1 MPa** |
| `λ_rel,m` | 0,446 | **0,827** |
| Regime | estável (`k_crit = 1,0`) | **instabilidade parcial** |
| `k_crit` | 1,0000 | **0,9396** |
| **η flambagem lateral** | 0,0977 | **0,1039** |
| η máximo do pipeline | 0,8303 | 0,8303 |

A viga deixa de ser classificada como «estável — sem redução» e passa a ter uma
redução real de `k_crit`. Continua folgada (η = 0,10) porque está muito
sobredimensionada, mas o defeito era **sistemático**: afetava também a varredura
de pré-dimensionamento, onde a escolha da geometria é feita.

### Z.16.5 — Estado

- `pytest -q` → **518 passed, 1 failed** (a pré-existente F-19).
  **13 testes novos** (`test_f07_lef_borda_comprimida.py`).
- Três testes pré-existentes atualizados por codificarem a razão crua
  (`test_flambagem_memoria::test_l_ef_igual_09_l1` e o par de F-06 sobre LTB).
- Pipeline: `EXIT 0`, `η_máximo = 0,8303`. A varredura completa
  (`rodar_varredura=True`) também foi executada, para exercitar `predim` e as
  quatro funções `varrer_*` que tiveram o `l_ef` movido para dentro dos laços.
- Painel de controlo: **10/10 verificações independentes OK**.


---

## Z.17 — F-11 · seção líquida das diagonais (EN 1993-1-1 §6.2.3(2))

    N_t,Rd = min( N_pl,Rd = A·f_y/γ_M0 ;  N_u,Rd = 0,9·A_net·f_u/γ_M2 )

`_n_t_rd_kN` devolvia só `N_pl,Rd`, sobre a área **bruta**. As diagonais são
barras redondas **roscadas nas extremidades**: a seção que rompe é a da rosca.

`area_resistente_rosca(d) = π/4·(d − 0,9382·p)²`, com o passo de rosca métrica
de perfil grosso tabelado por diâmetro. **Sem passo tabelado o valor não é
estimado — recusa-se**, pela mesma razão de sempre: uma área líquida inventada
seria pior do que nenhuma.

Em S235 a rotura da seção líquida **governa sempre** (A_s ≈ 0,81·A, e
0,9·f_u/γ_M2 = 259 MPa contra f_y/γ_M0 = 235 MPa): para Ø33, 179,7 kN contra
201,0 kN — **−10,6 %**.

### Efeito

| | Antes | Depois |
|---|---|---|
| Diagonal longitudinal | Ø33 | **Ø36** |
| η contravento vertical | 0,8303 | **0,7883** |
| Diagonal do frontão | Ø24 | **Ø27** |
| η contravento transversal | 0,7867 | **0,7024** |
| η estabilidade global | 0,6062 | **0,4790** (mais rigidez ⇒ α_cr maior) |
| **η máximo do pipeline** | 0,8303 | **0,7902** |

O auto-dimensionamento subiu ambas as diagonais um degrau comercial. O η máximo
passa a ser governado pelo **contraventamento da cobertura** (§9.2.5, 0,7902),
como Z.11.4 antecipava.

### O que fica por fazer

As **ligações de extremidade** das diagonais — gousset, esticador, olhal/pino,
solda ao montante — continuam por dimensionar. Passa a ser **declarado no
resultado** (`pendente`) em vez de omitido: a resistência calculada pressupõe
que a ligação não governa, e isso tem de estar escrito.

### Estado

`pytest -q` → **528 passed, 1 failed** (F-19). **10 testes novos**; três
pré-existentes atualizados (um codificava a área bruta, dois usavam Ø6 e Ø8 —
não comerciais — para forçar η > 1). Painel: **11/11 OK**.
