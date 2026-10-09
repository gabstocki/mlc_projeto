# 53 — Precisão numérica: η com duas casas, forças com três algarismos significativos

- **Tema:** Apresentação
- **Prioridade:** P2
- **Arquivos:** `mlc_projeto/output/report.py` (formatação `_br`); `mlc_projeto/main.py` (console); `tese/*.tex` (ex.: `cap07.tex:47` “0,2660”, forças como 277,48 kN)
- **Relaciona:** issue 50

## Origem (3ª revisão do orientador (2026-10))
Dados como q_k = 0,40 kN/m² ou γ_G = 1,35 têm 2–3 algarismos significativos; calcular não
aumenta a precisão. Taxas com 4 casas (0,3814) e forças como 277,48 kN transmitem precisão que
o cálculo não tem. **Usar duas casas para taxas e três algarismos significativos para forças.**

## O que fazer
- [x] Criar formatador único (η → 2 casas; forças/momentos → 3 alg. sig.) e aplicá-lo em report/console/Excel.
- [x] Revisar todas as tabelas e o texto da tese.
- [x] Atenção a η arredondado = 1,00 com valor real > 1 → decidir arredondar para cima ou mostrar “> 1,00”.

## Resolução (2026-10-08) ✅
**Convenção (escolha do usuário):** η com duas casas **arredondado sempre para cima** (a taxa
exibida nunca é menor que a calculada: 0,7492 → 0,75; 1,0001 → 1,01); forças, momentos,
tensões e cargas lineares com três algarismos significativos (arredondamento usual), **sem
acrescentar** algarismos a dados de entrada (50 kN continua 50). Declarada no §7.1 da tese.

- `mlc_projeto/output/formatacao.py`: `eta_exibido`, `fmt_eta`, `sig`, `fmt_sig` (Decimal,
  sem ruído binário). Testes: `tests/test_formatacao.py` (16).
- Console: `_print_eta`, tabela-resumo e η_max com 2 casas (detalhes intermediários mantidos).
- Relatório LaTeX (`report.py`): 58 ocorrências de η trocadas por `_be()`; Excel com o η exibido.
- Apêndice B (memorial_equacoes): η 2 casas, demais grandezas 3 alg. sig. (zeros finais
  omitidos, para não dar a 0,32 a forma 0,320); Apêndice C: 3 alg. sig. com zeros (resultados).
- Tese: ~190 η convertidos (4 e 3 casas, texto, tabelas e modo matemático, revisados por
  contexto — coeficientes como k_c = 0,445 e k_m,α preservados); ~115 esforços a 3 alg. sig.
  (texto e tabelas de esforço; geometria, volumes, massas, custos e flechas mantidos).
- Pendente consciente: forças no relatório LaTeX auxiliar (`relatorio_mlc.pdf`) seguem com o
  número de casas antigo — a unidade não é identificável por padrão nas ~2500 linhas.
