"""
connections/connections.py — Dimensionamento de ligações por pinos.

Implementa teoria de Johansen (modos I–IV) e cálculo de n_ef.

Referência: EC5 §8.2, §8.3.1.1 (n_ef), §8.3.1.2 (distâncias mínimas)
"""

import numpy as np
from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.loads     import Carregamentos


def johansen(
    mat:     GlulamMaterial,
    d:       float,
    t1:      float,
    t2:      float,
    f_u_k:   float = 400e6,
) -> dict:
    """
    Capacidade de carga lateral de um pino — todos os modos de Johansen.
    (EC5 §8.2)

    Args:
        d    : Diâmetro do pino (m)
        t1   : Espessura do elemento lateral (m)
        t2   : Espessura do elemento central (m)
        f_u_k: Resistência última do aço (Pa), default 400 MPa

    Returns:
        dict com F_v_Rk por modo (N) e modo governante
    """
    # TODO: implementar modos I–IV de Johansen
    raise NotImplementedError("connections.johansen — a implementar")


def n_ef(n: int, a1: float, d: float) -> float:
    """
    Número efetivo de pinos em linha (EC5 §8.3.1.1).

    n_ef = n^0,9 · (a1 / 13d)^(1/4)

    Args:
        n  : Número de pinos na linha
        a1 : Espaçamento entre pinos na direção da fibra (m)
        d  : Diâmetro do pino (m)
    """
    return n ** 0.9 * (a1 / (13 * d)) ** 0.25


def dimensionar_ligacao(
    geo:  GeometriaViga,
    mat:  GlulamMaterial,
    load: Carregamentos,
) -> dict:
    """
    Dimensiona a ligação viga-pilar ou viga-fundação.

    Returns:
        dict com n_pinos, n_ef, R_grupo (N), distâncias mínimas e ok
    """
    # TODO: implementar
    raise NotImplementedError(
        "connections.dimensionar_ligacao — a implementar"
    )
