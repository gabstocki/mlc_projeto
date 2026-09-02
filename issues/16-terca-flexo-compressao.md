# 16 — Terça: interação flexão + compressão combinada (Eq. 6.23/6.24)

- **Tema:** Terças
- **Prioridade:** P1
- **Normas:** EC5 §6.3.2, Eq. 6.23 / 6.24
- **Arquivos:** `mlc_projeto/checks/elu/tercas.py:155-160`; `mlc_projeto/checks/elu/contraventamento.py` (terça-biela); `mlc_projeto/main.py:525-547`

## Apontamento do orientador
> Na terça, corrigir a interação flexão e compressão, que deve ser verificada de
> forma combinada (fez separada: 0,299 e 0,075) — EC5 §6.3.2, Eq. 6.23/6.24.

## Estado atual no código
- A verificação de flexão da terça é **biaxial** (Eq. 6.12), sem termo de compressão:
  [tercas.py:155-160](../mlc_projeto/checks/elu/tercas.py).
- Quando a terça atua como **terça-biela** (elemento de contraventamento), ela recebe
  **compressão axial** de estabilização (§9.2.5) além da flexão da cobertura. Hoje a
  compressão (η≈0,075) e a flexão (η≈0,299) são reportadas **separadamente**
  (ver `res_elu["contraventamento"]["terca"]` e `res_elu["terca"]` em
  [main.py:529-547](../mlc_projeto/main.py)).

## O que precisa ser feito
- [x] Combinar flexão + compressão axial na terça-biela conforme EC5 §6.3.2:
      `σ_c,0,d/(k_c·f_c,0,d) + σ_m,y,d/f_m,d + k_m·σ_m,z,d/f_m,d ≤ 1` (Eq. 6.23) e a
      permutação (Eq. 6.24).
- [x] Usar a **mesma combinação de ações** para os dois efeitos (concomitância real).
- [x] Reportar um único η combinado no relatório em vez de dois valores isolados.

## Critério de aceite
Terça-biela verificada com interação combinada (Eq. 6.23/6.24), η único reportado.

---

## ✅ Resolução (implementada)

**Função nova:** `verifica_terca_flexocompressao(...)` em
[`checks/elu/tercas.py`](../mlc_projeto/checks/elu/tercas.py) — interação
combinada EC5 §6.3.2 Eq. 6.23/6.24.

### Forma normativa (confirmada no texto EN 1995-1-1:2004 §6.3.2)
- **§6.3.2(2):** para peças curtas (λ_rel,y **e** λ_rel,z ≤ 0,3) → usa Eq. 6.19/6.20
  de §6.2.4, com termo de compressão **ao quadrado** `(σ_c/(k_c·f_c0d))²`.
- **§6.3.2(3)** "in all other cases" → Eq. 6.23/6.24, com termo de compressão
  **LINEAR** `σ_c/(k_c·f_c0d)`.
- A terça-biela é **esbelta** (λ_z ≈ 100 » 0,3) → cai em §6.3.2(3) → forma linear.

      (6.23): σ_c,0,d/(k_c,y·f_c,0,d) + σ_m,y,d/f_m,d + k_m·σ_m,z,d/f_m,d ≤ 1
      (6.24): σ_c,0,d/(k_c,z·f_c,0,d) + k_m·σ_m,y,d/f_m,d + σ_m,z,d/f_m,d ≤ 1

### Concomitância (mesma combinação)
A flexão é obtida **reutilizando `verifica_terca`** (idênticos σ_m,y,d, σ_m,z,d,
f_m,d), que usa ELU_C2 = 1,35G + 1,5W + 1,05Q — a **mesma** combinação de onde
sai a força de estabilização §9.2.5 (`forca_compressao_estabilizar`). Concomitância
garantida por construção, não por hipótese.

### Eixos e flambagem
- y = eixo forte (i_y = h/√12), flexão da carga ⊥ à cobertura; k_c,y ≈ 0,967 (λ_y≈34).
- z = eixo fraco (i_z = b/√12), flambagem no plano da cobertura; k_c,z ≈ 0,368 (λ_z≈100).
- l_ef = L_t = 5,75 m nos dois eixos (não se reivindica a restrição do telhado
  fora do plano → conservador).

### Resultado (terça 0,20×0,58 m, N_c = 47,4 kN, ELU_C2)
- σ_c = 0,408 MPa | σ_m,y = 2,105 MPa | σ_m,z = 0,246 MPa | f_md = 13,44 MPa
- η_6.23 = 0,201 | **η_6.24 = 0,210 (governa — flambagem fraca)**
- **η combinado ÚNICO = 0,2105** substitui os dois isolados (flexão + compressão).

### Integração
- `main.py`: `res_elu["terca_flexocomp"]`, impresso como "Terça-biela flexo-comp. §6.3.2".
- `output/report.py`: linha nova no catálogo de exportação (resumo/Excel) e §9.3 do
  memorial reescrita para a interação combinada.
- **Testes:** [`tests/test_terca_flexocompressao.py`](../tests/test_terca_flexocompressao.py)
  (7 casos: fórmula linear vs. quadrática, concomitância, η único, Eq.6.24 governa).

### Nota / follow-up
A viga principal ([`checks/elu/flexao.py`](../mlc_projeto/checks/elu/flexao.py))
escreve as Eq. 6.23/6.24 com o termo de compressão **ao quadrado** — que é a
forma de §6.2.4, não de §6.3.2. Para a viga esbelta o correto seria a forma
**linear** (mais conservadora). Fica registado como possível refinamento
separado (não é o escopo desta issue, que trata da terça).
