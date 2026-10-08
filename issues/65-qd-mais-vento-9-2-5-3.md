# 65 — EC5 §9.2.5.3: q_d atua “além” das ações externas (vento) — soma, não máximo

- **Tema:** Contraventamento da cobertura — combinação de forças
- **Prioridade:** P2 (impacto numérico pequeno hoje: 1,4 kN sobre 104,7 kN)
- **Normas:** EN 1995-1-1 §9.2.5.3(1) e (2); EN 1990 §6.4.3.2
- **Arquivos:** `mlc_projeto/checks/elu/contraventamento.py` (`R_ext_proj = max(R_estab, R_vento0)`; `q_flecha = max(...)`)
- **Origem:** achado ao resolver a [issue 41](41-ell-contraventamento-9-2-5.md)

## Problema
A EN 1995-1-1 §9.2.5.3 pede que o sistema resista a q_d **em adição** aos efeitos das ações
horizontais externas (ex.: vento), e a flecha ℓ/500 sob q_d **e** essas ações. O código usa o
**máximo** das duas parcelas. Conferir a redação exata no texto normativo.

## O que fazer
- [ ] Confirmar a redação de §9.2.5.3(1)/(2).
- [ ] Definir a concomitância: N_d (estabilização) deve vir da mesma combinação do vento
      θ=0° (não da envoltória com vento θ=90°).
- [ ] Trocar max por soma na força e na flecha; atualizar testes e relatório.

## Resolução ✅ (2026-10-06)

**Norma:** EN 1995-1-1 §9.2.5.3(1) — o sistema resiste a q_d *“in addition to the effects of
external horizontal load (e.g. wind)”*; (2) — deslocamento ≤ ℓ/500 sob q_d **e** essas ações.
(Texto da norma não disponível em fonte aberta; redação confirmada indiretamente pela pesquisa
da Univ. Stuttgart sobre contraventamento de vigas de MLC sujeitas a LTB, que trata a soma.)

**Código** — `checks/elu/contraventamento.py`: `R_ext_proj = R_estab + R_vento0` (era máx) e
`q_flecha = q_d + q_vento0`. **Concomitância:** q_d vem da envoltória de N_d sobre todas as
combinações, não da combinação com vento θ=0° — a soma é conservadora (declarado no código/tese).
Testes: cenário de `test_contraventamento_cobertura.py` atualizado para a Opção B
(`empuxo_desenvolve=False`, como o projeto) + teste da flecha somada. Suíte 695 passed.

**Resultados:** R por apoio 104,7 → **106,1 kN**; F_diag 114,3 → 115,9 kN; η cobertura 0,790 →
**0,801** (Ø28 mantida); η_δ 0,307; terça-biela 0,261 → 0,263. η_max do projeto inalterado
(0,835, contraventamento vertical).

**Tese:** §5.5.1 e §7.5 (texto da soma + conservadorismo), tabelas (0,8009; terça 0,2634), §8, §9.
