# 21 — Chapas de aço, furos e soldas (EN 1993-1-8)

- **Tema:** Ligações (componente metálico)
- **Prioridade:** P1
- **Normas:** EN 1993-1-8 (chapas, furos, soldas); EN 1993-1-1 (seção bruta/líquida)
- **Arquivos:** `mlc_projeto/connections/connections.py:92-156`, `:549-663`

## Apontamento do orientador
> Verificações ausentes para ligações: verificações das chapas de aço, furos e soldas
> da ligação conforme EN 1993-1-8.

## Estado atual no código
- O lado da madeira é dimensionado (Johansen, n_ef, distâncias); o lado do **aço** só
  aparece como `F_U_K_PINO` (pino) e como área de chapa de base por compressão no
  concreto ([connections.py:592-602](../mlc_projeto/connections/connections.py)).
- **Não há** verificação de: resistência da chapa embutida (tração/flexão da chapa),
  **pressão de contato/rasgamento nos furos** (bearing), **seção líquida**, nem
  **soldas** chapa↔chapa base.

## O que precisa ser feito
- [x] Verificar a **chapa embutida** de L1/L1c (seção bruta/líquida em tração) —
      EN 1993-1-1 §6.2.3.
- [x] Verificar **bearing/pressão de contato** e rasgamento nos furos — EN 1993-1-8 Tab. 3.4.
- [x] Verificar **cisalhamento do pino** de aço — EN 1993-1-8 Tab. 3.4.
- [x] Verificar as **soldas** chapa embutida ↔ chapa de base — EN 1993-1-8 §4.5.3.3.
- [x] Definir aço da chapa (**S275**) e furação (close-fit d₀=d), publicado no resumo/§12.

## Critério de aceite
Componentes metálicos das ligações verificados por EN 1993-1-8 (chapa, furos, soldas),
com resultados no memorial.

---

## ✅ Resolução (implementada)

**Módulo novo:** [`connections/chapas_aco.py`](../mlc_projeto/connections/chapas_aco.py)
— `verificar_chapas_aco(...)` + adaptador `chapas_aco_ligacao(...)`. Escopo escolhido
pela usuária: **aço S275 + completo com soldas**.

### As quatro verificações (EN 1993-1-8 / EN 1993-1-1)
1. **Cisalhamento do pino** (Tab. 3.4): `F_v,Rd = n_planos·α_v·f_ub·A/γ_M2`
   (α_v=0,6; f_ub=400 MPa; 2 planos — chapa central).
2. **Bearing/rasgamento no furo** (Tab. 3.4): `F_b,Rd = k1·α_b·f_u·d·t_p/γ_M2`
   (α_b=min(α_d, f_ub/f_u, 1); k1=min(2,8·e2/d0−1,7; 1,4·p2/d0−1,7; 2,5); d0=d close-fit).
3. **Seção líquida da chapa** (EN 1993-1-1 §6.2.3): `N_t,Rd = min(A·f_y/γ_M0;
   0,9·A_net·f_u/γ_M2)`, A_net desconta as n_linhas fileiras. Avaliada com F_res
   (envelope conservador — a tração da chapa ocorre nas combinações de sucção).
4. **Solda chapa↔base** (§4.5.3.3): `f_vw,d=(f_u/√3)/(β_w·γ_M2)`, β_w=0,85 (S275);
   duplo filete l=2·h_p, garganta a declarada.

### Decisões DECLARADAS (confirmar detalhamento — issue 23)
- Aço **S275** (f_y=275, f_u=430 MPa); γ_M0=1,00, γ_M2=1,25.
- Chapa embutida **t_p=16 mm**; solda de filete **a=6 mm**.
- Redução de fila longa β_Lf (EN 1993-1-8 §3.8) aplicada (L1: β_Lf=0,93).

### Resultado (S275, t_p=16 mm, a=6 mm)
| Ligação | pino | bearing | sec. líquida | solda | η gov |
|---|---|---|---|---|---|
| **L1**  | 0,082 | 0,046 | 0,314 (rupt. líq.) | **0,395** | 0,395 (solda) ✓ |
| **L1c** | 0,095 | 0,054 | 0,405 (rupt. líq.) | **0,548** | 0,548 (solda) ✓ |

L1c mais solicitada (menos pinos por chapa; caminho de meia-espessura). A solda
governa em ambas.

### Integração
- `main.py` Fase 4: constantes `ACO_CHAPA_LIG="S275"`, `T_CHAPA_MM=16`,
  `A_SOLDA_MM=6`; `res_elu["chapa_aco_L1"]`/`["chapa_aco_L1c"]`.
- `output/report.py`: duas linhas novas no catálogo (resumo/Excel/§12).
- **Testes:** [`tests/test_chapas_aco.py`](../tests/test_chapas_aco.py)
  (9 casos: fórmulas das 4 verificações, limites α_b/k1, efeito de aço/espessura,
  β_Lf de fila longa, entradas inválidas, L1 real).

### Nota de escopo
L2/L2c (cumeeira, peça monolítica) não têm chapa de grupo carregada — a
transferência ali é compressão distribuída (§6.1.4/6.1.5, já verificada).
As soldas dos chumbadores de L3 dependem do detalhe da base (issue 23).
