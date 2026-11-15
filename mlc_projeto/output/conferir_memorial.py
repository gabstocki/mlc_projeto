"""
output/conferir_memorial.py — Confere a aritmética impressa no Apêndice B (issue 115).

Cada linha de equação do memorial tem a forma
    símbolo &= fórmula simbólica = expressão numérica = resultado
O conferidor converte os trechos puramente numéricos de LaTeX para Python e
verifica se a expressão numérica, avaliada com os números impressos, reproduz o
resultado impresso, dentro do arredondamento. Trechos com símbolos são ignorados.

Uso: python -m mlc_projeto.output.conferir_memorial [tese/apendiceB.tex]
"""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path

_RE_ALIGN = re.compile(r"\\begin\{align\}(.*?)\\end\{align\}", re.S)


def _chaves(s: str, i: int) -> tuple[str, int]:
    """Conteúdo do grupo {…} que começa em s[i] == '{'; devolve (conteúdo, fim)."""
    assert s[i] == "{"
    n, j = 0, i
    while j < len(s):
        if s[j] == "{":
            n += 1
        elif s[j] == "}":
            n -= 1
            if n == 0:
                return s[i + 1:j], j + 1
        j += 1
    raise ValueError("chaves desbalanceadas")


def _macro(s: str, nome: str, fn) -> str:
    """Substitui \\nome{a}{b}… pelo resultado de fn(args)."""
    while True:
        k = s.find(nome)
        if k < 0:
            return s
        j = k + len(nome)
        args = []
        idx = None
        if nome == "\\sqrt" and j < len(s) and s[j] == "[":
            f = s.index("]", j)
            idx = s[j + 1:f]
            j = f + 1
        n_args = 2 if nome == "\\frac" else 1
        for _ in range(n_args):
            a, j = _chaves(s, j)
            args.append(a)
        s = s[:k] + fn(args, idx) + s[j:]


def latex_para_python(t: str) -> str | None:
    """Converte um trecho numérico; None se contiver símbolos."""
    s = t.strip()
    s = re.sub(r"~?\\text\{[^}]*\}", "", s)
    s = re.sub(r"\\(nonumber|left|right|quad|,|;|!|displaystyle)", " ", s)
    s = re.sub(r"\\leq.*$|\\geq.*$|\\le\b.*$", "", s)
    s = re.sub(r"(\d)\.(\d{3})(?!\d)", r"\1\2", s)            # milhar 1.020 → 1020
    s = s.replace("{,}", ".")
    s = s.replace("\\times", "*").replace("\\cdot", "*")
    s = re.sub(r"\\(cos|sin|tan|operatorname\{tg\})\s*([0-9.]+)\s*\^\\circ",
               lambda m: f"{ {'cos': 'cos', 'sin': 'sin', 'tan': 'tan'}.get(m.group(1), 'tan')}(radians({m.group(2)}))", s)
    s = s.replace("^\\circ", "")
    s = _macro(s, "\\frac", lambda a, _: f"(({a[0]})/({a[1]}))")
    s = _macro(s, "\\sqrt", lambda a, i: f"(({a[0]})**(1/{i}))" if i else f"sqrt({a[0]})")
    s = re.sub(r"\\(min|max)\s*\{", lambda m: m.group(1) + "{", s)
    s = re.sub(r"(min|max)\{([^{}]*)\}", lambda m: f"{m.group(1)}({m.group(2).replace(';', ',')})", s)
    s = re.sub(r"\\(min|max)\s*\(", r"\1(", s)
    s = s.replace("{", "(").replace("}", ")").replace("[", "(").replace("]", ")")
    s = s.replace("^", "**").replace(";", ",")
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"([0-9.)])\s*(\(|sqrt|min|max|cos|sin|tan)", r"\1*\2", s)   # multiplicação implícita
    if not s or re.search(r"[A-Za-z_\\]", re.sub(r"\b(min|max|sqrt|cos|sin|tan|radians)\b", "", s)):
        return None
    return s


def _avaliar(expr: str) -> float:
    return float(eval(expr, {"__builtins__": {}},                   # noqa: S307
                      {"sqrt": math.sqrt, "cos": math.cos, "sin": math.sin, "tan": math.tan,
                       "radians": math.radians, "min": min, "max": max}))


def _tolerancia(impresso: str, valor: float) -> float:
    """Uma unidade da última casa impressa (as taxas são arredondadas para cima)
    + 0,6 % (os números de entrada também estão arredondados)."""
    m = re.search(r"\.(\d+)$", impresso.strip())
    casas = len(m.group(1)) if m else 0
    return 10 ** (-casas) + 0.006 * abs(valor)


def conferir(tex: str) -> list[dict]:
    """Devolve uma entrada por igualdade numérica conferida, com ok/erro."""
    saida = []
    for bloco in _RE_ALIGN.findall(tex):
        for linha in bloco.split("\\\\"):
            linha = re.sub(r"\\label\{[^}]*\}", "", linha).replace("&", "")
            partes = linha.split("=")
            conv = [latex_para_python(p) for p in partes]
            for a, b, ta, tb in zip(conv, conv[1:], partes, partes[1:]):
                if a is None or b is None or "," in b and not b.startswith(("min", "max")):
                    continue
                if not re.fullmatch(r"-?[0-9.]+", b):
                    continue                                       # só "expressão = número"
                try:
                    va, vb = _avaliar(a), float(b)
                except Exception:                                  # noqa: BLE001
                    continue
                if re.fullmatch(r"-?[0-9.]+", a):
                    continue                                       # número = número
                ok = abs(va - vb) <= _tolerancia(b, vb)
                saida.append({"expressao": ta.strip(), "impresso": tb.strip(),
                              "calculado": va, "ok": ok})
    return saida


def _cli() -> None:
    p = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("tese/apendiceB.tex")
    r = conferir(p.read_text(encoding="utf-8"))
    for x in r:
        if not x["ok"]:
            print(f"✗ {x['expressao'][:70]} = {x['impresso']}  (calculado {x['calculado']:.4g})")
    print(f"{sum(x['ok'] for x in r)}/{len(r)} igualdades conferidas")


if __name__ == "__main__":
    _cli()
