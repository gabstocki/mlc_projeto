# Auditoria técnica independente — estrutura em Madeira Lamelada Colada

**Data da auditoria:** 2026-09-04  
**Repositório:** `mlc_projeto`  
**Escopo:** cadeia completa `INPUT → ACTIONS → NBR 6123 → EN 1990 → ANALYSIS → EC5/EN 14080 → ULS/SLS → OUTPUT`  
**Regra de evidência:** todo resultado preexistente foi tratado como **UNVALIDATED**.  
**Intervenção no produto:** nenhuma linha de código de produção foi alterada. Foi acrescentada apenas a suíte de caracterização `tests/test_auditoria_regressoes.py`.

## A — Executive Summary

### Veredito executivo

**NOT VALIDATED**

O software não deve ser utilizado, em seu estado atual, para liberar fabricação, montagem ou aprovação estrutural. Há erros confirmados capazes de reduzir ações, esforços ou utilizações, além de uma incompatibilidade fundamental entre a condição de contorno adotada para a viga (`H=0`) e o sistema de contraventamento que declara o topo dos pilares travado. A mensagem global “APROVADO” não é sustentada por evidência normativa e mecânica suficiente.

Principais bloqueadores:

1. o fator `S2` do vento não depende da altura;
2. a Tabela 25 é aplicada fora do domínio geométrico declarado pela NBR 6123:2023;
3. a força longitudinal na cobertura isolada é calculada por `Cf·q·A`, em vez de `0,5·q·a·b`, resultando em **63,726 kN em vez de 796,571 kN**;
4. `H=0` é imposto como limite de apoio horizontal livre, embora outro módulo declare o topo dos pilares travado pelo diafragma/frontões;
5. o critério de força nocional aceita automaticamente `H_Ed=0`;
6. o predimensionador usa modelo, combinação, interação de estabilidade e integrador ELS diferentes do pipeline principal;
7. o integrador ELS legado fornece **2,123 mm contra 10,615 mm** no benchmark UDL, erro de **−80%**;
8. geometrias degeneradas podem resultar em utilização zero e aprovação;
9. verificações de seção variável avaliam a seção de momento máximo, não a seção de tensão máxima; no caso atual, **1,726 MPa contra 2,930 MPa**;
10. nenhum National Annex foi definido; os NDPs estão incorporados como constantes sem rastreabilidade.

### Respostas objetivas às 20 questões da missão

| Questão | Resposta auditada |
|---|---|
| Modelo mecânico correto? | **Não demonstrado; inconsistente no caminho de carga horizontal.** |
| Equações corretas? | **Não.** Há erros confirmados em vento, ELS, pilares e içamento. |
| Implementação correta? | **Não.** Há divergência de flags, seleção errada de seção e casos-limite inseguros. |
| Unidades consistentes? | **Parcialmente.** O núcleo usa SI coerente, mas não existe tipo/unidade em runtime nem validação de magnitude. |
| Propriedades MLC corretas? | **Plausíveis para GL24h homogênea, mas não documentalmente validadas.** |
| Classes GL corretas? | **Somente GL homogênea, origem não controlada; classes combinadas ausentes.** |
| `kmod` correto? | **Aritmética correta; seleção e origem dependem de versão/NA e do caso governante.** |
| `γM` correto? | **Não validável sem National Annex; valor hard-coded.** |
| `kdef` correto? | **Tabela plausível; aplicação no integrador legado é inválida.** |
| Service classes corretas? | **Mapeadas, sem validação ambiental do input.** |
| Load-duration classes corretas? | **Parcialmente; caminhos legados e combinações manuais não são uniformes.** |
| `Xk → Xd` correto? | **Fórmula-base correta; fatores e domínios não totalmente controlados.** |
| Combinações EN 1990 corretas? | **Não validadas; gerador é específico e NDP não definido.** |
| Vento NBR 6123 correto? | **Não.** Três erros críticos confirmados. |
| Interface vento → combinações correta? | **Sem dupla ponderação no caminho principal observado, mas recebe ação característica incorreta.** |
| ELU correto? | **Não.** |
| ELS correto? | **O integrador novo passa benchmark simples; o legado falha e o modelo de apoio permanece indefinido.** |
| Estabilidade correta? | **Não.** Critério `H_imp/H_Ed` falha para `H_Ed=0`; interações de pilar incompletas. |
| Verificações específicas de MLC ausentes? | **Sim.** Domínio de viga de altura variável não está formalizado; furos, entalhes, produto e ligações dependem de dados não verificados. |
| Pode aprovar estrutura insegura? | **Sim.** Casos reproduzíveis aprovam seção nula e ignoram força longitudinal materialmente maior. |

### Estado dos testes

- suíte original: **282 passed**;
- regressões adversariais acrescentadas: **21 xfailed estritos**;
- total: **282 passed, 21 xfailed** em Python 3.12.7;
- um `XPASS(strict)` após correção falhará deliberadamente, exigindo promoção do caso a teste normal.

`xfail` aqui significa “defeito reproduzido e ainda não corrigido”, não tolerância de qualidade.

### A.1 — Registro detalhado dos achados

## [AUD-001] `S2` independe da altura de referência

**Severity:** CRITICAL  
**Category:** WIND_NBR6123, UNITS  
**Confidence:** HIGH

**Location:**  
`mlc_projeto/core/wind.py → ParametrosVento → __post_init__/S2 → lines 51–70`

**Current implementation:**  
Seleciona `S2` apenas pela chave `(categoria, classe)` em uma tabela fixa; `Hmax` não entra no cálculo.

**Problem:**  
O efeito da rugosidade, dimensões da edificação e altura sobre o terreno é removido. O mesmo `S2` é retornado a 8,8 m e a 30 m.

**Mechanical basis:**  
A velocidade média e a pressão dinâmica variam com a altura no perfil de camada-limite atmosférica.

**Normative basis:**  
NBR 6123:2023, 5.3.3: `S2 = b_m·F_r·(z/10)^p`, com parâmetros dependentes de categoria e classe.

**Current equation:**  
`S2 = table[categoria, classe]`

**Expected equation/behavior:**  
`S2(z) = b_m·F_r·(z/10)^p`, usando a altura de referência normativamente pertinente a cada efeito.

**Structural consequence:**  
Pressão e forças podem ser subestimadas em alturas maiores. Para 30 m, categoria IV/classe B, o programa mantém `0,83`; a reconstrução dá `0,95562`, o que reduz `q` em cerca de **24,6%**.

**Conservatism:** VARIABLE; no caso atual é levemente conservador, mas torna-se NON-CONSERVATIVE com a altura.

**Minimal reproducible case:**  
`ParametrosVento(categoria="IV", classe="B", h=29, H1=1).S2`

**Current result:** `0,83`  
**Expected result:** `0,85·0,98·3^0,125 = 0,95562`

**Recommended correction:**  
Implementar a expressão dependente de `z`, registrar `b_m`, `F_r`, `p`, intervalo de validade e a altura usada em cada força local/global.

**Required regression test:**  
`test_aud_001_s2_depende_da_altura_de_referencia`.

---

## [AUD-002] Tabela 25 aplicada fora do domínio geométrico

**Severity:** CRITICAL  
**Category:** WIND_NBR6123, MODEL  
**Confidence:** HIGH

**Location:**  
`mlc_projeto/core/wind.py → coeficientes_tabela25/calcular_vento → lines 96–117, 277–287`

**Current implementation:**  
Valida apenas a faixa de `tan(β)` e aplica os coeficientes de cobertura isolada.

**Problem:**  
Não valida a condição declarada na Tabela 25, `h ≥ 0,5·l2`, nem a condição de ausência de obstruções que alterem o escoamento sob a cobertura.

**Mechanical basis:**  
Com pé-direito baixo/obstruções, a pressão sob a cobertura não corresponde ao escoamento livre idealizado para cobertura isolada.

**Normative basis:**  
NBR 6123:2023, Tabela 25 e nota associada. Fora do domínio, a ação deve ser tratada conforme a situação de edificação/fechamento indicada pela norma, incluindo investigação de pressão interna.

**Current equation:**  
`Cpe = interpolação_Tabela25(tanβ)` para qualquer `h`.

**Expected equation/behavior:**  
Rejeitar ou redirecionar o caso quando `h < 0,5·l2` ou houver obstruções incompatíveis.

**Structural consequence:**  
Toda a distribuição de vento na cobertura, ELU, uplift, fixações e contraventamentos fica sem base normativa.

**Conservatism:** VARIABLE

**Minimal reproducible case:**  
Projeto: `h=7,0 m`; mesmo adotando favoravelmente `l2=20,25 m`, exige-se `h≥10,125 m`.

**Current result:** coeficientes aceitos e relatório aprovado.  
**Expected result:** erro de domínio ou rota normativa alternativa documentada.

**Recommended correction:**  
Adicionar geometria `l2`, grau de obstrução/fechamento e validação explícita antes da seleção da tabela.

**Required regression test:**  
`test_aud_002_tabela25_rejeita_geometria_fora_do_dominio`.

---

## [AUD-003] Força longitudinal de cobertura isolada subestimada por fator 12,5

**Severity:** CRITICAL  
**Category:** WIND_NBR6123, MECHANICS  
**Confidence:** HIGH

**Location:**  
`mlc_projeto/core/wind.py → forca_vento_paralelo_cumeeira → lines 199–271`

**Current implementation:**  
Usa `CF_COBERTURA=0,04` e `F_fricção=q·Cf·A_planta`.

**Problem:**  
Substitui a equação específica da cobertura isolada por um coeficiente de atrito genérico.

**Mechanical basis:**  
A força longitudinal normativa já representa o efeito integrado nas duas faces da cobertura; não é `Cf` vezes área em planta.

**Normative basis:**  
NBR 6123:2023, 7.2.2: `Ft=0,5·q·a·b`, englobando as duas faces.

**Current equation:**  
`Ft,código = 0,04·q·a·b`

**Expected equation/behavior:**  
`Ft = 0,50·q·a·b`

**Structural consequence:**  
Demanda longitudinal da cobertura, contraventamentos, frontões, pilares e fundações é materialmente subestimada.

**Conservatism:** NON-CONSERVATIVE

**Minimal reproducible case:**  
`q=0,85514879 kN/m²`, `a=46 m`, `b=40,5 m`.

**Current result:** `F_fricção=63,726 kN`; total incluindo pilares `125,789 kN`.  
**Expected result:** `Ft=796,571 kN`; mantendo apenas para comparação a parcela de pilares atual, total mínimo `858,634 kN`.

**Recommended correction:**  
Implementar `Ft`, distribuir a ação por caminho resistente explícito e redimensionar todo o sistema longitudinal.

**Required regression test:**  
`test_aud_003_atrito_longitudinal_usa_equacao_especifica_da_cobertura_isolada`.

---

## [AUD-004] Padrões uniformes de vento não pertencem aos pares simultâneos da Tabela 25

**Severity:** HIGH  
**Category:** WIND_NBR6123, MODEL  
**Confidence:** HIGH

**Location:**  
`mlc_projeto/core/wind.py → padroes_cpe_tabela25 → lines 137–190`

**Current implementation:**  
Gera os pares `Cpb/Cps`, seus reversos e acrescenta casos uniformes `Cpb/Cpb` e `Cps/Cps`.

**Problem:**  
Os coeficientes indicados como simultâneos são recombinados em padrões novos sem base normativa demonstrada.

**Mechanical basis:**  
Um campo de pressão deve preservar a correlação espacial definida pelo caso de carga; extremos locais não podem ser combinados arbitrariamente.

**Normative basis:**  
NBR 6123:2023, Tabela 25: os coeficientes `Cpb` e `Cps` compõem carregamentos simultâneos indicados.

**Current equation:**  
Conjunto de oito padrões.

**Expected equation/behavior:**  
Somente os dois pares simultâneos e os reversos geométricos pertinentes, salvo caso adicional justificado por outra disposição normativa.

**Structural consequence:**  
O caso governante atual de flexão, `C1_unif_bv`, é fabricado: `M=714,248 kN·m`; o maior caso simultâneo reproduzido é `538,674 kN·m`. Em outros efeitos, a recombinação pode mudar sinais e caminhos de carga.

**Conservatism:** VARIABLE; conservador para a flexão global atual, não validável globalmente.

**Minimal reproducible case:**  
Comparar pares produzidos por `padroes_cpe_tabela25(tan(10°))` com `{(Cpb,Cps),(Cps,Cpb)}`.

**Current result:** 8 padrões.  
**Expected result:** 4 padrões (dois casos e seus reversos).

**Recommended correction:**  
Representar cada carregamento normativo como entidade indivisível, com identificação de tabela/caso.

**Required regression test:**  
`test_aud_004_tabela25_gera_somente_pares_simultaneos_normativos`.

---

## [AUD-005] Fixações de telha usam versão, classe e coeficientes incompatíveis

**Severity:** HIGH  
**Category:** WIND_NBR6123, MATERIAL  
**Confidence:** HIGH

**Location:**  
`mlc_projeto/checks/elu/fixacao_telha.py → verificar_fixacao_telha_succao → lines 27–49, 88–189`

**Current implementation:**  
Combina `Cpe local` de −1,0/−1,5/−2,0 com `Cpi=+0,8`, usa `q` global classe B e resistência característica default `R_fix,k=2,5 kN`.

**Problem:**  
O próprio módulo cita NBR 6123:1988, enquanto o núcleo declara 2023. Para elementos de vedação/fixações, a edição 2023 requer avaliação com classe A; em coberturas isoladas, cada elemento de vedação deve ser verificado com `cp=±2,0`. A resistência default não está associada a produto/laudo.

**Mechanical basis:**  
Fixações são governadas por picos locais e área tributária pequena, não pela média global da estrutura.

**Normative basis:**  
NBR 6123:2023, requisito de classe A para elementos de vedação/fixações e regra de `cp=±2,0` para cada elemento em cobertura isolada.

**Current equation:**  
`w_d=γQ·|Cpe−Cpi|·q_B`; `R_fix,d=2,5/γM,fix`.

**Expected equation/behavior:**  
`q_A(z)` e coeficiente local do domínio normativo correto; resistência de produto rastreável, com modo de ruptura do conjunto telha–fixador–terça.

**Structural consequence:**  
Capacidade da envoltória e uplift local não estão validados, ainda que o coeficiente líquido atual possa ser conservador em alguns casos.

**Conservatism:** VARIABLE

**Minimal reproducible case:**  
Passar `ParametrosVento(classe="B")` para `verificar_fixacao_telha_succao`.

**Current result:** cálculo aceito.  
**Expected result:** exigir/recalcular classe A e dados certificados do fixador.

**Recommended correction:**  
Separar vento global e local, remover defaults de produto da rota de aprovação e declarar edição normativa única.

**Required regression test:**  
`test_aud_005_fixacao_local_exige_s2_classe_a`.

---

## [AUD-006] Condição `H=0` conflita com o topo declarado como travado

**Severity:** CRITICAL  
**Category:** MODEL, MECHANICS, STABILITY  
**Confidence:** HIGH

**Location:**  
`mlc_projeto/main.py → constants/orquestrador → lines 243–260, 658–682, 740–747`; `mlc_projeto/core/loads.py → analisar_biarticulada → lines 292–312`; `mlc_projeto/checks/elu/contraventamento_transversal.py → module/demanda_transversal → lines 6–29`; `mlc_projeto/checks/elu/empuxo_acoplado.py → module → lines 31–48`

**Current implementation:**  
O pipeline define `EMPUXO_DESENVOLVE=False`, logo `H=0` e `M=M0`; simultaneamente, o diafragma/frontões torna o topo dos pilares `non-sway` e legitima `l_ef=H`.

**Problem:**  
`H=0` é o limite de deslocamento horizontal livre. Um topo efetivamente travado mobiliza reação horizontal. O estudo de mola considera apenas a rigidez isolada do pilar, não a rigidez do sistema diafragma–frontões–fundações que o próprio projeto usa como restrição.

**Mechanical basis:**  
Compatibilidade exige resolver `H` com a rigidez de todos os elementos do caminho de carga. Apoio livre e apoio impedido são condições de contorno distintas.

**Normative basis:**  
EN 1995-1-1, princípios de análise global e estabilidade: o modelo deve representar a estrutura e as condições de apoio com precisão adequada. Nenhum NDP resolve uma incompatibilidade mecânica.

**Current equation:**  
`H = H_rígido if desenvolve_empuxo else 0`.

**Expected equation/behavior:**  
Ou (a) detalhe de apoio deslizante explícito e caminho lateral separado, ou (b) modelo acoplado com rigidez horizontal real do diafragma, frontões, ligações, pilares e fundações.

**Structural consequence:**  
Momentos, normais, deslocamento horizontal, pilares, apoios, tirante, ancoragens e estabilidade podem estar incorretos. Para a combinação reproduzida: `H_rígido=377,973 kN`; modelo selecionado `H=0`.

**Conservatism:** VARIABLE

**Minimal reproducible case:**  
Executar a combinação governante com `desenvolve_empuxo=False` e comparar com o modelo rígido e com a declaração `topo travado`.

**Current result:** `H=0` e sistema global marcado estável.  
**Expected result:** uma única condição de contorno fisicamente fechada, com compatibilidade e reações.

**Recommended correction:**  
Suspender o resultado global até definir o detalhe de apoio e construir modelo acoplado 2D/3D. Incluir rigidez das ligações e verificar abertura horizontal em ELS.

**Required regression test:**  
Teste de integração que imponha deslocamento/reação coerentes nos dois limites e no caso de mola finita; `test_aud_018_fem_reproduz_a_condicao_de_contorno_selecionada` cobre o contrato mínimo.

---

## [AUD-007] Verificação de mísula ignora o modelo sem empuxo

**Severity:** HIGH  
**Category:** EC5, PYTHON, MODEL  
**Confidence:** HIGH

**Location:**  
`mlc_projeto/checks/elu/misula.py → verifica_misula → lines 88–100`

**Current implementation:**  
Chama `analisar_biarticulada` sem transmitir `load.empuxo_desenvolve`; o default da função é `True`.

**Problem:**  
O restante do pipeline atual usa `False`. A verificação local analisa outra estrutura.

**Mechanical basis:**  
Alterar a reação horizontal altera todo o diagrama `M(x)=M0(x)−H·yc(x)` e, portanto, a tensão na mísula.

**Normative basis:**  
EN 1995-1-1, verificação de viga de altura variável: tensões devem provir do mesmo modelo global e combinação de cálculo.

**Current equation:**  
`analisar_biarticulada(... desenvolve_empuxo=True default)`.

**Expected equation/behavior:**  
`desenvolve_empuxo=load.empuxo_desenvolve` ou, preferencialmente, consumo direto dos diagramas consolidados.

**Structural consequence:**  
No caso atual, `η` é **0,2057**; reconstrução coerente com `H=0` dá **0,28746**, subestimação de **39,75%**.

**Conservatism:** NON-CONSERVATIVE no caso atual

**Minimal reproducible case:**  
`_modelo(empuxo=False)` seguido de `verifica_misula` e varredura independente de `M0/W(x)`.

**Current result:** `η=0,2057`, `M=278,049 kN·m`.  
**Expected result:** `η=0,28746`, `M=425,004 kN·m`.

**Recommended correction:**  
Eliminar defaults divergentes e transportar explicitamente o identificador do modelo/diagrama para todas as verificações.

**Required regression test:**  
`test_aud_006_misula_respeita_o_modelo_sem_empuxo`.

---

## [AUD-008] Divisão por zero lógica aprova o critério de força nocional

**Severity:** CRITICAL  
**Category:** STABILITY, NUMERICAL  
**Confidence:** HIGH

**Location:**  
`mlc_projeto/checks/elu/estabilidade_global.py → verificar_estabilidade_global → lines 183–195`

**Current implementation:**  
`ratio_imp = H_imp/H_Ed if H_Ed>1e-9 else 0.0`; em seguida `ok_imp = ratio_imp <= limite`.

**Problem:**  
Para `H_Ed=0` e `H_imp>0`, a razão não é zero: é indefinida/infinita. O branch transforma a pior condição em aprovação automática.

**Mechanical basis:**  
Uma imperfeição horizontal não é resistida por uma força horizontal de referência nula. A força nocional deve entrar como ação/demanda do sistema resistente, não apenas ser comparada a uma reação ausente.

**Normative basis:**  
Princípios de estabilidade e imperfeições globais do modelo adotado; a norma não autoriza substituir divisão por zero por zero.

**Current equation:**  
`Himp/Hed := 0` quando `Hed=0`.

**Expected equation/behavior:**  
Razão `∞/N/A`, `ok_nocional=False`, ou reformulação que analise a força nocional no sistema de contraventamento.

**Structural consequence:**  
Sistema pode receber `ok=True` sem resistência horizontal compatível.

**Conservatism:** NON-CONSERVATIVE

**Minimal reproducible case:**  
Projeto atual, em que `H_Ed=0` e `H_imp=0,924 kN`.

**Current result:** `H_imp_over_H=0`, `ok_nocional=True`, `ok=True`.  
**Expected result:** critério não atendido/não aplicável até a força ser verificada no caminho lateral.

**Recommended correction:**  
Remover o fallback zero; tratar a força nocional como caso de carga explícito no modelo lateral.

**Required regression test:**  
`test_aud_007_forca_nocional_nao_passa_quando_h_de_referencia_e_zero`.

---

## [AUD-009] Integrador ELS legado impõe condição de contorno espúria

**Severity:** CRITICAL  
**Category:** SLS, MECHANICS, NUMERICAL  
**Confidence:** HIGH

**Location:**  
`mlc_projeto/checks/els/creep.py → calcular_flecha_inst → lines 35–66`; consumidor `mlc_projeto/predim/predim.py → varrer → lines 224–236`

**Current implementation:**  
Após integrar a curvatura, subtrai `theta[-1]·x/L` da rotação e depois corrige a flecha.

**Problem:**  
A primeira correção força artificialmente uma condição de rotação, embora a viga biapoiada permita rotações nas extremidades. Ela remove quatro quintos da flecha no benchmark UDL.

**Mechanical basis:**  
Para `EI w''=M`, existem duas constantes de integração; deve-se impor apenas `w(0)=w(L)=0`, não `θ(L)=0`.

**Normative basis:**  
Resistência dos materiais; EN 1995-1-1 exige avaliar deformações com propriedades de rigidez e combinações pertinentes, mas a falha precede a verificação normativa.

**Current equation:**  
`θ=∫κdx; θ←θ−θ(L)x/L; w=∫θdx; w←w−w(L)x/L`.

**Expected equation/behavior:**  
`θ=∫κdx+C1`; `w=∫θdx+C2`; escolher `C1,C2` apenas por `w(0)=w(L)=0`.

**Structural consequence:**  
Predimensionamento pode selecionar seção com flecha real cinco vezes maior.

**Conservatism:** NON-CONSERVATIVE

**Minimal reproducible case:**  
Viga `L=10 m`, `b=0,20 m`, `h=0,40 m`, `q=1 kN/m`, `E=11,5 GPa`.

**Current result:** `2,12296 mm`.  
**Expected result:** `5qL⁴/(384EI)=10,61481 mm`.

**Recommended correction:**  
Remover o integrador duplicado; usar o integrador já corrigido de `deflection_els.py` e manter benchmark analítico.

**Required regression test:**  
`test_aud_008_integracao_els_reproduz_viga_biapoiada_com_udl`.

---

## [AUD-010] Predimensionador é um pipeline estrutural obsoleto e não equivalente

**Severity:** CRITICAL  
**Category:** MODEL, EN1990, EC5, SLS  
**Confidence:** HIGH

**Location:**  
`mlc_projeto/predim/predim.py → eta_flexo_compressao_viga/varrer → lines 46–75, 119–236`

**Current implementation:**  
Declara análise de “3 rótulas”, chama o modelo com `H=True`, usa `1,35G+1,50W+1,05Q`, combinações ELS manuais, termo axial quadrático com `kc` e o integrador ELS legado.

**Problem:**  
Não representa nem o pipeline principal atual (`H=False`) nem um gerador EN 1990 controlado. Os CSVs de seleção de seção são resultados de outro problema mecânico.

**Mechanical basis:**  
Predimensionar requer os mesmos esforços, condições de contorno e relações tensão–deformação usados na verificação final.

**Normative basis:**  
EN 1990 para combinações; EN 1995-1-1 6.3.2 para estabilidade em compressão e regras ELS.

**Current equation:**  
`η=(σc/(kc fc0d))²+σm/fmd`; `q=1,35g+1,50w+1,05q`; `wfin` via integrador defeituoso.

**Expected equation/behavior:**  
Interação linear quando `kc` é aplicado; combinações provenientes de uma única engine; mesmo modelo global e mesmo solver ELS do cálculo final.

**Structural consequence:**  
Busca de seção pode eliminar alternativas inseguras ou selecionar alternativa que não satisfaz o modelo final.

**Conservatism:** VARIABLE, com componente ELS NON-CONSERVATIVE

**Minimal reproducible case:**  
Comparar `eta_flexo_compressao_viga` com reconstrução linear e comparar `varrer` com `Carregamentos` atual.

**Current result:** pipelines divergentes.  
**Expected result:** identidade de ações, esforços e equações para os mesmos inputs.

**Recommended correction:**  
Desativar o predimensionador para seleção de projeto até fazê-lo consumir a API consolidada; invalidar/renomear os CSVs existentes.

**Required regression test:**  
`test_aud_009_predimensionamento_usa_interacao_linear_de_estabilidade`, benchmark ELS AUD-009 e teste de equivalência end-to-end.

---

## [AUD-011] Expoentes da interação de içamento estão trocados

**Severity:** HIGH  
**Category:** EC5, STABILITY  
**Confidence:** HIGH

**Location:**  
`mlc_projeto/checks/elu/icamento.py → verificar_icamento → lines 131–144`

**Current implementation:**  
Calcula flexão linear e compressão ao quadrado na verificação rotulada como Eq. 6.35.

**Problem:**  
Os expoentes foram aplicados aos termos opostos.

**Mechanical basis:**  
O termo de flambagem lateral por flexão possui a forma quadrática da interação; o termo de compressão estabilizada por `kc,z` é linear.

**Normative basis:**  
EN 1995-1-1:2004, Eq. (6.35).

**Current equation:**  
`η = σm/(kcrit·fmd) + [σc/(kc,z·fc0d)]²`

**Expected equation/behavior:**  
`η = [σm/(kcrit·fmd)]² + σc/(kc,z·fc0d)`

**Structural consequence:**  
Erro de utilização variável com a proporção flexão/compressão; pode ser não conservador.

**Conservatism:** VARIABLE

**Minimal reproducible case:**  
Executar `verificar_icamento` no projeto e reconstruir os dois termos a partir das tensões retornadas.

**Current result:** aproximadamente `0,01110`.  
**Expected result:** aproximadamente `0,00799` no caso atual; a ordem pode inverter em outros casos.

**Recommended correction:**  
Corrigir expoentes e adicionar casos dominados separadamente por flexão e compressão.

**Required regression test:**  
`test_aud_010_icamento_aplica_expoentes_da_equacao_635`.

---

## [AUD-012] Pilar verifica apenas uma interação e quadratiza compressão pura

**Severity:** HIGH  
**Category:** EC5, STABILITY  
**Confidence:** HIGH

**Location:**  
`mlc_projeto/checks/elu/pilares.py → verifica_pilar → lines 89–126`

**Current implementation:**  
Escolhe um único `I/W/kc`; com momento verifica uma equação simplificada. Sem momento retorna `[σc/(kc fc0d)]²`.

**Problem:**  
Para compressão e flexão deve-se avaliar as duas interações conjugadas relativas aos eixos relevantes. O índice de compressão estabilizada é linear, não quadrático.

**Mechanical basis:**  
Flambagem pode governar num eixo enquanto a flexão atua no outro; reduzir tudo a um único eixo não preserva a interação espacial.

**Normative basis:**  
EN 1995-1-1:2004, Eqs. (6.23) e (6.24), e verificação de compressão estável de 6.3.2.

**Current equation:**  
Com `M`: uma única soma linear; com `M=0`: `η=r_c²`.

**Expected equation/behavior:**  
Calcular ambas as expressões com `kc,y`, `kc,z`, termos de flexão e `km`, e governar pelo máximo; para compressão pura, `η=r_c`.

**Structural consequence:**  
No caso atual do pilar lateral, o programa retorna `η=0,4566`; reconstrução das duas equações dá máximo **0,5946**, subestimação de cerca de **23,2%**. Em compressão pura, a margem reportada também é artificialmente ampliada.

**Conservatism:** NON-CONSERVATIVE

**Minimal reproducible case:**  
GL24h, `b=0,32 m`, `h=0,27 m`, `Lef=7 m`, `N=282,172 kN`, `Mz=3,017 kN·m`.

**Current result:** `η=0,4566`.  
**Expected result:** `max(η6.23,η6.24)=0,5946`.

**Recommended correction:**  
Retornar as duas utilizações, todos os `kc` e o eixo governante; rejeitar eixos/dimensões inválidos.

**Required regression test:**  
`test_aud_011_pilar_verifica_as_duas_interacoes_623_624` e `test_aud_011b_pilar_compressao_pura_usa_utilizacao_linear`.

---

## [AUD-013] Entradas degeneradas, `NaN` e seção nula podem produzir aprovação

**Severity:** CRITICAL  
**Category:** NUMERICAL, PYTHON, MODEL  
**Confidence:** HIGH

**Location:**  
`mlc_projeto/core/geometry.py → GeometriaViga → lines 20–38`; `mlc_projeto/core/wind.py → ParametrosVento → lines 25–79`; `mlc_projeto/checks/elu/pilares.py → verifica_pilar → lines 89–126`

**Current implementation:**  
Não existe validação finita/positiva centralizada. Em `verifica_pilar`, `A≤0` substitui o raio por `1e-9` e a tensão por zero.

**Problem:**  
Dados fisicamente impossíveis entram nas equações; fallbacks numéricos transformam divisão por zero em demanda zero.

**Mechanical basis:**  
Seção nula possui rigidez e resistência nulas; nunca pode ser aprovada sob carga não nula.

**Normative basis:**  
Pré-condição matemática e de domínio do modelo, anterior às verificações normativas.

**Current equation:**  
`i=1e-9 if A<=0`; `σc=0 if A<=0`; posteriormente `η=0` em certos caminhos.

**Expected equation/behavior:**  
Rejeitar valores não finitos, dimensões `≤0`, `n_pts<2`, propriedades/resistências `≤0` e estados de sinal incompatíveis.

**Structural consequence:**  
Falsa aprovação silenciosa e propagação de `NaN`/`inf` até relatórios.

**Conservatism:** NON-CONSERVATIVE

**Minimal reproducible case:**  
`verifica_pilar(mat,b=0,h=0.30,H=7,N_d=100)` e `GeometriaViga(L=0,...)`.

**Current result:** seção nula pode retornar `η=0` e `ok=True`; geometrias inválidas são instanciadas.  
**Expected result:** `ValueError` antes de qualquer cálculo.

**Recommended correction:**  
Criar esquemas de entrada imutáveis com validação `math.isfinite` e limites físicos; nunca usar epsilon para tornar seção inexistente calculável.

**Required regression test:**  
`test_aud_012_geometria_invalida_e_rejeitada` e `test_aud_013_secao_nula_nunca_e_aprovada`.

---

## [AUD-014] Seção crítica é escolhida por `max|M|`, não por `max|M/W(x)|`

**Severity:** HIGH  
**Category:** EC5, MECHANICS, MODEL  
**Confidence:** HIGH

**Location:**  
`mlc_projeto/checks/elu/flexao.py → verifica_flexao → lines 66–76`; `mlc_projeto/checks/elu/flambagem_lateral.py → verifica_flambagem_lateral → lines 195–227`

**Current implementation:**  
Obtém `x_Mmax` do solver e calcula propriedades apenas nessa seção.

**Problem:**  
Em viga de altura variável, máximo momento e máxima tensão não coincidem necessariamente. Também `kcrit` depende da seção selecionada.

**Mechanical basis:**  
`σm(x)=M(x)/W(x)` e `W(x)=b h(x)²/6`; perto do apoio, a redução de `h` pode dominar a redução de `M`.

**Normative basis:**  
EN 1995-1-1, verificações de tensão ao longo da peça e regras específicas para vigas de altura variável.

**Current equation:**  
`σcódigo=max|M| / W(x_Mmax)`.

**Expected equation/behavior:**  
`σmax=max_x |M(x)|/W(x)`, com varredura simultânea das interações e fatores locais.

**Structural consequence:**  
Caso atual `H=0`: código usa `M=714,248 kN·m`, `h=2,785 m`, `σ=1,726 MPa`; a varredura encontra `σ=2,930 MPa` em `x≈3,682 m`, **69,7% maior**.

**Conservatism:** NON-CONSERVATIVE

**Minimal reproducible case:**  
Viga atual de altura linear, combinação governante, diagrama isostático e varredura de `6|M|/(bh²)`.

**Current result:** `σm=1,726 MPa`.  
**Expected result:** `σm,max=2,930 MPa` antes dos fatores específicos.

**Recommended correction:**  
Avaliar as equações em todas as seções discretizadas, com refinamento/convergência e rastreio de `x` governante por modo.

**Required regression test:**  
`test_aud_014_viga_variavel_procura_maximo_de_tensao_nao_de_momento`.

---

## [AUD-015] National Annex não definido e combinações hard-coded

**Severity:** HIGH  
**Category:** EN1990, EC5, DOCUMENTATION  
**Confidence:** HIGH

**Location:**  
`mlc_projeto/core/loads.py → constants/Carregamentos._montar_combinacoes → lines 56–77, 527–573`; `mlc_projeto/core/materials.py → constants → lines 65–91`; verificações com fatores locais em `checks/**`

**Current implementation:**  
`γG`, `γQ`, `ψ`, `γM`, `kcr` e limites são constantes de módulo, sem objeto de configuração, edição normativa ou origem EN/NA.

**Problem:**  
O projeto não declara `EUROCODE_BASE + NATIONAL_ANNEX`. O gerador contempla um conjunto específico de situações persistentes e três combinações ELS, sem seleção configurável entre alternativas EN/NA, situações transitórias/acidentais genéricas ou favorabilidade por efeito.

**Mechanical basis:**  
O envelope depende de qual ação variável é líder, das acompanhantes, do sinal favorável/desfavorável e da situação de projeto.

**Normative basis:**  
EN 1990 e EN 1995 contêm Nationally Determined Parameters. A Comissão Europeia/JRC esclarece que cada país publica esses parâmetros no National Annex.

**Current equation:**  
Valores fixos, por exemplo `γG,sup=1,35`, `γQ=1,50`, fatores `ψ` específicos e `γM=1,25`.

**Expected equation/behavior:**  
`EUROCODE_BASE + NATIONAL_ANNEX = [identificado]`, ou classificação explícita de cada resultado dependente.

**Structural consequence:**  
Combinações e resistências de cálculo não podem receber status de conformidade normativa.

**Conservatism:** VARIABLE

**Minimal reproducible case:**  
Inspecionar `Carregamentos` e constatar ausência de `national_annex`/`ndp_source`.

**Current result:** valores silenciosamente assumidos.  
**Expected result:** **NDP NÃO DEFINIDO — RESULTADO DEPENDENTE DE NATIONAL ANNEX**.

**Recommended correction:**  
Criar configuração normativa versionada, bloquear execução “normativa” sem seleção explícita e diferenciar “Recommended value from EN” de “NDP adopted by NA”.

**Required regression test:**  
`test_aud_015_parametros_ndp_possuem_identificacao_do_national_annex` e golden tests de combinações para cada perfil normativo suportado.

---

## [AUD-016] Versões normativas e narrativa do relatório são contraditórias

**Severity:** HIGH  
**Category:** DOCUMENTATION, MODEL  
**Confidence:** HIGH

**Location:**  
`mlc_projeto/output/report.py → gerar_relatorio → lines 588–609, 742–849, 1210–1296, 2123–2142`; `mlc_projeto/checks/elu/fixacao_telha.py → module → line 48`; artefatos `output/relatorio_mlc.pdf`, `output/memorial_mlc.xlsx`, `output/relatorio_mlc.xlsx`

**Current implementation:**  
O relatório lista NBR 6123:1988, depois cita 2023; chama o sistema “1× hiperestático”, declara `H` grande e reação quase axial, embora o run atual use `H=0`; também afirma topo travado e empuxo praticamente nulo. Planilhas geradas não concordam entre si.

**Problem:**  
Não existe baseline normativa/analítica única nem metadado que vincule artefato a commit, input e versão. Texto incondicional descreve outro modelo e pode comunicar “APROVADO” incorretamente.

**Mechanical basis:**  
Um memorial deve reproduzir exatamente o modelo, ações, combinações e resultados executados.

**Normative basis:**  
Rastreabilidade é condição de V&V; a nova NBR 6123 entrou em vigor em dezembro de 2023 substituindo a edição de 1988.

**Current equation:**  
Narrativas e equações de Castigliano misturam casos rígido e liberado; a fórmula apresentada também não espelha integralmente a parcela axial do código.

**Expected equation/behavior:**  
Uma edição por norma, modelo selecionado expresso condicionalmente e hash/manifesto de inputs em cada saída.

**Structural consequence:**  
O decisor pode confiar em um “APROVADO” produzido por premissas distintas das exibidas.

**Conservatism:** VARIABLE, com risco de falsa aprovação

**Minimal reproducible case:**  
Pesquisar `NBR 6123:1988`, `hiperestática` e texto de `H` em `report.py`; comparar as duas planilhas.

**Current result:** versões/modelos conflitantes.  
**Expected result:** relatório internamente consistente e reproduzível.

**Recommended correction:**  
Fazer o relatório consumir apenas um objeto de resultados validado; remover texto estrutural hard-coded; incluir manifesto e impedir “APROVADO” se houver item `ERROR/NOT VALIDATED`.

**Required regression test:**  
`test_aud_016_relatorio_nao_declara_versao_obsoleta_do_vento` e snapshot semântico por modelo.

---

## [AUD-017] Sapata/chumbadores recebem aprovação sem verificação completa do produto e do concreto

**Severity:** HIGH  
**Category:** MATERIAL, MODEL, ULS  
**Confidence:** HIGH

**Location:**  
`mlc_projeto/connections/connections.py → dimensionar_sapata → lines 927–1044`; inputs `mlc_projeto/main.py → constants → lines 220–239`

**Current implementation:**  
Dimensiona quantidade por `ceil(H/(F_chu·ηalvo))`, com `F_chu=80 kN` default, e faz uma verificação simplificada de compressão da chapa/concreto.

**Problem:**  
Não verifica modos de falha da ancoragem no concreto (cone, arrancamento, pry-out, bordas/grupos, interação, concreto fissurado, embutimento), nem associa `F_chu` a produto, geometria e laudo. O código reconhece que a verificação final é externa, mas a agregação permite aprovação.

**Mechanical basis:**  
Capacidade de ancoragem não é a soma ilimitada de capacidades isoladas; grupo, distância à borda e substrato governam.

**Normative basis:**  
EN 1992-4 e especificação do sistema de ancoragem, no domínio aplicável. A auditoria não atribuiu capacidade sem dados.

**Current equation:**  
`n=ceil(Hd/(Fchu·ηalvo))`; `R=n·Fchu`.

**Expected equation/behavior:**  
Verificação completa com geometria, profundidade, concreto, bordas, grupo, interação e ETA/certificado; até lá, status `NOT VALIDATED`.

**Structural consequence:**  
Ligação à fundação pode falhar apesar de `η<1` no relatório.

**Conservatism:** NON-CONSERVATIVE potencial

**Minimal reproducible case:**  
Executar `dimensionar_sapata(load,geo)` sem qualquer dado de embutimento ou borda.

**Current result:** retorna `ok` sem campos de verificação EN 1992-4/produto.  
**Expected result:** bloqueio por dados insuficientes.

**Recommended correction:**  
Separar pré-seleção de quantidade de uma verificação normativa; exigir dados certificados e propagar `NOT VALIDATED` ao resultado global.

**Required regression test:**  
`test_aud_017_sapata_expoe_verificacao_completa_de_ancoragem`.

---

## [AUD-018] “Validação” OpenSees verifica apenas o modelo rígido e reutiliza o analítico de produção

**Severity:** HIGH  
**Category:** TEST, MODEL, NUMERICAL  
**Confidence:** HIGH

**Location:**  
`mlc_projeto/opensees/opensees_model.py → analisar_analitico/analisar_fem → lines 44–120, 145–166`; `mlc_projeto/opensees/opensees_vtk.py → export → line 371`

**Current implementation:**  
O “analítico” chama `analisar_biarticulada`; o FEM fixa deslocamento horizontal no apoio e no nó de simetria, sem parâmetro `desenvolve_empuxo`; combinações assimétricas são convertidas em carga média.

**Problem:**  
Não é benchmark independente e não representa o modelo principal atual `H=False`. A média elimina a assimetria da Tabela 25.

**Mechanical basis:**  
Uma validação cruzada precisa de formulação e implementação independentes, com as mesmas condições de contorno e campos de carga.

**Normative basis:**  
Princípios de verificação e validação de software de engenharia; EN 1995-1-1 exige análise adequada, não define OpenSees como prova.

**Current equation:**  
FEM rígido/simétrico comparado à própria função de produção rígida.

**Expected equation/behavior:**  
Modelos independentes para apoio livre, rígido e mola finita; cargas por meia-viga; comparação de reações, `N,V,M,u` por tolerância e convergência de malha.

**Structural consequence:**  
A figura de “validação” pode transmitir confiança sobre uma condição de contorno que não foi testada.

**Conservatism:** VARIABLE

**Minimal reproducible case:**  
Inspecionar assinatura de `analisar_fem`; executar modelo rígido: `H≈373,2 kN`, enquanto o pipeline selecionado retorna `H=0`.

**Current result:** apenas modelo rígido, carga média.  
**Expected result:** benchmark da condição efetivamente selecionada e de cargas assimétricas.

**Recommended correction:**  
Construir um harness independente, sem chamada ao solver analítico de produção, e retirar a palavra “validação” até cumprir esses critérios.

**Required regression test:**  
`test_aud_018_fem_reproduz_a_condicao_de_contorno_selecionada` e testes de assimetria/convergência.

---

## [AUD-019] Faixa Python declarada não é compatível com a sintaxe do relatório

**Severity:** MEDIUM  
**Category:** PYTHON  
**Confidence:** HIGH

**Location:**  
`pyproject.toml → project/tool.ruff/tool.mypy → lines 1–32`; `mlc_projeto/output/report.py → gerar_relatorio → múltiplas f-strings, por exemplo line 860`

**Current implementation:**  
Declara Python `>=3.10`, Ruff e mypy configurados para 3.10, mas usa f-strings PEP 701 que só são aceitas a partir de Python 3.12.

**Problem:**  
Instalação formalmente permitida em 3.10/3.11 falha ao importar o relatório. Ruff reporta 165 ocorrências/erros no estado auditado; mypy falha com dezenas de diagnósticos.

**Mechanical basis:**  
Não aplicável.

**Normative basis:**  
Reprodutibilidade de software; sem implicação direta de Eurocode.

**Current equation:** N/A  
**Expected equation/behavior:** sintaxe compatível com `requires-python` ou requisito `>=3.12` testado em CI.

**Structural consequence:**  
Pipeline de emissão pode falhar ou variar conforme o ambiente, prejudicando rastreabilidade.

**Conservatism:** VARIABLE

**Minimal reproducible case:**  
Analisar `report.py` com parser alvo Python 3.10/Ruff.

**Current result:** incompatibilidade de versão.  
**Expected result:** matriz CI coerente com metadados.

**Recommended correction:**  
Escolher versão suportada, normalizar f-strings, adicionar lint/type-check/CI e fixar dependências.

**Required regression test:**  
Job de CI em todas as versões declaradas; `python -m compileall` e import smoke test.

---

## [AUD-020] Comprimento efetivo de flambagem lateral é uma simplificação sem domínio demonstrado

**Severity:** MEDIUM  
**Category:** STABILITY, EC5, MODEL  
**Confidence:** MEDIUM

**Location:**  
`mlc_projeto/checks/elu/flambagem_lateral.py → calcular_l_ef/verifica_flambagem_lateral → lines 36–75, 185–227`

**Current implementation:**  
Retorna `0,9·l1` para restrição contínua e também `0,9·l1+2·0,0` para “só apoios”; a verificação sempre chama `continua_topo`.

**Problem:**  
Não representa a posição de aplicação da carga, altura relativa ao centro de cisalhamento, variação de seção, continuidade real da restrição ou rigidez das terças/ligações.

**Mechanical basis:**  
Estabilidade lateral depende do vão não contraventado, restrição torsional e posição da carga; uma restrição nominal não equivale automaticamente a trava efetiva.

**Normative basis:**  
EN 1995-1-1, 6.3.3 e tabela de comprimentos efetivos, dentro das condições de aplicação.

**Current equation:** `lef=0,9·l1` em quase todos os casos.  
**Expected equation/behavior:** selecionar a linha aplicável da tabela e demonstrar rigidez/resistência do travamento, com domínio para seção não prismática.

**Structural consequence:**  
`kcrit` pode ser superestimado e a resistência à flambagem lateral inflada.

**Conservatism:** VARIABLE

**Minimal reproducible case:**  
Comparar `calcular_l_ef(l1,"continua_topo")` e `calcular_l_ef(l1,"so_apoios")`: retornam o mesmo valor para UDL.

**Current result:** condições distintas colapsam em `0,9·l1`.  
**Expected result:** parâmetros e verificações distintos ou recusa de domínio.

**Recommended correction:**  
Formalizar a hipótese de restrição, modelar rigidez torsional das travas e fazer estudo de sensibilidade de `l1/lef`.

**Required regression test:**  
Casos da tabela normativa com parâmetros completos e teste de monotonicidade `lef↑ ⇒ kcrit não aumenta`.

## B — Repository Architecture

### B.1 Inventário de arquivos relevantes

| Arquivo | Função | Entradas | Saídas | Dependências | Criticidade |
|---|---|---|---|---|---|
| `README.md` | Instruções gerais | N/A | descrição | projeto | média |
| `pyproject.toml` | pacote/dependências/tooling | metadados | ambiente | setuptools | alta |
| `mlc_projeto/main.py` | orquestrador e inputs do caso | constantes do projeto | resultados/relatórios | todos os módulos | crítica |
| `core/geometry.py` | geometria da viga variável | L, h0, α, b | x, h, A, I, W | NumPy | crítica |
| `core/materials.py` | classes GL e fatores EC5 | classe, SC, duração | Xk, Xd, E, G, ρ | EN 14080/EC5 codificados | crítica |
| `core/wind.py` | vento NBR 6123 | V0, S1/S2/S3, geometria | q, Cpe, forças | NBR codificada | crítica |
| `core/loads.py` | combinações e análise global | geometria, ações, vento | combinações, N/V/M/H | NumPy/material | crítica |
| `predim/predim.py` | busca de seção | faixas geométricas | CSV/candidatos | core + ELS legado | crítica |
| `checks/els/creep.py` | ELS legado | M(x), G/Q | flecha instantânea/final | SciPy | crítica |
| `checks/els/deflection_els.py` | ELS atual flexão+cisalhamento | diagramas por ação | uinst/ufin | SciPy | crítica |
| `checks/elu/apoio.py` | região de apoio | V/M/geometria | utilização | EC5/material | alta |
| `checks/elu/cisalhamento.py` | cisalhamento da viga | V, seção | τ/fvd | EC5 | alta |
| `checks/elu/flexao.py` | flexo-compressão da viga | M,N,seção | η 6.23/6.24/6.35 | EC5/estabilidade | crítica |
| `checks/elu/flexo_compressao.py` | agregação viga/pilar | resultados | governante | flexao/pilares | alta |
| `checks/elu/flambagem_lateral.py` | LTB | l1, seção, M | λrel,m, kcrit, η | EC5 | crítica |
| `checks/elu/misula.py` | viga afilada/mísula | diagramas, α, material | km,α, η | EC5/core | crítica |
| `checks/elu/cumeeira.py` | ápice/cumeeira | Mcum, geometria | tensões/utilizações | EC5 | crítica |
| `checks/elu/pilares.py` | compressão/flexão de pilares | N,M,L,b,h | kc, η | EC5 | crítica |
| `checks/elu/estabilidade_global.py` | estabilidade/sway/nocional | ações, travamentos | αcr, Himp, ok | EC5/EN 1993 | crítica |
| `checks/elu/empuxo_acoplado.py` | estudo de mola horizontal | geometria,E,kapoio | Hdev, deslocamento | NumPy | crítica |
| `checks/elu/contraventamento.py` | travamento de cobertura | M,kcrit, painéis | forças/diagonais | EC5/EN 1993 | crítica |
| `checks/elu/contraventamento_vertical.py` | painéis longitudinais | vento/painel | barras/rigidez | EN 1993 | crítica |
| `checks/elu/contraventamento_transversal.py` | diafragma/frontões | vento/nocional | Htr, corda, diagonais | wind/EN 1993 | crítica |
| `checks/elu/corda_beiral.py` | corda de diafragma | H,L,B | Ncorda/ligação | connections | alta |
| `checks/elu/tercas.py` | terças | G,Q,W,geometria | ELU/ELS | EC5 | crítica |
| `checks/elu/fixacao_telha.py` | sucção em fixações | q,Cpe,Cpi,espaços | η fixador | NBR/constante produto | crítica |
| `checks/elu/succao_uplift.py` | uplift global | vento/pesos | reação/ancoragem | loads/connections | crítica |
| `checks/elu/tirante_base.py` | fechamento de empuxo | H, aço | diâmetro/η | modelo global | alta |
| `checks/elu/tirante_piso_robustez.py` | impacto/corrosão/fogo | tirante/cenários | robustez | aço | alta |
| `checks/elu/icamento.py` | situação transitória de içamento | peso, apoios temporários | M,V,LTB | EC5 | alta |
| `checks/elu/impacto_veiculo.py` | situação acidental | força/altura | efeitos locais | modelo de pilar | alta |
| `connections/connections.py` | ligações madeira/aço/fundação | esforços, fixadores | capacidades/etas | EC5/Johansen | crítica |
| `connections/chapas_aco.py` | chapas de aço | N,V,M,geometria | resistências | EN 1993 | alta |
| `connections/chapas_dim.py` | dimensões de chapas | ligação/geometria | espessura/arranjo | chapas_aco | alta |
| `connections/fadiga_ligacoes.py` | rigidez/fadiga declarada | Kser/ciclos | deformação/indicadores | EC5 | média |
| `opensees/opensees_model.py` | comparação FEM 2D | q,geometria,E | reações/M/u | OpenSeesPy | alta |
| `opensees/opensees_vtk.py` | exportação de modelo | combinações | VTK | OpenSees/core | média |
| `output/figuras.py` | gráficos | resultados | PNG | matplotlib | baixa |
| `output/report.py` | relatório PDF/XLSX | resultados consolidados | TeX/PDF/XLSX | openpyxl/LaTeX | crítica |
| `visualization/viz_3d.py` | visualização | geometria | figura | matplotlib | baixa |
| `tests/test_*.py` (42 originais) | testes de unidade/regressão internos | funções de produção | pass/fail | pytest | alta |
| `tests/test_auditoria_regressoes.py` | benchmarks independentes desta auditoria | casos mínimos | 20 xfails estritos | pytest | crítica |
| `issues/01…38.md`, `issues/README.md` | histórico de correções/decisões | análises anteriores | documentação | código | alta |
| `output/relatorio_mlc.pdf` | memorial gerado | run anterior | PDF | report.py | crítica |
| `output/relatorio_mlc_diagrama_MVN.pdf` | diagramas | run anterior | PDF | report.py | alta |
| `output/memorial_mlc.xlsx` | planilha antiga | run anterior | workbook | report antigo | crítica |
| `output/relatorio_mlc.xlsx` | planilha atual | run anterior | workbook | report.py | crítica |
| `output/varredura_*.csv/.md` | resultados de predim | sweep | tabelas | predim legado | crítica |
| `output/*.png`, `output/vtk/*.vtk`, `pipeline_console.txt` | evidência/visualização | runs anteriores | imagens/modelos/log | pipeline | média |
| `output/test_min.pdf`, `output/test_none2.pdf`, `.out` | artefatos temporários | testes | arquivos auxiliares | output | baixa |
| arquivos `__init__.py` | namespaces | N/A | importação | Python | baixa |

Não existem `.ipynb`, `.json`, `.yaml` ou `.yml` de configuração normativa. Não foram encontrados PDFs normativos controlados no repositório.

### B.2 Fluxo de execução reconstruído

```text
main.py: constantes de projeto
  ├── GeometriaViga ──> h(x), A(x), I(x), W(x)
  ├── GlulamMaterial ─> Xk, kmod, kdef, γM, Xd
  ├── ParametrosVento ─> V_k, q
  │     ├── Tabela 25 ─> padrões θ=90°
  │     └── vento longitudinal/pilares ─> θ=0°
  └── Carregamentos
        ├── EN 1990 hard-coded ─> ELU/ELS
        └── analisar_biarticulada
              ├── M0, RA, RB
              ├── H_rígido por compatibilidade
              └── H selecionado (0 ou rígido) ─> N,V,M
                    ├── verificações EC5/ações especiais
                    ├── contraventamentos e ligações
                    ├── ELS atual
                    └── report.py ─> PDF/XLSX/figuras
```

### B.3 Caminhos alternativos identificados

1. `predim/predim.py`: combinações, modelo e ELS próprios, incompatíveis com o principal.
2. `checks/els/creep.py`: integrador antigo ainda consumido pelo predimensionador.
3. `checks/elu/misula.py`: reanalisa combinações com o default rígido.
4. `opensees_model.py`: condição rígida e carga média; não representa o run principal.
5. `report.py`: possui texto/equações hard-coded que não derivam integralmente do objeto de resultados.
6. artefatos XLSX/CSV de épocas diferentes convivem sem manifesto de versão.

## C — Normative Architecture

| Estágio | Norma governante requerida | Implementação observada | Status |
|---|---|---|---|
| velocidade/pressão/coefs. de vento | ABNT NBR 6123 | `core/wind.py`, porém com erros AUD-001/002/003/004 | ERROR |
| ação característica de vento | ABNT NBR 6123 | objeto em kN/m² e forças em kN | ERROR |
| outras ações | EN 1991 aplicável | peso/sobrecarga codificados no caso | NOT VALIDATED |
| combinações/segurança | EN 1990 + NA | `core/loads.py` hard-coded | NOT VALIDATED |
| análise estrutural | mecânica/EN 1995 5 | solver próprio | ERROR no domínio global atual |
| madeira/MLC | EN 1995-1-1 | módulos `checks` | ERROR em interações específicas |
| propriedades GL | EN 14080 | tabela homogênea em `materials.py` | VALIDATED WITH RESERVATIONS |
| aço/ancoragem | EN 1993/EN 1992-4, conforme aplicável | parcial/simplificado | NOT VALIDATED |
| fogo | EN 1995-1-2 | não implementado para MLC principal | NOT VALIDATED/fora do escopo declarado |

Separação pretendida no núcleo é conceitualmente correta: o vento é calculado antes das combinações. Não foi encontrada dupla aplicação sistemática de `γQ` no caminho principal `NBR → Carregamentos`; o problema é que o valor característico transferido já está incorreto ou fora do domínio.

## D — Normative Versions

| Norma | Versão pretendida | Versão aparentemente implementada | Evidência | Status |
|---|---|---|---|---|
| ABNT NBR 6123 | 2023 no núcleo | mistura 2023/1988 | `wind.py` vs `fixacao_telha.py:48` e `report.py:594` | **NORMATIVE VERSION MISMATCH** |
| EN 1990 | não declarada | fatores compatíveis com prática da 1ª geração, sem baseline | comentários em `loads.py` | NOT VALIDATED |
| EN 1991 | não declarada | ações específicas, sem manifesto | `main.py`, `loads.py` | NOT VALIDATED |
| EN 1995-1-1 | 2004+A1:2008 aparentemente | 1ª geração, com referências 2004/A1 | comentários/material/report | VALIDATED WITH RESERVATIONS quanto à identificação |
| EN 14080 | 2013 declarada | tabela rotulada 2013 | `materials.py:20–59` | versão identificada, fonte não controlada |
| EN 1993 | não declarada | coeficientes/fórmulas fragmentadas | `chapas_aco.py`, contraventamentos | NOT VALIDATED |
| EN 1992-4 | citada como verificação futura | não implementada | `connections.py`/relatório | NOT VALIDATED |
| amendments/corrigenda | nenhum declarado | desconhecido | ausência de manifesto | NOT VALIDATED |

A entrada em vigor da NBR 6123:2023 e substituição da edição de 1988 é confirmada pelo [comunicado da ABECE](https://site.abece.com.br/em-vigor-a-nova-nbr-6123/). Para a 2ª geração dos Eurocodes, a auditoria não migrou silenciosamente as equações: manteve como baseline aparente a primeira geração declarada no código. O [JRC registra o desenvolvimento/implementação da segunda geração](https://publications.jrc.ec.europa.eu/repository/bitstream/JRC144386/JRC144386_01.pdf), reforçando a necessidade de fixar a edição.

## E — National Annex / NDP Assessment

`EUROCODE_BASE + NATIONAL_ANNEX = NÃO DEFINIDO`

Classificação obrigatória aplicada a todos os resultados afetados:

> **NDP NÃO DEFINIDO — RESULTADO DEPENDENTE DE NATIONAL ANNEX**

Impactos identificados:

- abordagem e fatores de combinação EN 1990, inclusive valores favoráveis/desfavoráveis;
- fatores `ψ` conforme categoria de uso/ação;
- `γM` de material e ligações conforme a adoção nacional aplicável;
- parâmetros nacionais/opções de aplicação do EC5, inclusive limites de serviço quando definidos pelo projeto/NA;
- situações EQU/STR e ações acidentais/transitórias.

O repositório não diferencia **Recommended value from EN** de **Nationally Determined Parameter**. Segundo o [JRC — Nationally Determined Parameters](https://eurocodes.jrc.ec.europa.eu/en-eurocodes-implementation/nationally-determined-parameters), os Estados-Membros determinam os NDPs; os valores recomendados podem ser adotados, mas isso deve ser explícito. Os [National Standards/National Annexes](https://eurocodes.jrc.ec.europa.eu/en-eurocodes-implementation/national-standards) são a fonte apropriada para identificar essa seleção.

## F — Units Audit

### F.1 Sistema reconstruído

| Grandeza | Unidade interna dominante | Conversões observadas | Status |
|---|---|---|---|
| comprimento/geometria | m | mm apenas em fixadores/chapas | consistente por função, sem tipo |
| área/inércia/módulo resistente | m²/m⁴/m³ | mm² em ligações | consistente localmente |
| força distribuída | kN/m | `×1e3` antes de tensão/flecha | consistente no núcleo |
| força | kN | `×1e3 → N` | consistente na maioria das verificações |
| momento | kN·m | `×1e3 → N·m` | consistente no núcleo |
| tensão/resistência | Pa internamente | `/1e6 → MPa` no output | consistente na maioria |
| módulos | Pa | valores-tabela `MPa×1e6` | consistente |
| pressão de vento | kN/m² | `0,613 Vk² /1000` | dimensionalmente correto |
| densidade | kg/m³ | `ρg/1000 → kN/m³` | dimensionalmente correto |
| ângulo | graus no input, radianos no cálculo | `radians`, `tan` | consistente |

### F.2 Equações dimensionais auditadas

- `q=0,613 Vk²`: N/m²; divisão por 1000 produz kN/m² — **OK**.
- `M=qL²`: kN·m — **OK**.
- `σ=M·10³/W`: N/m² — **OK**.
- `τ=1,5V·10³/(kcr A)`: N/m² — **OK**.
- `κ=M/(EI)`: 1/m — **OK** quando `M` está em N·m.
- `f11=∫y²/(EI)ds + ∫1/(EA)ds`: m/N — **OK**.
- `H=num/den`: N ou kN conforme escala comum — **OK** na implementação, porque `E` cancela e `M0` está em kN·m.

Não foi confirmada expressão principal dimensionalmente incompatível. O risco de unidades permanece **HIGH** como controle de software porque floats crus permitem N/kN, mm/m e MPa/Pa sem detecção; não há biblioteca de grandezas nem checks de magnitude. O defeito de `creep.py` é de condição de contorno, não de dimensão.

## G — Material / GL Class Audit

### G.1 Tabela implementada (valores exibidos em MPa; densidade em kg/m³)

| GL | fm,k | ft,0,k | ft,90,k | fc,0,k | fc,90,k | fv,k | E0,mean | E0,05 | Gmean | ρk/ρmean |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| GL20h | 20 | 16,0 | 0,5 | 20 | 2,5 | 3,5 | 8400 | 7000 | 650 | 340/370 |
| GL24h | 24 | 19,2 | 0,5 | 24 | 2,5 | 3,5 | 11500 | 9600 | 650 | 385/420 |
| GL28h | 28 | 22,3 | 0,5 | 28 | 2,5 | 3,5 | 12600 | 10500 | 650 | 425/460 |
| GL32h | 32 | 25,6 | 0,5 | 32 | 2,5 | 3,5 | 14200 | 11800 | 650 | 440/490 |

Constatações:

- os valores são coerentes com a tabela que o código atribui à EN 14080:2013 para MLC homogênea; a auditoria não encontrou uma cópia normativa controlada no repo para elevar a origem a `VALIDATED`;
- somente classes homogêneas `h` estão implementadas; MLC combinada não é suportada;
- `E90,mean=300 MPa` é citado em comentário, mas não é exposto na API;
- não existe vínculo com fabricante, certificado, espécie, classe das lamelas, finger joints, adesivo ou controle de produção;
- `Xmean`, `Xk` e `Xd` são separados por nomes e propriedades — ponto positivo;
- `fd=kmod·fk/γM` está implementado corretamente em termos algébricos;
- `kmod`, `kdef`, `γM` e `kcr` continuam dependentes da edição/NA/domínio declarados em AUD-015;
- classe de serviço 3 e vento “curta” são escolhas do caso; falta evidência ambiental e regra central que selecione a duração governante em todo caminho alternativo.

Status: **VALIDATED WITH RESERVATIONS** para transcrição/aritmética da GL24h homogênea; **NOT VALIDATED** para produto fornecido e adequação da classe resistente à fabricação.

## H — NBR 6123 Wind Audit

### H.1 Cálculo manual independente do caso atual

Dados reconstruídos: `V0=45 m/s`, `S1=1`, categoria IV, classe B, `S3=1`, `z=Hmax=8,7853 m`.

```text
S2 = 0,85·0,98·(8,7853/10)^0,125 = 0,81962395
Vk = 45·1·0,81962395·1 = 36,8831 m/s
q  = 0,613·Vk²/1000 = 0,83390156 kN/m²
```

Programa:

```text
S2 = 0,83
q  = 0,85514879 kN/m²
```

Diferença atual: `+2,55%` em `q` (conservadora apenas para esta altura). A validação normativa do caso para na sequência porque a geometria não satisfaz o domínio da Tabela 25.

### H.2 Resultado por componente

| Componente | Resultado |
|---|---|
| V0/S1/S3 e fórmula de q | mecanicamente coerentes |
| S2 | ERROR — AUD-001 |
| domínio da cobertura isolada | ERROR — AUD-002 |
| pares simultâneos | ERROR — AUD-004 |
| vento longitudinal | ERROR — AUD-003 |
| pressão local/fixações | ERROR — AUD-005 |
| sinais/sucção | tratamento por valor absoluto em módulos locais exige revisão de casos, não validado |
| áreas de influência | coerentes dimensionalmente, mas alimentadas por coeficientes inválidos |

Como apoio de auditoria, foi consultada uma [cópia pública não controlada da NBR 6123:2023](https://studylib.net/doc/28507076/nbr-6123---2023-). Ela não substitui uma norma licenciada/controlada no projeto; serviu para confrontar fórmula, domínio e força longitudinal. A edição deve ser adquirida e incorporada ao controle documental.

## I — NBR 6123 → EN 1990 Interface

### Estágio A — ação característica

`core/wind.py` produz `q`, pressões `w` e forças em nível característico, sem `γQ` na maior parte do núcleo. Esse desenho de interface é apropriado, mas os valores são inválidos pelos achados de vento.

### Estágio B — participação em combinações

`core/loads.py` aplica `γQ`/`ψ` ao montar ELU/ELS. Não foi observada dupla ponderação geral `W×γQ×γQ`. Exceções locais montam situações especiais manualmente (`fixacao_telha`, `uplift`, `içamento`, `terças`); elas precisam ser rastreadas pelo mesmo tipo de ação para impedir ponderação duplicada futura.

O contrato de dados não informa se uma ação é `characteristic`, `representative` ou `design`; são apenas floats. Portanto, a interface é **VALIDATED WITH RESERVATIONS** quanto à ordem das etapas, mas **ERROR** quanto ao valor transferido e **NOT VALIDATED** quanto à tipagem de nível de segurança.

## J — EN 1990 Combination Audit

O gerador principal cria combinações persistentes específicas do projeto e três famílias ELS, com aliases governantes. Foram observadas 21 entradas ELU, das quais quatro são aliases de combinações já existentes, e três entradas ELS. Não é um gerador genérico independente capaz de enumerar:

- cada ação variável líder e acompanhantes;
- favorabilidade por efeito/resposta;
- alternativas normativas/NA para situações persistentes/transitórias;
- situações acidentais de modo uniforme;
- conjunto completo de combinações característica, frequente e quase permanente para qualquer categoria.

As ações de categoria H são tratadas como não concomitantes com vento em partes do caminho atual, mas módulos legados ainda codificam `G+W+Q` simultaneamente. Sem NA, a auditoria não atribuiu correção normativa aos números `γ/ψ`.

Status: **NOT VALIDATED**, com erro de consistência no predimensionador (AUD-010).

## K — Structural Mechanics Audit

### K.1 Propriedades de seção

Para a seção retangular variável, o código usa:

```text
A(x) = b h(x)
Iy(x) = b h(x)^3/12
Wy(x) = b h(x)^2/6
i(x) = sqrt(I/A)
```

As expressões são corretas e dimensionalmente coerentes para seção retangular íntegra. O erro está na seleção da seção crítica (AUD-014) e na ausência de redução/alteração geométrica quando houver furos, entalhes, ligações ou dano.

### K.2 Estática e compatibilidade

- `M0`, reações e diagramas para UDL uniforme/por meia-viga satisfazem equilíbrio em casos simples.
- A expressão de compatibilidade rígida inclui flexão e axial no código, ponto tecnicamente positivo.
- A escolha binária `H=0`/`H=Hrígido` não resolve a estrutura física declarada; falta o caso de rigidez finita acoplada (AUD-006).
- Para cargas assimétricas, o núcleo preserva `q_esq/q_dir`; o módulo OpenSees de validação não preserva.
- Não há análise de segunda ordem global integrada ao solver. `kc`, `kcrit` e índices são pós-processamento de primeira ordem.

### K.3 Tensões e deformações

- tensão axial `N/A`, flexão `M/W` e cisalhamento retangular `1,5V/Aef` estão dimensionalmente corretos;
- o uso indiscriminado de `abs()` deve ser revisto onde tração/compressão ou favorabilidade alteram a resistência;
- a viga variável exige envelope ponto a ponto de tensão/interação;
- o ELS principal inclui parcela de cisalhamento, relevante no caso: aproximadamente `1,93 mm` de `9,11 mm` instantâneos no S1 (cerca de 21%).

Status mecânico global: **ERROR**.

## L — EC5 ULS Audit

| Verificação | Evidência | Status |
|---|---|---|
| flexão simples | fórmula correta, seção governante errada | ERROR |
| tração paralela | resistência disponível; poucos caminhos globais em tração | NOT VALIDATED |
| tração perpendicular | módulos de mísula/cumeeira existem; dependem de diagramas/modelo | VALIDATED WITH RESERVATIONS |
| compressão paralela | transformação `fk→fd` correta; pilar/interações erradas | ERROR |
| compressão perpendicular/bearing | apoio implementado, domínio e geometria precisam revisão | NOT VALIDATED |
| cisalhamento | forma com `kcr` implementada; versão/NA e seção efetiva precisam baseline | VALIDATED WITH RESERVATIONS |
| N+M biaxial/estabilidade | viga possui equações declaradas; pilar não avalia ambas | ERROR |
| flambagem lateral | equação-base existe; `lef` e seção crítica não validados | ERROR |
| içamento | expoentes trocados | ERROR |
| ligações | muitas verificações locais presentes; produto/ancoragem final incompletos | NOT VALIDATED |

Não se encontrou aplicação geral duplicada de `kmod` ou `γM`. Entretanto, a existência da fórmula correta em `materials.py` não valida a seleção do fator, a duração líder ou o National Annex.

## M — EC5 SLS Audit

### M.1 Caminho principal

`checks/els/deflection_els.py` passa o benchmark de viga prismática simplesmente apoiada sob UDL:

- analítico: `10,6148098 mm`;
- numérico: `10,6148055 mm`;
- erro relativo: aproximadamente `−4×10⁻⁷`.

O módulo separa flexão e cisalhamento e usa `E0,mean`/`Gmean`, o que é conceitualmente apropriado para rigidez média em ELS.

### M.2 Caminho legado e flecha final

`checks/els/creep.py` falha por −80% e continua ativo no predimensionamento (AUD-009). A combinação final implementada deve ser revalidada após definir NA, ação quase permanente, `ψ2`, duração e modelo de apoio. No caso atual, o pipeline reporta aproximadamente:

```text
uinst,S1 = 9,11 mm = 7,18 mm (flexão) + 1,93 mm (cisalhamento)
ufin     = 17,94 mm
ηELS     = 0,2215
```

Esses números são **UNVALIDATED** porque as cargas de vento e condição de contorno não são válidas.

### M.3 Verificações ausentes/insuficientes em ELS

- abertura horizontal dos apoios/springings;
- deslocamentos do sistema acoplado diafragma–frontão;
- vibração, se pertinente ao uso;
- deformação de ligações/semi-rigidez no modelo global;
- limites de flecha explicitamente vinculados ao NA/especificação do projeto;
- efeitos de fabricação, contra-flecha e tolerâncias da viga variável.

Status ELS: **ERROR** para o software completo; **VALIDATED WITH RESERVATIONS** apenas para o integrador principal no benchmark UDL prismático.

## N — Stability Audit

Prioridade elevada. Resultados:

1. classificação `non-sway` exige ambos os sistemas de contraventamento, mas o mesmo travamento não entra na rigidez que define `H`;
2. `Himp/Hed` aprova indevidamente `Hed=0` (AUD-008);
3. pilar não avalia as duas equações/eixos (AUD-012);
4. o comprimento efetivo do pilar é fixado em `1,0H` e depende da validade do topo travado;
5. flambagem lateral usa seção de máximo momento e `lef` simplificado (AUD-014/AUD-020);
6. não há análise geométrica não linear/segunda ordem global ou imperfeição equivalente aplicada ao modelo;
7. o estudo de coluna isolada apresenta tendência física coerente com o comprimento, mas a utilização de compressão pura é quadratizada.

Estudo paramétrico independente, GL24h, seção constante e carga fixa:

| L (m) | λrel | kc | η retornado |
|---:|---:|---:|---:|
| 1 | 0,1838 | 1,0000 | 0,0111 |
| 2 | 0,3676 | 0,9923 | 0,0112 |
| 4 | 0,7351 | 0,9203 | 0,0131 |
| 8 | 1,4702 | 0,4230 | 0,0619 |
| 16 | 2,9404 | 0,1118 | 0,8855 |

A monotonicidade é adequada, mas o índice correto de compressão pura deve ser linear; a passagem/ordem de grandeza não valida o módulo.

Status: **ERROR**.

## O — Glulam-Specific Audit

A geometria representa uma peça monolítica de altura variável, com intradorso reto e extradorso inclinado em duas águas. O software possui módulos de mísula e ápice/cumeeira, portanto não trata tudo como viga prismática. Contudo:

- a classificação geométrica normativa (viga afilada/pitched-cambered e domínio de cada equação) não é um input explícito;
- a mísula usa diagrama de outro modelo (AUD-007);
- o ápice depende de momento/reação de modelo global não validado;
- a seleção global de seção crítica não varre tensões (AUD-014);
- propriedades de produto, lamelas, finger joints, adesivo e certificação não são verificadas;
- furos, entalhes, reforços e reduções de seção não são representados por geometria nem explicitamente proibidos;
- tensões radiais/perpendiculares, distribuição no ápice e fatores geométricos precisam benchmark normativo controlado;
- não há verificação de fogo EN 1995-1-2 para o elemento principal.

Qualquer uso fora da geometria atual deve ser classificado como **MODEL DOMAIN ERROR** até existir um dispatcher de tipologia e validações de domínio.

Status: **NOT VALIDATED**.

## P — Analytical Benchmarks

Parâmetros de referência dos testes axiais/flexionais quando aplicável: `L=10 m`, `E=11,5 GPa`, `b=0,20 m`, `h=0,40 m`, `A=0,08 m²`, `I=0,00106667 m⁴`.

| Teste | analytical_result | software_result | abs. error | rel. error | Status |
|---|---|---|---:|---:|---|
| 01 — tração axial, N=10 kN | σ=0,125 MPa; δ=0,108696 mm | tensão local disponível; não há solver axial global de deslocamento | N/A | N/A | NOT VALIDATED |
| 02 — compressão axial elástica, N=10 kN | σ=0,125 MPa; δ=0,108696 mm | tensão disponível; deslocamento axial global ausente | N/A | N/A | NOT VALIDATED |
| 03 — biapoiada, P=10 kN central | RA=RB=5 kN; Mmax=25 kN·m; w=16,9837 mm | solver principal não aceita carga pontual; fórmula local de terça não valida o global | N/A | N/A | NOT VALIDATED |
| 04 — biapoiada, q=1 kN/m | R=5 kN; Vmax=5 kN; Mmax=12,5 kN·m; w=10,614810 mm | integrador atual=10,614806 mm | 0,000004 mm | 0,00004% | VALIDATED WITH RESERVATIONS |
| 04 — mesmo caso, integrador legado | w=10,614810 mm | 2,122960 mm | 8,491850 mm | 80,0% | ERROR |
| 05 — balanço, P=10 kN na ponta | V=10 kN; M=100 kN·m; w=271,739 mm | não há solver de balanço | N/A | N/A | NOT VALIDATED |
| 06 — coluna, L crescente | `kc` e resistência devem cair monotonicamente | monotonicidade observada | — | — | VALIDATED WITH RESERVATIONS |

### Property-based checks

| Propriedade | Resultado |
|---|---|
| carga ×2 ⇒ reações/M ×2 no solver linear | observado no domínio linear |
| E ×2 ⇒ flecha flexional /2 | satisfeito pelo integrador principal |
| I ×2 ⇒ flecha flexional /2 | satisfeito no caso prismático |
| fm,k ↑ ⇒ utilização de flexão não aumenta | satisfeito pela fórmula direta, sem cobrir seleção de classe/produto |
| comprimento de coluna ↑ ⇒ resistência estável não aumenta | satisfeito na série acima |
| inversão de eixos ⇒ eixo crítico muda coerentemente | não validado end-to-end; pilar falha nas interações conjugadas |
| span ↑ ⇒ resposta coerente | não coberto em toda a cadeia variável/vento |

## Q — Adversarial Tests

| Entrada/cenário | Comportamento observado | Classificação |
|---|---|---|
| `L=0`, `b=0`, `h≤0` | criação aceita em classes-base; fallbacks posteriores | CRITICAL |
| seção de pilar nula + N>0 | pode retornar `η=0`, `ok=True` | CRITICAL |
| `NaN` em ângulo/dimensões | propagação silenciosa/argmax potencialmente enganoso | CRITICAL |
| `inf` em ação/propriedade | ausência de guard central; não há resultado confiável | HIGH |
| dimensão negativa | áreas/inércias com sinal impossível em caminhos não protegidos | CRITICAL |
| material/GL inexistente | `GlulamMaterial` rejeita com `ValueError` | PASS |
| service class/duração inexistente | rejeitada | PASS |
| combinação de vento nula | retorna arrays zero; comportamento deliberado | PASS com ressalva de classificação |
| `Hed=0`, `Himp>0` | razão convertida em zero e aprovada | CRITICAL |
| vento positivo/negativo | módulos usam `abs` em alguns pontos; envelope de sinal não centralizado | NOT VALIDATED |
| seção quase degenerada | epsilons evitam exceção e podem ocultar singularidade | CRITICAL |
| vão extremo | sem limites de domínio/convergência | NOT VALIDATED |

As regressões reproduzíveis foram codificadas; o restante exige uma futura suíte com Hypothesis/geração de domínio e invariantes sem `NaN/inf` silencioso.

## R — Python Errors

Além dos erros matemáticos detalhados:

- defaults divergentes (`desenvolve_empuxo=True`) permitem analisar estruturas distintas sem aviso;
- `abs()` remove sinal em verificações onde tração/compressão podem exigir resistências diferentes;
- `max(..., epsilon)` mascara singularidades físicas;
- constantes normativas e de produto são globals sem proveniência;
- aliases de combinações contam como entradas adicionais, dificultando auditoria do envelope;
- módulos reexecutam análise em vez de consumir diagramas imutáveis;
- a tipagem não distingue kN/N, m/mm, Pa/MPa ou nível `k/rep/d`;
- `report.py` depende de sintaxe Python 3.12 apesar de `>=3.10`;
- `openseespy` não consta das dependências, embora o diretório seja apresentado como validação;
- não há CI/configuração que execute versões Python declaradas, lint, mypy, benchmarks e geração de artefatos.

Status: **ERROR** nos pontos que afetam cálculo; **MEDIUM** para compatibilidade/tooling.

## S — Missing Checks

Verificações ausentes ou sem evidência positiva:

1. configuração/versionamento de norma, amendment, corrigendum e National Annex;
2. domínio completo da NBR 6123 para fechamento/obstrução/altura e pressão interna;
3. modelo acoplado da rigidez horizontal e deslocamento dos springings;
4. análise de segunda ordem/imperfeições aplicada ao sistema resistente;
5. envelope ponto a ponto de todas as interações em seção variável;
6. benchmark independente de carga pontual, balanço, axial e carga assimétrica;
7. semi-rigidez/deformação das ligações no modelo global;
8. produto GL certificado, composição de lamelas, finger joints e adesivo;
9. furos, entalhes e reforços — ou proibição explícita no domínio;
10. verificação completa de ancoragens no concreto;
11. fogo da estrutura principal, quando requisito do projeto;
12. vibração e deslocamentos horizontais em ELS, quando pertinentes;
13. tolerâncias, montagem e estados transitórios além do içamento simplificado;
14. robustez global/caminhos alternativos e ações acidentais de forma sistemática;
15. relatório com manifest/hash reproduzível e bloqueio de aprovação por item não validado.

## T — Compliance Matrix

| Item | Implementado | Mecânica | Norma | Benchmark | Status |
|---|---|---|---|---|---|
| geometria retangular variável | sim | fórmulas básicas corretas | domínio parcial | propriedades simples | VALIDATED WITH RESERVATIONS |
| propriedades GL homogênea | sim | coerente | fonte declarada, não controlada | testes internos | VALIDATED WITH RESERVATIONS |
| produto/fabricação MLC | não | — | EN 14080 | nenhum | NOT VALIDATED |
| transformação `fk→fd` | sim | correta | NA ausente | testes diretos | VALIDATED WITH RESERVATIONS |
| service/load-duration classes | sim | parcial | versão/entrada não controladas | testes internos | VALIDATED WITH RESERVATIONS |
| vento: velocidade/pressão | sim | S2 incorreto | NBR 6123 | manual | ERROR |
| vento: domínio Tabela 25 | sim sem validação | modelo incorreto | NBR 6123 | caso atual | ERROR |
| vento longitudinal | sim | equação errada | NBR 6123 | manual | ERROR |
| vento local/fixações | sim | domínio misturado | versões 1988/2023 | nenhum independente | ERROR |
| interface NBR→EN | sim | ordem adequada | tipagem/NA ausentes | inspeção | VALIDATED WITH RESERVATIONS |
| combinações EN 1990 | parcial | envelope específico | NA ausente | sem enumerador independente | NOT VALIDATED |
| análise global rígida | sim | formulação plausível | modelo não selecionado | FEM não independente | NOT VALIDATED |
| análise global `H=0` | sim | conflita com travamento | modelo inadequado | nenhum FEM equivalente | ERROR |
| flexão viga variável | sim | seção crítica errada | EC5 | varredura independente | ERROR |
| mísula | sim | diagrama divergente | EC5 | reconstrução | ERROR |
| ápice/cumeeira | sim | depende de modelo inválido | EC5 | nenhum controlado | NOT VALIDATED |
| cisalhamento | sim | fórmula plausível | edição/NA | testes internos | VALIDATED WITH RESERVATIONS |
| pilares | sim | interação incompleta | EC5 | reconstrução 6.23/6.24 | ERROR |
| LTB | sim | `lef`/seção não validados | EC5 | sensibilidade parcial | ERROR |
| estabilidade global | sim | razão zero incorreta | EC5/imperfeições | adversarial | ERROR |
| ELS integrador atual | sim | correto para UDL prismática | EC5 parcial | analítico | VALIDATED WITH RESERVATIONS |
| ELS legado/predim | sim | condição de contorno errada | EC5 | analítico | ERROR |
| içamento | sim | expoentes trocados | EC5 | reconstrução | ERROR |
| contraventamento longitudinal | sim | ação subestimada | NBR/EN | manual de ação | ERROR |
| contraventamento transversal | sim | caminho conflita com H | EN/modelo | nenhum acoplado | ERROR |
| ligações madeira/aço | parcial | vários modos locais | fontes fragmentadas | testes internos | NOT VALIDATED |
| sapata/chumbadores | parcial | modos ausentes | EN 1992-4 | nenhum | NOT VALIDATED |
| fogo | não | — | EN 1995-1-2 | — | NOT VALIDATED |
| relatório/output | sim | contraditório | versões misturadas | comparação de artefatos | ERROR |

Nenhum item recebeu `VALIDATED` irrestrito.

## U — Required Corrections

### P0 — STOP: results cannot be trusted

1. bloquear a emissão de “APROVADO” enquanto existirem achados P0/`NOT VALIDATED`;
2. corrigir `S2(z)`, validar o domínio da Tabela 25 e implementar `Ft=0,5qab`;
3. definir fisicamente o apoio da viga e modelar a rigidez acoplada do caminho horizontal;
4. corrigir o branch `Hed=0` e aplicar forças nocionais ao sistema resistente;
5. retirar o predimensionador legado da rota de decisão;
6. rejeitar inputs degenerados/não finitos;
7. refazer envelopes da viga variável ponto a ponto;
8. recalcular contraventamentos, pilares, fundações e ligações após correção das ações/modelo.

### P1 — required before engineering use

1. definir edições normativas, amendments/corrigenda e `EUROCODE_BASE + NATIONAL_ANNEX`;
2. corrigir padrões simultâneos e vento local classe A;
3. corrigir mísula, pilares e Eq. 6.35 de içamento;
4. construir gerador independente de combinações EN 1990 com golden cases;
5. concluir EN 1992-4 e dados certificados de produtos/fixadores/GL;
6. criar benchmark FEM independente para a condição adotada e cargas assimétricas;
7. tornar o relatório derivado, reprodutível e condicional.

### P2 — important improvement

1. formalizar `lef`/restrição torsional e domínio de LTB;
2. adicionar análise de segunda ordem e sensibilidade de imperfeições;
3. tipar unidades e níveis de ação/resistência;
4. consolidar ELS e remover código duplicado;
5. documentar domínio de vigas afiladas, ápice, furos/entalhes/reforços;
6. alinhar Python, dependências, lint e type-check.

### P3 — quality improvement

1. limpar artefatos temporários/stale;
2. adicionar manifesto de run com commit, inputs, versões e checksums;
3. separar visualizações de evidência de validação;
4. ampliar property-based testing e cobertura de mensagens/erros.

## V — Required Regression Tests

A suíte adicionada contém casos independentes para os achados de maior severidade:

| Test ID | Prova independente | Estado atual |
|---|---|---|
| AUD-001 | fórmula fechada `S2(z)` | xfail |
| AUD-002 | domínio geométrico da Tabela 25 | xfail |
| AUD-003 | `Ft=0,5qab` | xfail |
| AUD-004 | conjunto de pares simultâneos | xfail |
| AUD-005 | contrato de vento local classe A | xfail |
| AUD-006 | mísula com `H=False`, diagrama `M0` independente | xfail |
| AUD-007 | `Himp/Hed` para denominador zero | xfail |
| AUD-008 | flecha UDL fechada | xfail |
| AUD-009 | interação de estabilidade linear | xfail |
| AUD-010 | expoentes da Eq. 6.35 | xfail |
| AUD-011 | máximo das Eqs. 6.23/6.24 e compressão pura linear | 2 xfails |
| AUD-012 | geometrias zero/NaN | 3 xfails |
| AUD-013 | seção nula | xfail |
| AUD-014 | máximo ponto a ponto de tensão | xfail |
| AUD-015 | presença de NA/proveniência NDP | xfail |
| AUD-016 | edição única da NBR no relatório | xfail |
| AUD-017 | contrato de ancoragem/produto completo | xfail |
| AUD-018 | FEM aceita a condição de contorno selecionada | xfail |

Após cada correção, o teste correspondente deve primeiro produzir `XPASS(strict)` e falhar a suíte; em seguida a marca `xfail` deve ser removida. Não se deve alterar o valor esperado para reproduzir o código corrigido — o esperado continua vindo de equação fechada, domínio normativo ou invariante independente.

Testes adicionais obrigatórios ainda não codificados porque dependem de uma decisão normativa/modelo inexistente:

- golden combinations para o National Annex escolhido;
- carga pontual, balanço e deslocamento axial no solver geral;
- modelo acoplado com mola e limites `k→0`, `k→∞`;
- cargas assimétricas no FEM;
- ancoragens com casos certificados EN 1992-4;
- vigas curvas/afiladas/ápice com exemplos normativos controlados;
- fogo, se aplicável.

## W — Final Verdict

### NOT VALIDATED

Há evidência positiva apenas para partes isoladas: propriedades geométricas retangulares, transformação algébrica `fk→fd` e integrador ELS atual no benchmark UDL prismático. Isso não compensa os erros de ação, domínio, condição de contorno, estabilidade e caminhos alternativos.

O risco dominante é sistêmico: uma ação característica de vento incorreta alimenta combinações sem National Annex; os esforços são obtidos por uma condição de contorno incompatível com o travamento; verificações locais reexecutam modelos divergentes; e o relatório pode ainda assim declarar aprovação.

O software só poderá ser reavaliado depois de concluídos os itens P0/P1 e de os benchmarks independentes passarem sem `xfail`. Até lá, qualquer resultado, inclusive PDF/XLSX/CSV já gerado, permanece **UNVALIDATED**.

### Referências de auditoria

- ABNT NBR 6123:2023 — edição a incorporar de forma controlada; [comunicado de vigência](https://site.abece.com.br/em-vigor-a-nova-nbr-6123/) e [cópia pública não controlada consultada](https://studylib.net/doc/28507076/nbr-6123---2023-).
- European Commission/JRC — [Nationally Determined Parameters](https://eurocodes.jrc.ec.europa.eu/en-eurocodes-implementation/nationally-determined-parameters).
- European Commission/JRC — [National Standards and National Annexes](https://eurocodes.jrc.ec.europa.eu/en-eurocodes-implementation/national-standards).
- JRC — [Eurocode 5 worked background/teaching material](https://eurocodes.jrc.ec.europa.eu/sites/default/files/2022-06/EN1995_2_Winter.pdf), usado apenas como fonte auxiliar; o texto normativo controlado prevalece.
- JRC — [Second-generation Eurocodes development report](https://publications.jrc.ec.europa.eu/repository/bitstream/JRC144386/JRC144386_01.pdf), usado para controle de versão, não para substituir a edição implementada.
