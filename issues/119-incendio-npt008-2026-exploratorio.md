# 119 — Incêndio: NPT 008 (nova edição, nov/2026) e análise localizada como estudo exploratório

- **Tema:** Incêndio
- **Prioridade:** P1 — referência normativa possivelmente desatualizada na data da defesa
- **Origem:** Revisão técnica (comentários tipo banca), 2026-11-14, item 11

## A verificar
- Segundo o revisor, a NPT 008 de 2012 foi substituída por edição vigente desde 05/11/2026, com a definição de edificação aberta lateralmente no item 5.14 e o retardante (> 750 m²) no 5.19.3. **Conferir no site do CBMPR antes de alterar.**
- Incêndio localizado:
  - os 54 min (3 veículos) precisam de fonte;
  - a chama não atingir a cobertura não exclui radiação e convecção;
  - temperatura da pluma ≠ temperatura do elemento;
  - os tempos da madeira não demonstram a sobrevivência das ligações e do contraventamento;
  - "sem consequência estrutural" é forte demais.

## O que fazer
- [x] Obter a NPT 008 vigente; atualizar a referência, os itens citados e a análise de isenção (cap. 7 e cap. 1).
- [x] Reapresentar a §7.x como estudo exploratório de cenários: hipóteses, fontes (curva do automóvel, propagação), limitações e o caráter do incêndio-padrão como substituto, discutido e não presumido.
- [x] Incluir ligações e contraventamento na discussão (aço exposto: intumescente já especificado nos pilaretes; olhais, diagonais?).

## Resolução (2026-11-15) ✅ — com uma ressalva

**Conferência no CBMPR (15/11/2026):** o endereço da corporação disponibiliza a NPT 008 versão 02 (2012); a única versão posterior encontrada é o **texto de consulta pública da versão 03 (set/2025)**, em que estão os itens citados pelo revisor (5.14 edificação aberta lateralmente; 5.19.3 retardante > 750 m²). Não foi possível confirmar a publicação da versão final de 2026. Por isso a tese cita a versão 02 como a disponível e indica, para o texto de 2025, o que muda:
- 5.11 → 5.14, com o acréscimo de aberturas ≥ 5 % da área do piso (atendido);
- A2.3.10 b) e A2.4 c) mantidos (este remete ao 5.14) → a isenção se mantém pelas duas vias;
- novo A2.3.5 (garagens G-1/G-2 abertas, condicionado ao anexo D da NBR 14432);
- 5.17 → 5.19.3, mesma redação (retardante).
Nova referência `CBPMPR-NPT008:2025`. Cap. 1, 7 (§ TRRF), 8 (retardante) e 9 atualizados.

**Incêndio de veículo** (cap. 7, `ssec:incendio-veiculo`) reapresentado como **estudo exploratório**: hipóteses em alíneas, com fonte para a curva do automóvel e a propagação de 12 min (`Joyeux:2002`, EUR 20466 EN, programa europeu de ensaios em estacionamentos — conferido na lista de referências do relatório de Liège, *Robustness of car parks against localised fire*); 8,3 MW declarado como não sendo limite superior; incêndio-padrão como substituição não demonstrada; pluma a 390 °C não exclui radiação/convecção nem é a temperatura da peça; "sem consequência estrutural" retirado. Novo parágrafo sobre ligações e contraventamentos (combinação de incêndio com ψ₂ = 0 para o vento; chapas embutidas protegidas pela madeira; tampões de 15 mm; aço da cobertura no nível da pluma a 390 °C, temperatura efetiva não calculada) e fechamento com o que o estudo demonstra e o que fica em aberto. Cap. 9 registra o caráter exploratório.

**Atualização (2026-11-15):** o autor forneceu a versão oficial — NPT 008 versão 03, julho/2026, Anexo Único da Portaria do Comando-Geral nº 368/2026 (vigência 30 dias após o DOE). Conteúdo idêntico ao da consulta pública nos itens usados. A tese passa a citar só ela (`CBMPR-NPT008:2026`; sigla CBMPR):
- 5.14 aberta lateralmente (+5 % da área do piso), A2.3.10 b)/A2.3.10.1, A2.4 c), A2.3.5 (garagens abertas, não necessária), A2.2 (exclusões gerais, não aplicáveis);
- condição geral da isenção: itens 5.11 e A2.1 (antes "5.8");
- retardante: 5.19.3;
- **5.5.3** ampara o uso do Eurocódigo para madeira em incêndio (nota 3 da Tabela A) — citado no cap. 7;
- **5.5.1** temperatura crítica do aço ≤ 550 °C *ou calculada para cada elemento*: adotada a segunda opção (835 °C pela EN 1993-1-2; intumescente para 750 °C) — citado no cap. 7.
PDF da norma na raiz, acrescentado ao .gitignore.
