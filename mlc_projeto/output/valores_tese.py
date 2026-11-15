"""
output/valores_tese.py — Números da tese gerados pela execução do pipeline (issue 99).

O orientador apontou contagens divergentes entre o resumo e os capítulos
(verificações 64 / 55, testes 736 / 730, NDP 18 / 19). Eram números digitados,
que envelheciam a cada alteração do programa. Este módulo os escreve a partir da
mesma execução que gera os apêndices:

  · tese/valores_pipeline.tex — macros \\nVerif, \\nVerifExec, \\nVerifNA, \\nNDP,
    \\nTestes (algarismos) e as variantes por extenso (\\nVerifExt, ...), além de
    \\etaMaxGlobal;
  · tese/tab_ndp.tex — a tabela dos parâmetros de determinação nacional, lida do
    registro `core.normativo.parametros_ndp()`, o mesmo que o programa declara em
    toda saída de cálculo.

Não editar os .tex à mão.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from mlc_projeto.core.normativo import parametros_ndp
from mlc_projeto.output.formatacao import fmt_eta

_UNID = ("zero", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito", "nove",
         "dez", "onze", "doze", "treze", "quatorze", "quinze", "dezesseis", "dezessete",
         "dezoito", "dezenove")
_DEZ = ("", "", "vinte", "trinta", "quarenta", "cinquenta", "sessenta", "setenta",
        "oitenta", "noventa")
_CEN = ("", "cento", "duzentos", "trezentos", "quatrocentos", "quinhentos", "seiscentos",
        "setecentos", "oitocentos", "novecentos")


def por_extenso(n: int, feminino: bool = False) -> str:
    """Inteiro de 0 a 999 por extenso, no gênero do substantivo contado."""
    if not 0 <= n <= 999:
        raise ValueError("por_extenso: 0 ≤ n ≤ 999")
    if n < 20:
        u = _UNID[n]
        return {"um": "uma", "dois": "duas"}.get(u, u) if feminino else u
    if n < 100:
        d, u = divmod(n, 10)
        return _DEZ[d] + (f" e {por_extenso(u, feminino)}" if u else "")
    if n == 100:
        return "cem"
    c, r = divmod(n, 100)
    cen = _CEN[c]
    if feminino and c >= 2:
        cen = cen.replace("entos", "entas")
    return cen + (f" e {por_extenso(r, feminino)}" if r else "")


def contar_testes(raiz: Path) -> int | None:
    """Número de testes coletados pelo pytest (None se a coleta falhar)."""
    try:
        out = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q"],
                             cwd=raiz, capture_output=True, text=True, timeout=300).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    m = re.search(r"(\d+) tests? collected", out)
    return int(m.group(1)) if m else None


#: Rótulo e cláusula de cada NDP na tabela da tese (ordem de apresentação).
_ROTULOS_NDP = {
    "gamma_G_sup":          (r"$\gamma_G$ desfavorável", "EN 1990, tab. A1.2(B)"),
    "gamma_G_inf":          (r"$\gamma_G$ favorável", "EN 1990, tab. A1.2(B)"),
    "gamma_G_EQU_estab":    (r"$\gamma_G$ estabilizante, EQU", "EN 1990, tab. A1.2(A)"),
    "gamma_G_EQU_desestab": (r"$\gamma_G$ desestabilizante, EQU", "EN 1990, tab. A1.2(A)"),
    "gamma_Q":              (r"$\gamma_Q$", "EN 1990, tab. A1.2(B)"),
    "psi_0_Q":              (r"$\psi_0$ sobrecarga", "EN 1990, tab. A1.1, categoria H"),
    "psi_1_Q":              (r"$\psi_1$ sobrecarga", "EN 1990, tab. A1.1, categoria H"),
    "psi_2_Q":              (r"$\psi_2$ sobrecarga", "EN 1990, tab. A1.1, categoria H"),
    "psi_0_W":              (r"$\psi_0$ vento", "EN 1990, tab. A1.1"),
    "psi_2_W":              (r"$\psi_2$ vento", "EN 1990, tab. A1.1"),
    "gamma_M_madeira":      (r"$\gamma_M$ madeira", "EN 1995-1-1, tab. 2.3"),
    "gamma_M_ligacao":      (r"$\gamma_M$ ligação", "EN 1995-1-1, tab. 2.3"),
    "k_cr":                 (r"$k_{cr}$", "EN 1995-1-1, item 6.1.7"),
    "k_s_contravento":      (r"$k_s$ do contraventamento", "EN 1995-1-1, tab. 9.2"),
    "k_f_2":                (r"$k_{f,2}$ do contraventamento", "EN 1995-1-1, tab. 9.2"),
    "k_f_3":                (r"$k_{f,3}$ do contraventamento", "EN 1995-1-1, tab. 9.2"),
    "gamma_M_fi":           (r"$\gamma_{M,fi}$", "EN 1995-1-2, item 2.3(1)"),
    "alpha_cc":             (r"$\alpha_{cc}$", "EN 1992-1-1, item 3.1.6(1)"),
    "gamma_C":              (r"$\gamma_C$", "EN 1992-1-1, tab. 2.1N"),
    "alpha_cr_min":         (r"$\alpha_{cr}$ mínimo", "EN 1993-1-1, item 5.2.1(3), por analogia"),
}


def _valor(v) -> str:
    if isinstance(v, (int, float)):
        x = float(v)
        s = f"{x:.1f}" if x >= 10 else f"{x:.2f}"
        return s.replace(".", ",")
    return str(v)


def tabela_ndp() -> str:
    ndp = parametros_ndp()
    faltam = set(ndp) - set(_ROTULOS_NDP)
    if faltam:
        raise KeyError(f"NDP sem rótulo na tabela da tese: {sorted(faltam)}")
    L = ["% tab_ndp.tex — GERADA por mlc_projeto/output/valores_tese.py a partir de "
         "core.normativo.parametros_ndp(). NÃO EDITAR À MÃO.",
         r"\tabela", r"{Parâmetros de determinação nacional adotados}", r"{\scriptsize",
         r"\begin{tabular}{lrl}", r"\toprule",
         r"    \textbf{Parâmetro} & \textbf{Valor} & \textbf{Cláusula de origem} \\",
         r"\midrule"]
    for k, (rot, cl) in _ROTULOS_NDP.items():
        if k in ndp:
            L.append(f"    {rot} & {_valor(ndp[k].valor)} & {cl} \\\\")
    L += [r"\bottomrule", r"\end{tabular}}", r"{Elaborado pelo autor (2026)}", r"{ndp}",
          r"{}", r"{}", ""]
    return "\n".join(L)


def contar_codigo(raiz: Path) -> tuple[int, int]:
    """Arquivos .py e linhas do pacote mlc_projeto (Apêndice A)."""
    arqs = sorted((raiz / "mlc_projeto").rglob("*.py"))
    linhas = sum(len(a.read_text(encoding="utf-8", errors="ignore").splitlines()) for a in arqs)
    return len(arqs), linhas


def macros(*, n_verif: int, n_exec: int, n_na: int, eta_max: float,
           n_testes: int | None, n_ndp: int) -> str:
    def m(nome, val):
        return f"\\newcommand{{\\{nome}}}{{{val}}}"
    L = ["% valores_pipeline.tex — GERADO por mlc_projeto/output/valores_tese.py na "
         "execução do pipeline. NÃO EDITAR À MÃO.",
         m("nVerif", n_verif), m("nVerifExt", por_extenso(n_verif, True)),
         m("nVerifExec", n_exec), m("nVerifExecExt", por_extenso(n_exec, True)),
         m("nVerifNA", n_na), m("nVerifNAExt", por_extenso(n_na, True)),
         m("nNDP", n_ndp), m("nNDPExt", por_extenso(n_ndp)),
         m("etaMaxGlobal", fmt_eta(eta_max))]
    if n_testes is not None:
        L.append(m("nTestes", f"{n_testes:,}".replace(",", ".")))
    return "\n".join(L) + "\n"


def gerar_valores_tese(*, tese: Path, n_verif: int, n_exec: int, n_na: int,
                       eta_max: float, contar: bool = True, extra: str = "") -> dict:
    """Escreve valores_pipeline.tex e tab_ndp.tex; preserva \\nTestes se a coleta falhar."""
    raiz = tese.parent
    n_testes = contar_testes(raiz) if contar else None
    arq = tese / "valores_pipeline.tex"
    if n_testes is None and arq.exists():
        m = re.search(r"\\nTestes\}\{([\d.]+)\}", arq.read_text(encoding="utf-8"))
        n_testes = int(m.group(1).replace(".", "")) if m else None
    n_ndp = len(parametros_ndp())
    n_arq, n_lin = contar_codigo(raiz)
    extra = (f"\\newcommand{{\\nArquivosCodigo}}{{{n_arq}}}\n"
             f"\\newcommand{{\\nLinhasCodigo}}{{{n_lin:,}}}\n".replace(",", ".")) + extra
    arq.write_text(macros(n_verif=n_verif, n_exec=n_exec, n_na=n_na, eta_max=eta_max,
                          n_testes=n_testes, n_ndp=n_ndp) + extra, encoding="utf-8")
    (tese / "tab_ndp.tex").write_text(tabela_ndp(), encoding="utf-8")
    return {"n_verif": n_verif, "n_exec": n_exec, "n_na": n_na, "n_testes": n_testes,
            "n_ndp": n_ndp}
