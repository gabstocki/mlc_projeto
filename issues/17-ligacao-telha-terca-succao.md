# 17 — Ligação telha-terça sob sucção (ou dado do fabricante)

- **Tema:** Terças / ligações secundárias
- **Prioridade:** P2
- **Normas:** NBR 6123 (sucção); ficha técnica do fabricante da telha
- **Arquivos:** ligação não verificada no código; ver `mlc_projeto/core/wind.py` (sucção)

## Apontamento do orientador
> Ligação telha-terça sob sucção: se não verificar, colocar dado do fabricante da
> telha no memorial que justifique os elementos usados na ligação.

## Estado atual no código
- As pressões de sucção existem (Tab.25 C2, padrões `*_unif_st`, etc. em
  [wind.py:120-190](../mlc_projeto/core/wind.py)), mas **não há verificação** da
  fixação telha→terça (parafusos/ganchos) contra arranchamento por sucção.

## O que precisa ser feito
- [x] Calcular a sucção de projeto na fixação (área tributária do parafuso × w_suc,d).
- [x] Verificar a fixação telha-terça (resistência ao arranchamento) com resistência
      TÍPICA de fixador, marcada para confirmar na ficha do fabricante.

## Critério de aceite
Fixação telha-terça verificada sob sucção ou justificada por dado do fabricante no
memorial.

---

## ✅ Resolução (implementada)

**Módulo novo:** [`checks/elu/fixacao_telha.py`](../mlc_projeto/checks/elu/fixacao_telha.py)
— `verificar_fixacao_telha_succao(...)`, verificação LOCAL do fixador ao
arrancamento por sucção (NBR 6123). Escopo escolhido: **calcular + fixador típico**.

### Metodologia (NBR 6123)
    C_net   = C_pe,local − C_pi                 (uplift, < 0)
    w_suc,d = γ_Q·|C_net|·q                      (kN/m²)
    w_up,d  = w_suc,d − γ_G,fav·g_telha          (peso da telha alivia)
    F_fix,d = w_up,d·(s_terça · e_fix)           (kN por fixador)
    η       = F_fix,d / R_fix,d,  R_fix,d = R_fix,k/γ_M

- **C_pe local por zona** (NBR 6123 Tab. 5, telhado baixa inclinação):
  campo −1,0 · borda −1,5 · **canto −2,0**.
- **C_pi = +0,8** (§6.2.5): o galpão é **aberto nas laterais** → interior
  pressurizado (abertura dominante), soma ao uplift. Cenário conservador.
- γ_Q=1,5 (EN 1990, coerência com o modelo); γ_G,fav=0,9; γ_M=1,3 (aço-madeira/ETA).

### Resultado (q=0,855 kN/m², s=2,53 m, R_fix,k=2,5 kN típico)
- Fixação uniforme a 0,33 m: campo OK (η=0,96) mas **borda/canto reprovam**
  (η=1,24 e 1,52) — resultado físico esperado (sucções locais de borda).
- **Solução adotada: e_fix = 0,20 m (a cada nervura)** → todas as zonas OK,
  **η_gov = 0,921 (canto)**.
- Espaçamento máx. de fixador p/ η≤1: campo 0,34 m · borda 0,27 m · canto 0,22 m
  (o memorial pode relaxar o campo para ~1 fixador a cada 2 nervuras).

### Integração
- `main.py`: constantes `E_FIX_TELHA_M=0,20`, `R_FIX_K_KN=2,5`;
  `res_elu["fixacao_telha"]`, impresso na Fase 2 e no resumo.
- `output/report.py`: linha nova no catálogo (resumo/Excel/§12).
- **Testes:** [`tests/test_fixacao_telha_succao.py`](../tests/test_fixacao_telha_succao.py)
  (8 casos: fórmula, canto governa, C_pi soma, escala com e_fix, e_fix requerido,
  peso da telha alivia, entradas inválidas).

### CAVEAT (dado do fabricante)
`R_fix,k = 2,5 kN` é TÍPICO de catálogo (parafuso autoperfurante Ø6,3 mm +
arruela EPDM; governa o *pull-over* na chapa fina, não o *pull-out* na madeira).
**Confirmar na ficha técnica da telha adotada** e substituir — a metodologia e
os espaçamentos exigidos por zona permanecem válidos com o R_fix,k real.
