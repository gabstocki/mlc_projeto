# Benchmarks e testes adversariais — auditoria v2

Scripts de EVIDÊNCIA do relatório `../AUDITORIA_ADVERSARIAL_V2.md`.

Regra: o cálculo de **referência** é reconstruído da formulação normativa/matemática e
**não importa nenhuma função do repositório auditado**. O pacote `mlc_projeto` é
importado apenas para **ler** o valor a comparar.

| Script | Cobre |
|---|---|
| `bm_independente.py` | BM-01 vento · BM-02 g_k · BM-03 EN 1990 + análise · BM-04 §6.1.7 · BM-05 §6.4.2 · BM-06 §6.4.3 · BM-07 §6.3.3 · BM-09 §6.1.5 · BM-11 atrito θ=0° · BM-12 componente horizontal da cobertura |
| `bm_els.py` | BM-08 flecha flexão+cisalhamento (Timoshenko, I(x), A(x)) com sanidade de seção constante |
| `bm2.py` | BM-10 Johansen L1 (Eq. 8.11 vs 8.13(k), f_h,α,k, Tab. 8.5 a4,t) · BM-13 α_cr de sistema |
| `bm_envelope.py` | BM-14 envelope sobre as 17 combinações ELU (rota Tab. 10, configuração atual) |
| `bm_envelope_t25.py` | BM-14 na rota Tab. 25 — demonstra a alcançabilidade de [F-06] |
| `adv.py` | ADV-A a ADV-F: domínio, sinais, NaN/inf, agregação do veredito, monotonicidade, continuidade, inversão de eixos |

Execução:

```bash
.venv/bin/python auditoria_v2/bm_independente.py
.venv/bin/python auditoria_v2/bm_els.py
.venv/bin/python auditoria_v2/bm2.py
.venv/bin/python auditoria_v2/bm_envelope.py
.venv/bin/python auditoria_v2/bm_envelope_t25.py
.venv/bin/python auditoria_v2/adv.py
```
