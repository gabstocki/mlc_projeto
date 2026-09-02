# 22 — Critério η-alvo 0,75: ligações com η≈1 — verificar ativação

- **Tema:** Ligações (critério de projeto)
- **Prioridade:** P1
- **Normas:** critério de projeto (fragilidade da ruptura em madeira)
- **Arquivos:** `mlc_projeto/connections/connections.py:604-614`, `:660`; `mlc_projeto/main.py:145`

## Apontamento do orientador
> Verificar se o critério de aprovação está ativado: tem duas ligações com 1 e o
> memorial diz que coeficiente-alvo de 0,75 para ligações, com fundamento correto na
> fragilidade da ruptura em madeira.

## Estado atual no código
- `ETA_LIG_ALVO = 0.75` ([main.py:145](../mlc_projeto/main.py)) — margem de projeto
  para ligações (uso público / ruptura frágil).
- Mas em vários pontos o `ok_alvo` é **contornado**:
  - Sapata **com tirante**: `ok_alvo = ok_norma` (η pode ir a ~1,0, não a 0,75):
    [connections.py:613-614](../mlc_projeto/connections/connections.py).
  - Sapata central L3c: `ok = eta_N ≤ 1.0` (η alvo não aplicado):
    [connections.py:878-879](../mlc_projeto/connections/connections.py).
- Resultado: ligações reportadas como OK com η≈1, contrariando o alvo 0,75 declarado.

## O que precisa ser feito
- [x] Definir **onde** o alvo 0,75 se aplica (modos FRÁGEIS) e aplicá-lo de forma
      consistente, com as exceções documentadas.
- [x] Garantir que o `ok` global reflita o critério (ok = η ≤ η_limite por modo).
- [x] Rever a tabela para não exibir "aprovado" com η>0,75 onde o alvo se aplica.

## Critério de aceite
Critério η-alvo 0,75 aplicado de forma consistente (ou exceções justificadas);
nenhuma ligação sujeita ao alvo aprovada com η>0,75.

---

## ✅ Resolução (implementada)

**Política formalizada** em [`connections/connections.py`](../mlc_projeto/connections/connections.py):
`ETA_ALVO_LIGACAO=0.75` + `classificar_criterio_eta(modo_fragil)` +
`aplicar_criterio_eta(res, modo_fragil)` (injeta `eta_limite`, `alvo_aplica`,
`criterio_eta` e recalcula `ok = η ≤ η_limite` [e `ok_geometria`]).

### Onde o alvo 0,75 se aplica — modos FRÁGEIS (sem redistribuição)
- Ruptura da madeira no grupo de cavilhas: **L1, L1c** (embutimento/n_ef).
- **Corte de bloco** (Anexo A): bloco L1/L1c.
- **Fendilhamento** (§8.1.4): fendilh. L1/L1c.
- **Ancoragem frágil no concreto** (cone/arrancamento): L3 sem tirante.

### Exceções justificadas — limite normativo η≤1,0 (NÃO é ruptura frágil da madeira)
- **Compressão no concreto** sob a chapa de base (L3 c/ tirante, L3c — esmagamento).
- **Compressão da madeira** na cumeeira (L2/L2c — §6.1.4/§6.1.5).
- **Aço dúctil** (chapa/furo/solda — EN 1993, issue 21).

### Aplicação e verificação (nada "vira" — era problema de transparência)
Bloco de política no `main.py` (Fase 4) classifica e imprime cada ligação:

| Ligação | η | modo | limite | ok |
|---|---|---|---|---|
| L1 | 0,709 | frágil | 0,75 | ✓ |
| L1c | 0,748 | frágil | 0,75 | ✓ |
| bloco L1/L1c | 0,271/0,496 | frágil | 0,75 | ✓ |
| fendilh. L1/L1c | 0,197/0,365 | frágil | 0,75 | ✓ |
| L2/L2c | 0,602 | compr. madeira | 1,0 | ✓ |
| **L3/L3c** | **1,000** | **compr. concreto** | **1,0** | ✓ (exceção) |
| chapa L1/L1c | 0,395/0,548 | aço dúctil | 1,0 | ✓ |

**Todos os modos frágeis ≤ 0,75** (L1c=0,748 é o máximo). As "duas ligações com 1"
(L3/L3c) são compressão no concreto — exceção legítima, agora explícita.

### Integração / documentação
- `main.py` Fase 4: bloco "Critério η-alvo" com tabela e guarda (avisa se algum
  modo frágil > 0,75).
- `output/report.py` §11: intro reescrita documentando a política e as exceções
  (por que L3/L3c aparecem com η=1,00 sem contrariar o alvo).
- **Testes:** [`tests/test_criterio_eta_alvo.py`](../tests/test_criterio_eta_alvo.py)
  (8 casos: classificação, frágil reprova >0,75, dúctil aprova até 1,0, geometria,
  L1/L1c sob alvo, L3/L3c exceção, critério de aceite).
