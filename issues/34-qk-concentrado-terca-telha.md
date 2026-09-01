# 34 — Carga concentrada Q_k = 1,0 kN (categoria H): verificação local terça/telha

- **Tema:** Ações / verificações locais
- **Prioridade:** P2
- **Normas:** EN 1991-1-1 Tab. 6.10 (categoria H — carga concentrada Q_k)
- **Arquivos:** `mlc_projeto/checks/elu/tercas.py`; verificação local inexistente

## Origem
Desdobramento da issue [2](02-qk-categoria-H.md). Ao adotar a sobrecarga de cobertura
categoria H (EN 1991-1-1 Tab. 6.10), além da UDL `q_k = 0,40 kN/m²` a norma prevê uma
**carga concentrada de manutenção** `Q_k = 1,0 kN` (recomendado; faixa 0,9–1,5 kN),
aplicada numa pequena área, para **verificações locais**.

## Estado atual
- O modelo global usa apenas a UDL (`Q_AREA = 0,40 kN/m²`). A carga concentrada `Q_k`
  **não** é verificada.
- `QK_CONC_KN = 1.0` já está declarado em `main.py` (constante, ainda não consumida).

## Por que importa
`Q_k` (ponto de manutenção) pode governar efeitos **locais**:
- **Terça**: momento de carga concentrada a meio-vão `M = Q_d·L_t/4` (não concomitante
  com a UDL máxima — EN 1991-1-1 §6.3.4.2: q_k e Q_k não atuam juntos).
- **Telha metálica**: flexão local do painel entre terças sob o ponto de manutenção
  (normalmente coberto pela ficha do fabricante — ver issue [17](17-ligacao-telha-terca-succao.md)).

## O que precisa ser feito
- [ ] Verificar a **terça** sob `Q_k = 1,0 kN` (1,5·Q_k a meio-vão), tomada como
      combinação alternativa à UDL (a mais desfavorável governa).
- [ ] Verificar/justificar a **telha** sob `Q_k` (cálculo ou dado do fabricante).
- [ ] Registrar no memorial.

## Critério de aceite
Terça (e telha) verificadas sob a carga concentrada Q_k = 1,0 kN (EN 1991-1-1
Tab. 6.10), como alternativa à UDL, com registro no memorial.
