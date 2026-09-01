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
- [x] Adicionar a parcela de flecha por cisalhamento: `w_v = ∫ κ_s·V/(G·A(x)) dx`
      com fator de forma κ_s = 1,2 (retangular) e `G = G_mean` (ELS).
- [x] Usar `A(x)` da seção variável (já disponível em `geo.A(x)`).
- [x] Somar w_flexão + w_cisalhamento em todas as combinações ELS (inst. e final).
- [x] Documentar a contribuição percentual do cisalhamento no memorial.
- [x] Estender a verificação também às **terças** ([tercas.py](../mlc_projeto/checks/elu/tercas.py))
      e à flecha analítica lá usada, se relevante.

## Critério de aceite
Flechas ELS incluem a parcela de cisalhamento (EC5 §2.2.3/Anexo B); memorial mostra
a separação flexão vs cisalhamento.

## Resolução (2026-08-31)
- `flecha_numerica` ([deflection_els.py](../mlc_projeto/checks/els/deflection_els.py))
  agora soma a parcela de Timoshenko `w_s(x)=∫ κ_s·V(x)/(G·A(x)) dx`, com
  `V=dM/dx`, `κ_s=1,2` e `G=G_mean`. Retorna os perfis separados de flexão e
  cisalhamento; `verificar_ELS` expõe `w_S1_flex_mm`, `w_S1_cis_mm`, `pct_cis_S1`
  (e idem para G). Relatório console e LaTeX ([report.py](../mlc_projeto/output/report.py))
  mostram a separação.
- `flecha_terca`/`verifica_terca` ([tercas.py](../mlc_projeto/checks/elu/tercas.py))
  somam `w_v = κ_s·q·L²/(8·G·A)` (forma fechada) e reportam `pct_cis`.
- **Bug corrigido junto**: a integração da flexão aplicava a correção linear
  em `θ` (rotação) *e* em `w`, impondo rotação nula nos apoios ⇒ condição de
  **bi-engaste** em vez de bi-articulada, subestimando a flecha de flexão em
  ~5× (qL⁴/384EI em vez de 5qL⁴/384EI). Removida a correção espúria em `θ`;
  validado contra as soluções fechadas (teste
  `test_flecha_numerica_bem_condicionada_secao_constante`).
- **Magnitude**: para a viga do projeto (h_ap≈2,79 m, L=20,25 m, ação de arco
  M=M0−H·y_c que reduz a flexão), o cortante responde por **~40%** da flecha
  característica (mais do que os ~20% estimados) — confirma que é obrigatório e
  não desprezível. Como a viga é muito rígida, η_ELS permanece ≪ 1.
- **Pendência fora de escopo**: `creep.py:calcular_flecha_inst` tem o mesmo bug
  de condição de contorno (usado só no pré-dimensionamento `predim`); registrado
  como follow-up.
- Testes: `tests/test_els_deflection.py` (parcela de cortante + regressão do
  bug de flexão) e `tests/test_tercas_cisalhamento.py`. Suíte: 105 passam.
