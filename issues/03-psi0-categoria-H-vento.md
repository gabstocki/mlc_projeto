# 03 — ψ₀ categoria H = 0: sobrecarga de cobertura não combina com vento

- **Tema:** Ações e combinações
- **Prioridade:** P1
- **Normas:** EN 1990 Tab. A1.1; EN 1991-1-1 §3.3.2(1)
- **Arquivos:** `mlc_projeto/core/loads.py:55`, `:472-473`, `:490-495`

## Apontamento do orientador
> Outro fator na combinação que precisa ser verificado: 1,05Q combinado com vento.
> O EN 1990 (Tab. A1.1; EN 1991-1-1 §3.3.2(1)) prevê que, para cobertura não
> acessível (categoria H), ψ₀ = 0, e a sobrecarga de cobertura não se combina com
> vento.

## Estado atual no código
- `PSI_0_Q = 0.70` em [loads.py:55](../mlc_projeto/core/loads.py).
- Combinação com **vento dominante** aplica `ψ₀·1,5·Q = 1,05Q` como acompanhante:
  [loads.py:472-473](../mlc_projeto/core/loads.py)
  (`1,35G + 1,5W + 1,05Q`).
- Combinação com **Q dominante** aplica `ψ₀,W·1,5·W = 0,9W`:
  [loads.py:490-495](../mlc_projeto/core/loads.py).

## O que precisa ser feito
- [ ] Para categoria H, adotar **ψ₀,Q = 0**: remover a parcela `1,05Q` das
      combinações com vento dominante (ELU_W_*).
- [ ] Confirmar que a sobrecarga de cobertura e o vento **não atuam simultaneamente**
      (são ações variáveis não concomitantes para categoria H).
- [ ] Manter as duas famílias separadas: (a) Q dominante sem vento; (b) vento
      dominante sem Q. Reavaliar qual governa.
- [ ] Distinguir ψ₀ da sobrecarga (Q) do ψ₀ do vento (W) — não confundir os dois.

## Critério de aceite
Combinações revisadas sem concomitância Q+W para categoria H; ψ₀,Q = 0 documentado.
