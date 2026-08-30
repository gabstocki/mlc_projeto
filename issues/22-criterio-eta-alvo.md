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
- [ ] Definir **onde** o alvo 0,75 se aplica (todas as ligações estruturais frágeis?)
      e aplicá-lo de forma consistente, ou documentar explicitamente as exceções
      (ex.: η_N de compressão no concreto não é ruptura frágil da madeira).
- [ ] Garantir que o `ok` global reflita o critério declarado no memorial.
- [ ] Rever a tabela de verificações para não exibir "aprovado" com η>0,75 onde o alvo
      se aplica.

## Critério de aceite
Critério η-alvo 0,75 aplicado de forma consistente (ou exceções justificadas);
nenhuma ligação sujeita ao alvo aprovada com η>0,75.
