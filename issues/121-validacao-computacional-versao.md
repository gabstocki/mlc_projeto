# 121 — Validação computacional documentada e versão congelada

- **Tema:** Programa — verificação independente
- **Prioridade:** P1
- **Origem:** Revisão técnica (comentários tipo banca), 2026-11-14, item 13

## O que fazer
- [x] Classificar os testes (unitários, de regressão, de referência) e documentar os **casos de referência independentes**: soluções analíticas, exemplos publicados (EC5, STEP, manuais), cálculo manual. Informar valor esperado, fonte e tolerância.
- [x] Verificações de equilíbrio (reações × cargas, por combinação) e de convergência da discretização (n_pts da viga, malha OpenSees).
- [x] Descrever o modelo OpenSeesPy: elementos, liberações, cargas, apoios e o que ele valida.
- [ ] Identificação imutável: commit/tag/release + dados de entrada + instruções de reprodução no Apêndice A. Substituir o endereço "…VALIDAR" e registrar o hash no PDF (gerado pelo pipeline).
- [x] Explicar 78 arquivos (Apêndice A) × 60 (Tab. 56): contagem com e sem testes?
- [x] Discutir o risco de modo comum: o mesmo programa calcula, tabela e escreve as equações; a verificação independente responde a isso.

## Resolução (2026-11-15)

- **Casos de referência independentes** (`mlc_projeto/output/validacao.py`): 12 casos — 5 analíticos (viga prismática, balanço, carga assimétrica), 4 normativos recalculados à mão sem chamar a função do programa (k_c, n_ef, Johansen 8.11, cone EN 1992-4), equilíbrio nas 29 combinações (≤ 0,0001 kN), convergência 401 × 3.201 pontos (< 10⁻⁵) e OpenSees × integrador (0,03 %). Gera `tese/tab_referencias.tex`; o pipeline para se algum caso sair da tolerância. Teste `tests/test_issue121_referencias.py`.
- **Classificação dos testes** (macros geradas): 788 unitários e 109 de integração (arquivos que executam o pipeline); mais os 12 casos de referência.
- **Tabela de pacotes** gerada (`output/apendice_programa.py` → `tab_ap_modulos.tex`): 87 arquivos e 34.613 linhas do programa (o mesmo de `\nArquivosCodigo`), testes à parte (111 arquivos). Os "78 × 60" vinham da tabela escrita à mão, desatualizada.
- **Apêndice A:** nova seção "Verificação do programa" (risco de modo comum, classes de testes, tabela de referências, equilíbrio, convergência, modelos OpenSees: viga com 40 elasticBeamColumn por simetria; diafragma em planta); "Disponibilidade e reprodução" com o URL real (github.com/gabstocki/mlc_projeto, no lugar de …VALIDAR), commit, data, etiqueta e estado gerados pelo pipeline, dependências do pyproject e os três comandos de reprodução.
- [ ] **Pendente (decisão do autor): congelar a versão** — commit das alterações, etiqueta (p. ex. `v1.0-monografia`) e nova execução do pipeline para que o PDF registre o commit sem "arquivos alterados ainda não registrados". Conferir também a visibilidade pública do repositório.
