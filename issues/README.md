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
| 43 | P1 | [Detalhamento das ligações com espaçamentos](43-detalhamento-ligacoes-espacamentos.md) |
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
