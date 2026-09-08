"""
Testes de regressão — coerência entre o ambiente DECLARADO e o ambiente EXECUTADO.

Contexto normativo/metodológico
-------------------------------
A auditoria técnica independente (AUD-019, seções R e U/P2) registra que o
projeto declara ``requires-python = ">=3.10"`` e ``numpy>=1.26`` enquanto o
código-fonte usa construções que só existem em versões superiores. Um memorial
de cálculo estrutural só é rastreável se o ambiente declarado for exatamente o
ambiente em que os resultados foram produzidos: uma declaração que o
interpretador não consegue satisfazer torna qualquer artefato (PDF/XLSX/CSV)
irreprodutível.

Duas não-conformidades foram tratadas na Onda 0:

NC-01  ``np.trapezoid`` só existe em NumPy >= 2.0, mas o floor declarado era
       ``numpy>=1.26``. Em NumPy 1.26.4 a suíte falhava em 123 testes com
       ``AttributeError: module 'numpy' has no attribute 'trapezoid'``.
       Correção: usar ``scipy.integrate.trapezoid`` (mesma regra do trapézio,
       equivalência bit-a-bit verificada, e ``scipy`` já era dependência
       declarada e já era a biblioteca de integração do projeto).

NC-02  ``report.py``/``pilares.py``/``connections.py`` usam f-strings PEP 701
       (aspas iguais aninhadas no campo de substituição), aceitas apenas a
       partir de Python 3.12, contra um floor declarado de 3.10.
       Correção: declarar ``requires-python = ">=3.12"`` — a versão em que o
       projeto é efetivamente exercitado. Declarar 3.10/3.11 sem interpretador
       disponível para testá-los seria manter uma afirmação não verificável,
       exatamente o defeito apontado pela auditoria.

Os testes abaixo impedem que as duas declarações voltem a divergir do código.
"""

from __future__ import annotations

import ast
import compileall
import importlib
import io
import pkgutil
import sys
import tokenize
import tomllib
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import Version

import mlc_projeto

RAIZ = Path(__file__).resolve().parents[1]
PYPROJECT = RAIZ / "pyproject.toml"
PACOTE = RAIZ / "mlc_projeto"


# ── Leitura dos metadados declarados ──────────────────────────────────────────

def _pyproject() -> dict:
    with PYPROJECT.open("rb") as fh:
        return tomllib.load(fh)


def _floor_python() -> tuple[int, ...]:
    """Menor versão de Python admitida por ``requires-python``."""
    spec = _pyproject()["project"]["requires-python"]
    for clausula in spec.split(","):
        clausula = clausula.strip()
        if clausula.startswith(">="):
            return tuple(int(p) for p in clausula[2:].strip().split("."))
    raise AssertionError(
        f"requires-python = {spec!r} não declara um limite inferior '>=X.Y'. "
        "Sem floor explícito não há ambiente declarado auditável."
    )


def _arquivos_py() -> list[Path]:
    return sorted(PACOTE.rglob("*.py"))


# ── Detector de sintaxe PEP 701 (Python >= 3.12) ──────────────────────────────

def _quote_de(token_str: str) -> str:
    """Extrai o delimitador de um token de string, ignorando prefixos (f, r, b…)."""
    i = 0
    while i < len(token_str) and token_str[i] not in "\"'":
        i += 1
    resto = token_str[i:]
    for q in ('"""', "'''", '"', "'"):
        if resto.startswith(q):
            return q
    return ""


def _ocorrencias_pep701(fonte: str) -> list[int]:
    """
    Linhas com f-strings PEP 701 — aspas iguais às da própria f-string
    reutilizadas dentro do campo de substituição, p.ex.::

        f'{d.get('chave'):.2f}'

    Construção inválida até Python 3.11 (SyntaxError) e aceita a partir de 3.12.
    O detector cobre esse caso, que é o efetivamente presente no repositório;
    não cobre as demais liberalizações da PEP 701 (barra invertida na expressão,
    f-string multilinha aninhada).
    """
    linhas: list[int] = []
    pilha: list[str] = []
    tokens = tokenize.generate_tokens(io.StringIO(fonte).readline)
    for tok in tokens:
        if tok.type == tokenize.FSTRING_START:
            pilha.append(_quote_de(tok.string))
        elif tok.type == tokenize.FSTRING_END:
            if pilha:
                pilha.pop()
        elif tok.type == tokenize.STRING and pilha:
            if _quote_de(tok.string) == pilha[-1]:
                linhas.append(tok.start[0])
    return linhas


def test_detector_pep701_nao_e_vacuo():
    """
    Auto-teste do detector: um detector que nunca detecta faria os testes
    seguintes passarem por vacuidade.
    """
    positivo = "x = f'{d.get('k'):.2f}'\n"
    negativo = "x = f'{d.get(\"k\"):.2f}'\ny = f\"{a}{b}\"\nz = 'simples'\n"
    assert _ocorrencias_pep701(positivo) == [1]
    assert _ocorrencias_pep701(negativo) == []


# ── NC-02 — Python declarado × sintaxe usada ──────────────────────────────────

def test_interpretador_satisfaz_requires_python():
    floor = _floor_python()
    atual = sys.version_info[: len(floor)]
    assert atual >= floor, (
        f"Interpretador {'.'.join(map(str, atual))} abaixo do floor declarado "
        f"{'.'.join(map(str, floor))}. Resultados gerados aqui não são rastreáveis."
    )


def test_sintaxe_usada_nao_excede_o_floor_declarado():
    """
    Se o código usa f-strings PEP 701, ``requires-python`` deve declarar >= 3.12.
    Falha tanto se a sintaxe subir quanto se o floor descer.
    """
    floor = _floor_python()
    achados: dict[str, list[int]] = {}
    for arq in _arquivos_py():
        linhas = _ocorrencias_pep701(arq.read_text(encoding="utf-8"))
        if linhas:
            achados[str(arq.relative_to(RAIZ))] = linhas

    if achados and floor < (3, 12):
        amostra = "; ".join(f"{k}:{v[:3]}" for k, v in list(achados.items())[:3])
        pytest.fail(
            f"requires-python declara >={'.'.join(map(str, floor))} mas há "
            f"f-strings PEP 701 (Python >= 3.12) em {len(achados)} arquivo(s): "
            f"{amostra}. Corrija a sintaxe ou eleve o floor declarado."
        )


def test_pacote_compila_no_interpretador_declarado():
    """Smoke test de compilação — equivalente a ``python -m compileall``."""
    ok = compileall.compile_dir(
        str(PACOTE), quiet=2, force=True, legacy=False, workers=1
    )
    assert ok, "Falha de compilação em mlc_projeto/ — ver saída do compileall."


def test_todos_os_modulos_importam():
    """
    Import smoke test: nenhum módulo do pacote pode falhar na importação.
    Cobre imports quebrados e dependências ausentes na declaração.
    """
    falhas: list[str] = []
    for mod in pkgutil.walk_packages(mlc_projeto.__path__, prefix="mlc_projeto."):
        if ".opensees" in mod.name:
            continue  # openseespy é opcional e não consta das dependências (AUD-018/R)
        try:
            importlib.import_module(mod.name)
        except Exception as exc:  # noqa: BLE001 — queremos o diagnóstico agregado
            falhas.append(f"{mod.name}: {type(exc).__name__}: {exc}")
    assert not falhas, "Módulos que não importam:\n" + "\n".join(falhas)


# ── NC-01 — dependências declaradas × APIs efetivamente usadas ────────────────

def test_dependencias_instaladas_satisfazem_pyproject():
    from importlib.metadata import PackageNotFoundError, version

    falhas: list[str] = []
    for dep in _pyproject()["project"]["dependencies"]:
        req = Requirement(dep)
        try:
            instalada = version(req.name)
        except PackageNotFoundError:
            falhas.append(f"{req.name}: declarada em pyproject e não instalada")
            continue
        if not SpecifierSet(str(req.specifier)).contains(Version(instalada), prereleases=True):
            falhas.append(f"{req.name}: instalada {instalada}, declarada {req.specifier}")
    assert not falhas, "Ambiente diverge do declarado:\n" + "\n".join(falhas)


def test_nao_ha_uso_de_api_numpy_acima_do_floor_declarado():
    """
    Regressão direta de NC-01.

    ``numpy.trapezoid`` foi introduzido em NumPy 2.0 (renomeação de ``np.trapz``).
    Enquanto o floor declarado for ``numpy<2.0``, o código não pode referenciá-lo.
    A integração do projeto usa ``scipy.integrate.trapezoid``, idêntico em regra
    e resultado e independente da major do NumPy.
    """
    dep_numpy = next(
        Requirement(d) for d in _pyproject()["project"]["dependencies"]
        if Requirement(d).name == "numpy"
    )
    floor_2 = SpecifierSet(str(dep_numpy.specifier)).contains(Version("1.26.4"))

    if not floor_2:
        pytest.skip("floor de numpy já exclui 1.x — np.trapezoid seria admissível")

    ofensas: list[str] = []
    for arq in _arquivos_py():
        arvore = ast.parse(arq.read_text(encoding="utf-8"), filename=str(arq))
        for no in ast.walk(arvore):
            if (
                isinstance(no, ast.Attribute)
                and no.attr == "trapezoid"
                and isinstance(no.value, ast.Name)
                and no.value.id in {"np", "numpy"}
            ):
                ofensas.append(f"{arq.relative_to(RAIZ)}:{no.lineno}")

    assert not ofensas, (
        "numpy.trapezoid exige NumPy >= 2.0, acima do floor declarado "
        f"({dep_numpy.specifier}). Use scipy.integrate.trapezoid em: "
        + ", ".join(ofensas)
    )


def test_trapezoid_do_scipy_implementa_a_regra_do_trapezio():
    """
    [F-19] Verificação da equivalência que autoriza a substituição de NC-01.

    A versão anterior deste teste comparava ``scipy.integrate.trapezoid`` com
    ``numpy.trapz``. Isso tinha dois problemas:

    1. ``np.trapz`` foi REMOVIDO em NumPy 2.0. Como o intervalo declarado
       (``numpy>=1.26``) admite a 2.x, a suíte não passava no seu próprio
       intervalo declarado — era esse o achado F-19.
    2. Comparar uma biblioteca com o alias de outra biblioteca prova apenas
       que as duas concordam, não que alguma delas está certa.

    A referência passa a ser escrita aqui de raiz, com ``math.fsum``, que soma
    com arredondamento correto — é portanto uma referência MAIS exata do que
    qualquer das duas implementações vetorizadas. Não depende de nenhuma API
    do NumPy e vale em todas as majors.

    Tolerância: 1 ulp da escala de condicionamento Σ|Δx·(|y_i|+|y_{i+1}|)/2|.
    Medido: pior desvio 1,51e-16 (≈ 0,68 ulp), idêntico em NumPy 1.26.4 e
    2.4.6.
    """
    import math

    import numpy as np
    from scipy.integrate import trapezoid

    def referencia(y, x):
        """Regra composta do trapézio com soma de arredondamento correto."""
        return math.fsum((x[k + 1] - x[k]) * (y[k + 1] + y[k]) / 2.0
                         for k in range(len(x) - 1))

    def escala(y, x):
        """Condicionamento: soma dos módulos das contribuições."""
        return math.fsum(abs(x[k + 1] - x[k]) * (abs(y[k + 1]) + abs(y[k])) / 2.0
                         for k in range(len(x) - 1))

    rng = np.random.default_rng(20260906)
    pior = 0.0
    for _ in range(200):
        n = int(rng.integers(2, 400))
        x = np.sort(rng.uniform(-1.0e3, 1.0e3, n))
        y = rng.uniform(-1.0e6, 1.0e6, n)
        xs, ys = x.tolist(), y.tolist()
        obtido = float(trapezoid(y, x))
        exato = referencia(ys, xs)
        cond = escala(ys, xs)
        desvio = abs(obtido - exato) / cond if cond else 0.0
        pior = max(pior, desvio)
    assert pior <= 2.3e-16, f"desvio de {pior:.3e} excede 1 ulp da escala"


def test_nenhum_ficheiro_usa_api_removida_no_intervalo_declarado():
    """
    [F-19] O simétrico de ``test_nao_ha_uso_de_api_numpy_acima_do_floor``.

    Aquele guarda contra usar uma API que só existe ACIMA do intervalo
    declarado (``np.trapezoid``, NumPy >= 2.0). Faltava o outro lado: usar uma
    API que já não existe no TOPO do intervalo (``np.trapz``, removida na 2.0).
    Era por aí que o F-19 entrava — e entrava por um ficheiro de teste, que a
    guarda existente nem sequer varre.

    Ambos os lados são agora vigiados, no pacote **e** nos testes.
    """
    dep_numpy = next(
        Requirement(d) for d in _pyproject()["project"]["dependencies"]
        if Requirement(d).name == "numpy"
    )
    admite_2x = SpecifierSet(str(dep_numpy.specifier)).contains(Version("2.0.0"))
    if not admite_2x:
        pytest.skip("intervalo declarado exclui NumPy 2.x — np.trapz é admissível")

    ofensas: list[str] = []
    for arq in sorted(PACOTE.rglob("*.py")) + sorted((RAIZ / "tests").rglob("*.py")):
        arvore = ast.parse(arq.read_text(encoding="utf-8"), filename=str(arq))
        for no in ast.walk(arvore):
            if (
                isinstance(no, ast.Attribute)
                and no.attr == "trapz"
                and isinstance(no.value, ast.Name)
                and no.value.id in {"np", "numpy"}
            ):
                ofensas.append(f"{arq.relative_to(RAIZ)}:{no.lineno}")

    assert not ofensas, (
        f"numpy.trapz foi removido na NumPy 2.0, admitida pelo intervalo "
        f"declarado ({dep_numpy.specifier}). Use scipy.integrate.trapezoid "
        f"em: " + ", ".join(ofensas)
    )


def test_toda_dependencia_declara_limite_superior():
    """
    [F-19] Um intervalo sem teto não é um ambiente declarado.

    ``numpy>=1.26`` admite a 3.x, que não existe e não pode ser exercitada.
    Declarar o que não se consegue testar é a não-conformidade que AUD-019
    levantou — e foi assim que a suíte passou a falhar sozinha quando o venv
    do projeto avançou para a NumPy 2.4.6.

    O teto na major seguinte é a afirmação conservadora e verdadeira: «não
    verificado além daqui». Subi-lo exige exercitar o projeto na major nova.
    """
    sem_teto = []
    for dep in _pyproject()["project"]["dependencies"]:
        req = Requirement(dep)
        tem_teto = any(e.operator in ("<", "<=", "==", "~=")
                       for e in req.specifier)
        if not tem_teto:
            sem_teto.append(f"{req.name}{req.specifier}")
    assert not sem_teto, (
        "dependências sem limite superior — o ambiente declarado admite "
        "versões que nunca foram exercitadas: " + ", ".join(sem_teto)
    )
