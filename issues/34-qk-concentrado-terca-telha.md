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
- [x] Verificar a **terça** sob `Q_k = 1,0 kN` (γ_Q·Q_k a meio-vão), combinação
      alternativa à UDL (a mais desfavorável governa).
- [x] **Telha** sob `Q_k`: demanda local calculada, a confrontar com a ficha (issue 17).
- [x] Registrar no memorial.

## Critério de aceite
Terça (e telha) verificadas sob a carga concentrada Q_k = 1,0 kN (EN 1991-1-1
Tab. 6.10), como alternativa à UDL, com registro no memorial.

---

## ✅ Resolução (implementada)

**Função nova:** `verifica_terca_carga_concentrada(...)` em
[`checks/elu/tercas.py`](../mlc_projeto/checks/elu/tercas.py).

### Combinação (EN 1991-1-1 Tab. 6.10 / §6.3.4.2)
Q_k=1,0 kN a meio-vão da terça biapoiada, **não concomitante** com a UDL q_k nem
com o vento (cat. H). Duração **média** (imposta, k_mod=0,65):

    M_d = γ_G·g_lin·L_t²/8 + γ_Q·Q_k·L_t/4
    V_d = γ_G·g_lin·L_t/2  + γ_Q·Q_k/2

### Resultado (terça 0,20×0,58, L_t=5,75 m)
- M_d=7,65 kN·m (M_g=5,49 + M_Q=2,16); **η_flex=0,055 · η_cis=0,048 → η=0,055**.
- **A UDL governa** (η_flex=0,170 > 0,055) → o Q_k concentrado não é crítico para a
  terça, como esperado. A verificação demonstra e documenta isso.

### Telha
Demanda local no painel entre terças: M_local,d = γ_Q·Q_k·s/4 = **0,949 kN·m/m**,
a confrontar com a capacidade a carga concentrada da **ficha do fabricante** (dado
proprietário — ligado à issue 17; fixação a cada nervura já adotada).

### Integração
- `main.py` Fase 2: `res_elu["terca_Qk_conc"]` (consome `QK_CONC_KN=1.0` já declarado).
- `output/report.py`: linha no catálogo (resumo/§12) + nota do §4 atualizada com o
  resultado (antes só remetia à issue 34).
- **Testes:** [`tests/test_terca_qk_concentrado.py`](../tests/test_terca_qk_concentrado.py)
  (7 casos: M_g+M_Q, duração média, tensão, UDL governa, escala com Q_k, telha, aprova).
