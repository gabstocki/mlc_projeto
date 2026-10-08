# 39 — Vento: a estrutura É cobertura isolada; aplicar o último parágrafo do §7.2.1 (NBR 6123:2023)

- **Tema:** Ações — vento / Fundamentação normativa
- **Prioridade:** P1 (procedimento correto, justificativa errada no memorial)
- **Normas:** ABNT NBR 6123:2023 §7.2, §7.2.1 (último parágrafo), §7.2.2, §7.2.6, Tabela 25; tabela de C_pe de edificação fechada (Tab. 10?)
- **Arquivos:** `tese/cap04.tex:248-262` (§4.4.2 Rota normativa para a ação do vento — “o enquadramento como cobertura isolada foi descartado”, l. 257); `tese/cap06.tex:126-171` (§6.2.3 Ação do vento); `mlc_projeto/core/wind.py`; `mlc_projeto/core/normativo.py:498` (`tabela_10_alpha_90` POR RESOLVER); `ANEXO_A_NBR6123.md`; `output/pipeline_console.txt:30`
- **Relaciona:** memória [[tab25-fora-do-dominio]]; issues 17, 28

## Origem (3ª revisão do orientador (2026-10))
A estrutura é **cobertura isolada** (§7.2: cobertura sobre suportes de reduzidas dimensões,
aberta nas quatro faces). A Tabela 25 só vale com `0,07 ≤ tg θ ≤ 0,6` **e** `h ≥ 0,5·ℓ₂`.
Aqui `h ≈ 7,0–8,6 m < 0,5 × 20,25 = 10,1 m` → fora do domínio, e extrapolar não é permitido.
Para esse caso — e também quando há obstruções sob a cobertura (veículos) — o **último
parágrafo do §7.2.1** manda calcular como **edificação fechada de mesma cobertura**, com
`c_pi = +0,8` (obstrução a sotavento) e `c_pi = −0,3` (obstrução a barlavento).

> “O procedimento está correto, mas a justificativa está errada.”

## O que fazer
- [ ] Reescrever **§4.4.2** e **§6.2.3**: a estrutura **é** cobertura isolada; aplica-se o
      último parágrafo do §7.2.1 (geometria fora da Tab. 25 **e** obstrução por veículos).
      Retirar “o enquadramento como cobertura isolada foi descartado”.
- [ ] Informar o **valor exato de h adotado** (e de onde vem: beiral? cumeeira? média?).
- [ ] Informar a **tabela de C_pe de edificação** efetivamente usada (número, entrada α/θ,
      valores) e **resolver a pendência `tabela_10_alpha_90`** que a saída do pipeline ainda
      marca como POR RESOLVER (`normativo.py:498`; confirmar contra o PDF `NBR6123-2023.pdf`).
- [ ] Declarar a interpretação de **“zona de obstrução”** = cobertura inteira (estacionamento).
- [ ] Explicitar que o uso de **§7.2.2 (atrito)** e **§7.2.6 (bordas)** fica coerente por
      pertencerem à mesma seção §7.2.
- [ ] Atualizar docstrings/notas de `wind.py` e o `ANEXO_A_NBR6123.md` com o mesmo enquadramento.

## Critério de aceite
Texto da tese e do relatório descrevem o mesmo enquadramento; pipeline sem a pendência
`tabela_10_alpha_90`; h, tabela de C_pe e zona de obstrução declarados.

## Resolução ✅ (2026-10-06)

**Enquadramento (texto reescrito na tese §4.4.2 e §6.2.3):** a estrutura **é** cobertura isolada
(NBR 6123:2023 §7.2); a Tab. 25 não se aplica porque **h = 7,00 m** (pé-direito ao beiral) <
0,5·ℓ2 (20,25 m para a cobertura de 40,5 m; ≥ 10,1 m por água dupla), com tg θ = 0,176 dentro do
intervalo; e há obstrução (veículos) → **último parágrafo do §7.2.1**: edificação fechada de
mesma cobertura, c_pi = +0,8 (sotavento) / −0,3 (barlavento). **Zona de obstrução = cobertura
inteira.** C_pe da **Tab. 10** (telhados múltiplos simétricos de tramos iguais; h ≤ a' = 20,25 m).
Uso coerente de §7.2.2 (atrito) e §7.2.6 (vedação), da mesma seção §7.2.

**Pendência `tabela_10_alpha_90` resolvida:** lida no PDF (pág. 24 da norma; figura da Tab. 10):
α = 90° (vento // cumeeiras), θ ≤ 45°: **b1 = −0,8, b2 = −0,6, b3 = −0,2**, com b1 = b2 = h a
partir do frontão de barlavento; c_pe médio de borda −1,5/−2,0 (y = mín(h; 0,1b) = 4,6 m).
- `core/wind.py`: `TABELA_10_ALPHA90`, `TABELA_10_CPE_MEDIO`; `padroes_cpe_edificacao_fechada`
  gera +6 padrões (3 faixas × 2 c_pi) → **14 padrões, 29 combinações ELU**.
- `core/normativo.py`: item **CONFIRMADO** (12/15; restam V0, S3, Ca do pilar).
  `ANEXO_A_NBR6123.md` regenerado.
- **Impacto:** nenhuma verificação muda — os padrões assimétricos de α = 0° continuam a governar
  (b1 com c_pi +0,8 = −1,6 uniforme < sucção governante). **Mas** b3 com c_pi −0,3 dá C_net = +0,1
  (pressão leve) → a demonstração da issue 45 foi refeita: Q+0,6W dá M = 526,4 kN·m (+4,4 %), porém
  com k_mod de curta (0,70) contra 0,65 da média: utilização relativa 0,97 < 1 — a dispensa
  continua a favor da segurança (`combinacao_Q_com_vento_acompanhante(mat=...)`).

**Decisões registradas (para o orientador):**
- Atrito com α = 90°: a nota da Tab. 10 remete ao §6.1.5 (edificação fechada); mantido o §7.2.2
  (cobertura isolada, envolvente, 776,8 kN), coerente com o enquadramento e mais severo.
- Vedação: mantido §7.2.6 (c_p = ±2,0). Sensibilidade: com c_pe médio −2,0 da Tab. 10 e c_pi +0,8
  (C_net = −2,8), a fixação da telha iria de η 0,68 para ≈ 0,95 — ainda atende.

**Testes:** atualizados para 14 padrões / 29 combinações; item F-18 fechado; issue 45 refeita.
Suíte 694 passed; pipeline APROVADO.
