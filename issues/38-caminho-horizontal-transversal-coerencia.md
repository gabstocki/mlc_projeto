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
- [ ] **Registrar esta auditoria** e refutar quantitativamente o "M≈1300 kNm/colapso" com o
      FEM acoplado (figura `output/issue35_empuxo_vs_rigidez.png`) no memorial.
- [ ] **Forçar a decisão da [issue 35](35-empuxo-pilar-caminho-carga.md):** Opção A (tirante/
      escora **no nível do beiral** → H=483 se desenvolve, `M_viga=533` válido, pilares
      axiais) **ou** Opção B (sem empuxo → viga biapoiada `M≈913`, tirante só para uplift).
      Marcar a opção adotada aqui e na 35.
- [ ] **Propagar a coerência textual** (hoje inconsistente): [pilares.py:4,22-25](../mlc_projeto/checks/elu/pilares.py)
      ainda dizem "Pórtico de 3 rótulas / H=621 kN" (legado); memorial reporta `M_viga` e
      tirante com `H` que o modelo atual não sustenta.
- [ ] **Verificar a divergência de `H` sob sucção:** console mostra `H=−84,6 kN`
      ([pipeline_console.txt:184](../output/pipeline_console.txt)) enquanto a
      [issue 33](33-succao-uplift-ancoragem-tirante.md) cita `H=−245,5 kN`. Reconciliar qual
      é o vigente e propagar à ancoragem (tirante frouxo → fundação).
- [ ] **Coerência dos diagnósticos de rigidez:** a [issue 24](24-tirante-fy315-flexibilidade.md)
      cita `k_tir=52 kN/mm`, `δ=21,1 mm`, `∅80`; o console atual mostra `k_tir=19 kN/mm`,
      `δ=20,1 mm`, `∅48` ([pipeline_console.txt:124,126](../output/pipeline_console.txt)) —
      confirmar o dimensionamento vigente e alinhar o texto da 24.

## Critério de aceite
A afirmação do orientador está auditada e registrada (incoerência confirmada; mecanismo de
"colapso do pilar" refutado com o FEM acoplado); a decisão de modelo da
[issue 35](35-empuxo-pilar-caminho-carga.md) está **tomada e propagada** (textos de
`pilares.py`, tirante e memorial coerentes com a opção adotada); as divergências numéricas
de `H` (sucção) e das rigidezes/diâmetro do tirante estão reconciliadas.
