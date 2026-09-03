# 36 — Download do contraventamento (±V_Ed·tanβ) não entra na verificação dos pilares dos painéis

- **Tema:** Caminho de carga / Pilares / Contraventamento
- **Prioridade:** P1 (introduz TRAÇÃO não verificada nos montantes sob uplift + ancoragem; e subestima a compressão dos pilares contraventados)
- **Normas:** EN 1995-1-1 §6.1.2 (tração //fibras), §6.2.3/§6.3.2 (flexo-compressão), §2.3 (combinação de esforços no membro); EN 1993-1-1 §5.3.2–§5.3.3 (forças de contraventamento pelo caminho completo); EN 1990 §6.4.3 (combinações — o download deve ser combinado com a gravidade concomitante)
- **Arquivos:** `mlc_projeto/checks/elu/contraventamento_vertical.py:36-38`, `:206-212`; `mlc_projeto/checks/elu/contraventamento_transversal.py`; `mlc_projeto/checks/elu/pilares.py:199`; `mlc_projeto/main.py:637`; ancoragem: `mlc_projeto/checks/elu/succao_uplift.py`
- **Relaciona:** [14](14-contraventamento-vertical.md), [31](31-estabilidade-transversal-portico.md), [33](33-succao-uplift-ancoragem-tirante.md), [35](35-empuxo-pilar-caminho-carga.md).

## Origem
Insistência (correta) da usuária: **"o modelo não carrega os pilares de madeira, sendo
estes subutilizados."** Rastreando o encaminhamento de cargas, confirma-se uma **parcela
axial real que existe nos pilares e não é verificada**.

## Problema (caminho de carga incompleto)
O sistema lateral usa **cruzes de St. André** (contraventamento vertical longitudinal,
[issue 14](14-contraventamento-vertical.md); e frontões transversais, [issue 31](31-estabilidade-transversal-portico.md)).
Cada painel converte o cortante horizontal `V_Ed` em:

```
N_diag  = V_Ed / cosβ      (diagonal — verificada ✔)
H_base  = V_Ed             (→ fundação, cortante ✔)
N_uplift = V_Ed · tanβ     (componente VERTICAL nos MONTANTES do painel)
```
([contraventamento_vertical.py:36-38](../mlc_projeto/checks/elu/contraventamento_vertical.py)).

Os **montantes do painel são os próprios pilares de madeira** (o painel tem altura `H_col`
e largura `b_baia` = vão entre pilares). A diagonal tracionada aplica no topo de um pilar
uma **compressão adicional** `+V_Ed·tanβ` e, no pilar oposto, uma **tração/arrancamento**
`−V_Ed·tanβ`. Hoje o código roteia `N_uplift` **"→ fundação/ancoragem"** e apenas o
**imprime** ([main.py:637](../mlc_projeto/main.py)); **nenhuma verificação de pilar ou de
ancoragem o consome**. O pilar é checado só com `N_d = fator·R_v` (reação de gravidade)
em [pilares.py:199](../mlc_projeto/checks/elu/pilares.py).

## Quantificação (geometria/combinações reais)
β = 50,6° (tanβ = 7,0/5,75); `R_v` (gravidade) = 180,4 kN.

| Parcela | Valor |
|---|---|
| Download bracing LONGITUDINAL (vertical, θ=0°) | **56,5 kN** |
| Download bracing TRANSVERSAL (frontão, θ=90°) | **35,0 kN** |
| Pilar contraventado, **compressão**: `R_v + 56,5` | N=236,9 kN → **η 0,07 → 0,13** |
| Pilar de canto (2 painéis), **uplift**: `R_v,min − (56,5+35,0)` | R_v,min≈3,9 kN (ELU_C3/uplift) → **N ≈ −88 kN (TRAÇÃO)** |

- **Compressão:** subestimada nos pilares dos painéis (efeito modesto, η≈0,13, porque a
  seção 0,32×0,27 já é folgada — mas o esforço existe e deve constar).
- **Tração/uplift (o ponto sério):** quando o vento **reduz `R_v`** (uplift/sucção) e ao
  mesmo tempo **alimenta o contraventamento** (V_Ed alto), o montante tracionado pode ir a
  **tração líquida ~50–90 kN** — **não verificada** à tração //fibras (EN 1995 §6.1.2) nem
  na **ancoragem base** (EN 1993/EN 1992-4). A concomitância vento↑ / `R_v`↓ é física e
  precisa ser tratada na **mesma combinação** (EN 1990).

## O que precisa ser feito
- [x] Definir explicitamente o montante de cada painel: adotado **o pilar de madeira** é o
      montante (o download entra na verificação do pilar).
- [x] **Somar `±V_Ed·tanβ` ao `N_d`** na verificação do(s) pilar(es) dos painéis, incluindo
      o pilar de **canto** (long. + transv.), na combinação concomitante.
- [x] Verificar a **tração líquida** do montante sob uplift (EN 1995-1-1 §6.1.2) e **expor
      a demanda de ancoragem** (`N_ancoragem_kN`).
- [x] **Somar a tração de contraventamento à combinação de ancoragem** em
      [succao_uplift](../mlc_projeto/checks/elu/succao_uplift.py) / [issue 33](33-succao-uplift-ancoragem-tirante.md):
      base de CANTO agora soma `Σ V_Ed·tanβ` ao uplift de sucção (concomitante).
- [x] **Distinguir pilar-interno × pilar-de-canto** e verificar o canto de forma
      **combinada** (gravidade + download + momento de vento). Conclusão: a **seção
      0,32×0,27 é adequada** ao canto (η=0,56 membro; não precisa aumentar); a distinção
      fica explícita no modelo/relatório (interno η≈0,14 × canto η≈0,56 / ancoragem 0,72).
- [ ] **(refino)** Tratar a concomitância **por direção de vento** (θ=0° ativa só o painel
      longitudinal; θ=90° só o frontão) — hoje usa-se o envelope Σ dos dois (conservador).

## Critério de aceite
Os montantes dos painéis de contraventamento têm o download `±V_Ed·tanβ` incluído na sua
verificação (compressão e tração), na combinação concomitante correta; o caso de tração
líquida sob uplift é verificado no membro e na ancoragem; a distinção pilar-interno ×
pilar-contraventado está explícita no modelo e no memorial.

---

## ✅ Resolução (implementada — parcial; ancoragem plena em follow-up)

### Novo membro verificado
- **`checks/elu/pilares.py`**: função `verifica_pilar_contraventado(...)` — soma o
  download `Σ V_Ed·tanβ` à reação de gravidade e verifica o montante em **dois estados**:
  compressão com instabilidade (EC5 §6.3.2, `N_c = R_v + ΣD`) e **tração líquida** sob
  uplift (EC5 §6.1.2, `N_t = ΣD − R_v,min`, `σ_t,0,d ≤ f_t,0,d`); devolve η governante e a
  **demanda de ancoragem** `N_ancoragem_kN = N_t`.
- **`main.py`** (Fase 2): calcula o **pilar de canto** (montante do painel longitudinal +
  do frontão transversal), com `Σdownload = cvv.N_uplift + cvt.N_uplift`, `R_v` de
  compressão (majorante) e `R_v,min` (uplift). Resultado no pipeline:
  `Σdownload≈117,9 kN → N_comp≈259 kN, η_comp≈0,25`; tração líquida `N_t≈113,6 kN`
  (ancoragem), `η_t≈0,12`. **Governa compressão, η=0,25** (antes o download não constava).
- **`output/report.py`**: nova linha no catálogo (§12): "Pilar montante contravent.".

### Ancoragem concomitante (follow-up implementado)
- **`checks/elu/succao_uplift.py`**: novo parâmetro `N_brace_anc_kN` e caso de ancoragem
  **base de CANTO** — soma a tração de download do contraventamento (`Σ V_Ed·tanβ`) ao
  uplift de sucção (mesmo evento de vento): `N_canto = N_uplift_ext + Σ V_Ed·tanβ`,
  interação N–V linear. `eta_gov` passa a considerar o canto.
- **`main.py`** passa `N_brace_anc_kN = cvv.N_uplift + cvt.N_uplift` (envelope conservador).
- **Efeito:** a ancoragem sobe de **η=0,36 → η=0,72** (N_canto=29,3+117,9=147,2 kN;
  governa "canto (contraventado)"). Passa, mas a margem real agora é honesta — antes a
  ancoragem estava **subestimada pela metade**.

### Seção diferenciada do pilar de canto (follow-up implementado)
- **`verifica_pilar_contraventado`** ganhou `M_vento_kNm` e verifica o canto **combinado**:
  **flexo-compressão** (§6.3.2, `N=R_v+ΣD` + M, com k_c) e **flexo-tração** (§6.2.3 Eq. 6.17,
  `N_t=ΣD−R_v,min` + M). `main.py` passa o maior momento de vento (θ=0°/θ=90°);
  `report.py` rótulo "Pilar canto (grav+brace+vento)".
- **Resultado:** o canto por completo dá **η=0,56 (flexo-compressão)**, flexo-tração 0,18 e
  **ancoragem 0,72**. A **seção 0,32×0,27 é ADEQUADA** — não precisa aumentar. Distinção
  explícita **pilar interno η≈0,14 × canto η≈0,56** (membro) / **0,72** (ancoragem):
  o que diferencia o canto é a **ancoragem**, não a seção de madeira.

### Verificação
- Suíte: **245 testes ✓** (`test_pilar_contraventado.py` 7 casos + `test_succao_uplift.py`).
- Pipeline: **APROVADO, η_max=1,00, 37 verificações**. PDF/Excel regenerados.

### Pendência restante (P2)
- Concomitância por direção de vento (hoje envelope Σ dos dois painéis, conservador).
