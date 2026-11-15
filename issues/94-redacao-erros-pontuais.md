# 94 — Erros de redação pontuais

- **Tema:** Redação
- **Prioridade:** P2
- **Arquivos:** `tese/cap01.tex`, `cap03.tex`, `cap04.tex`, `cap05.tex`, `cap07.tex`, `cap08.tex`, `cap09.tex`, Tabela 8 (software)
- **Origem:** 4ª revisão, item 7.2

## Checklist
- [x] §1.1 — repetição “dependem de parâmetros de determinação nacional, os parâmetros de determinação nacional (NDP)”.
- [x] §3.5.1 e §8.4.1 — “submetida sob um anexo nacional” → “submetida a um anexo nacional”.
- [x] §4.2.3 — “sobe de 0,90 a 0,90 entre α = 6,5° e 7,5°”: usar mais casas ou reescrever.
- [x] §7.2.2 — “A sela balança 125 mm” → “projeta-se em balanço 125 mm”; “não balança” → “não tem balanço”.
- [x] §7.5.3 — “O fendilhamento do concreto, esse, é aplicável” e “transmitido que é pela chaveta”: ordem direta.
- [x] §7.4 — “Não se credita o atrito” → “Não se considera o atrito”.
- [x] §6.3 — “Solicita-o o peso próprio, o esforço [...] e o vento” → “Solicitam-no”.
- [x] “contra” no sentido de comparação → “em comparação com” / “frente a” (varrer o texto inteiro: “lidos contra os 208.462 kN/m”, “504 kN·m contra os 504 kN·m”, “contra 1.780 kN”…).
- [x] §3.3.2 — com k_def = 2,00 a parcela diferida **dobra** a instantânea; a flecha final é que triplica.
- [x] §4.1 — “cinquenta e cinco verificações” × 64 do §6.1 (ver issue 99).
- [x] Padronizar “pinus” (§2.2 “pínus” × §7.10.2 “pinus”).
- [x] Números em algarismos no texto técnico (“vinte e nove combinações”, “sessenta por cento”…).
- [x] Tabela 8 — “TEX Live” → “TeX Live”; “abnTEX2” → “abnTeX2” (logos).

## Resolução (2026-11-12)
- §1.1: a sigla passou a ser introduzida uma só vez ("dependem de \criarsigla*{NDP}{parâmetros de determinação nacional}").
- "Submetida sob" passou a "submetida a" (cap. 4 e 9).
- §4.2.3 "0,90 a 0,90": o trecho já não existe; a seção foi reescrita na varredura refeita (issue 106).
- Sela "projeta-se em balanço 125 mm" e "não se considera o atrito": já estavam corrigidos.
- §7.5.3: "já que a chaveta o transmite ao bloco. O fendilhamento do concreto é aplicável…", em ordem direta.
- "Solicitam-no o peso próprio…".
- "contra" comparativo passou a "frente a", "em comparação com", "para" ou "comparados com", em 15 ocorrências (cap. 3, 5, 6, 7 e 8). Ficaram os usos próprios: proteção contra corrosão e incêndio, compressão contra a face.
- k_def: o cap. 4 diz que a parcela diferida chega ao dobro da instantânea e a flecha final ao triplo. O cap. 7 ("multiplicar por três a parcela permanente da flecha") já estava certo.
- §4.1: as contagens vêm das macros (issue 99).
- "pinus": já padronizado, sem ocorrência de "pínus".
- Números em algarismos: 29 combinações, 14/13 padrões, 15 combinações, 16 folhas, 17, 18 vigas, 15/14 pilares, 22 %, 2 %, 15/12/25 %. O custo usa as macros de porcentagem.
- Tabela 8: "TeX Live" e "abnTeX2" em texto simples, sem os logotipos.
- Apêndice A: "27.096 linhas em sessenta arquivos" estava desatualizado. Agora sai das macros `\nLinhasCodigo` / `\nArquivosCodigo`, geradas pelo pipeline (hoje 32.986 linhas em 78 arquivos).
