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

Não é uma reprodução da NBR 6123:2023. A auditoria **não dispõe do texto da
norma** e a carta de auditoria proíbe preencher a lacuna de memória ou por
analogia com a edição de 1988.

É a lista fechada de **todos** os números do projeto que dependem da NBR 6123,
com o local exato no código, a cláusula que o código alega e — para cada item
por confirmar — a pergunta a fazer. Com a norma em mãos, fecha-se numa sessão.

## Porque isto importa em obra

O vento governa **toda** a estrutura metálica de contraventamento e a
verificação da telha. Um erro numa destas tabelas não produz um aviso: produz
um dimensionamento errado que passa em todos os testes. Daí a lista existir em
código (`itens_nbr_nao_confirmados()`), fazer falhar a suíte se um valor NBR
novo entrar sem registo, e ser impressa no cabeçalho do pipeline.

## Estado

| | |
|---|---|
| Itens catalogados | {len(CATALOGO_NBR6123)} |
| **Por confirmar** | **{len(itens_nbr_nao_confirmados())}** |
| Confirmados | {len(CATALOGO_NBR6123) - len(itens_nbr_nao_confirmados())} |

Dois estados apenas, deliberadamente: `CONFIRMADO` significa que o texto
literal foi obtido e transcrito. Tudo o resto é `NAO_CONFIRMADO` — «é o valor
de sempre» e «bate com a edição de 1988» não são fontes.

---

## A. Itens por confirmar

Para cada um: ler a cláusula na norma, comparar com o valor transcrito, e
depois marcar `estado="CONFIRMADO"` no catálogo (ou abrir achado, se divergir).
"""

RODAPE = """
---

## C. Verificação independente já realizada — BM-15

`auditoria_v2/bm_nbr_tabelas.py` lê as tabelas do código-fonte por análise
sintática (sem importar o repositório) e testa sete invariantes que um erro de
transcrição quebraria:

| | Invariante | Resultado |
|---|---|---|
| V1 | Tab. 1: b decresce e p cresce de I para V | OK |
| V2 | Tab. 1: p cresce de A para C | OK |
| V3 | Tab. 1: z_g cresce com a categoria, constante entre classes | OK |
| V4 | Tab. 2: F_r decresce de A para C | OK |
| V5 | **S2(z_g) igual nas cinco categorias** (vento gradiente) | **dispersão 0,72 %** |
| V6 | Tab. 25: os quatro ramos juntam-se em tg β = 0,4 sem salto | salto = 0 |
| V7 | Tab. 10: coerência de sinais e pico de sucção em θ = 10° | OK |

**V5 é a invariante forte.** Acima da camada limite o escoamento é geostrófico:
a velocidade não depende do terreno. Logo `S2(z_g) = b·F_r·(z_g/10)^p` tem de
dar o mesmo nas cinco categorias — o que liga três colunas independentes da
tabela. Dá 1,331 a 1,347, dispersão máxima 0,72 %.

Poder de deteção medido, perturbando um único valor:

| Perturbação | Dispersão resultante | |
|---|---|---|
| b(IV) +0,10 | 8,69 % | detetado |
| p(III) +0,020 | 6,02 % | detetado |
| z_g(II) +100 m | 1,75 % | **não detetado** (limite 2 %) |

**Limitação declarada:** z_g é a coluna mal policiada. b e p entram na
convergência com peso alto; z_g entra elevado a p (≈ 0,1) e um erro grosseiro
de 100 m ainda cabe dentro do limite. Confirmar z_g à vista, não por invariante.

### O que V1–V7 provam e o que não provam

**Provam** que a transcrição é uma tabela de camada-limite consistente: os
valores não foram inventados nem baralhados, e um erro futuro de edição não
passa em silêncio (as invariantes estão congeladas em
`tests/test_f18_proveniencia_nbr.py`).

**Não provam** fidelidade à edição :2023. Se a ABNT tiver revisto os
parâmetros em 2023, uma tabela revista seria igualmente coerente — e o
benchmark diria OK à mesma. A coerência interna não distingue edições.

## D. Numeração das tabelas — a inconsistência a esclarecer

O deslocamento de numeração alegado entre :1988 e :2023 não é uniforme:

| Conteúdo | Nº na :1988 (alegado) | Nº usado no código | Δ |
|---|---|---|---|
| Cobertura isolada duas águas | Tab. 18 | Tab. 25 | +7 |
| Telhados múltiplos | Tab. 6 | Tab. 10 | +4 |
| Parâmetros meteorológicos | Tab. 1 (com F_r) | Tab. 1 (sem F_r) + Tab. 2 | — |

O terceiro caso é o mais delicado: na :1988 b, p **e F_r** estão todos na
Tab. 1, e a Tab. 2 é o S2 tabelado. O código separa F_r numa «Tab. 2» e trata o
S2 tabelado por «Tab. 3» (`core/wind.py:144`). Ou a :2023 reorganizou a
apresentação, ou a citação está errada. **Só o texto decide.**

## E. Como fechar

1. Obter a NBR 6123:2023.
2. Percorrer a secção A deste anexo, item a item.
3. Para cada um que confira: `estado="CONFIRMADO"` no catálogo, com o texto
   literal na `evidencia`, à maneira do que já foi feito para o §7.2.2.
4. Para cada um que divirja: **abrir achado** — é um erro de dimensionamento,
   não um erro de documentação.
5. Regenerar este anexo e correr `pytest tests/test_f18_proveniencia_nbr.py`.
6. Quando a lista esvaziar, `aviso_nbr()` deixa de emitir a reserva sozinho.
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

    partes.append("---\n\n## B. Itens confirmados\n")
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
