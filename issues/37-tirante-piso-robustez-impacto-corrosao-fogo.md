# 37 — Tirante ao nível do piso em estacionamento: impacto veicular, corrosão, fogo e tropeço não verificados

- **Tema:** Ações acidentais / Durabilidade / Robustez / Tirante de base
- **Prioridade:** P1 (ação acidental e durabilidade sobre o elemento que fecha o empuxo; hoje inteiramente delegado a "execução")
- **Normas:** EN 1991-1-7 (ações acidentais — impacto de veículo); EN 1990 §A1 / §6.4 (combinação acidental); EN 335 (classe de uso) / EN ISO 12944 (corrosividade); EN 1993-1-2 (aço em situação de incêndio); EN 1995-1-1 §2.3 / uso público
- **Arquivos:** `mlc_projeto/checks/elu/tirante_base.py:173` (punt para "execução"); `mlc_projeto/checks/elu/impacto_veiculo.py` (já existe p/ pilares, F_dx=50 kN / F_dy=25 kN); `mlc_projeto/visualization/viz_3d.py:301` (`z_tir=0.08 m`); `mlc_projeto/main.py` (Fase 2 impacto; Fase 4a tirante)
- **Relaciona:** [24](24-tirante-fy315-flexibilidade.md), [33](33-succao-uplift-ancoragem-tirante.md), [35](35-empuxo-pilar-caminho-carga.md), [38](38-caminho-horizontal-transversal-coerencia.md), [30](30-memorial-classe-uso-adesivo.md).

> **⚠ Superada pela Opção B (issue 35 implementada):** ao assumir que o empuxo não se
> desenvolve, o **tirante de base foi REMOVIDO** (não fecha empuxo inexistente nem resiste
> ao uplift vertical). Sem tirante no piso, esta issue (impacto/corrosão/fogo/tropeço do
> tirante) **deixa de se aplicar**. O módulo `tirante_piso_robustez.py` e a verificação
> ficam disponíveis caso a Opção A volte a ser considerada (`EMPUXO_DESENVOLVE=True` +
> `TIRANTE_BASE=True`). Mantido como referência.

## Origem
Apontamento do orientador (revisão do "caminhamento horizontal transversal"):
o tirante que fecha o empuxo está modelado **ao nível do piso** (`z_tir ≈ 0,08 m`,
`L_m = vão`) atravessando o **estacionamento**. Enquanto o empuxo em si é tratado nas
issues [35](35-empuxo-pilar-caminho-carga.md)/[38](38-caminho-horizontal-transversal-coerencia.md),
a **exposição física** desse elemento a `8 cm` do piso é uma lacuna separada:
[tirante_base.py:173](../mlc_projeto/checks/elu/tirante_base.py) apenas registra
*"Ancoragem nas bases e proteção a impacto (estacionamento) a detalhar em projeto de
execução"* — nenhuma verificação a consome.

## Problema (verificações ausentes para o TIRANTE — não para o pilar)
O projeto **já** verifica o impacto de veículo **nos pilares**
([impacto_veiculo.py](../mlc_projeto/checks/elu/impacto_veiculo.py), `F_dx=50 kN`,
`F_dy=25 kN`, EN 1991-1-7, `η=0,48` — [pipeline_console.txt:89](../output/pipeline_console.txt)).
O **tirante ao nível do piso** vê a **mesma ação acidental** e hoje não é verificado:

1. **Impacto de veículo (EN 1991-1-7).** Barra ∅48 mm a 8 cm do piso, no plano de
   marcha, exposta a `F_d`. Um impacto transversal pode dobrar/romper a barra ou
   arrancar a ancoragem → **perda do fecho do empuxo** (se a decisão da
   [issue 38](38-caminho-horizontal-transversal-coerencia.md) for a Opção A, o tirante
   é elemento primário; sua perda muda o caminho de carga). Verificar na **combinação
   acidental** (EN 1990) e/ou **proteger fisicamente** (guarda-rodas/mureta/embutir em
   canaleta no contrapiso).
2. **Corrosão / classe de uso.** Aço nu em piso de estacionamento (umidade, sais,
   respingos) → **EN 335 UC3 / corrosividade EN ISO 12944 (C3+)**. `MR315` é declarado
   como "confirmar produto/norma" ([tirante_base.py:38-42](../mlc_projeto/checks/elu/tirante_base.py));
   falta especificar proteção (galvanização/pintura), classe de corrosividade e
   eventual sobreespessura de sacrifício. Coerência com a [issue 30](30-memorial-classe-uso-adesivo.md).
3. **Incêndio (EN 1993-1-2).** Barra de aço exposta perde resistência rapidamente; se
   o tirante for elemento primário (Opção A), avaliar tempo de resistência / proteção
   ou justificar caminho alternativo em incêndio.
4. **Tropeço / serventia.** Barra a 8 cm sobre piso de circulação de pessoas/veículos
   é obstáculo — embutir ou sinalizar; requisito de uso público.

> Observação de modelo: parte do risco só é **crítico** se a decisão da
> [issue 38](38-caminho-horizontal-transversal-coerencia.md) mantiver o tirante como
> **fecho de empuxo primário** (Opção A). Se a decisão for a Opção B (sem empuxo, viga
> biapoiada), o tirante deixa de ser primário para gravidade e resta apenas a função de
> **ancoragem ao uplift** ([issue 33](33-succao-uplift-ancoragem-tirante.md)) — mesmo
> assim exposta às mesmas ações. Por isso esta issue é **independente** mas deve ser
> lida **após** a decisão da 38.

## O que precisa ser feito
- [x] Verificar o tirante e sua ancoragem à **ação acidental de impacto** (EN 1991-1-7,
      `F_dx=50 / F_dy=25 kN`) na **combinação acidental** (EN 1990), **ou** especificar
      **proteção física** (guarda-rodas/mureta/embutimento) que dispense a verificação —
      documentar a opção adotada.
- [x] Especificar **classe de corrosividade** e **proteção anticorrosiva** do tirante e
      da ancoragem (EN 335 / EN ISO 12944), coerente com a classe de serviço 3 e com a
      [issue 30](30-memorial-classe-uso-adesivo.md).
- [x] Avaliar/justificar o **comportamento em incêndio** (EN 1993-1-2) do tirante caso
      seja elemento primário.
- [x] Tratar **tropeço/serventia** (embutir em canaleta ou solução equivalente) e
      registrar no detalhamento.
- [x] Substituir a nota "a detalhar em execução" de
      [tirante_base.py:173](../mlc_projeto/checks/elu/tirante_base.py) por verificação
      efetiva **ou** por requisito de projeto explícito e rastreável no memorial.

## Critério de aceite
O tirante ao nível do piso tem impacto veicular (EN 1991-1-7), corrosão (EN 335 /
EN ISO 12944), incêndio (EN 1993-1-2, se primário) e tropeço tratados por verificação
ou por requisito de projeto explícito no memorial — não mais delegados genericamente a
"execução". A dependência da decisão de modelo da [issue 38](38-caminho-horizontal-transversal-coerencia.md)
está registrada.

---

## ✅ Resolução (implementada)

**Decisões de projeto** (confirmadas com a usuária): proteção = **tirante embutido em
canaleta no contrapiso**; papel = **primário** (fecho de empuxo — conservador enquanto a
[issue 38](38-caminho-horizontal-transversal-coerencia.md) não fecha a decisão A/B).

### Novo módulo
- **[`checks/elu/tirante_piso_robustez.py`](../mlc_projeto/checks/elu/tirante_piso_robustez.py)**:
  `verificar_robustez_tirante_piso(...)` orquestra quatro frentes e devolve η governante,
  `ok` e a lista de `requisitos` (rastreável no memorial):
  - **Impacto (EN 1991-1-7):** modela a **barra nua** ao choque transversal
    (`M_Ed = F·L/4` vs `M_pl,Rd = f_y·d³/6`). Para ∅48 no vão de 20,25 m dá **η≈44**
    (não resiste) — justificando que a proteção é **obrigatória**, não opcional. Com o
    tirante **embutido**, a laje **intercepta** o choque (`η_impacto = 0`): a proteção é
    o elemento verificado, não a barra.
  - **Corrosão (EN 335 UC3 / EN ISO 12944 C3):** sobreespessura de sacrifício
    `Δr=1,0 mm` → `d_ef=46 mm` (−8% de `N_t,Rd`); tração reverificada na seção efetiva
    dá **η=0,722** — **governa** a robustez (< 1,0, e sob o alvo 0,75).
  - **Incêndio (EN 1993-1-2):** o cobrimento da canaleta (argamassa/graute) funciona como
    proteção passiva → requisito atendido por cobrimento mínimo.
  - **Tropeço/serventia:** barra sob o piso acabado (embutida) → sem obstáculo.
- Módulo **parametrizado** por `protecao` ∈ {embutido, guarda_rodas, nenhuma} e `primario`
  (bool) — troca de estratégia sem reescrever o código.

### Integração
- **`main.py`** (Fase 4a): novas constantes `PROTECAO_TIRANTE="embutido"` e
  `TIRANTE_PRIMARIO=True`; chama a verificação após o diagnóstico de flexibilidade e
  imprime o bloco `[issue 37]`. Resultado em `res_tirante["robustez_piso"]` e
  `res_elu["tirante_piso_robustez"]`.
- **`output/report.py`**: nova linha no catálogo (§12, "Robustez tirante piso") + nova
  **subseção 10c** do memorial com os quatro aspectos e o `\registonota` dos requisitos
  de projeto — substitui a nota genérica "a detalhar em execução".

### Verificação
- **Testes:** [`tests/test_tirante_piso_robustez.py`](../tests/test_tirante_piso_robustez.py)
  (16 casos: impacto barra-nua/embutido/guarda-rodas, corrosão monotônica e sob alvo,
  incêndio primário×não-primário, tropeço, orquestrador). Suíte: **261 testes ✓**.
- **Pipeline:** **APROVADO, η_max=1,00**; robustez do tirante **η=0,722 ✓** (governa
  corrosão; impacto interceptado pela proteção). PDF/Excel regenerados (subseção 10c no
  memorial).

### Dependência registrada
A criticidade de incêndio/impacto pressupõe o tirante **primário**. Se a
[issue 38](38-caminho-horizontal-transversal-coerencia.md) adotar a **Opção B** (sem
empuxo; tirante só para uplift), basta rodar com `TIRANTE_PRIMARIO=False` — o incêndio
deixa de ser crítico (a corrosão continua governando a robustez).
