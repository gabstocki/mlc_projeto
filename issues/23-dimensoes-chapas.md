# 23 — Dimensões das chapas não publicadas (incl. base do pilar central)

- **Tema:** Ligações / memorial
- **Prioridade:** P2
- **Normas:** —
- **Arquivos:** `mlc_projeto/connections/connections.py:832-910`; `mlc_projeto/output/report.py`

## Apontamento do orientador
> Dimensões de algumas chapas não publicadas no memorial.
> [Bloco de reprodutibilidade] Dimensões da chapa de base do pilar central.

## Estado atual no código
- A sapata calcula `A_chapa_cm2` e `lado_chapa_cm`
  ([connections.py:600-601](../mlc_projeto/connections/connections.py),
  [:867-868](../mlc_projeto/connections/connections.py)), mas **espessuras** das chapas
  e as dimensões das **chapas embutidas** de L1/L2 não são calculadas nem publicadas.
- A chapa de base do **pilar central** (L3c) tem área, mas falta detalhamento completo
  no memorial.

## O que precisa ser feito
- [x] Publicar no memorial todas as dimensões das chapas: base (L3/L3c), embutidas
      (L1/L1c), incluindo **espessura**, largura, altura e furação.
- [x] Ligar às verificações metálicas da issue [21](21-chapas-aco-en1993.md)
      (a espessura sai do dimensionamento, não pode ser arbitrada).
- [x] Incluir a chapa de base do pilar central (L3c) explicitamente.

## Critério de aceite
Todas as chapas dimensionadas e publicadas (com espessura) no memorial, incluindo a do
pilar central.

---

## ✅ Resolução (implementada)

**Módulo novo:** [`connections/chapas_dim.py`](../mlc_projeto/connections/chapas_dim.py)
— `espessura_chapa_embutida`, `espessura_chapa_base` e `esquadro_chapas`.

### A espessura SAI do dimensionamento (não arbitrada)
**Chapa embutida (L1/L1c)** — t_p = máx de:
- **t_thick = d** (chapa central rígida — para o pino desenvolver a rótula
  plástica na face da chapa, base dos modos de Johansen usados em L1/L1c);
- t_gross = F_res·γ_M0/(f_y·h_p) (escoamento bruto);
- t_net = F_res·γ_M2/(0,9·f_u·(h_p−n·d0)) (ruptura líquida);
- t_bear = F_1,Ed·γ_M2/(k1·α_b·f_u·d) (bearing);
- t_det = 8 mm (mínimo construtivo).

**Chapa de base (L3/L3c)** — t_base = c·√(3·σ_c·γ_M0/f_y) (flexão do balanço c,
EN 1993-1-8 §6.2.5). Dimensões = pilar + 2c (área de apoio + borda do chumbador).

### 🔎 Achado (liga à issue 21)
Para o pino Ø24, **t_thick = d = 24 mm GOVERNA** as chapas embutidas → adota-se
**25 mm** (comercial). Os **16 mm arbitrados na issue 21 eram inconsistentes** com a
hipótese de chapa grossa da capacidade de Johansen de L1/L1c. O `main.py` agora
alimenta a issue 21 com a espessura do esquadro (25 mm) — bearing/seção líquida
caíram (mais folga), solda inalterada; tudo continua ✓.

### Esquadro publicado (S275)
| Chapa | Tipo | Larg×Alt (mm) | t_req | t_adot | Governa |
|---|---|---|---|---|---|
| L1  | embutida | 1296×1000 | 24,0 | **25,0** | t≥d (rígida) |
| L1c | embutida | 1896×720  | 24,0 | **25,0** | t≥d (rígida) |
| L3  | base | 400×400 | 8,3 | **9,5** | flexão balanço |
| **L3c** | base | 514×514 | 15,6 | **16,0** | flexão balanço |

Furação: L1/L1c 84 furos Ø24 (ajustado); L3/L3c 4 furos Ø22 p/ chumbador Ø20 (borda ≥40 mm).

### Integração
- `main.py` Fase 4: `esquadro_chapas(...)`, `res_elu["esquadro_chapas"]`;
  a espessura adotada alimenta as verificações da issue 21 (não mais T_CHAPA_MM fixo).
- `output/report.py` §11: subseção "Esquadro de chapas" publica a tabela completa,
  incluindo a base do pilar central (L3c).
- **Testes:** [`tests/test_chapas_dim.py`](../tests/test_chapas_dim.py) (6 casos:
  arredondamento comercial, t≥d governa embutida, dimensões, flexão do balanço,
  L3c≥L3, esquadro completo com central).
