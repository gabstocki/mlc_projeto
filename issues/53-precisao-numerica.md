# 53 — Precisão numérica: η com duas casas, forças com três algarismos significativos

- **Tema:** Apresentação
- **Prioridade:** P2
- **Arquivos:** `mlc_projeto/output/report.py` (formatação `_br`); `mlc_projeto/main.py` (console); `tese/*.tex` (ex.: `cap07.tex:47` “0,2660”, forças como 277,48 kN)
- **Relaciona:** issue 50

## Origem (3ª revisão do orientador (2026-10))
Dados como q_k = 0,40 kN/m² ou γ_G = 1,35 têm 2–3 algarismos significativos; calcular não
aumenta a precisão. Taxas com 4 casas (0,3814) e forças como 277,48 kN transmitem precisão que
o cálculo não tem. **Usar duas casas para taxas e três algarismos significativos para forças.**

## O que fazer
- [ ] Criar formatador único (η → 2 casas; forças/momentos → 3 alg. sig.) e aplicá-lo em report/console/Excel.
- [ ] Revisar todas as tabelas e o texto da tese.
- [ ] Atenção a η arredondado = 1,00 com valor real > 1 → decidir arredondar para cima ou mostrar “> 1,00”.
