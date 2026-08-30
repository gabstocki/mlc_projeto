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
- [ ] Calcular a sucção de projeto na fixação (área tributária do parafuso × w_suc,d).
- [ ] Verificar a fixação telha-terça (resistência ao arranchamento) **ou** citar o
      dado do fabricante da telha (nº de fixadores/m², resistência) que justifique a
      solução, registrando no memorial.

## Critério de aceite
Fixação telha-terça verificada sob sucção ou justificada por dado do fabricante no
memorial.
