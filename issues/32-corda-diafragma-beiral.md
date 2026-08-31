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
- [ ] Definir o **elemento de beiral** (material/seção): perímetro em MLC, terça de
      beiral reforçada, ou perfil de aço.
- [ ] Verificar o membro para `N_corda` (tração e compressão — a corda inverte de sinal
      conforme o sentido do vento), combinado com sua flexão local se também for terça.
- [ ] Confirmar a continuidade/ligações das emendas da corda ao longo dos 46 m (a corda
      precisa ser contínua para o diafragma funcionar).
- [ ] Registrar no memorial e ligar ao resultado do contraventamento transversal.

## Critério de aceite
Elemento de beiral dimensionado e verificado como corda do diafragma (para `N_corda`,
tração e compressão), com continuidade das emendas garantida e registro no memorial.
