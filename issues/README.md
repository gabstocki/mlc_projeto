# Backlog de revisão — 2ª versão do memorial MLC

Issues derivadas dos apontamentos do orientador sobre a **2ª versão** do memorial
(revisão concluída em 2026-08-29). Cada arquivo é uma issue autocontida para ser
trabalhada caso a caso. Referências normativas: **EN 1995-1-1 (EC5)**, **EN 1990**,
**EN 1991**, **EN 1993-1-8**, **EN 14080**, **NBR 6123**.

> **Nada do modelo/código foi alterado.** Este backlog apenas registra e organiza o
> trabalho a fazer.

## Prioridades
- **P0 — Crítico:** pode invalidar o dimensionamento ou a segurança estrutural.
- **P1 — Importante:** altera esforços/resultados ou é obrigatório por norma.
- **P2 — Completude:** documentação, reprodutibilidade e refinamentos.

## Índice

### Ações e combinações (EN 1990 / EN 1991)
| # | Prioridade | Issue |
|---|-----------|-------|
| 01 | P1 | [Peso próprio gk superestimado](01-gk-peso-proprio-superestimado.md) ✅ |
| 02 | P1 | [Sobrecarga qk categoria H (0,25 → 0,4 kN/m²)](02-qk-categoria-H.md) ✅ |
| 03 | P1 | [ψ₀ categoria H = 0 — sobrecarga não combina com vento](03-psi0-categoria-H-vento.md) ✅ |
| 04 | P1 | [Coeficiente G favorável: 0,9G (NBR) → EN 1990 Tab. A1.2(B)](04-coef-G-favoravel-C3.md) ✅ |
| 05 | P2 | [Combinação frequente ψ₁ categoria H = 0](05-psi1-combinacao-frequente.md) ✅ |
| 33 | P1 | [Sucção/uplift: ancoragem ao arrancamento e tirante frouxo](33-succao-uplift-ancoragem-tirante.md) — desdobramento da 1 ✅ |
| 34 | P2 | [Carga concentrada Q_k=1,0 kN (cat. H): verificação local terça/telha](34-qk-concentrado-terca-telha.md) — desdobramento da 2 ✅ |

### ELS / flechas
| # | Prioridade | Issue |
|---|-----------|-------|
| 06 | P1 | [wfin omite parcela de vento (ψ₀=0,6) e ψ₂ não explícito](06-wfin-vento-psi2.md) ✅ |
| 07 | P1 | [Flecha sem parcela de deformação por cisalhamento](07-flecha-cisalhamento.md) ✅ |

### Materiais (EN 14080)
| # | Prioridade | Issue |
|---|-----------|-------|
| 08 | P2 | [E0,mean / E0,05 sem fonte; EN 1194:1999 revogada](08-materiais-modulos-fonte.md) ✅ |

### Viga — mísula e ápice (EC5 §6.4)
| # | Prioridade | Issue |
|---|-----------|-------|
| 09 | P1 | [Mísula: verificação da face inclinada σm,α,d ausente (§6.4.2)](09-misula-face-inclinada.md) ✅ |
| 10 | P2 | [Zona do ápice: documentar kdis, kvol, Vap, σt,90, kr (§6.4.3)](10-apice-parametros.md) ✅ |
| 11 | P2 | [Memória de cálculo da flambagem lateral (lef, σm,crit, λrel,m, kcrit)](11-flambagem-lateral-memoria.md) ✅ |

### Sistema de eixos e esforços
| # | Prioridade | Issue |
|---|-----------|-------|
| 12 | P1 | [Sistema de eixos: N no eixo da peça vs V vertical](12-sistema-eixos-N-V.md) ✅ |
| 13 | P0 | [Esforços nos pilares: dois valores de N; pilar central subdimensionado](13-pilares-esforcos-central.md) ✅ |

### Estabilidade e contraventamento
| # | Prioridade | Issue |
|---|-----------|-------|
| 14 | P0 | [Contraventamento vertical/frontões ausente — mecanismo lateral; αcr de arco ≠ sway](14-contraventamento-vertical.md) ✅ |
| 15 | P1 | [Contraventamento do telhado: n=18 vs dois planos de 9; kf/ks e duplicação](15-contraventamento-telhado-n18.md) ✅ |
| 31 | P0 | [Estabilidade transversal do pórtico (mecanismo sway no plano)](31-estabilidade-transversal-portico.md) — desdobramento da 14 ✅ |
| 32 | P2 | [Elemento de beiral como corda do diafragma de cobertura](32-corda-diafragma-beiral.md) — desdobramento da 31 ✅ |
| 35 | P1 | [Empuxo de gravidade não se desenvolve (beiral flexível): incoerência viga×pilar×tirante; revisa a 24](35-empuxo-pilar-caminho-carga.md) ✅ (Opção B implementada: viga biapoiada, tirante removido, reforço L1) |
| 36 | P1 | [Download do contraventamento (±V_Ed·tanβ) não entra na verificação dos pilares dos painéis; tração sob uplift](36-download-contraventamento-pilares.md) ✅ (resta refino P2: concomitância por direção de vento) |
| 38 | P1 | [Caminho horizontal transversal do empuxo: auditar o "colapso do pilar" e fechar a decisão da 35](38-caminho-horizontal-transversal-coerencia.md) — auditoria ✅ (decisão: Opção B; implementação do modelo na 35) |

### Terças
| # | Prioridade | Issue |
|---|-----------|-------|
| 16 | P1 | [Terça: interação flexão + compressão combinada (Eq. 6.23/6.24)](16-terca-flexo-compressao.md) ✅ |
| 17 | P2 | [Ligação telha-terça sob sucção (ou dado do fabricante)](17-ligacao-telha-terca-succao.md) ✅ |

### Ligações (EC5 §8 / EN 1993-1-8)
| # | Prioridade | Issue |
|---|-----------|-------|
| 18 | P0 | [Cavilhas Ø36 mm > limite EC5 §8.6(2) — L1/L1c fora do escopo](18-cavilhas-diametro-36mm.md) ✅ |
| 19 | P0 | [Ruptura de bloco na ligação de 64 pinos](19-ruptura-de-bloco.md) ✅ |
| 20 | P1 | [Fendilhamento — F90,Rd (EC5 §8.1.4)](20-fendilhamento-f90.md) ✅ |
| 21 | P1 | [Chapas de aço, furos e soldas (EN 1993-1-8)](21-chapas-aco-en1993.md) ✅ |
| 22 | P1 | [Critério η-alvo 0,75: ligações com η≈1 — verificar ativação](22-criterio-eta-alvo.md) ✅ |
| 23 | P2 | [Dimensões das chapas não publicadas (incl. base do pilar central)](23-dimensoes-chapas.md) ✅ |
| 24 | P2 | [Tirante: fy 315 MPa e hipótese de apoio horizontal indeslocável](24-tirante-fy315-flexibilidade.md) ✅ |
| 37 | P1 | [Tirante ao nível do piso em estacionamento: impacto veicular, corrosão, fogo e tropeço](37-tirante-piso-robustez-impacto-corrosao-fogo.md) — desdobramento do caminho transversal ✅ |

### Modelo — coerência e situações transitórias
| # | Prioridade | Issue |
|---|-----------|-------|
| 25 | P1 | [L2 pino Ø30 na cumeeira: resquício do modelo triarticulado](25-L2-pino-cumeeira-remover.md) ✅ |
| 26 | P1 | [Situação de içamento da viga (combinação de montagem)](26-icamento-viga.md) ✅ |

### Reprodutibilidade do memorial
| # | Prioridade | Issue |
|---|-----------|-------|
| 27 | P1 | [Derivação de Castigliano + diagramas M/V/N (anexo de análise)](27-memorial-castigliano-diagramas.md) ✅ |
| 28 | P1 | [Tabela das 24 combinações + Cpe dos 8 padrões](28-memorial-24-combinacoes.md) ✅ |
| 29 | P1 | [Memória da ligação L1 (Johansen, fh,0,k, My,Rk, t1/t2, a1–a4, Kser)](29-memorial-ligacao-L1.md) ✅ |
| 30 | P2 | [Declarar classe de uso (EN 335), adesivo (EN 301) e tratamento preservativo](30-memorial-classe-uso-adesivo.md) ✅ |

## Rastreabilidade dos apontamentos

Todos os ~30 comentários do orientador estão cobertos. O bloco final de
"omissões que tornam não reprodutíveis os resultados" foi consolidado com os
comentários avulsos correspondentes (ex.: os dois valores de N nos pilares →
issue 13; parâmetros do ápice → issue 10; memória de flambagem → issue 11) para
evitar duplicação.

---

# Backlog — 3ª revisão do orientador (2026-10)

Apontamentos do e-mail do orientador sobre a versão com viga biapoiada (Opção B). Ele
conferiu de forma independente M_d, R_d, flechas, t90 na cumeeira, cisalhamento, pilar
central e fendilhamento — **os valores conferem**. As issues abaixo tratam as correções
técnicas, o memorial e a formatação. Os comentários anotados no PDF vão até a p. 35
(issue 62 estende ao restante). PDF anotado: `main (1)gavassoni.pdf` na raiz — 17 anotações,
todas cobertas; as das pp. 29 e 36 não estavam no e-mail (issue 63).


### Ações — vento e combinações
| # | Prioridade | Issue |
|---|-----------|-------|
| 39 | P1 | [Vento: a estrutura É cobertura isolada; último parágrafo do §7.2.1 (h, tabela C_pe, zona de obstrução)](39-vento-cobertura-isolada-7-2-1.md) | ✅
| 45 | P1 | [Sobrecarga dominante + vento acompanhante ψ₀=0,6? (EN 1991-1-1 §3.3.2(1))](45-combinacao-Q-dominante-vento-psi0.md) | ✅

### Análise e estabilidade
| # | Prioridade | Issue |
|---|-----------|-------|
| 40 | P2 | [Esforço normal analítico N(x)=V(x)·sen(α/2)](40-esforco-normal-analitico.md) | ✅
| 41 | P1 | [ℓ do EC5 §9.2.5 = 20,25 m (k_ℓ 0,57→0,86); remover “efeito contraintuitivo”](41-ell-contraventamento-9-2-5.md) ✅ |
| 64 | P1 | [Caminho longitudinal: treliça apoia na linha central sem contraventamento vertical](64-caminho-longitudinal-linha-central.md) — desdobramento da 41 | ✅ (Opção A: 4 fachadas + 4 central)
| 65 | P2 | [§9.2.5.3: q_d além do vento (soma, não máximo)](65-qd-mais-vento-9-2-5-3.md) — desdobramento da 41 | ✅
| 66 | P1 | [L1 nas baías contraventadas: força ⊥ ao pórtico (reação da treliça) não verificada](66-l1-forca-fora-do-plano-bracing.md) — desdobramento da 42 | ✅
| 46 | P1 | [Imperfeições: EN 1995-1-1 §5.4.4; α_cr por analogia](46-imperfeicoes-EC5-5-4-4.md) | ✅
| 47 | P1 | [Flambagem lateral sob sucção (intradorso comprimido)](47-ltb-succao-intradorso.md) | ✅

### Ligações e contraventamento
| # | Prioridade | Issue |
|---|-----------|-------|
| 42 | P1 | [Caminho da reação de apoio: contato direto; compressão no apoio; desenho L1c](42-caminho-reacao-apoio-L1-L1c.md) | ✅
| 43 | P1 | [Detalhamento das ligações com espaçamentos](43-detalhamento-ligacoes-espacamentos.md) | ✅
| 44 | P1 | [Diagonais: capacidade (rosca × escoamento) e critério uniforme](44-diagonais-capacidade-rosca.md) | ✅
| 48 | P1 | [Base L3: impacto de veículo + arrancamento 83,9 kN; η=0,0000 incoerente](48-base-L3-impacto-arrancamento.md) | ✅

### Memorial — conteúdo e apresentação
| # | Prioridade | Issue |
|---|-----------|-------|
| 49 | P2 | [Reescrever §5.2.3 com o mecanismo real](49-reescrever-5-2-3-mecanismo.md) | ✅
| 50 | P1 | [Equações simbólicas nas verificações governantes](50-equacoes-simbolicas-memorial.md) | ✅
| 51 | P2 | [Tabelas de entrada × resultado; anexos de análise e saída do pipeline](51-organizacao-entradas-resultados-anexos.md) | ✅
| 52 | P1 | [Desenhos cotados/em escala + nomenclatura V1, P1…](52-desenhos-nomenclatura.md) | ✅
| 53 | P2 | [Precisão numérica (η 2 casas; forças 3 alg. sig.)](53-precisao-numerica.md) | ✅
| 55 | P2 | [Declarar softwares e uso de IA](55-softwares-ia-declarados.md) | ✅
| 56 | P1 | [Lista de símbolos + coluna de símbolo na Tabela 4](56-lista-simbolos-tabela4.md) | ✅

### Texto e formatação (anotações do PDF, até p. 35)
| # | Prioridade | Issue |
|---|-----------|-------|
| 54 | P2 | [Palavras-chave / Keywords](54-palavras-chave-keywords.md) | ✅
| 57 | P2 | [Introdução: abertura mais ampla](57-introducao-paragrafo-inicial.md) | ✅
| 58 | P2 | [§1.1: ELU/ELS não começaram em 2022](58-contexto-normativo-elu-els.md) | ✅
| 59 | P2 | [Objetivos como subseção do cap. 1](59-objetivos-reorganizar.md) | ✅
| 60 | P1 | [Reescrever a revisão bibliográfica](60-revisao-bibliografica-reescrever.md) | ✅
| 61 | P2 | [Cap. 4: redação](61-cap4-redacao.md) | ✅
| 62 | P2 | [Revisão textual do restante (após p. 35)](62-revisao-textual-geral.md) | ✅
| 63 | P2 | [Figuras: variáveis da varredura (§5.2) e modelo estrutural (§6.1)](63-figuras-varredura-e-modelo.md) — só no PDF | ✅

**Ordem sugerida:** 41, 45, 46, 47, 48, 44, 42 (alteram resultados) → 39, 40, 49 → 43, 52, 50, 56, 53, 51 → texto (54–62).

---

# Backlog — 4ª revisão do orientador (2026-11)

Observações sobre a versão com as issues 39–66 e 43 resolvidas. O orientador considera
atendida praticamente toda a revisão anterior e **confirma a concepção das ligações**
(gravidade por contato, arrancamento pelos pinos, oblongos verticais). Os pontos novos tratam
caminho de cargas, durabilidade, incêndio, desenhos, redação e coerência.

> **Mapa de numeração:** o §N citado pelo orientador corresponde a `tese/capNN.tex` com
> NN = N + 1 a partir do §2 (o `cap02.tex` foi removido): §2 → cap03, §3 → cap04, …, §7 → cap08, §8 → cap09.

### Pré-textuais e fundamentação
| # | Prioridade | Issue | Item |
|---|-----------|-------|------|
| 67 | P1 | [Nome oficial do curso (capa, rosto, termo)](67-nome-oficial-curso.md) ✅ — dado do autor | intro |
| 68 | P2 | [Lógica das ligações explícita no texto; η ≤ 0,75 como critério do autor](68-logica-ligacoes-texto.md) | 1 ✅ |

### Ligações — caminho de cargas e verificações
| # | Prioridade | Issue | Item |
|---|-----------|-------|------|
| 69 | P0 | [Ligação chapa de topo / sela ao pilar](69-ligacao-chapa-topo-sela-pilar.md) ✅ | 2.1 |
| 70 | P1 | [Rasgo: b − t_rasgo na compressão ⊥ e no cisalhamento](70-rasgo-largura-apoio-cisalhamento.md) ✅ | 2.2 |
| 71 | P1 | [Altura do rasgo, lâmina de 14 mm, folga no fundo](71-altura-rasgo-folga-fundo.md) ✅ | 2.3, 6.3, 10.8 |
| 72 | P1 | [Oblongos L1/L1c: posição do pino e curso (retração/fluência)](72-oblongos-L1-posicao-pino-retracao.md) ✅ | 2.4 |
| 73 | P1 | [Enrijecedores da sela L1c](73-sela-L1c-enrijecedores.md) ✅ | 2.5 |
| 74 | P1 | [Chumbadores: texto “soldada 8.8” e cortante com alavanca](74-chumbadores-texto-8-8-alavanca.md) ✅ | 2.6 |
| 75 | P0 | [Ruptura de bloco: pé dos pilares, montante terça–viga, L1/L1c](75-ruptura-de-bloco-pe-pilares-montante.md) ✅ | 2.7–2.9 |
| 76 | P0 | [Pé do pilar: seção líquida, F90 do impacto, direção do choque, a4,t](76-pe-pilar-impacto-secao-liquida.md) ✅ | 2.10, 3.1 |
| 77 | P1 | [Terça–viga: apoio em garfo; Tab. 34](77-terca-viga-garfo-tab34.md) ✅ | 2.11, 3.4 |
| 78 | P1 | [Soldas: especificar e verificar](78-soldas-especificar-verificar.md) ✅ | 2.12 |
| 79 | P0 | [d0 com folga nos furos das chapas](79-folga-d0-furos-chapas.md) ✅ | 3.2 |
| 80 | P1 | [Furos da chapa de base: tolerância e aperto](80-furos-chapa-base-tolerancia.md) ✅ | 3.3 |

### Durabilidade
| # | Prioridade | Issue | Item |
|---|-----------|-------|------|
| 81 | P1 | [Retração impedida: ovalizar ⊥ às fibras](81-retracao-impedida-chapas-embutidas.md) ✅ | 4.1 |
| 82 | P1 | [Beiral e oitão — decisão do autor](82-beiral-oitao-decisao.md) ✅ | 4.2 |
| 83 | P1 | [Topos, vedação do rasgo, calha e rufos](83-protecao-topos-rasgo-rufos.md) | 4.3, 6.7 ✅ |
| 84 | P2 | [Faces expostas: acabamento e estética](84-faces-expostas-acabamento.md) | 4.4 ✅ |
| 85 | P1 | [UC 3.2, espécie e tratamento](85-classe-uso-UC32-tratamento.md) ✅ | 4.5 |
| 86 | P1 | [Proteção contra corrosão](86-protecao-corrosao-aco.md) | 4.6 ✅ |
| 87 | P0 | [Pilarete metálico](87-pilarete-metalico.md) ✅ | 4.7, 6.6 |

### Incêndio
| # | Prioridade | Issue | Item |
|---|-----------|-------|------|
| 88 | P1 | [TRRF pela NBR 14432 e CBPMPR](88-incendio-TRRF-NBR14432-CBPR.md) | 5.1, 8.6, 10.7 ✅ |
| 89 | P2 | [Incêndio localizado de veículo](89-incendio-localizado-veiculo.md) | 5.2 ✅ |

### Desenhos
| # | Prioridade | Issue | Item |
|---|-----------|-------|------|
| 90 | P1 | [L1/L1c: corte A–A, linha oculta, chapa em VG, DES-05](90-desenhos-L1-L1c-corte-vg.md) | 6.1–6.3 ✅ |
| 91 | P1 | [Desenhos faltantes; soldas/aço/proteção; sela e bases](91-desenhos-faltantes.md) | 6.4–6.6 ✅ |

### Redação, referências e notação
| # | Prioridade | Issue | Item |
|---|-----------|-------|------|
| 92 | P2 | [Retirar a narrativa do processo de revisão](92-redacao-sem-historico-revisao.md) | 7.1 ✅ |
| 93 | P1 | [Refazer a varredura global com o critério atual](93-refazer-varredura-global.md) | 7.1 (§4.5.2) ✅ |
| 94 | P2 | [Erros de redação pontuais](94-redacao-erros-pontuais.md) ✅ | 7.2 |
| 95 | P1 | [Referências: letras, EN 1992-4, “Citado n vezes”, destaque](95-referencias-formato-abnt.md) ✅ | 8.1, 8.3, 8.4 |
| 96 | P1 | [Afirmações sem fonte](96-afirmacoes-sem-fonte.md) ✅ — dados do autor | 8.2 |
| 97 | P1 | [Símbolos: ausentes, unicidade, notação única](97-lista-simbolos-unicidade.md) ✅ | 9.1–9.3 |
| 98 | P2 | [Lista de siglas](98-lista-siglas.md) ✅ | 9.4 |

### Coerência
| # | Prioridade | Issue | Item |
|---|-----------|-------|------|
| 99 | P1 | [Números divergentes, precisão, Apêndice D](99-coerencia-numerica-capitulos.md) — por último ✅ | 10.1, 10.8 |
| 100 | P1 | [Afirmações que contradizem os resultados](100-afirmacoes-contraditorias.md) | 10.2 ✅ |
| 101 | P1 | [Objetivos × resultados (terças; objetivo c)](101-objetivos-terca-detalhamento.md) — decisão do autor | 10.3 ✅ |
| 102 | P1 | [Esforços característicos para a fundação](102-esforcos-caracteristicos-fundacao.md) ✅ | 10.4 |
| 103 | P2 | [Título e resumo](103-titulo-resumo.md) ✅ — decisão do autor | 10.5, 10.6 |
| 124 | P1 | [Varredura: causas de reprovação omitidas (`ok` numpy.bool_)](124-varredura-causas-numpy-bool.md) ✅ | achado próprio, 2026-11-15 |
| 123 | P2 | [Redação: menos certeza do que a demonstração e ajustes pontuais](123-redacao-certeza-e-ajustes.md) ✅ | revisão técnica, item 15 |
| 122 | P2 | [Resumo e conclusões com o alcance efetivamente demonstrado](122-alcance-conclusoes-resumo.md) ✅ | revisão técnica, item 14 |
| 121 | P1 | [Validação computacional documentada e versão congelada](121-validacao-computacional-versao.md) ✅ (falta etiquetar a versão) | revisão técnica, item 13 |
| 120 | P2 | [Especificações de materiais menos categóricas (adesivo, tratamento, GL24h)](120-especificacoes-materiais-redacao.md) ✅ | revisão técnica, item 12 |
| 119 | P1 | [Incêndio: NPT 008 (nova edição, nov/2026) e análise localizada como estudo exploratório](119-incendio-npt008-2026-exploratorio.md) ✅ — NPT 008 v03/2026 | revisão técnica, item 11 |
| 118 | P2 | [Hierarquia de ruptura: retirar ductilidade presumida](118-hierarquia-ruptura-ductilidade.md) ✅ | revisão técnica, item 10 |
| 117 | P2 | [Quantitativo por lista explícita de peças (terças, espaçadores)](117-quantitativo-explicito-pecas.md) ✅ | revisão técnica, item 9 |
| 116 | P1 | [Equivalência cálculo × cota de desenho × lista de fabricação](116-calculo-desenho-fabricacao.md) ✅ | revisão técnica, item 8 |
| 115 | P1 | [Memorial: equações que não reproduzem o resultado e tabelas dessincronizadas](115-memorial-equacoes-tabelas-sincronia.md) ✅ | revisão técnica, item 7 |
| 114 | P1 | [Peso próprio da viga com altura variável (hoje uniforme médio)](114-peso-proprio-variavel-viga.md) ✅ | revisão técnica, item 6 |
| 113 | P1 | [Rigidez horizontal do apoio no sistema espacial (empuxo nulo)](113-rigidez-horizontal-apoio-sistema.md) ✅ | revisão técnica, item 5 |
| 112 | P1 | [Deslocamento total sob sucção: folgas, pinos, tirante, chapas e viga](112-deslocamentos-succao-total.md) ✅ | revisão técnica, item 4 |
| 111 | P1 | [L1: furos ovalizados e engajamento progressivo dos pinos](111-l1-oblongos-engajamento-progressivo.md) ✅ — grupo 3×2 | revisão técnica, item 3 |
| 110 | **P0** | [Caminho transversal até os frontões e diafragma nas baías intermediárias](110-caminho-transversal-diafragma.md) ✅ | revisão técnica, item 2 |
| 109 | **P0** | [Vento longitudinal entra sem γ_Q nos contraventamentos](109-vento-longitudinal-sem-gamma-q.md) ✅ | revisão técnica, item 1 |
| 108 | P2 | [Sela e pé das lâminas do bipartido: tirante por lâmina?](108-tirante-por-lamina-bipartido.md) ✅ mantida a solução atual | — |
| 107 | P2 | [Largura de 0,30 m passou a aprovar: manter 0,32 m?](107-largura-030-aprova.md) ✅ mantida 0,32 m | — |
| 106 | P1 | [Efeitos do bipartido e do tirante ainda não propagados](106-efeitos-bipartido-tirante.md) | — ✅ |
| 105 | P1 | [Concepção das ligações (tirante interno, nó por contato, chapas duplas) e padrão gráfico](105-concepcao-ligacoes-padrao-grafico.md) | — ✅ |
| 104 | **P0** | [Nó de topo: excentricidade h0 entre escora e topo do pilar](104-no-topo-excentricidade-escora.md) — achado na 91; pilar bipartido | — ✅ |

## Sequência de trabalho

Princípio: decidir o que muda a **concepção** antes de calcular; calcular de **cima para
baixo** em cada caminho de carga (o que está acima define a força e a geometria do que está
abaixo); **especificar** depois que as peças estiverem fixas; **desenhar** só a geometria final;
**texto e coerência** por último, sobre números estáveis.

| Fase | Ordem | Issue | Por que nesta posição |
|---|---|---|---|
| 0 — Decisões | 1 | 82 Beiral/oitão | Muda o modelo da viga (balanço), a posição da L1, a exposição dos topos e a classe de uso |
| | 2 | 101 Terças: dimensionar ou ajustar objetivo | Se dimensionar, muda seção/espaçamento → terça–viga, escoras, nó de topo |
| | 3 | 85 Espécie e tratamento (UC 3.2) | Pode mudar ρ_k/classe e o texto de materiais |
| 1 — Concepção/modelo | 4 | (82 implementada, se “sim”) | Maior propagação; tudo abaixo depende dela |
| | 5 | (101 implementada, se dimensionar) | |
| | 6 | 87 Pilarete metálico | Muda altura livre do pilar, ponto do impacto e a cadeia da base |
| 2 — Topo (viga → pilar) | 7 | 72 Oblongos: curso e posição do pino | Define o curso → altura da chapa |
| | 8 | 71 Altura do rasgo, folga no fundo | Fecha a altura da chapa (977 mm hoje) e a lâmina superior |
| | 9 | 70 Apoio com b − t_rasgo | Depende da espessura do rasgo |
| | 10 | 73 Enrijecedores da sela | Sela definida antes de prendê-la ao pilar |
| | 11 | 81 Retração impedida (critério) | Critério que a 69 deve adotar desde a concepção; aplica a escoras e montante |
| | 12 | 69 Chapa de topo/sela → pilar | Nova ligação com forças do arrancamento e do nó de topo |
| | 13 | 77 Terça–viga: garfo e Tab. 34 | Fecha a cobertura |
| 3 — Base (pilar → fundação) | 14 | 76 Pé do pilar sob impacto | Direção do choque e a4,t mudam a geometria do pé |
| | 15 | 75 Ruptura de bloco (pé, montante, L1/L1c) | Com a geometria do pé e do montante já fixa |
| | 16 | 80 Furos da chapa de base e aperto | Chapa de base sobre o pilarete |
| | 17 | 74 Chumbadores: texto 8.8 e alavanca | Depende de graute/porca e do pilarete |
| | 18 | 102 Esforços característicos à fundação | Forças finais da base |
| 4 — Especificação | 19 | 78 Soldas | Todas as chapas já definidas (inclui 69, 73, 87) |
| | 20 | 86 Corrosão | Lista final de peças de aço |
| | 21 | 83 Topos, rasgo, calha e rufos | Depende da 82 |
| | 22 | 84 Faces expostas | Depende da 82 e da 85 |
| 5 — Incêndio | 23 | 88 TRRF (NBR 14432 / CBPMPR) | Pode retirar a verificação R30 → muda a contagem de verificações |
| | 24 | 89 Incêndio localizado de veículo | Comentário sobre a solução final |
| 6 — Resultados globais | 25 | 93 Refazer a varredura global | Só depois de todo cálculo mudar |
| 7 — Desenhos | 26 | 90 L1/L1c: corte A–A, linha oculta, VG | Geometria final do topo |
| | 27 | 91 Desenhos faltantes, soldas, aço, níveis | Depende de 69, 78, 86, 87 |
| 8 — Texto | 28 | 68 Lógica das ligações | Sobre a solução final |
| | 29 | 92 Retirar a narrativa de revisão | |
| | 30 | 100 Afirmações contraditórias | |
| | 31 | 101 (c) Objetivo (c) no §8.1 | Após 69 e 91 |
| | 32 | 96 Afirmações sem fonte | Dados do autor |
| | 33 | 95 Formato das referências | Depois de todas as referências novas (EN 1090-2, NBR 14432, NPT…) |
| | 34 | 97 Lista de símbolos | Depois dos símbolos novos (pilarete, soldas, retração) |
| | 35 | 98 Lista de siglas | Depois da 88 (TRRF, CBPMPR) |
| | 36 | 94 Erros pontuais | Passada de estilo sobre o texto já reescrito |
| | 37 | 103 Título e resumo | Resumo escrito sobre os resultados finais |
| 9 — Fechamento | 38 | 99 Coerência numérica + Apêndice D | Última execução do pipeline gera texto, apêndices e console |
| A qualquer momento | — | 67 Nome do curso | Só depende do dado oficial |

Feitas: 79 (d0 com folga) ✅, 82 (beiral 1,00 m em A/C + oitões) ✅, 101 parte (a) (terça 0,20 × 0,40 dimensionada) ✅ — parte (c) após 69/91, 85 (pinus, lamelas tratadas, UC 3.1/3.2) ✅, 87 (pilarete Ø139,7×8, h 0,30 m) ✅, 72 (curso 15 mm abaixo / 20 mm acima) ✅, 71 (pinos a 818 mm, rasgo 892, 108 mm acima) ✅, 70 (b − 29 mm: apoio 0,49, cisalh. 0,41) ✅, 73 (3 enrijecedores 125×125×12,5 + chapas laterais 250) ✅, 81 (D⊥ ≤ 133 mm ou ovalizado ⊥; pé ≤ 3 fileiras) ✅, 69 (chapa vertical + cavilhas no topo; nó deslizante 2×M24) ✅, 77 (garfo M_d/80; l_ef 160; a1/a2 corrigidos) ✅, 76 (a4,t 80 → 2 fileiras; F90 0,58; fora do plano por contato) ✅, 75 (Anexo A completo, conferido na EN 1995-1-1; L3a a2 90) ✅, 80 (furo Ø36 + arruela-chapa soldada) ✅, 74 (chaveta em cruz nas bases correntes) ✅, 102 (característicos por ação, tabelas geradas) ✅, 78 (quadro de soldas, 30 cordões) ✅, 86 (galvanização a fogo + dúplex nas bases; respiros no pilarete) ✅, 83 (rufos ventilados, rasgo ventilado, calha 300×150 com saída por pórtico; DES-10) ✅, 84 (impregnante pigmentado + plano de manutenção) ✅, 88 (isenta de TRRF pela NPT 008 PR; R30 informativo; retardante 5.17) ✅, 89 (incêndio de veículo: madeira 83 min; pilarete com intumescente R60) ✅, 93 (varredura 3.213 pontos; 1.067 aprovadas; b ≥ 0,30 e α ≥ 8° por elementos externos à viga) ✅, 90 (DES-05 L1 + A–A, DES-05B L1c + B–B, DES-05C chapa em VG; furos em linha oculta) ✅, 91 (DES-11 a 14; soldas em cada folha; 7 emendas da corda; montante 2×4 no rasgo superior; terminal CV-H; nó → 104) ✅, 68 (lógica das ligações no texto: caminho único, f_t,90 ≪ f_c,90, borda carregada, Eq. 8.11 chapa espessa, 0,75 critério do autor, tab:cadeia-base) ✅, 92 (narrativa de revisão retirada; varredura de painéis CV refeita: 4/4 adotado) ✅, 100 (afirmações × resultados: CV cobertura 0,89, Tab. 13, §6.8, içamento a 0,247·L iguala M, resumo 'reduziu') ✅, 101 (c) (§8.1 por objetivo; nó de topo declarado não detalhado → 104) ✅, 104 (pilar bipartido nos 14 montantes; nó no nível da escora; DES-15) ✅, 105 (tirante interno, nó por contato, chapas duplas; DES-00, listas de peças; 1.448 → 928 cavilhas) ✅.

**Rastreabilidade:** todos os itens da 4ª revisão (1.1–10.8) estão em alguma issue (coluna “Item”).

## Revisão técnica (comentários tipo banca, 2026-11-14) — issues 109–123

Ordem de execução, seguindo o item 16 dos comentários:

| Etapa | Issues | Por quê |
|---|---|---|
| 1 — Ações e caminho de carga | **109** (γ_Q no vento longitudinal), **110** (diafragma transversal) | Mudam forças em todo o contraventamento; 110 pode exigir novo sistema |
| 2 — Modelo da viga | 114 (peso próprio variável), 113 (rigidez horizontal no sistema, usa o modelo da 110) | Mudam M_Ed e o modelo de apoio |
| 3 — Ligação de arrancamento | 111 (engajamento progressivo), 112 (deslocamento total) | Pode reformular a L1 |
| 4 — Sincronização | 115 (memorial), 116 (cálculo × desenho), 117 (quantitativos) | Depois do cálculo estabilizado |
| 5 — Programa | 121 (verificação independente, versão congelada) | Documenta a versão final |
| 6 — Incêndio e especificação | 119, 120, 118 | Texto e norma atualizada |
| 7 — Fechamento | 122 (conclusões), 123 (redação) | Por último |
