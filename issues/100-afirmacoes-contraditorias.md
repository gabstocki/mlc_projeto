# 100 — Afirmações que contradizem os resultados

- **Tema:** Coerência
- **Prioridade:** P1
- **Arquivos:** `tese/cap07.tex` (§6.5, §6.6, §6.8), `tese/cap04.tex` (Tabela 13), resumo
- **Origem:** 4ª revisão, item 10.2

## Checklist
- [ ] §6.5 — contraventamento da cobertura “terceira maior taxa” × “o limite efetivo do dimensionamento” (resquício).
- [ ] Tabela 13 — critério da diagonal da cobertura “estabilização das terças”, mas a força é governada
      pelo vento paralelo à cumeeira (105 kN frente a 1,4 kN).
- [ ] §6.8 — “as cinco verificações mais solicitadas [...] entre 0,80 e 0,85” omite o T-stub da base L3 (0,84).
- [ ] §6.6 — içamento a 0,207 L “iguala os momentos”, mas os valores são −21 e +63 kN·m: corrigir a
      afirmação ou a posição (0,207 L iguala os momentos de uma viga prismática; na viga de seção variável não).
- [ ] Resumo — “eliminou o risco de fendilhamento” → “reduziu” (η = 0,34).

## Resolução ✅ (2026-11-11)

**§6.5, contraventamento da cobertura (`cap07`):**
- "terceira maior taxa … limite efetivo do dimensionamento" virou "sistema de estabilização mais solicitado, η 0,89, no nível das componentes de aço dimensionadas até o alvo 0,90; insensível à seção da viga".
- Números atualizados: reação 115,8 + 1,3 = 117 kN; diagonal a 128 kN.
- `tab:verif-contraventamento` atualizada (cobertura 0,89, transversal 0,82, vertical 0,78; ligações 0,84/0,81/0,78; estabilidade 0,51; corda 0,12) e com a linha da ligação da diagonal da cobertura.
- Parágrafos do CV vertical (943 kN, 118 kN por painel, Ø36, 186/239 kN, 0,78) e do transversal (140 kN, 69,8 por frontão, Ø27, 110/135 kN, 0,82). Saiu "a maior taxa do projeto".

**Tabela 13 (`tab:criterios-predim`, cap05):**
- Diagonal da cobertura: o critério virou "vento paralelo à cumeeira coletado pela cobertura e levado às baías rígidas".
- `tab:varredura-diagonal-cobertura` recalculada com a força atual (128 kN; N_pl,Rd): Ø22 1,44 e Ø25 1,11 reprovam; Ø28 0,89 adotado; Ø30 0,78.
- Saiu "25 mm atende sem margem".

**§6.8 ("cinco verificações entre 0,80 e 0,85"):** reescrito com a distribuição atual.
- As maiores, entre 0,82 e 0,90, são as componentes de aço no alvo 0,90 (soldas, pilarete das bases L3a/L3f, acomodação da retração) e os CV da cobertura e transversal.
- Na viga, o máximo é o apoio na sela (0,58), o cisalhamento fica em 0,41 e a flambagem lateral em 0,10.
- O T-stub de L3 é hoje 0,31, então a omissão apontada deixou de existir.

**§6.6, içamento:** corrigida a **posição**, e não só a frase.
- `icamento.py`: `a_rel=None` (padrão; `A_ICAM_REL = None` no main) calcula, por bissecção, a posição que iguala |M⁻| e |M⁺| na viga de seção variável. O resultado é **0,247·L = 5,0 m**, com M = ±32 kN·m (a 0,207·L seria −21/+63).
- Também mudaram: η 0,04, l_ef,LTB 10,2 m e k_crit 0,852.
- O texto explica que 0,207 vale para a peça prismática.
- Teste novo `test_posicao_padrao_iguala_os_momentos_na_viga_de_secao_variavel`.

**Resumo e abstract:**
- "eliminou o risco de fendilhamento" virou "reduziu o fendilhamento a 0,67" (o 0,34 da issue era antigo).
- "máx. da seção 0,39 por cisalhamento; governa o transversal 0,85" virou "0,58 no apoio da sela; governam as peças de aço e os CV, até 0,90".
- O cap. 9 foi alinhado da mesma forma (η máx 0,90; 0,58/0,41; 0,89/0,82/0,78).

**Verificação:** pipeline APROVADO, η_max 0,90; 835 testes passam; tese com 164 páginas, 0 overfull, nenhuma referência pendente.

**Fica para a 99:** contagens ("sessenta e quatro verificações" etc.).
