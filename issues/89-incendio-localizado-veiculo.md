# 89 — Robustez dos pilares adjacentes às vagas frente a incêndio localizado de veículo

- **Tema:** Incêndio
- **Prioridade:** P2 (recomendação)
- **Normas:** EN 1991-1-2 Anexo C (incêndio localizado), EN 1995-1-2
- **Arquivos:** `tese/cap07.tex` (situações acidentais) ou §7.8 / considerações finais
- **Relaciona:** 88
- **Origem:** 4ª revisão, item 5.2

## O que fazer
- [x] Comentar (mesmo com isenção) a robustez dos pilares adjacentes às vagas para o cenário de
      incêndio localizado de veículo — o cenário realista num estacionamento aberto. Estimativa
      qualitativa ou simplificada (Anexo C: chama localizada, taxa de liberação de calor de um carro).

## Resolução ✅

- **Módulo** `checks/elu/incendio_veiculo.py`; nova `ssec:incendio-veiculo` (cap07).
- **Chama do carro** (EN 1991-1-2 An. C): Q = 8,3 MW, D = 3,21 m → L_f = 5,39 m < 6,50 m. Não alcança a viga; pluma sob a viga a 390 °C, só carbonização superficial.
- **Pilar de madeira** (seção reduzida, faces atingidas como incêndio-padrão): colapso em 83 min (central) e 100 min (perímetro) com 4 faces, contra 54 min de 3 veículos em sequência (30 + 2 × 12). η 0,66.
- **Pilarete de aço sem proteção** (EN 1993-1-2 incremental, A_m/V = 125 m⁻¹):
  - 798 °C com 1 veículo, 923 °C com 3.
  - θ_cr pela Eq. 4.22: 855 °C no central (η 0,75 com 1 veículo; 1,53 com 3). O perímetro atende.
- **Decisão do usuário:** pintura intumescente em todos os pilaretes.
  - Sobre o zinco, no lugar do acabamento dúplex; sistema para exterior.
  - Dimensionada pelo fabricante (EN 13381-8) para R60, A_m/V 125 e θ_cr de projeto 750 °C → η 0,50.
  - Tabela de proteção (86) e plano de manutenção (84) atualizados; `NOTA_CORROSAO` com "pilarete com intumescente R60".
- **Pé do pilar:** força normal por contato; cavilhas descarregadas no incêndio (sem vento).
- **Catálogo:** `incendio_veiculo` (robustez). Bib: EN 1991-1-2, EN 1993-1-2, EN 13381-8.
- **TODO:** fonte da curva do automóvel (8,3 MW; 30 min; 12 min de propagação).
- **Testes:** `test_issue89_incendio_veiculo.py`. 818 passed. Tese 151 p., 0 overfull.

### Conferência com as normas (EN 1991-1-2 e EN 1993-1-2 em PDF na raiz)
- **Conferido sem mudança:**
  - EN 1991-1-2: Anexo C (C.1–C.3), validade D ≤ 10 m e Q ≤ 50 MW, α_c = 25 (§3.2.1).
  - EN 1993-1-2: ε_m = 0,7 (§2.2), Tab. 3.1, c_a (§3.4.1.2), Eq. 4.25 com Δt ≤ 5 s e k_sh = 1 para tubo, Tab. 4.2 (A_m/V ≈ 1/t), Eq. 4.22.
- **Corrigido:** a §4.2.4(2) não admite a Eq. 4.22 com instabilidade. O pilarete passou a ser verificado à flambagem em incêndio pela §4.2.3.2 (χ_fi, α = 0,65√(235/f_y), k_E,θ, l_cr = 2h).
- **Novos valores (pilarete central):**
  - θ_cr: 835 °C (era 855).
  - Sem proteção: η 0,84 com 1 veículo e 1,66 com 3.
  - Com intumescente: η 0,56.
  - Perímetro: 0,83 sem proteção.
- **Testes:** 819 passed.
