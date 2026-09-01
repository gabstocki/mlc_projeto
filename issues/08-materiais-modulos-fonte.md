# 08 — E0,mean / E0,05 sem fonte; EN 1194:1999 revogada

- **Tema:** Materiais
- **Prioridade:** P2
- **Normas:** EN 14080:2013 (glulam); **EN 1194:1999 revogada**
- **Arquivos:** `mlc_projeto/core/materials.py:24-29` (GL24h)

## Apontamento do orientador
> Entre a primeira e a segunda versão, E0,mean passou de 11.500 para 11.600 MPa e
> E0,05 de 9.600 para 9.400 MPa, sem justificativa no memorial. Conferir os três
> valores na tabela da norma e citar a fonte — tenha cuidado que a EN 1194:1999 foi
> revogada.

## Estado atual no código
- GL24h em [materials.py:24-29](../mlc_projeto/core/materials.py):
  `E0_mean = 11600e6`, `E0_05 = 9400e6`, `G_mean = 720e6`.
- Cabeçalho cita "EN 14080:2013 Tabela 1 (homogéneo)"
  ([materials.py:4-8](../mlc_projeto/core/materials.py)), mas os valores mudaram
  entre versões sem nota.

## O que precisa ser feito
- [x] Conferir os **três** valores (E0,mean, E0,05, G_mean) na tabela vigente da
      **EN 14080:2013** para GL24h e citar a fonte exata (tabela/linha).
- [x] Garantir que nenhuma referência remeta à **EN 1194:1999** (revogada).
- [x] Registrar no memorial a justificativa de qualquer alteração entre versões.
- [x] Conferir também as demais classes usadas e ρ_k/ρ_mean.

## Critério de aceite
Módulos de GL24h coincidentes com a EN 14080:2013, com fonte citada e sem referência
à norma revogada.

## Resolução (2026-08-31)
**Diagnóstico:** o código misturava valores da EN 14080:2013 (f_v,k, f_t90,k,
f_c90,k, algumas densidades) com valores da **EN 1194:1999 REVOGADA** (módulos e
f_c0 de GL24h/28h/32h). Os valores atuais do GL24h (11600 / 9400 / 720) são
exatamente os da EN 1194:1999 — o alerta do orientador estava certo. A alteração
"11500→11600 e 9600→9400" entre versões foi, na verdade, uma **regressão** para a
norma revogada.

**Fonte conferida:** EN 14080:2013 §5.1.6, **Tabela 5** ("Characteristic strength
and stiffness properties in N/mm² and densities in kg/m³ for homogeneous glulam"),
texto integral da norma. Valores de G_mean=650, G_05=540, E90,mean=300, f_v,k=3,5,
f_t90,k=0,5, f_c90,k=2,5 são **constantes** para todas as classes homogéneas.

**Correções em [materials.py](../mlc_projeto/core/materials.py)** (novo → antigo EN 1194):
| Classe | E0,mean | E0,05 | G_mean | f_c0,k | ρ_k | ρ_mean |
|--------|---------|-------|--------|--------|-----|--------|
| GL20h  | 8400    | 7000  | **650** (540) | 20 | 340 | 370 |
| GL24h  | **11500** (11600) | **9600** (9400) | **650** (720) | 24 | 385 | 420 |
| GL28h  | 12600 | **10500** (10200) | **650** (780) | **28,0** (26,5) | **425** (410) | **460** (450) |
| GL32h  | 14200 | **11800** (11600) | **650** (850) | **32,0** (29,0) | 440 | **490** (480) |

**Impacto no dimensionamento** (projeto usa GL24h):
- G_mean 720→650 (−9,7%) e E0,mean 11600→11500 (−0,9%): flecha ELS sobe pouco
  (w_net,fin 1,13→1,18 mm; a parcela de cisalhamento da issue 7 cresce ~11%);
  η_ELS≈0,015 permanece ≪ 1.
- E0,05 9400→9600 (+2,1%): flambagem lateral/pilar levemente **menos**
  conservadora (σ_m,crit ∝ E0,05). Nenhuma verificação muda de estado.
- f_c0 de GL28h/32h corrigido, mas fora do caminho crítico (projeto = GL24h).
- **Cross-impact issue 7:** a flecha de cisalhamento agora usa G=650 (não 720).

**Testes:** `tests/test_materials.py` fixa os valores da EN 14080:2013 e uma
regressão que rejeita explicitamente os valores da EN 1194:1999. Suíte: 114 passam.
