# 21 — Chapas de aço, furos e soldas (EN 1993-1-8)

- **Tema:** Ligações (componente metálico)
- **Prioridade:** P1
- **Normas:** EN 1993-1-8 (chapas, furos, soldas); EN 1993-1-1 (seção bruta/líquida)
- **Arquivos:** `mlc_projeto/connections/connections.py:92-156`, `:549-663`

## Apontamento do orientador
> Verificações ausentes para ligações: verificações das chapas de aço, furos e soldas
> da ligação conforme EN 1993-1-8.

## Estado atual no código
- O lado da madeira é dimensionado (Johansen, n_ef, distâncias); o lado do **aço** só
  aparece como `F_U_K_PINO` (pino) e como área de chapa de base por compressão no
  concreto ([connections.py:592-602](../mlc_projeto/connections/connections.py)).
- **Não há** verificação de: resistência da chapa embutida (tração/flexão da chapa),
  **pressão de contato/rasgamento nos furos** (bearing), **seção líquida**, nem
  **soldas** chapa↔chapa base.

## O que precisa ser feito
- [ ] Verificar a **chapa embutida** de L1/L2/L3 (espessura, tração/flexão, seção
      líquida nos furos) — EN 1993-1-8 / EN 1993-1-1.
- [ ] Verificar **bearing/pressão de contato** e rasgamento nos furos da chapa.
- [ ] Verificar as **soldas** (chapa embutida ↔ chapa de base; chumbadores).
- [ ] Definir aço da chapa (ex.: S275/S355) e furação, e publicar no memorial.

## Critério de aceite
Componentes metálicos das ligações verificados por EN 1993-1-8 (chapa, furos, soldas),
com resultados no memorial.
