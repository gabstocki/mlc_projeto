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
- [ ] Conferir os **três** valores (E0,mean, E0,05, G_mean) na tabela vigente da
      **EN 14080:2013** para GL24h e citar a fonte exata (tabela/linha).
- [ ] Garantir que nenhuma referência remeta à **EN 1194:1999** (revogada).
- [ ] Registrar no memorial a justificativa de qualquer alteração entre versões.
- [ ] Conferir também as demais classes usadas e ρ_k/ρ_mean.

## Critério de aceite
Módulos de GL24h coincidentes com a EN 14080:2013, com fonte citada e sem referência
à norma revogada.
