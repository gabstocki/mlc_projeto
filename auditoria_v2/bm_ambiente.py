"""
BM-16 — Os resultados do memorial dependem da versão das bibliotecas?

[F-19] O projeto declarava `numpy>=1.26` — um intervalo sem teto, que abrange
uma fronteira de major. A pergunta que importa num memorial de cálculo não é se
a suíte passa: é se os NÚMEROS mudam. Um memorial cujos η dependem da versão do
NumPy instalado não é rastreável.

Este benchmark corre o pipeline completo em cada interpretador disponível, em
subprocessos isolados, e compara os η um a um em igualdade EXATA (não
aproximada: qualquer diferença é sinal de que o resultado depende do ambiente).

NOTA DE INDEPENDÊNCIA: aqui o objeto sob teste é a própria saída do repositório
em ambientes distintos, logo executá-lo é o ponto. O que tem de ser independente
— a comparação — está escrito aqui e não usa nada do repositório.

Uso:
    python auditoria_v2/bm_ambiente.py [interpretador ...]
Sem argumentos, usa o interpretador corrente e ./.venv/bin/python, se existir.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]

# Executado dentro de cada interpretador. Não imprime nada além do JSON.
SONDA = r'''
import contextlib, io, json, sys
import importlib.metadata as md
import mlc_projeto.main as M
M.gerar_relatorio = lambda *a, **k: {}
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    r = M._main_impl(rodar_varredura=False, abrir_viz=False)
etas = {}
for nome, res in r.items():
    if nome == "meta" or not isinstance(res, dict):
        continue
    v = res.get("eta")
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        etas[nome] = repr(float(v))          # repr: comparação bit-a-bit
pacotes = {}
for nome in ("numpy", "scipy", "pandas", "matplotlib", "sympy", "openpyxl"):
    try:
        pacotes[nome] = md.version(nome)
    except Exception:
        pacotes[nome] = "ausente"
print("@@JSON@@" + json.dumps({
    "python": sys.version.split()[0],
    "executavel": sys.executable,
    "pacotes": pacotes,
    "status": r["meta"].get("status"),
    "eta_max": repr(float(r["meta"].get("eta_max", float("nan")))),
    "etas": etas,
}))
'''


def sondar(interpretador: str) -> dict:
    proc = subprocess.run(
        [interpretador, "-c", SONDA],
        capture_output=True, text=True, cwd=RAIZ,
        env={"PYTHONPATH": str(RAIZ), "PATH": "/usr/bin:/bin", "HOME": str(pathlib.Path.home()),
             "MPLBACKEND": "Agg"},
    )
    if proc.returncode != 0:
        raise RuntimeError(f"{interpretador} falhou:\n{proc.stderr[-2000:]}")
    marca = proc.stdout.rindex("@@JSON@@") + len("@@JSON@@")
    return json.loads(proc.stdout[marca:])


def main(argv: list[str]) -> int:
    alvos = argv[1:]
    if not alvos:
        alvos = [sys.executable]
        venv = RAIZ / ".venv" / "bin" / "python"
        if venv.exists() and str(venv) != sys.executable:
            alvos.append(str(venv))

    print("=" * 78)
    print("BM-16 — INVARIÂNCIA DOS RESULTADOS FACE AO AMBIENTE")
    print("=" * 78)

    if len(alvos) < 2:
        print("Só um interpretador disponível — nada a comparar.")
        print("Passe dois ou mais caminhos como argumento.")
        return 2

    amostras = []
    for alvo in alvos:
        d = sondar(alvo)
        amostras.append(d)
        print(f"\n{d['executavel']}")
        print(f"  Python {d['python']}")
        print("  " + ", ".join(f"{k} {v}" for k, v in d["pacotes"].items()))
        print(f"  status={d['status']}  η_max={d['eta_max']}  ({len(d['etas'])} η)")

    base = amostras[0]
    falhas: list[str] = []
    print("\n" + "-" * 78)
    for outra in amostras[1:]:
        rot = f"{base['pacotes']['numpy']} vs {outra['pacotes']['numpy']}"
        so_base = set(base["etas"]) - set(outra["etas"])
        so_outra = set(outra["etas"]) - set(base["etas"])
        if so_base or so_outra:
            falhas.append(f"conjunto de verificações difere ({rot}): "
                          f"{sorted(so_base)} / {sorted(so_outra)}")
        comuns = sorted(set(base["etas"]) & set(outra["etas"]))
        difs = [k for k in comuns if base["etas"][k] != outra["etas"][k]]
        for k in difs:
            falhas.append(f"{k}: {base['etas'][k]} vs {outra['etas'][k]}  ({rot})")
        if base["eta_max"] != outra["eta_max"]:
            falhas.append(f"η_max: {base['eta_max']} vs {outra['eta_max']}  ({rot})")
        if base["status"] != outra["status"]:
            falhas.append(f"status: {base['status']} vs {outra['status']}  ({rot})")
        print(f"numpy {rot}: {len(comuns)} η comparados em igualdade EXATA, "
              f"{len(difs)} divergentes")

    print("=" * 78)
    if falhas:
        print(f"BM-16: {len(falhas)} DIVERGÊNCIA(S) — o memorial depende do ambiente")
        for f in falhas:
            print(f"  ✗ {f}")
    else:
        n = len(base["etas"])
        print(f"BM-16: os {n} η e o veredito são BIT-IDÊNTICOS em todos os")
        print(f"       ambientes ensaiados. O memorial é reprodutível no")
        print(f"       intervalo declarado em pyproject.toml.")
    print("=" * 78)
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
