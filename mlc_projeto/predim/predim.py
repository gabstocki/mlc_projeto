"""
predim/predim.py — Pré-dimensionamento por varredura paramétrica.

Varre combinações (h0, alpha, b) e retorna mapa de utilização η.
"""

import numpy as np
from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.loads     import Carregamentos


def pre_dimensionar(
    geo:  GeometriaViga,
    mat:  GlulamMaterial,
    load: Carregamentos,
) -> dict:
    """
    Verificação expedita de pré-dimensionamento.

    Verifica flexão, cisalhamento e flecha na geometria fornecida.
    Retorna taxa de utilização máxima e status de cada verificação.

    Referências:
        EC5 §6.1.6 (flexão), §6.1.7 (cisalhamento), Tab. 7.2 (flecha)
    """
    # TODO: implementar verificações expeditas
    raise NotImplementedError("predim.pre_dimensionar — a implementar")
