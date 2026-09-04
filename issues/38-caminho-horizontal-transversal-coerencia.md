# 38 — Caminho horizontal transversal do empuxo: auditar o "colapso do pilar" e fechar a decisão da issue 35

- **Tema:** Modelo — coerência / Auditoria de esforços / Pilares / Tirante
- **Prioridade:** P1 (não é colapso — ver auditoria abaixo; mas invalida os esforços publicados da viga/tirante e a rotulagem dos textos até a decisão ser tomada e propagada)
- **Normas:** EN 1995-1-1 §5.4, §6.2/§6.3; EN 1993-1-1 §5.2.1; EN 1990 §6.4.3
- **Arquivos:** `mlc_projeto/checks/elu/pilares.py:4-27` (texto "3 rótulas / H=621", M=V=0); `mlc_projeto/checks/elu/tirante_base.py:8-11,160` (T=H, H_sapata≈0, hipótese rígida); `mlc_projeto/core/loads.py` (Castigliano apoio indeslocável); `mlc_projeto/output/report.py` (memorial: M_viga, tirante); `output/pipeline_console.txt:124,184`
- **Relaciona:** **implementação/fix é da [35](35-empuxo-pilar-caminho-carga.md)**; complementa [24](24-tirante-fy315-flexibilidade.md), [31](31-estabilidade-transversal-portico.md), [33](33-succao-uplift-ancoragem-tirante.md), [36](36-download-contraventamento-pilares.md); robustez do tirante → [37](37-tirante-piso-robustez-impacto-corrosao-fogo.md).

## Origem
Apontamento do orientador — *"caminhamento horizontal transversal: incorreto e inseguro"*.
Afirma que o empuxo `H=378 kN` é calculado no **topo** dos pilares (springing a 7 m) mas o
tirante está no **piso** (`z_tir=0,08 m`); logo `H` teria de atravessar o pilar como
cortante e momento, e um pilar biarticulado com `H_top=+378` e `H_base=−378` afastados de
7 m **não fecha sem momento** → conclui `M ~ H·H_pilar/2 ≈ 1300 kNm` e **colapso** do pilar
`0,32×0,27` em flexo-compressão.

Esta issue **audita** essa afirmação e **força o fecho** da decisão de modelo (que já está
diagnosticada, porém **aberta**, na [issue 35](35-empuxo-pilar-caminho-carga.md)).

## Auditoria da afirmação (o que procede e o que não procede)

**Procede — a incoerência estática é real e está no código:**
- [pilares.py:9-12](../mlc_projeto/checks/elu/pilares.py): `M_d=0, V_d=0`, "empuxo H vai
  para a sapata, não para o pilar".
- [tirante_base.py:8-11](../mlc_projeto/checks/elu/tirante_base.py): `T≈H_arco=378 kN`,
  `H_sapata≈0`, tirante no piso ([viz_3d.py:301](../mlc_projeto/visualization/viz_3d.py) `z_tir=0,08`).
- As duas afirmações são **mutuamente exclusivas** num caminho rígido. Estática do pilar
  **biarticulado** (rótula topo + base), momento em torno da base: a única força com braço
  é `H_topo·7 m` ⟹ `ΣM_base = H_topo·7 = 0` ⟹ **`H_topo = 0`**. Um pilar rótula-rótula
  **não transmite** empuxo do topo a um tirante de piso sem fletir. Confirmado pelo próprio
  código: [tirante_base.py:160](../mlc_projeto/checks/elu/tirante_base.py) admite "apoio
  horizontal INDESLOCÁVEL, flexibilidade NÃO realimentada".

**NÃO procede a conclusão "M≈1300 kNm / colapso":** ela pressupõe que `H` se desenvolve
**rígido** *e* é arrastado por um pilar que **fleta** (leitura de pórtico rígido, que
contradiz a hipótese biarticulada). O **FEM acoplado da [issue 35](35-empuxo-pilar-caminho-carga.md)**
mostra o oposto: como o pilar biarticulado é horizontalmente **muito mole**
(`3EI/H³ ≈ 53 kN/m`, em série com a base), **o empuxo praticamente não se desenvolve**
(`H ≈ 0`); a viga tende a **biapoiada** (`M_viga ≈ 913` vs 533 publicado, ainda `η≈0,24`,
folga ampla); os pilares ficam **corretamente pouco solicitados** (`η≈0,14`,
[pipeline_console.txt:43](../output/pipeline_console.txt)); **não há** 1300 kNm nem colapso.
⇒ A penalidade real **não** é o pilar: é (a) o `M` da viga subestimado e (b) a **abertura
horizontal do beiral em ELS (~20–35 mm) não verificada** — exatamente o que a
[issue 35](35-empuxo-pilar-caminho-carga.md) já aponta.

**Conclusão da auditoria:** a crítica é **pertinente no diagnóstico** (incoerência real,
insegura *enquanto os textos/memorial reportam H=378 e M=533*), mas o **mecanismo de falha
apontado (colapso do pilar) está incorreto** — o modo real é viga+ELS. A ação corretiva é a
**decisão A/B** já formulada na 35, que continua **por fazer**.

## O que precisa ser feito (verificação e fecho — implementação na issue 35)
- [x] **Registrar esta auditoria** e refutar quantitativamente o "M≈1300 kNm/colapso" com o
      modelo acoplado (agora **código reproduzível e testado**, não só a figura).
- [x] **Forçar a decisão da [issue 35](35-empuxo-pilar-caminho-carga.md):** **Opção B adotada**
      (assumir sem empuxo → viga biapoiada; tirante só para uplift). Registrada aqui, na 35 e
      no memorial (§8b.3).
- [x] **Propagar a coerência textual:** [pilares.py](../mlc_projeto/checks/elu/pilares.py)
      corrigido ("3 rótulas / H=621 kN" → biarticulado + nota do mecanismo lateral e do
      empuxo que não se desenvolve). Memorial (§8b.3) registra que `M_viga`/tirante ainda
      refletem o modelo rígido — **recomputo é da issue 35**.
- [x] **Divergência de `H` sob sucção reconciliada:** vigente `H=−84,6 kN` (ELU_C3);
      `−245,5 kN` da [issue 33](33-succao-uplift-ancoragem-tirante.md) é defasado
      (pré-correção do termo axial). Nota adicionada na 33.
- [x] **Diagnósticos de rigidez reconciliados:** [issue 24](24-tirante-fy315-flexibilidade.md)
      (`k_tir=52`, `δ=21,1`, `∅80`) é pré-correção; vigente `k_tir=19`, `δ=20,1`, `∅48`.
      Nota adicionada na 24.

## Critério de aceite
A afirmação do orientador está auditada e registrada (incoerência confirmada; mecanismo de
"colapso do pilar" refutado com o modelo acoplado); a decisão de modelo da
[issue 35](35-empuxo-pilar-caminho-carga.md) está **tomada** (Opção B) e propagada nos textos
de `pilares.py`/memorial; as divergências numéricas de `H` (sucção) e das rigidezes/diâmetro
do tirante estão reconciliadas.

---

## ✅ Resolução (auditoria fechada; implementação do modelo na issue 35)

### Auditoria reproduzível
- **Novo módulo** [`checks/elu/empuxo_acoplado.py`](../mlc_projeto/checks/elu/empuxo_acoplado.py):
  substitui o script pontual da figura `issue35_empuxo_vs_rigidez.png` por código testado.
  `rigidez_horizontal_arco` (`f11=∫y_c²/EI+∫cos²θ/EA`), `rigidez_lateral_pilar`
  (rótula=0 | engastada=`3EI/H³`), `empuxo_desenvolvido` (`H_dev=H_rig·k/(k+k_arco)`) e o
  orquestrador `analisar_empuxo_acoplado`.
- **`main.py`** (Fase 4a): imprime a auditoria como diagnóstico de coerência.
- **`report.py`**: memorial **§8b.3** com o achado e a caixa de decisão (Opção B).
- **Testes:** [`tests/test_empuxo_acoplado.py`](../tests/test_empuxo_acoplado.py) (10 casos).
  Suíte: **271 ✓**. Pipeline: **APROVADO, η_max=1,00** (auditoria é diagnóstico, não check).

### Números (config vigente: L=20,25 m, h0=1,0 m, α=10°, b=0,32; pilar 0,32×0,27×7 m; GL24h)
| Grandeza | Valor |
|---|---|
| `k_arco` (arco raso, muito rígido) | **208 462 kN/m** |
| `k_pilar` biarticulado (mecanismo) / engastado (limite) | **0** / 53 kN/m (~3 949× mais mole) |
| `H_dev` (limite generoso engastado) | **≈0,1 kN de 377** (0,0%) |
| `M_viga` modelo (empuxo rígido) → biapoiada | **417 → 714 kN·m (+71%)** |

**Refutação do "colapso":** o pilar biarticulado não pode receber empuxo horizontal
(`ΣM_base=H·H_col ⇒ H_top=0`); como `k_arco ≫ k_pilar`, o empuxo **não se desenvolve** e o
pilar fica com esforço horizontal ≈ 0. O "M≈1300 kN·m / flexo-compressão" **não ocorre**.

### Decisão: **Opção B** (assumir sem empuxo)
Justificativa: a viga já é folgada em `M0≈714` (η sobe ~0,14→0,24, sem falha), então **não
compensa** forçar o empuxo com tirante/escora a 7 m (Opção A). A física real é a biapoiada.

### Handoff para a [issue 35](35-empuxo-pilar-caminho-carga.md) — ✅ IMPLEMENTADO
- [x] Viga reverificada **biapoiada** (`M0≈714 kN·m`): flexo-comp. `η=0,13`, cumeeira `0,46`.
- [x] **Flecha real** (biapoiada, `deflection_els` herda o flag): `η_ELS=0,22`.
- [x] **Tirante removido**; sapata sem tirante com piso construtivo de 4 chumbadores;
      ancoragem ao uplift `η=0,46`.
- [x] Memorial atualizado (§8b.3: decisão IMPLEMENTADA; valores refletem o modelo sem empuxo).
- [x] **Déficit exposto e resolvido:** ligação do beiral L1/L1c falhava ao fendilhamento
      (`η=1,16`, cortante 107→141 kN); **reforço ⊥ às fibras** (parafusos §8.7.2,
      `11×∅10 mm` → `η=0,71`). **Pipeline APROVADO, η_max=1,00.**
