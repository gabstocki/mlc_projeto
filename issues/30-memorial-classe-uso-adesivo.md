# 30 — Declarar classe de uso (EN 335), adesivo (EN 301) e tratamento preservativo

- **Tema:** Reprodutibilidade do memorial / durabilidade
- **Prioridade:** P2
- **Normas:** EN 335 (classe de uso), EN 301 (adesivo), EN 14080 (glulam), EN 335/351 (tratamento)
- **Arquivos:** `mlc_projeto/core/materials.py`; `mlc_projeto/main.py:76-93`; memorial

## Apontamento do orientador
> [Bloco de reprodutibilidade] Declarar classe de uso (EN 335), o tipo de adesivo
> (EN 301) e o tratamento preservativo.

## Estado atual no código
- O projeto adota **Classe de Serviço 3** (EC5 §2.3.1.3) — estrutura aberta/intempérie
  ([main.py:76-87](../mlc_projeto/main.py)) e k_def/k_mod de CS3.
- **Não** há declaração da **classe de uso EN 335** (biológica), nem do **adesivo
  EN 301** (tipo I/II), nem do **tratamento preservativo**.

## O que precisa ser feito
- [x] Classe de uso **EN 335 UC3.1** (coerente com CS3; coberto mas aberto).
- [x] Adesivo **EN 301 Tipo I** (obrigatório p/ CS3, EN 14080 §5.3).
- [x] Tratamento preservativo **EN 351** + detalhamento de proteção, justificado.
- [x] Registrado no memorial (§5b Durabilidade).

## Critério de aceite
Classe de uso EN 335, adesivo EN 301 e tratamento preservativo declarados e
justificados no memorial, coerentes com a CS3 adotada.

---

## ✅ Resolução (implementada)

Declarações de durabilidade em `main.DURABILIDADE`, coerentes com a CS3, fixadas
pela norma onde ela não deixa escolha:

- **Classe de uso (EN 335): UC3.1** — exterior acima do solo, umedecimento
  limitado (coberto pelo telhado, mas aberto nas laterais). Mapeia na CS3 do EC5;
  peças plenamente abrigadas poderiam ser UC2 (nota).
- **Adesivo (EN 301): Tipo I** — exigido para CS3 (EN 14080 §5.3), apto a exposição
  exterior/alta umidade (ex.: MUF ou resorcina RF/PRF).
- **Espécie / durabilidade natural:** conífera (Picea/Pinus), EN 350 classe 4
  (baixa) → em UC3 requer tratamento e/ou proteção por detalhamento.
- **Tratamento preservativo (EN 351):** impregnação das lamelas antes da colagem
  (classe de penetração/retenção conforme UC3.1), COMPLEMENTADA por detalhamento
  de proteção (beirais/pingadeiras, drenagem, ventilação, sem acúmulo de água) e
  acabamento; confirmar biocida/retenção com o tratador no projeto executivo.

### Integração
- `main.py`: dict `DURABILIDADE` + linha na Fase 0 + `meta["durabilidade"]`.
- `output/report.py`: subseção **§5b Durabilidade** (EN 335/301/351) no memorial.
- **Testes:** [`tests/test_durabilidade.py`](../tests/test_durabilidade.py) (5 casos:
  CS3, UC3, adesivo Tipo I, tratamento com norma+detalhamento, durab. natural).
