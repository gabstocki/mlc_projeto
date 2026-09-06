"""
core/validacao.py — Pré-condições de domínio dos dados de entrada.

Contexto normativo/metodológico
-------------------------------
Achado AUD-013 da auditoria técnica independente (severidade CRITICAL):

    "Não existe validação finita/positiva centralizada. Em ``verifica_pilar``,
    ``A<=0`` substitui o raio por ``1e-9`` e a tensão por zero. Dados fisicamente
    impossíveis entram nas equações; fallbacks numéricos transformam divisão por
    zero em demanda zero. [...] Seção nula possui rigidez e resistência nulas;
    nunca pode ser aprovada sob carga não nula."

Estas verificações são **anteriores** a qualquer regra do Eurocode ou da NBR:
são pré-condições matemáticas e de domínio do modelo. Uma seção de área nula,
um vão nulo ou um ângulo ``NaN`` não descrevem uma estrutura, e portanto não
podem produzir uma utilização ``η`` nem um veredito ``ok``.

Princípio adotado: **falhar alto, nunca compensar**. Não se usa ``max(x, eps)``
nem substituição por zero para tornar calculável uma geometria inexistente —
esse é exatamente o mecanismo que produz a falsa aprovação descrita em AUD-013.
"""

from __future__ import annotations

import math
from typing import SupportsFloat


class DominioInvalidoError(ValueError):
    """
    Entrada fora do domínio físico/matemático do modelo.

    Subclasse de ``ValueError`` para que o contrato já praticado no projeto
    (``GlulamMaterial`` rejeita classe GL inexistente com ``ValueError``) seja
    preservado e o chamador não precise distinguir os dois casos.
    """


def _como_float(nome: str, valor: SupportsFloat) -> float:
    try:
        return float(valor)
    except (TypeError, ValueError) as exc:
        raise DominioInvalidoError(
            f"{nome} = {valor!r} não é um número real."
        ) from exc


def exigir_finito(nome: str, valor: SupportsFloat) -> float:
    """Rejeita ``NaN`` e ``±inf``, que se propagam silenciosamente até o relatório."""
    v = _como_float(nome, valor)
    if not math.isfinite(v):
        raise DominioInvalidoError(
            f"{nome} = {v} não é finito. Valores NaN/inf propagam-se sem erro "
            f"pelas verificações e podem chegar ao relatório como aprovação."
        )
    return v


def exigir_positivo(nome: str, valor: SupportsFloat, *, unidade: str = "") -> float:
    """Grandeza estritamente positiva: dimensão, vão, rigidez, resistência."""
    v = exigir_finito(nome, valor)
    if v <= 0.0:
        u = f" {unidade}" if unidade else ""
        raise DominioInvalidoError(
            f"{nome} = {v}{u} deve ser estritamente positivo. Uma seção, vão ou "
            f"propriedade nula/negativa não possui rigidez nem resistência e não "
            f"pode ser verificada (AUD-013)."
        )
    return v


def exigir_nao_negativo(nome: str, valor: SupportsFloat, *, unidade: str = "") -> float:
    """Grandeza que admite zero (esforço, carga, excentricidade)."""
    v = exigir_finito(nome, valor)
    if v < 0.0:
        u = f" {unidade}" if unidade else ""
        raise DominioInvalidoError(f"{nome} = {v}{u} não pode ser negativo.")
    return v


def exigir_no_intervalo(
    nome: str,
    valor: SupportsFloat,
    *,
    minimo: float,
    maximo: float,
    incluir_minimo: bool = True,
    incluir_maximo: bool = True,
    unidade: str = "",
) -> float:
    """Grandeza com domínio de validade explícito (ângulos, relações geométricas)."""
    v = exigir_finito(nome, valor)
    ok_min = v >= minimo if incluir_minimo else v > minimo
    ok_max = v <= maximo if incluir_maximo else v < maximo
    if not (ok_min and ok_max):
        u = f" {unidade}" if unidade else ""
        ab, fe = ("[", "]") if incluir_minimo else ("(", ")")
        raise DominioInvalidoError(
            f"{nome} = {v}{u} fora do domínio {ab}{minimo}, {maximo}{fe}."
        )
    return v


def exigir_inteiro_minimo(nome: str, valor: int, *, minimo: int) -> int:
    """Contagens discretas: número de pontos de integração, de pilares, de pinos."""
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise DominioInvalidoError(f"{nome} = {valor!r} deve ser inteiro.")
    if valor < minimo:
        raise DominioInvalidoError(f"{nome} = {valor} deve ser >= {minimo}.")
    return valor
