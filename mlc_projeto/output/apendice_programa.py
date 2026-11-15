"""
output/apendice_programa.py — Dados do Apêndice A gerados na execução (issue 121).

  · tab_ap_modulos.tex: arquivos e linhas por pacote, contados no próprio código
    (antes a tabela era escrita à mão e divergia de \\nArquivosCodigo); a suíte de
    testes aparece à parte e não entra no total do programa;
  · macros de identificação da versão: commit, data e se a árvore de trabalho tem
    alterações não registradas no momento da execução;
  · classificação dos testes: de integração (executam o pipeline completo) e
    unitários, mais os casos de referência independentes (output/validacao.py).
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

PACOTES = [
    ("core", "core", "Geometria paramétrica, material, ações, vento, proveniência normativa e validação de domínio"),
    ("predim", "predim", "Varredura paramétrica do espaço de geometrias"),
    ("checks/elu", "checks/elu", "Verificações de estado-limite último de elementos e sistemas"),
    ("checks/els", "checks/els", "Verificações de estado-limite de serviço"),
    ("connections", "connections", "Ligações, chapas metálicas, bases e ancoragem"),
    ("output", "output", "Memorial, tabelas, figuras, desenhos, apêndices gerados, validação e custo"),
    ("opensees", "opensees", "Modelos de elementos finitos independentes (viga, diafragma)"),
    ("visualization", "visualization", "Visualização tridimensional do modelo"),
    ("main.py", "main.py", "Orquestração do \\textit{pipeline} e dados de projeto"),
]


def _linhas(p: Path) -> int:
    return len(p.read_text(encoding="utf-8", errors="ignore").splitlines())


def contar_por_pacote(raiz: Path) -> list[tuple[str, int, int, str]]:
    pkg = raiz / "mlc_projeto"
    todos = sorted(pkg.rglob("*.py"))
    usados: set[Path] = set()
    linhas = []
    for nome, rel, desc in PACOTES:
        alvo = pkg / rel
        arqs = [alvo] if alvo.is_file() else sorted(alvo.rglob("*.py"))
        usados.update(arqs)
        linhas.append((nome, len(arqs), sum(_linhas(a) for a in arqs), desc))
    resto = [a for a in todos if a not in usados]                 # __init__ de raiz
    if resto:
        linhas.append(("\\_\\_init\\_\\_", len(resto), sum(_linhas(a) for a in resto),
                       "Inicialização dos pacotes"))
    return linhas


def tabela_modulos(raiz: Path) -> str:
    rows = contar_por_pacote(raiz)
    n = sum(r[1] for r in rows)
    lin = sum(r[2] for r in rows)
    tests = sorted((raiz / "tests").glob("*.py"))
    f = lambda x: f"{x:,}".replace(",", ".")
    L = ["% tab_ap_modulos.tex — GERADA por mlc_projeto/output/apendice_programa.py (issue 121). NÃO EDITAR À MÃO.",
         r"\tabela{Pacotes do programa e respectivas responsabilidades}{\footnotesize",
         r"\begin{tabular}{lcrp{5.6cm}}", r"\toprule",
         r"    \textbf{Pacote} & \textbf{Arq.} & \textbf{Linhas} & \textbf{Responsabilidade} \\",
         r"\midrule"]
    for nome, na, nl, desc in rows:
        L.append(f"    \\texttt{{{nome}}} & {na} & {f(nl)} & {desc} \\\\")
    L += [r"\midrule",
          f"    \\textbf{{Total do programa}} & \\textbf{{{n}}} & \\textbf{{{f(lin)}}} & \\\\",
          r"\addlinespace",
          f"    \\texttt{{tests}} & {len(tests)} & {f(sum(_linhas(t) for t in tests))} & "
          "Suíte de testes, fora do total do programa \\\\",
          r"\bottomrule", r"\end{tabular}}{Elaborado pelo autor (2026)}{ap-modulos}{}{}", ""]
    return "\n".join(L)


def _git(raiz: Path, *args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=raiz, capture_output=True, text=True,
                              timeout=30).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def identificacao_versao(raiz: Path) -> dict:
    h = _git(raiz, "rev-parse", "--short=10", "HEAD")
    data = _git(raiz, "log", "-1", "--format=%cs")
    tag = _git(raiz, "describe", "--tags", "--exact-match")
    # alterações em arquivos rastreados ou novos, fora das saídas que o próprio
    # pipeline regenera (tese/, output/)
    st = [l for l in _git(raiz, "status", "--porcelain").splitlines()
          if not re.search(r"\s(tese|output)/", l)]
    return {"commit": h or "indisponível", "data": data or "--", "tag": tag,
            "limpo": not st, "n_alterados": len(st)}


def classificar_testes(raiz: Path) -> dict:
    try:
        out = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q"],
                             cwd=raiz, capture_output=True, text=True, timeout=300).stdout
    except (OSError, subprocess.SubprocessError):
        return {}
    ids = [l for l in out.splitlines() if "::" in l]
    integ_arqs = {p.name for p in (raiz / "tests").glob("*.py")
                  if "_main_impl" in p.read_text(encoding="utf-8", errors="ignore")}
    n_int = sum(1 for i in ids if Path(i.split("::")[0]).name in integ_arqs)
    return {"total": len(ids), "integracao": n_int, "unitarios": len(ids) - n_int}


def macros_programa(raiz: Path, n_referencias: int) -> str:
    v = identificacao_versao(raiz)
    c = classificar_testes(raiz)
    estado = ("sem alterações locais além das saídas regeneradas" if v["limpo"]
              else f"com {v['n_alterados']} arquivos alterados ainda não registrados")
    L = [f"\\newcommand{{\\versaoCommit}}{{{v['commit']}}}",
         f"\\newcommand{{\\versaoData}}{{{v['data']}}}",
         f"\\newcommand{{\\versaoTag}}{{{v['tag'] or 'sem etiqueta'}}}",
         f"\\newcommand{{\\versaoEstado}}{{{estado}}}",
         f"\\newcommand{{\\nCasosReferencia}}{{{n_referencias}}}"]
    if c:
        L += [f"\\newcommand{{\\nTestesIntegracao}}{{{c['integracao']}}}",
              f"\\newcommand{{\\nTestesUnitarios}}{{{c['unitarios']}}}"]
    return "\n".join(L) + "\n"


def gerar_apendice_programa(tese: Path, raiz: Path, n_referencias: int) -> str:
    (Path(tese) / "tab_ap_modulos.tex").write_text(tabela_modulos(raiz), encoding="utf-8")
    return macros_programa(raiz, n_referencias)
