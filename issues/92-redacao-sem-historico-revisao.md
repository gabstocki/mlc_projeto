# 92 — Retirar a narrativa do processo de revisão (apresentar a solução final)

- **Tema:** Redação
- **Prioridade:** P2
- **Arquivos:** `tese/cap05.tex` (§4.5.2, §4.5.3), `tese/cap06.tex` (§5.1.1), `tese/cap08.tex` (§7.2.1, §7.2.2, §7.4.1, §7.7)
- **Relaciona:** 93 (a do §4.5.2 se resolve refazendo a varredura)
- **Origem:** 4ª revisão, item 7.1

> Mapa de numeração: §N do PDF = `capNN.tex` com NN = N + 1 a partir do §2 (o cap02.tex foi removido).

## Trechos
- [ ] §4.5.3 — “A falta só se tornou visível no desenho cotado da elevação”.
- [ ] §5.1.1 — “a hipótese, aventada em fase anterior do trabalho [...]”.
- [ ] §4.5.2 — “A varredura foi executada [...] antes da adoção do item 5.4.4” → resolver pela issue 93.
- [ ] §7.2.1 — “Era essa a solicitação que levava o fendilhamento [...]”.
- [ ] §7.2.2 — “O valor anterior, de 0,27, decorria de um comprimento de apoio de 0,90 m [...]”.
- [ ] §7.4.1 — “O desenho cotado das bases mostrou que a chapa [...] adotada inicialmente [...]” e “Faltavam ainda duas verificações”.
- [ ] §7.7 — “A conferência levou a uma correção no detalhe da ligação L1 [...]”.
- [ ] Varredura geral por marcadores (“inicialmente”, “anterior”, “passou a”, “corrigid”, “versão”).
- Comparação entre alternativas pode ficar, como estudo de concepção.

## Resolução ✅ (2026-11-11)

| Trecho | Situação |
|---|---|
| §4.5.3 frontão ("só se tornou visível no desenho cotado") | `cap05`: reescrito como requisito ("o painel precisa de um segundo montante a 5,75 m do canto") |
| §5.1.1 ("hipótese aventada em fase anterior… 1.300 kN·m") | `cap06`: vira consequência do modelo ("o pilar não atrai o empuxo: não recebe momento por efeito de arco"). O número de 1.300 kN·m saiu, porque vinha do cálculo antigo de H, superestimado 3,5× |
| §4.5.2 ("executada… antes da adoção do item 5.4.4") | Não era a varredura global (93), e sim a de **painéis de CV vertical**. **Refeita com o pipeline atual** (script na scratchpad, 7 distribuições fachada/central) |
| §7.2.1 ("Era essa a solicitação… 0,97") | Já saíra na issue 68 |
| §7.2.2 (0,27 / 0,90 m), §7.4.1 ("desenho cotado das bases mostrou", "Faltavam"), §7.7 ("A conferência levou") | Já não existiam no texto (removidos em issues anteriores) |
| cap08 "o balanço passou a ser verificado" | "é verificado" |
| cap09, 6.º ponto (0,97 → 0,339) | Mantida como comparação de concepção (permitida), com a lógica e os números atuais: borda carregada, ⅓ da reação, 0,67 |

**Varredura de painéis refeita:** uma única `tab:distribuicao-paineis` substitui a `tab:varredura-paineis` (todos os painéis nas fachadas, Ø33, 106 kN) e a tabela antiga de distribuição. Resultados:

| Fachada / central | Resultado |
|---|---|
| 4/2 e 8/2 | Reprovam: pilar central montante 1,02 e diagonal central Ø48 |
| **4/4** | **Adotado**: Ø36/36, 118 kN, canto 0,45, central 0,75, ancoragem central 0,60, 1.158 kg, 8 baías |
| 8/4, 12/4, 4/8, 8/8 | Atendem, com 12 a 16 baías ocupadas |

O aço continua praticamente independente de n (1.029–1.158 kg), então a conclusão se mantém.

**Varredura final por marcadores:** os restantes são legítimos (história da NBR 7190, declaração de IA "escrito inicialmente pelo autor", "passa a" descrevendo mecânica).

Tese: 163 páginas, 0 overfull (`\tabcolsep` 3 pt na tabela nova), nenhuma referência pendente.

**Fica:** o comentário em `main.py` (L. ~300–360) ainda narra as varreduras antigas. É código, não tese.
