# 26 — Situação de içamento da viga (combinação de montagem)

- **Tema:** Modelo — situações transitórias
- **Prioridade:** P1
- **Normas:** EN 1991-1-6 (ações durante a execução); EC5 (verificação da peça)
- **Arquivos:** verificação inexistente (novo módulo em `checks/elu/`)

## Apontamento do orientador
> Falta verificação de situação de içamento da viga maciça — combinação ao menos.

## Estado atual no código
- O pipeline verifica apenas a estrutura **em serviço**; não há nenhuma verificação
  da fase **transitória de montagem/içamento** da viga de MLC.

## Por que importa
No içamento, a viga é apoiada/suspensa em pontos diferentes dos apoios definitivos,
gerando **momentos e cortantes com sinais e posições distintos** (momento negativo nos
pontos de içamento, viga em balanço, possível flambagem lateral com contenção mínima).
É uma situação de projeto por si.

## O que precisa ser feito
- [x] Esquema de içamento definido (confirmado com a projetista).
- [x] Combinação de içamento (peso próprio × γ_G × φ_dyn dinâmico, EN 1991-1-6).
- [x] Flexão (M⁻ e M⁺), cortante e **flambagem lateral sem contraventamento**.
- [x] Registrar no memorial.

## Critério de aceite
Ao menos uma combinação de içamento verificada (flexão/cortante/LTB), com o esquema de
suspensão documentado.

---

## ✅ Resolução (implementada)

**Módulo novo:** [`checks/elu/icamento.py`](../mlc_projeto/checks/elu/icamento.py)
— `verificar_icamento(...)`.

### Esquema (confirmado pela projetista)
- **2 pontos** de suspensão simétricos a **0,207·L** (posição que equilibra |M⁻|=|M⁺|);
- **lingas inclinadas** (30° da vertical) direto ao gancho → compressão axial N_c;
- viga **SEM contraventamento** (terças não montadas) → LTB no vão entre pontos.

### Combinação (EN 1991-1-6)
`w_d(x) = γ_G·φ_dyn·γ_glulam·A(x)` com γ_G=1,35, φ_dyn=1,10 (amplificação dinâmica),
seção variável A(x); duração **instantânea** (k_mod=0,90).

### Estática e verificações (numéricas, seção variável)
2 pontos → M⁻ nos balanços, M⁺ no vão, V nos pontos. Resultados:
- W_d=75 kN, R=38 kN/ponto; **M⁻=−21, M⁺=63 kN·m, V=26 kN**; N_c(lingas)=22 kN.
- η_flexão=0,009 · η_cisalh=0,042 · **η_LTB(Eq.6.35)=0,011** (l_ef=11,9 m, k_crit=0,797).
- **η governante = 0,042 (cisalhamento) → APROVADO**.

### Achado
Os momentos de **peso próprio** na montagem são pequenos face aos de serviço; mesmo a
**LTB sem contraventamento** (k_crit=0,80, l_ef=11,9 m) dá η baixo porque a solicitação
é baixa. A viga está segura no içamento com folga ampla.

### Integração
- `main.py` Fase 2: constantes A_ICAM_REL/GAMMA_G_ICAM/PHI_DYN_ICAM/PSI_LINGA_DEG;
  `res_elu["icamento"]`.
- `output/report.py`: linha no catálogo (resumo/§12) + subseção no memorial (§8)
  com o esquema, a combinação e os η, mais a ressalva de confirmar o rigging.
- **Testes:** [`tests/test_icamento.py`](../tests/test_icamento.py) (8 casos:
  peso/reações, sinais de M, pontos 0,207L, duração instantânea, N_c das lingas,
  LTB k_crit<1, escala com φ_dyn, governante/ok).
