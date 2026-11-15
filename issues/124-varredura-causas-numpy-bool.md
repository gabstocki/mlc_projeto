# 124 — Varredura global: causas de reprovação omitidas (`ok` numpy.bool_)

- **Tema:** Programa / varredura
- **Prioridade:** P1
- **Origem:** encontrado ao conferir a varredura refeita após o engrossamento do CV-T (issue 110), 2026-11-15

## Problema
`predim/varredura_global.rodar_ponto` montava a coluna `reprova` com
`v.get("ok") is False`. Verificações cujo `ok` sai de uma comparação com float do
NumPy devolvem `numpy.bool_`, e `numpy.False_ is False` é falso: a causa era omitida.

- O **status** (APROVADO/REPROVADO) e as contagens estavam corretos: vêm de `meta`.
- A lista de causas estava incompleta. Exemplos: α = 9,0°, h₀ = 0,40 m, b = 0,32 m
  reprovada com `reprova` vazio (cisalhamento η = 1,001); α = 8,0°, h₀ = 0,40 m,
  b = 0,30 m com só `misula`, embora a estabilidade global (w/f_c = 0,052 > 0,05)
  também reprovasse.
- As alíneas do cap. 5 sobre as regiões de reprovação foram escritas a partir dessa coluna.

## Correção
- [x] `reprova` usa `ok is not None and not bool(ok)`.
- [x] Teste `test_reprova_reconhece_numpy_bool` (tests/test_issue93_varredura.py).
- [x] Varredura refeita (1.114 aprovadas; nenhuma reprovada sem causa) e alíneas do cap. 5 conferidas.

## Resolução (2026-11-15)
Com as causas completas, a varredura mostra 400 reprovações por cisalhamento e 207
pelo abaixamento relativo da cumeeira (w_Ed/f_c > 0,05), antes invisíveis na coluna.
Nenhuma muda o status de uma geometria. Ajustes na tese:
- Cap. 6 (`sec:ordem-analise`): descrito o critério w_Ed/f_c ≤ 0,05, critério do autor que não estava
  na tese (adotada: 0,011).
- Cap. 5, alíneas: abaixamento da cumeeira nas geometrias com α < 8° e h₀ pequeno e em 8,0°/0,40/0,30;
  pilar central reprova só com b = 0,20 (antes "0,20 e 0,22"); taxa média 0,40 com b = 0,32.
✅
