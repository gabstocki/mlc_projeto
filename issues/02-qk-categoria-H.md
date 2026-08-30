# 02 — Sobrecarga qk categoria H (0,25 → 0,4 kN/m²)

- **Tema:** Ações e combinações
- **Prioridade:** P1
- **Normas:** EN 1991-1-1 §6.3.4 / Tab. 6.10 (categoria H — coberturas não acessíveis)
- **Arquivos:** `mlc_projeto/main.py:110`, `mlc_projeto/core/loads.py:322`

## Apontamento do orientador
> Conferir o valor de qk = 0,25 kN/m. Acho que no EN 1990 [EN 1991-1-1] deveria ser,
> para categoria H, 0,4 kN/m².

## Estado atual no código
- `Q_AREA = 0.25` kN/m² em [main.py:110](../mlc_projeto/main.py) (default
  `Carregamentos.q_area = 0.25`, [loads.py:322](../mlc_projeto/core/loads.py)).

## O que precisa ser feito
- [ ] Confirmar a categoria da cobertura (H — não acessível exceto manutenção) e o
      valor de qk conforme EN 1991-1-1 Tab. 6.10 / Anexo Nacional aplicável.
- [ ] Ajustar `Q_AREA` para 0,4 kN/m² (ou o valor do Anexo Nacional adotado) e
      registrar a fonte no memorial.
- [ ] Verificar interação com a issue [03](03-psi0-categoria-H-vento.md): para
      categoria H, qk **não** combina com vento (ψ₀ = 0), então o aumento de qk
      afeta sobretudo a combinação com Q dominante.

## Critério de aceite
qk = 0,4 kN/m² (ou valor justificado do Anexo Nacional), com fonte citada.
