# 07 — Flecha sem parcela de deformação por cisalhamento

- **Tema:** ELS / flechas
- **Prioridade:** P1
- **Normas:** EC5 §2.2.3(2) e Anexo B (deformação por cortante)
- **Arquivos:** `mlc_projeto/checks/els/deflection_els.py:34-65` (`flecha_numerica`)

## Apontamento do orientador
> As flechas devem incluir a parcela de deformação por cisalhamento, ausente no
> memorial. Me parece que não será desprezível: h/L = 0,14 e E/G ≈ 16 — ela responde
> por cerca de 20% da flecha total. Mesmo se for menos que isso, é obrigatório por
> norma (EC5 §2.2.3 e Anexo B).

## Estado atual no código
- `flecha_numerica` integra apenas a curvatura de flexão
  `κ = M/(E·I(x))` ([deflection_els.py:56-65](../mlc_projeto/checks/els/deflection_els.py)).
- **Não há** termo de deformação por cisalhamento (nenhuma referência a `G` ou a
  `V/(G·A)` no módulo).
- Seção variável e vão grande (h_ap ≈ 2,79 m, L = 20,25 m) → h/L elevado, cisalhamento
  relevante.

## O que precisa ser feito
- [ ] Adicionar a parcela de flecha por cisalhamento: `w_v = ∫ κ_s·V/(G·A(x)) dx`
      com fator de forma κ_s = 1,2 (retangular) e `G = G_mean` (ELS).
- [ ] Usar `A(x)` da seção variável (já disponível em `geo.A(x)`).
- [ ] Somar w_flexão + w_cisalhamento em todas as combinações ELS (inst. e final).
- [ ] Documentar a contribuição percentual do cisalhamento no memorial.
- [ ] Estender a verificação também às **terças** ([tercas.py](../mlc_projeto/checks/elu/tercas.py))
      e à flecha analítica lá usada, se relevante.

## Critério de aceite
Flechas ELS incluem a parcela de cisalhamento (EC5 §2.2.3/Anexo B); memorial mostra
a separação flexão vs cisalhamento.
