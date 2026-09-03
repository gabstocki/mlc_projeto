# 32 — Elemento de beiral como corda do diafragma de cobertura

- **Tema:** Estabilidade global / contraventamento
- **Prioridade:** P2
- **Normas:** EC5 §6.2.3 / §6.3.2 (tração/compressão + instabilidade do membro); EN 1993-1-1 §6.2.3 (se aço)
- **Arquivos:** `mlc_projeto/checks/elu/contraventamento_transversal.py` (fornece `N_corda_kN`); verificação de membro inexistente

## Origem
Desdobramento da issue [31](31-estabilidade-transversal-portico.md). O contraventamento
transversal modela a cobertura como um **diafragma horizontal** (viga entre frontões).
As **cordas/banzos** desse diafragma são os elementos de **beiral** (perímetro da
cobertura), que recebem a força axial `N_corda = M_diaf / B_cob`. Essa força é hoje
**calculada e reportada** (`N_corda_kN`), mas **não é verificada** num elemento de
membro — o beiral não existe como seção dimensionada no modelo.

## Estado atual
- [contraventamento_transversal.py](../mlc_projeto/checks/elu/contraventamento_transversal.py)
  devolve `N_corda_kN` (ex.: ≈ 8,6 kN na configuração atual) e a nota de que essa força
  deve ser somada ao elemento de beiral.
- Não há seção nem verificação do elemento de beiral no pipeline.

## O que precisa ser feito
- [x] Elemento de beiral definido: **terça de beiral** em MLC GL24h (contínua).
- [x] Membro verificado para `N_corda` em **tração E compressão** (inverte com o vento),
      combinado com a flexão local (terça de borda).
- [x] Continuidade/emendas da corda ao longo dos 46 m (nº e força por emenda).
- [x] Registrar no memorial e ligar ao contraventamento transversal.

## Critério de aceite
Elemento de beiral dimensionado e verificado como corda do diafragma (para `N_corda`,
tração e compressão), com continuidade das emendas garantida e registro no memorial.

---

## ✅ Resolução (implementada)

**Módulo novo:** [`checks/elu/corda_beiral.py`](../mlc_projeto/checks/elu/corda_beiral.py)
— `verificar_corda_beiral(...)`.

### Elemento adotado
A **terça de beiral** (MLC GL24h, seção 0,20×0,58, mesma das terças) atua como
**banzo do diafragma**, contínua ao longo dos 46 m. É um membro flexo-axial:
flexão local (terça de borda, tributária s/2) + N_corda (do contraventamento
transversal), que **inverte de sinal** com o sentido do vento.

### Verificação (ambos os sinais)
- **Flexo-COMPRESSÃO** — EC5 §6.3.2 Eq. (6.23)/(6.24), com flambagem k_c,y/k_c,z:
  η ≈ 0,090.
- **Flexo-TRAÇÃO** — EC5 §6.2.3 Eq. (6.17)/(6.18), termo axial ÷f_t0d: η ≈ 0,091 (governa).
- **η governante ≈ 0,091 → APROVADO** (N_corda=7,6 kN é pequeno; diafragma muito
  profundo B_cob≈2·L). Reutiliza `verifica_terca` para a flexão concomitante.

### Continuidade (obrigatória)
Corda contínua nos 46 m: **3 emendas** (barras ~11,75 m), cada uma transferindo
N_corda=7,6 kN em **tração e compressão** (chapa/parafusos, §8) — sem continuidade
o diafragma não funciona.

### Integração
- `main.py` Fase 2: `res_elu["corda_beiral"]`, lê `N_corda_kN` do contraventamento
  transversal (acoplamento explícito).
- `output/report.py`: linha no catálogo (resumo/§12) + nota atualizada no §8b.2
  (antes dizia "verificação à parte"; agora mostra o resultado e as emendas).
- **Testes:** [`tests/test_corda_beiral.py`](../tests/test_corda_beiral.py) (6 casos:
  ambos os sinais, σ_N, Eq.6.17 com f_t0d, escala com N, emendas, corda leve aprova).
