# 35 — Empuxo de gravidade não se desenvolve (beiral flexível); incoerência viga×pilar×tirante

- **Tema:** Modelo — coerência / Empuxo do arco / Pilares / Tirante / ELS
- **Prioridade:** P1 (não é colapso — a viga tem folga; mas invalida esforços do memorial: M da viga, tirante e flecha)
- **Normas:** EN 1995-1-1 §5.4, §6.4; EN 1993-1-1 §5.2.1
- **Arquivos:** `mlc_projeto/core/loads.py:209-325` (hipótese indeslocável); `checks/elu/pilares.py:10-27`; `checks/elu/tirante_base.py`; `checks/elu/estabilidade_global.py:13-14`; `checks/els/deflection_els.py`; `main.py:234-242`
- **Relaciona:** revisa a conclusão da [24](24-tirante-fy315-flexibilidade.md); complementa [31](31-estabilidade-transversal-portico.md), [13](13-pilares-esforcos-central.md), [33](33-succao-uplift-ancoragem-tirante.md). **Auditoria/fecho da decisão A/B → [38](38-caminho-horizontal-transversal-coerencia.md)**; robustez do tirante no piso → [37](37-tirante-piso-robustez-impacto-corrosao-fogo.md).

## Origem
Observação da usuária: **"os pilares me parecem pouco solicitados"**. Aprofundado com um
**FEM 2D do pórtico completo** (2 vãos, seções reais). Conclusão: os pilares estão
**corretamente** pouco solicitados — mas pelo motivo oposto ao que o memorial assume, e
isso expõe uma **incoerência** entre o modelo da viga e o da estrutura.

## Diagnóstico (FEM acoplado)
O empuxo `H` que **reduz o momento da viga** só existe se os **beirais** (apoios da viga,
no topo dos pilares de 7 m) forem **horizontalmente indeslocáveis** — hipótese explícita
do Castigliano em [loads.py](../mlc_projeto/core/loads.py) e da [issue 24](24-tirante-fy315-flexibilidade.md).

Mas os beirais se apoiam em **pilares esbeltos de madeira** (0,32×0,27 m, 7 m) e o único
tirante está na **base**. A rigidez horizontal que o beiral realmente vê é a **flexão do
pilar** (`3EI/H³ ≈ 53 kN/m`), **em série** com o tirante/ancoragem da base — governada
pelo termo mais mole (o pilar). Varredura da rigidez do beiral `k` (FEM, q=17,8 kN/m):

| k no beiral (kN/m) | Empuxo H (kN) | M_viga (kN·m) |
|---|---|---|
| ∞ (indeslocável = hipótese do projeto) | **483** | **533** |
| 1×10⁶ | 337 | 637 |
| 1×10⁵ | 92 | 833 |
| **≈53 (pilar real 0,32×0,27)** | **≈0** | **≈913** |
| 0 (livre) | 0 | 913 |

Para desenvolver os 483 kN é preciso `k ≳ 10⁸ kN/m` — ~2 milhões de vezes a rigidez do
pilar. **Na prática o empuxo NÃO se desenvolve**: a viga se comporta como **biapoiada**,
`M_viga ≈ 913 kN·m` (não os 533 do memorial). Figura: `output/issue35_empuxo_vs_rigidez.png`.

**Por que a [issue 24](24-tirante-fy315-flexibilidade.md) não pegou isso:** ela comparou a
rigidez do arco (`k_arco`) com a do **tirante** (52 kN/mm) e "restrições paralelas da base",
concluindo que H fica próximo do rígido. Mas essas restrições estão na **base**; entre o
beiral (onde o empuxo atua) e a base há a **flexão do pilar** (0,053 kN/mm), **em série** e
~1000× mais mole — omitida na análise. É ela que governa. ⇒ a dispensa da issue 24 precisa
ser revista.

## Consequências (calibradas — FEM)
- **Pilares:** **corretamente pouco solicitados** (η_lat≈0,07 axial / 0,31 vento). Eles
  não recebem o empuxo porque são moles demais para atraí-lo. A observação da usuária
  procede. ✔ sem ação nos pilares.
- **NÃO é mecanismo / colapso:** a estabilidade lateral é garantida pelo contraventamento
  transversal ([issue 31](31-estabilidade-transversal-portico.md)); sob gravidade simétrica
  o empuxo simplesmente não se desenvolve.
- **Viga (memorial não-conservador):** `M_max` real ≈ **913** vs **533** publicado (+71%).
  Porém a seção é muito alta (h_ap≈2,79 m) ⇒ **η_flexão só passa de ~0,14 para ~0,24** —
  **ampla folga, sem falha**. Mas o memorial reporta M/η da viga com o empuxo que não existe.
- **Tirante:** dimensionado para T=H≈483 kN que **não se materializa na base** ⇒
  **conservador/desnecessário** como fecho de empuxo (sua função pode ser só de
  ancoragem ao uplift — [issue 33](33-succao-uplift-ancoragem-tirante.md)).
- **ELS/flecha (a verificar):** [deflection_els](../mlc_projeto/checks/els/deflection_els.py)
  usa o M reduzido pelo empuxo ⇒ **subestima a flecha**; além disso há **abertura do beiral
  ~35 mm** (ULS) / ~20 mm (ELS) não verificada. **Provável ponto real de atenção.**

## O que precisa ser feito (decisão de coerência do modelo)

> **DECISÃO TOMADA (issue 38): Opção B — assumir sem empuxo.** A auditoria reproduzível
> ([`empuxo_acoplado.py`](../mlc_projeto/checks/elu/empuxo_acoplado.py)) confirmou que o empuxo
> não se desenvolve (`H_dev≈0`; `k_arco=208 462` vs `k_pilar≈0` kN/m) e que a viga tende a
> biapoiada (`M: 417→714 kN·m`, +71%). Os números aqui (H≈483/M≈913) são de uma configuração
> anterior; os vigentes estão na [issue 38](38-caminho-horizontal-transversal-coerencia.md).

- [x] ~~Opção A — realizar o empuxo (tirante/escora no beiral)~~ — **descartada**: a viga já é
      folgada em `M0`, não compensa o custo de um elemento a 7 m por pórtico.
- [x] **Opção B (adotada) — IMPLEMENTADA:** `EMPUXO_DESENVOLVE=False` em `main.py`;
      `analisar_biarticulada(desenvolve_empuxo=...)` zera o empuxo efetivo → viga
      **biapoiada** (`M=M0≈714 kN·m`). O `H_rígido` (Castigliano) fica no retorno para a
      auditoria (`H_rigido_kN`). Resultado: flexo-comp. viga `η=0,13`; cumeeira `0,46`.
- [x] **Flecha real (Opção B):** ELS reavaliado com `M0` (o `deflection_els` herda o
      flag) → `η_ELS=0,22` (folga ampla; a seção é muito alta).
- [x] **Tirante REMOVIDO** (não fecha empuxo inexistente nem resiste ao uplift vertical);
      sapata sem tirante com **piso construtivo de 4 chumbadores** (ancoragem ao uplift,
      `succao_uplift` η=0,46). A [issue 37](37-tirante-piso-robustez-impacto-corrosao-fogo.md)
      (robustez do tirante no piso) deixa de se aplicar.
- [x] Rever a **[issue 24](24-tirante-fy315-flexibilidade.md)** — **feito** (via issue 38).
- [x] Coerência dos textos: `pilares.py` — **corrigido** (38).

### Consequência exposta (déficit real da Opção A que estava mascarado)
Sem o empuxo, o **cortante do beiral sobe 107→141 kN** e a ligação **L1/L1c falha ao
fendilhamento** (§8.1.4, `η=1,16>1`). Resolvido com **reforço ⊥ às fibras** (parafusos
autoatarraxantes, EC5 §8.7.2): `11×∅10 mm, l_ef=400 mm → η=0,71`. **Pipeline APROVADO,
η_max=1,00.**

## Critério de aceite
Modelo coerente sobre o empuxo: ou o beiral é efetivamente indeslocável (restrição real no
nível do beiral) e a viga/tirante refletem H≈483; ou assume-se sem empuxo e viga/tirante/ELS
são reavaliados para essa realidade. Flecha real (com abertura do beiral) verificada.
Conclusão da issue 24 revista.
