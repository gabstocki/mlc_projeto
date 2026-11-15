# 83 — Proteção dos topos de vigas e terças, vedação do rasgo, calha e rufos (detalhes e desenhos)

- **Tema:** Durabilidade — detalhes construtivos
- **Prioridade:** P1
- **Arquivos:** `tese/cap08.tex` §7.8, `output/desenhos.py` (nova folha de detalhes de proteção)
- **Relaciona:** 82, 91
- **Origem:** 4ª revisão, itens 4.3 e 6.7

## O que fazer
- [x] Topos das vigas nos beirais (onde ficam a L1, o rasgo e os pinos) e topos das terças nos
      frontões: capeamento ou rufo ventilado com pingadeira, sem contato direto com a madeira, e
      selagem do topo.
- [x] Vedação do rasgo contra entrada de água sem eliminar a ventilação prevista no §7.8.
- [x] Desenhar: capeamento dos topos de viga e terça, calha central com extravasor, rufos de beiral e de oitão.

## Resolução ✅

- **Topos (beiral e oitão, `ssec:topos-expostos`):**
  - Selante microporoso no topo.
  - Rufo de chapa galvanizada e pintada sobre sarrafos verticais, com folga ventilada de 20 mm aberta em cima e embaixo.
  - Pingadeira 30 mm abaixo da madeira.
  - No beiral, a telha avança 70 mm além do rufo.
  - O capeamento em contato direto com a madeira foi rejeitado no texto.
- **Rasgo da L1 (`ssec:vedacao-rasgo`):**
  - O rasgo antes era uma cavidade fechada pela chapa de topo.
  - Agora é prolongado `E_RASGO_VENTILACAO_MM = 30` além das duas faces do pilar e abre-se para baixo, o que ventila e drena.
  - Vedação nos pontos de entrada: cordão elástico na junta viga–chapa de topo e tampões removíveis nas cabeças dos pinos.
  - A L1c ventila pelo vão entre as vigas, sob a T9 e a calha.
- **Correção encontrada:** o balanço da viga usava a seção bruta na raiz, onde está o rasgo.
  - `modulo_secao_com_rasgo` dá W 0,0493 de 0,0533 m³ e b − t_r no cisalhamento.
  - η continua 0,11 e o balanço é recalculado após `geometria_rasgo`.
- **Calha central (`checks/calha.py`, `ssec:calha-central`):**
  - Seção 300×150 em suportes nas faces da T9, 50 mm acima da capa da terça (que tem pingadeiras).
  - Telhas do último pano sobre perfis de borda, a 9,2 % (mínimo 5 %).
  - Uma saída por pórtico, 0,40 m fora do eixo. Pontos altos e juntas de dilatação a meio vão.
  - Extravasores: extremidades abertas nos oitões e ladrão junto a cada saída.
- **Dimensionamento hidráulico:**
  - NBR 10844 com I = 228 mm/h (Curitiba, T = 25 anos; TODO confirmar): A = 127 m² e Q = 481 L/min por saída.
  - Calha por Manning: η 0,20.
  - Condutor Ø100 por Wyly-Eaton (EN 12056-3, f ≤ 0,33): η 0,75.
- **Terça T9 com a calha cheia** (0,45 kN/m variável + 0,10 permanente): η 0,48 (antes 0,44). Nova verificação `terca_calha`; `calha` entra no catálogo.
- **DES-10** (nova folha): ponta do beiral, oitão e calha central. O DES-05 mostra o rasgo prolongado com setas.
- **Bib:** NBR 10844:1989 e EN 12056-3:2000.
- **Testes:** `test_issue83_protecao.py`; contagem de folhas 9 → 10. 814 passed. Tese 145 p., 0 overfull.
- **Pendente (91):** detalhe da saída, do condutor e do ladrão em elevação longitudinal.
