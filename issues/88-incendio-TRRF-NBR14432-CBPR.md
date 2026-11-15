# 88 — Tempo requerido de resistência ao fogo pela NBR 14432 e pela norma do CBPMPR

- **Tema:** Incêndio
- **Prioridade:** P1
- **Normas:** ABNT NBR 14432:2001; Código de Segurança Contra Incêndio e Pânico do CBPMPR — NPT de resistência ao fogo (NPT 008) e de carga de incêndio (NPT 014); EN 1995-1-2
- **Arquivos:** `tese/cap01.tex` §1.4 (delimitação), `tese/cap09.tex` §8.4.3, verificação de seção residual (R30) no código/texto, bibliografia
- **Origem:** 4ª revisão, itens 5.1, 8.6 e 10.7

## Problema
O R30 está como “declaração de projeto”, sem enquadramento normativo. O EC5 define como
verificar, não se a verificação é exigida.

## O que fazer
- [x] Determinar o TRRF informando: ocupação (G-1 ou G-2), edificação térrea e aberta lateralmente,
      área 1.863 m², carga de incêndio q_fi.
- [x] Avaliar as isenções prováveis (garagem aberta lateralmente; térrea com q_fi ≤ 500 MJ/m²).
- [x] Se isenta: retirar a verificação de seção residual (ou mantê-la como informativa, explicitando).
- [x] Incluir a referência da instrução técnica estadual usada.
- [x] Atualizar §1.4 e §8.4.3.

## Resolução ✅

- **Fontes lidas:** textos oficiais baixados do site do CBPMPR e extraídos com pdftotext.
  - NPT 008 v02 (jan/2012).
  - NPT 014 v05 (ago/2020, vigência mar/2021).
- **Enquadramento:**
  - Ocupação G-1/G-2: estacionamento de veículos, CNAE 5223-1/00; q_fi = 200 MJ/m² para as duas divisões (NPT 014 Anexo A).
  - Edificação térrea, classe P1.
  - Aberta lateralmente (NPT 008 §5.11).
  - Área de 2.067 m²: não cabe nas isenções por área (A2.3.1 e A2.3.2).
- **Isenta por duas vias independentes:**
  1. **A2.3.10 b):** térrea com q_fi ≤ 500 MJ/m². Nenhuma exceção de A2.3.10.1 se aplica (cobertura não é piso nem rota de fuga, sem compartimentação).
  2. **A2.4 c):** se a CTPI somar a madeira da estrutura (324 m³ × 420 kg/m³ × 19 MJ/kg / 2.067 m² ≈ 1.250 MJ/m²), a Tabela A dá 30 min para G aberta lateralmente P1, reduzidos em 30 min para térrea aberta lateralmente → 0.
- **Achado:** o item 5.17 exige retardante ao fogo em edificação > 750 m² com madeira, mesmo isenta.
  - Especificado em `ssec:faces-expostas`: retardante de superfície, uso exterior, compatível com o impregnante, com laudo.
  - Linha nova em cap04.
- **TODO (confirmar com o CBPMPR):**
  - Se q_fi inclui a estrutura.
  - Se A2.4 c) se aplica sobre a linha "abertos lateralmente" (vedação de sobreposição em A2.6).
  - A nota 3 da Tabela A remete a um item 5.20 inexistente.
  - Classe de reação ao fogo do retardante (NPT 010).
- **Código:**
  - `R_fogo_req_min` passa a origem PROJETO, com a cláusula da NPT 008, e sai de `parametros_a_confirmar`.
  - Catálogo: "Fogo R30 (informativa)", η 0,21.
  - Console explica a isenção.
- **Testes:** `test_fogo` e `test_f13` atualizados. 814 passed.
- **Tese:**
  - cap01 §delimitação reescrita.
  - Nova `ssec:trrf` no cap07.
  - cap09 §escopo atualizado.
  - Bib: CBPMPR-NPT008:2012 e NPT014:2020.
  - 149 p., 0 overfull.
- **Incêndio localizado de veículo:** fica para a issue 89.
