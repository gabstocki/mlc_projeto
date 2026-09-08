"""
Gera ANEXO_A_NBR6123.md — a folha de conferência do achado F-18.

O anexo NÃO reproduz a norma (a auditoria não tem o texto). Enumera cada valor
de origem NBR usado no projeto, onde está, o que o código alega e a pergunta
concreta a fazer com a norma em papel à frente. Fecha-se marcando o estado no
catálogo (`core/normativo.py`), nunca editando este ficheiro à mão.

Uso:  python auditoria_v2/gerar_anexo_nbr.py
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from mlc_projeto.core.normativo import (  # noqa: E402
    CATALOGO_NBR6123, NORMA_VENTO, itens_nbr_nao_confirmados,
)

DESTINO = pathlib.Path(__file__).resolve().parents[1] / "ANEXO_A_NBR6123.md"

CABECALHO = f"""# ANEXO A — Proveniência dos valores da {NORMA_VENTO}

> **Folha de conferência do achado [F-18].** Gerada por
> `auditoria_v2/gerar_anexo_nbr.py` a partir de `CATALOGO_NBR6123`
> (`mlc_projeto/core/normativo.py`). **Não editar à mão** — corrigir o
> catálogo e regenerar.

## O que este anexo é, e o que não é

**Não reproduz a NBR 6123:2023.** A norma é obra protegida por direito autoral
e o repositório tem remoto público; `NBR6123-2023.pdf` está deliberadamente
fora do git (ver `.gitignore`). O controle documental exige uma cópia
controlada disponível ao projetista, não a sua redistribuição — e um memorial
cita cláusulas, não reimprime a norma.

É o registo de **todos** os números do projeto que dependem da NBR 6123, com o
local exato no código, a cláusula, o estado de verificação e a evidência.

## Como foi verificado

`auditoria_v2/bm_nbr_texto.py` (BM-17) **lê o PDF** com `pdftotext`, extrai as
tabelas e confronta valor a valor com o que o repositório implementa. Extrai,
compara, descarta: nada da norma fica no repositório. Sem o PDF, aborta com
instrução — nunca degrada em silêncio para uma verificação mais fraca.

| Verificação | Resultado |
|---|---|
| Tabela 1 — parâmetros meteorológicos | **45/45** valores |
| Tabela 2 — fator de rajada | **3/3** valores |
| **Tabela 3 — S2 tabelado contra a fórmula de §5.3.3** | **279 células**, pior Δ = 0,0050 |
| Tabela 10 — telhados múltiplos | **40/40** valores |
| Tabela 25 — cobertura isolada duas águas | **8 expressões**, 216 amostras |
| §4.2 c), §5.2 a), §7.2.1, §7.2.2, §7.2.6, nota da Tab. 10 | à letra |

A **Tabela 3** é a verificação forte. A norma dá o S2 tabelado *e* a fórmula
que o gera; confrontar uma com a outra testa `b`, `p`, `z_g`, `F_r` e a regra
especial da Categoria V de uma só vez, contra dados externos ao repositório. O
pior desvio em 279 células é 0,0050 — exatamente o arredondamento a duas casas.

## Porque isto importa em obra

O vento governa **toda** a estrutura metálica de contraventamento e a
verificação da telha. Um erro numa destas tabelas não produz um aviso: produz
um dimensionamento errado que passa em todos os testes.

## Estado

| | |
|---|---|
| Itens catalogados | {len(CATALOGO_NBR6123)} |
| Confirmados contra o texto | **{len(CATALOGO_NBR6123) - len(itens_nbr_nao_confirmados())}** |
| **Por resolver** | **{len(itens_nbr_nao_confirmados())}** |

Dois estados apenas, deliberadamente: `CONFIRMADO` significa que o texto
literal foi lido e confrontado. Tudo o resto é `NAO_CONFIRMADO`.

**Nenhum dos que sobram é uma tabela.** São um valor que depende de um dado que
o projeto não declara, duas decisões que só o projetista toma, e uma lacuna.

---

## A. Itens por resolver

"""

RODAPE = """
---

## C. O que mudou, e porquê importa

A primeira versão deste anexo declarava
`NOT VERIFIABLE — REQUIRES EXTERNAL NORMATIVE SOURCE` para as onze tabelas e
cláusulas, e construiu o BM-15 — sete invariantes de coerência interna — como o
melhor que se podia fazer sem a norma.

**A norma estava na raiz do projeto o tempo todo.** A auditoria nunca listou a
árvore à procura dela: inventariou os `.py` e ignorou o resto. É falha de
cobertura da própria auditoria, e o episódio do [F-13] — em que se argumentou
que `Ft = 0,5·q·a·b` era fisicamente impossível, com retratação depois — teria
sido evitado abrindo o ficheiro.

O BM-15 continua a correr, agora no papel certo: guarda de regressão barata
que não precisa do PDF. Quem clonar o repositório sem a cópia licenciada tem
as sete invariantes; quem a tiver corre o BM-17 e verifica contra o texto.

## D. Achados abertos pela leitura da norma

Verificar contra a fonte confirmou onze itens **e destapou dois defeitos** que
nenhuma verificação de coerência interna podia apanhar:

**[F-20] `C_a = 1,2` sob citação inexistente.** Estava citado como
«§6.3 / Tab. 13». Na :2023, §6.3 é *Pressões internas em edificações* e a
Tab. 13 é *edificações cilíndricas de seção circular*. A rota correta é §8.1.1
(Tab. 26, `Cx`/`Cy`) com o fator `K` de comprimento finito (Tab. 28). O valor
cai dentro do intervalo plausível mas não foi obtido por essa rota. Peso:
7,2 % da ação de vento θ = 0°.

**[F-21] `S3 = 1,00` rotulado «grupo 2».** A Tab. 4 dá grupo 2 → 1,06
(Tp 75 anos) e grupo 3 → 1,00 (Tp 50 anos). O valor usado é o do grupo 3; o
rótulo diz grupo 2. Se a classificação correta for o grupo 2, **toda** a ação
de vento sobe 1,06² = **+12,4 %** — defeito não conservativo. Só o projetista
classifica a edificação.

Nenhum dos dois foi corrigido: ambos exigem dados que o projeto não tem
(a secção do pilar para a Tab. 28; a classificação da edificação). Estão
declarados no código, no catálogo e nas saídas.

## E. Como fechar o que resta

1. **`v0_isopleta`** — declarar a localidade da obra e ler a isopleta na
   Figura 1.
2. **`s3_estatistico`** — classificar a edificação na Tab. 4 e acertar valor e
   rótulo entre si.
3. **`ca_pilar`** — refazer `C_a` por §8.1.1 com a secção real do pilar.
4. **`tabela_10_alpha_90`** — decidir se a rota de edificação fechada exige as
   colunas b1/b2/b3 para vento paralelo às cumeeiras.

Para cada um: `estado="CONFIRMADO"` no catálogo com a evidência escrita, ou
abrir achado se divergir. Depois regenerar este anexo e correr
`pytest tests/test_f18_proveniencia_nbr.py`.
"""


def bloco_item(item, n: int) -> str:
    linhas = [
        f"### A.{n} — {item.designacao}",
        "",
        f"| | |",
        f"|---|---|",
        f"| Cláusula alegada | `{item.clausula}` |",
        f"| Local no código | `{item.local}` |",
        f"| Símbolos | {', '.join(f'`{s}`' for s in item.simbolos)} |",
        f"| Chave no catálogo | `{item.chave}` |",
        "",
    ]
    if item.evidencia:
        linhas += [f"**Verificação independente:** {item.evidencia}", ""]
    linhas += [f"**A confirmar:** {item.questao}", ""]
    return "\n".join(linhas)


def main() -> int:
    partes = [CABECALHO, ""]
    for n, item in enumerate(itens_nbr_nao_confirmados(), start=1):
        partes.append(bloco_item(item, n))

    partes.append("---\n\n## B. Itens confirmados contra o texto\n")
    for item in CATALOGO_NBR6123:
        if item.estado != "CONFIRMADO":
            continue
        partes.append(f"### {item.designacao}\n")
        partes.append(f"| | |\n|---|---|\n"
                      f"| Cláusula | `{item.clausula}` |\n"
                      f"| Local | `{item.local}` |\n")
        partes.append(f"\n{item.evidencia}\n")

    partes.append(RODAPE)
    texto = "\n".join(partes)

    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, check=True,
                             cwd=DESTINO.parent).stdout.strip()
        texto += f"\n---\n\n*Gerado de `CATALOGO_NBR6123` em {sha}.*\n"
    except Exception:
        texto += "\n"

    DESTINO.write_text(texto, encoding="utf-8")
    print(f"escrito: {DESTINO}  ({len(texto.splitlines())} linhas)")
    print(f"por confirmar: {len(itens_nbr_nao_confirmados())}"
          f" / {len(CATALOGO_NBR6123)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
