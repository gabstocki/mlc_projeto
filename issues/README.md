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
